"""U5 -- split-step MPS parabolic-equation propagator (the solver core).

Marches an acoustic field forward in range on the range-independent Munk
environment with a symmetric (Strang) split-step scheme:

    u(r + dr) = R_half . Diffraction . R_half . u(r)

- **Refraction** is diagonal in depth: the pointwise phase ``exp(i dr/(4 k0)
  ksq(z))`` from the local index, where ``ksq(z) = (omega/c(z))^2 - k0^2``. In
  the absorbing seabed ``ksq`` is complex (attenuation), so the operator's
  modulus is < 1 there and energy is suppressed rather than reflected.
- **Diffraction** is a Crank-Nicolson / (1,1)-Pade rational approximation of the
  depth operator ``exp(i dr/(2 k0) d^2/dz^2)`` -- the same rational-of-the-
  depth-operator family RAM's split-step Pade uses, here as the dense matrix
  ``(I - a D)^{-1} (I + a D)`` with ``a = i dr/(4 k0)`` and ``D`` the tridiagonal
  second difference.

The environment is range-independent, so the operators are built **once** and
reused every step; the diffraction MPO's bond dimension is therefore a fixed
instrument, reported alongside the state bond dimension chi(range) (R6).

Two marchers share the operators: :func:`march_dense` (no truncation -- the
trusted reference for a single step, per the U5 execution note) and
:func:`march_mps` (the MPS path, instrumented). All ``quimb`` calls are isolated
behind this module with lazy imports, mirroring ``mps_field`` / ``qrc_enso.qrc``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .environment import OceanEnvironment, munk_sound_speed
from .mps_field import decode_field, encode_field, state_chi

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quimb.tensor import MatrixProductOperator, MatrixProductState

# pyram's attenuation->wavenumber conversion factor (RAM's ``eta``): turns
# dB/wavelength into the imaginary part of the complex index. Reused here so the
# absorber is scaled the same way the reference solver scales it.
_ETA = 1.0 / (40.0 * np.pi * np.log10(np.e))
_ATTN_FLOOR = 10.0  # dB/wavelength at the very bottom of the absorbing layer


# --------------------------------------------------------------------------- #
# Range-independent split-step operators
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SplitStepOperators:
    """Range-independent refraction + diffraction operators on the QTT grid.

    ``refraction_half`` is the length-``Nz`` diagonal half-step phase;
    ``diffraction`` is the dense ``Nz x Nz`` Crank-Nicolson matrix. Both are
    fixed for the whole march (range-independent environment).
    """

    depth: np.ndarray  # canonical 2^n depth axis (m), length Nz
    refraction_half: np.ndarray  # diagonal half-step phase, length Nz
    diffraction: np.ndarray  # dense (Nz, Nz) Crank-Nicolson matrix
    c0: float  # reference sound speed (m/s)
    k0: float  # reference wavenumber (1/m)
    dz: float  # depth step (m)
    dr: float  # range step (m)


def _attenuation_profile(env: OceanEnvironment, z: np.ndarray) -> np.ndarray:
    """dB/wavelength attenuation: 0 in water, ramping up through the absorber.

    Zero in the water column; the seabed attenuation at the top of the absorbing
    layer ramping to a high floor at ``zmax`` so the layer soaks up downgoing
    energy before it reaches the (artificial) grid bottom -- mirroring pyram's
    ``profl`` absorber ramp.
    """
    attn = np.zeros_like(z)
    bottom = z > env.water_depth
    if bottom.any():
        # Linear ramp from seabed_attn (top of absorber) to _ATTN_FLOOR (zmax).
        span = env.zmax - env.water_depth
        frac = (z[bottom] - env.water_depth) / span
        attn[bottom] = env.seabed_attn + (_ATTN_FLOOR - env.seabed_attn) * frac
    return attn


def _ksq(env: OceanEnvironment, k0: float) -> np.ndarray:
    """Complex depth-wavenumber profile ``ksq(z) = (omega/c (1+i eta alpha))^2 - k0^2``.

    Real in the water column (no attenuation), complex in the absorbing seabed.
    A positive imaginary part makes the refraction phase decay (energy
    absorbed), the same sign convention pyram uses for ``ksqb``.
    """
    z = env.depth_grid()
    c = env.sound_speed_profile()
    omega = 2.0 * np.pi * env.freq
    attn = _attenuation_profile(env, z)
    index = (omega / c) * (1.0 + 1j * _ETA * attn)
    return index**2 - k0**2


def build_operators(
    env: OceanEnvironment,
    *,
    dr: float | None = None,
    c0: float | None = None,
) -> SplitStepOperators:
    """Build the range-independent split-step operators for ``env``.

    ``c0`` defaults to the mean water-column Munk speed (pyram's reference-speed
    convention); ``dr`` to pyram's default range step ``8 * 1500 / freq``. Pass
    the values from :class:`~mps_acoustics.pe_reference.StarterField` to march in
    pyram's exact reference frame.
    """
    z = env.depth_grid()
    nz = z.size
    dz = env.zmax / nz

    if c0 is None:
        water = z <= env.water_depth
        c0 = float(np.mean(munk_sound_speed(z[water])))
    if dr is None:
        dr = 8.0 * 1500.0 / env.freq

    omega = 2.0 * np.pi * env.freq
    k0 = omega / c0

    # Refraction: diagonal phase from the (complex) local index. Half-step for
    # the symmetric Strang split.
    ksq = _ksq(env, k0)
    refraction_half = np.exp(1j * dr / (4.0 * k0) * ksq)

    # Diffraction: Crank-Nicolson rational approximation of exp(i dr/(2 k0) D),
    # D the Dirichlet tridiagonal second difference. Built once (Nz x Nz dense).
    main = np.full(nz, -2.0)
    off = np.ones(nz - 1)
    d_op = (np.diag(off, 1) + np.diag(off, -1) + np.diag(main)) / dz**2
    a = 1j * dr / (4.0 * k0)
    eye = np.eye(nz)
    diffraction = np.linalg.solve(eye - a * d_op, eye + a * d_op)

    return SplitStepOperators(
        depth=z,
        refraction_half=refraction_half,
        diffraction=diffraction,
        c0=c0,
        k0=k0,
        dz=dz,
        dr=dr,
    )


# --------------------------------------------------------------------------- #
# Dense reference marcher (the U5 execution-note baseline)
# --------------------------------------------------------------------------- #
def dense_step(field: np.ndarray, ops: SplitStepOperators) -> np.ndarray:
    """One symmetric split-step applied densely (no truncation).

    ``R_half . Diffraction . R_half`` -- the trusted single-step reference the
    MPS step is validated against.
    """
    u = ops.refraction_half * np.asarray(field, dtype=complex)
    u = ops.diffraction @ u
    return ops.refraction_half * u


def march_dense(
    starter: np.ndarray,
    ops: SplitStepOperators,
    n_steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    """March a field densely for ``n_steps``, returning ``(field_grid, ranges)``.

    ``field_grid`` has shape ``(Nz, n_steps + 1)``; column 0 is the starter (range
    0) and column ``j`` is the field after ``j`` steps (range ``j * dr``).
    """
    u = np.asarray(starter, dtype=complex)
    grid = np.empty((u.size, n_steps + 1), dtype=complex)
    grid[:, 0] = u
    for j in range(1, n_steps + 1):
        u = dense_step(u, ops)
        grid[:, j] = u
    ranges = np.arange(n_steps + 1) * ops.dr
    return grid, ranges


# --------------------------------------------------------------------------- #
# MPS marcher (instrumented)
# --------------------------------------------------------------------------- #
def build_mpos(
    ops: SplitStepOperators,
    *,
    cutoff: float = 1e-10,
    max_bond: int | None = None,
) -> tuple["MatrixProductOperator", "MatrixProductOperator"]:
    """Construct the refraction (diagonal) and diffraction MPOs from ``ops``.

    Both are built once from the range-independent dense operators. Returns
    ``(refraction_mpo, diffraction_mpo)``; the diffraction MPO's bond dimension
    is the cost-driving ``D_mpo`` instrumented per R6.
    """
    from quimb.tensor import MatrixProductOperator

    refraction = MatrixProductOperator.from_dense(
        np.diag(ops.refraction_half), dims=2, cutoff=cutoff, max_bond=max_bond
    )
    diffraction = MatrixProductOperator.from_dense(
        ops.diffraction, dims=2, cutoff=cutoff, max_bond=max_bond
    )
    return refraction, diffraction


def mps_step(
    mps: "MatrixProductState",
    refraction_mpo: "MatrixProductOperator",
    diffraction_mpo: "MatrixProductOperator",
    *,
    cutoff: float = 1e-10,
    max_bond: int | None = None,
) -> "MatrixProductState":
    """One symmetric split-step on an MPS: apply each MPO and truncate.

    ``R_half . Diffraction . R_half`` with SVD truncation (``cutoff`` /
    ``max_bond``) after each gate -- the same operator sequence as
    :func:`dense_step`, so a single step matches the dense step within the
    truncation tolerance.
    """
    out = mps
    for mpo in (refraction_mpo, diffraction_mpo, refraction_mpo):
        out = out.gate_with_mpo(mpo, max_bond=max_bond, cutoff=cutoff)
    return out


@dataclass(frozen=True)
class MarchResult:
    """Outcome of an MPS range march, with the R6 instrumentation.

    ``field`` is the decoded ``(Nz, n_steps + 1)`` depth x range grid (column 0
    the starter); ``chi`` is the state bond dimension recorded at every column
    (``chi[0]`` the starter's); ``diffraction_mpo_bond`` / ``refraction_mpo_bond``
    are the fixed operator bonds.
    """

    depth: np.ndarray  # canonical 2^n depth axis (m), length Nz
    ranges: np.ndarray  # range axis (m), length n_steps + 1
    field: np.ndarray  # complex pressure, shape (Nz, n_steps + 1)
    chi: np.ndarray  # state bond dimension per range, length n_steps + 1
    diffraction_mpo_bond: int
    refraction_mpo_bond: int


def march_mps(
    starter: np.ndarray,
    ops: SplitStepOperators,
    n_steps: int,
    *,
    cutoff: float = 1e-10,
    max_bond: int | None = None,
) -> MarchResult:
    """March the MPS field forward for ``n_steps``, instrumenting chi and the MPO bond.

    The starter is encoded as an MPS at ``cutoff``; each step applies the
    refraction and diffraction MPOs with truncation, recording state chi(range).
    Deterministic for a fixed ``cutoff``/``max_bond`` and environment.
    """
    refraction_mpo, diffraction_mpo = build_mpos(
        ops, cutoff=cutoff, max_bond=max_bond
    )

    mps = encode_field(starter, cutoff=cutoff, max_bond=max_bond)
    nz = np.asarray(starter).size
    field = np.empty((nz, n_steps + 1), dtype=complex)
    chi = np.empty(n_steps + 1, dtype=int)
    field[:, 0] = decode_field(mps)
    chi[0] = state_chi(mps)

    for j in range(1, n_steps + 1):
        mps = mps_step(
            mps,
            refraction_mpo,
            diffraction_mpo,
            cutoff=cutoff,
            max_bond=max_bond,
        )
        field[:, j] = decode_field(mps)
        chi[j] = state_chi(mps)

    ranges = np.arange(n_steps + 1) * ops.dr
    return MarchResult(
        depth=ops.depth,
        ranges=ranges,
        field=field,
        chi=chi,
        diffraction_mpo_bond=int(diffraction_mpo.max_bond()),
        refraction_mpo_bond=int(refraction_mpo.max_bond()),
    )
