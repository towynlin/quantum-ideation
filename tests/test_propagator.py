"""U5 tests -- split-step MPS-PE propagator (R1, R2, R6).

Covers free-field spreading (R1), the single-step dense cross-check (U5
execution note), and the chi + diffraction-MPO-bond instrumentation (R6). The
homogeneous and synthetic cases need no solver; the ``pyram`` self-starter is
computed once in a module-scoped fixture (its JIT warm-up is slow).
"""

from __future__ import annotations

import numpy as np
import pytest

from mps_acoustics import propagator as prop
from mps_acoustics.environment import OceanEnvironment
from mps_acoustics.mps_field import decode_field, encode_field
from mps_acoustics.pe_reference import pyram_starter
from mps_acoustics.propagator import (
    SplitStepOperators,
    build_mpos,
    build_operators,
    dense_step,
    march_dense,
    march_mps,
    mps_step,
)

# A small Munk env for the fast numerical-consistency tests (Nz = 2^8).
_ENV = dict(freq=50.0, source_depth=1000.0, receiver_depth=800.0, range_max=20_000.0)


def _free_field_ops(nz: int = 256, dz: float = 1.0, k0: float = 0.2, dr: float = 5.0):
    """Homogeneous (ksq = 0) split-step operators: refraction is the identity.

    Built directly so the marcher can be checked against the closed-form
    free-field (paraxial) Gaussian-spreading solution, with no environment or
    bottom interaction.
    """
    off = np.ones(nz - 1)
    d_op = (np.diag(off, 1) + np.diag(off, -1) + np.diag(np.full(nz, -2.0))) / dz**2
    a = 1j * dr / (4.0 * k0)
    diffraction = np.linalg.solve(np.eye(nz) - a * d_op, np.eye(nz) + a * d_op)
    return SplitStepOperators(
        depth=np.arange(nz) * dz,
        refraction_half=np.ones(nz, dtype=complex),
        diffraction=diffraction,
        c0=1500.0,
        k0=k0,
        dz=dz,
        dr=dr,
    )


def _gaussian(z: np.ndarray, z0: float, w0: float) -> np.ndarray:
    return np.exp(-((z - z0) ** 2) / (2.0 * w0**2)).astype(complex)


# --------------------------------------------------------------------------- #
# R1 -- free-field spreading against the analytic solution
# --------------------------------------------------------------------------- #
def test_free_field_gaussian_spreading_matches_analytic():
    # Paraxial PE du/dr = (i/2k0) d2u/dz2: a Gaussian starter spreads so its
    # on-axis amplitude decays as w0 / (w0^4 + (R/k0)^2)^(1/4).
    ops = _free_field_ops()
    z = ops.depth
    w0 = 8.0
    starter = _gaussian(z, z[len(z) // 2], w0)
    n_steps = 20
    big_r = n_steps * ops.dr
    analytic_peak = w0 / (w0**4 + (big_r / ops.k0) ** 2) ** 0.25

    dense_grid, ranges = march_dense(starter, ops, n_steps)
    mps_result = march_mps(starter, ops, n_steps, cutoff=1e-12)

    assert ranges[-1] == pytest.approx(big_r)
    dense_peak = np.abs(dense_grid[:, -1]).max()
    mps_peak = np.abs(mps_result.field[:, -1]).max()
    assert dense_peak == pytest.approx(analytic_peak, rel=5e-3)
    assert mps_peak == pytest.approx(analytic_peak, rel=5e-3)


# --------------------------------------------------------------------------- #
# Execution note -- a single MPS step matches a dense split-step step
# --------------------------------------------------------------------------- #
def test_single_mps_step_matches_dense_step():
    env = OceanEnvironment(n_sites=8, **_ENV)
    ops = build_operators(env)
    starter = _gaussian(ops.depth, env.source_depth, 200.0)

    mps = encode_field(starter, cutoff=1e-12)
    refraction_mpo, diffraction_mpo = build_mpos(ops, cutoff=1e-12)
    stepped = mps_step(mps, refraction_mpo, diffraction_mpo, cutoff=1e-12)

    # Compare the MPS step against the dense step on the *same* (encoded) field,
    # so the only difference is the per-step SVD truncation.
    mps_out = decode_field(stepped)
    dense_out = dense_step(decode_field(mps), ops)
    relerr = np.linalg.norm(mps_out - dense_out) / np.linalg.norm(dense_out)
    assert relerr < 1e-4


# --------------------------------------------------------------------------- #
# R6 -- state chi(range) and diffraction-MPO bond instrumentation
# --------------------------------------------------------------------------- #
def test_chi_and_mpo_bond_recorded_every_step():
    env = OceanEnvironment(n_sites=8, **_ENV)
    ops = build_operators(env)
    starter = _gaussian(ops.depth, env.source_depth, 200.0)
    n_steps = 12

    result = march_mps(starter, ops, n_steps, cutoff=1e-10)

    # chi is recorded for the starter (column 0) and every step.
    assert result.chi.shape == (n_steps + 1,)
    assert np.all(result.chi >= 1)
    assert result.ranges.shape == (n_steps + 1,)
    # Both operator bonds are recorded and positive.
    assert result.diffraction_mpo_bond >= 1
    assert result.refraction_mpo_bond >= 1


def test_diffraction_mpo_bond_is_bounded_in_nz():
    # The diffraction operator is a banded second-difference rational, so its MPO
    # bond must not grow with the depth-grid size (a high-bond operator would
    # dominate the O(chi^2 * D_mpo^2) per-step cost regardless of field chi).
    bonds = []
    for n_sites in (8, 10):
        env = OceanEnvironment(n_sites=n_sites, **_ENV)
        _, diffraction_mpo = build_mpos(build_operators(env), cutoff=1e-10)
        bonds.append(int(diffraction_mpo.max_bond()))
    assert bonds[0] == bonds[1]  # constant across a 4x grid refinement
    assert max(bonds) <= 8  # small and bounded


def test_tighter_cutoff_raises_state_chi():
    env = OceanEnvironment(n_sites=8, **_ENV)
    ops = build_operators(env)
    starter = _gaussian(ops.depth, env.source_depth, 200.0)

    loose = march_mps(starter, ops, 10, cutoff=1e-6)
    tight = march_mps(starter, ops, 10, cutoff=1e-12)
    # The monotone accuracy-vs-chi trade-off: a tighter cutoff keeps more bond.
    assert tight.chi.max() >= loose.chi.max()


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_march_is_deterministic():
    env = OceanEnvironment(n_sites=8, **_ENV)
    ops = build_operators(env)
    starter = _gaussian(ops.depth, env.source_depth, 200.0)

    a = march_mps(starter, ops, 8, cutoff=1e-8)
    b = march_mps(starter, ops, 8, cutoff=1e-8)
    assert np.array_equal(a.field, b.field)
    assert np.array_equal(a.chi, b.chi)


# --------------------------------------------------------------------------- #
# pyram self-starter + absorbing bottom (slower -- JIT warm-up)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def starter():
    env = OceanEnvironment(n_sites=10, **_ENV)
    return env, pyram_starter(env)


def test_pyram_starter_encodes_near_source(starter):
    env, st = starter
    # The self-starter is a localized source field: its peak sits at the source
    # depth (within a grid cell or two of self-starter spreading).
    peak_depth = st.depth[np.argmax(np.abs(st.field))]
    assert abs(peak_depth - env.source_depth) < 0.05 * env.water_depth

    # It encodes onto the QTT grid and decodes back within tolerance.
    recon = decode_field(encode_field(st.field, cutoff=1e-10))
    relerr = np.linalg.norm(recon - st.field) / np.linalg.norm(st.field)
    assert relerr < 1e-4


def test_absorber_suppresses_energy_without_reflection(starter):
    env, st = starter
    ops = build_operators(env, dr=st.dr, c0=st.c0)
    result = march_mps(st.field, ops, 30, cutoff=1e-8)

    norms = np.linalg.norm(result.field, axis=0)
    # A passive medium with an absorbing bottom never gains energy: if the
    # bottom reflected, downgoing energy would return and the norm would grow.
    assert norms.max() <= norms[0] * (1.0 + 1e-9)
    assert norms[-1] <= norms[0] + 1e-9

    # Energy that does reach the absorbing layer stays a tiny fraction of the
    # field (it is soaked up, not bounced back up into the water column).
    bottom = result.depth > env.water_depth
    bottom_energy = np.linalg.norm(result.field[bottom, :], axis=0)
    assert bottom_energy.max() < 0.01 * norms.max()
