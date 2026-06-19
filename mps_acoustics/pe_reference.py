"""U3 -- reference transmission loss: ``pyram`` cross-checked by ``pykrak``.

Produces a *trusted* reference transmission-loss (TL) field on the common
power-of-two depth axis declared by the U2 environment, and isolates every
``pyram``/``pykrak`` call behind this module (lazy heavy imports, mirroring the
adapter-isolation pattern in ``qrc_enso/qrc.py``).

Two solvers run the same range-independent Munk case:

- ``pyram`` -- a pure-Python RAM split-step Pade PE solver. It is the reference
  the MPS marcher is compared against step-for-step, but it is *same-family*
  with the MPS path (both implement the PE Pade operator), so validating against
  it alone would be circular.
- ``pykrak`` -- an *independent* KRAKEN normal-mode solver. It does not share the
  PE approximation, so agreement between the two is a genuine cross-check.

``pyram`` may be used as the MPS reference only once it agrees with ``pykrak``
over the reference-amplitude-masked region (R10). The shared :func:`transmission_loss`
function (R3) defines TL identically for the reference and MPS paths.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .environment import OceanEnvironment, munk_sound_speed

# Compatibility shim: pykrak's numba kernels call np.trapz, which NumPy >= 2.0
# removed in favour of np.trapezoid. Restore the alias on the shared numpy
# module object so pykrak's JIT compilation resolves it.
if not hasattr(np, "trapz"):  # pragma: no cover - environment-dependent
    np.trapz = np.trapezoid  # type: ignore[attr-defined]

# Matches the floor pyram uses inside outpt() so reconstructed TL lines up.
_EPS = 1e-20

# Free-field reference-pressure convention difference between the two codes.
# RAM/pyram report TL re 1 m: p_ref is the source's free-field pressure at 1 m.
# pykrak's modal sum returns the pressure of the 1/(4*pi*R) free-field Green's
# function, whose 1 m reference pressure is 1/(4*pi). Converting pykrak's raw
# -20log10|p| onto the re-1 m scale therefore subtracts 20*log10(4*pi) ~ 21.98 dB
# (equivalently, scale pykrak pressure by 4*pi before taking TL). This is a
# first-principles constant, not a fitted offset: it is identical (~22 dB) across
# independent Pekeris and Munk environments.
_PYKRAK_TL_OFFSET_DB = 20.0 * np.log10(4.0 * np.pi)


# --------------------------------------------------------------------------- #
# Shared TL function (R3)
# --------------------------------------------------------------------------- #
def transmission_loss(
    pressure: np.ndarray | complex,
    ranges: np.ndarray | float | None = None,
) -> np.ndarray:
    """Transmission loss (dB) from complex pressure, ``TL = -20 log10|p|``.

    A single definition shared by the reference and MPS paths (R3). The pressure
    is taken relative to the 1 m reference distance (unit-amplitude source), so
    ``|p| = 1`` maps to 0 dB.

    ``ranges`` makes the cylindrical-spreading convention explicit. Parabolic-
    equation pressure (pyram's ``CP Grid``, and the MPS field) excludes the
    ``1/sqrt(r)`` spreading term, so the caller supplies the range axis and the
    ``+10 log10(r)`` correction is applied -- reproducing pyram's own ``TL Grid``.
    Fields that already include spreading (e.g. pykrak's modal sum) pass
    ``ranges=None``.
    """
    amp = np.abs(np.asarray(pressure, dtype=complex))
    tl = -20.0 * np.log10(amp + _EPS)
    if ranges is not None:
        tl = tl + 10.0 * np.log10(np.asarray(ranges, dtype=float) + _EPS)
    return tl


# --------------------------------------------------------------------------- #
# Reference fields on the common grid
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ReferenceField:
    """A TL field on the common (canonical 2^n depth) x (range) grid."""

    method: str  # "pyram" | "pykrak"
    depth: np.ndarray  # canonical 2^n depth axis (m), length Nz
    ranges: np.ndarray  # output ranges (m)
    tl: np.ndarray  # transmission loss (dB), shape (Nz, n_ranges)

    @property
    def receiver_curve(self) -> np.ndarray:
        """TL vs range at the depth closest to the field's peak amplitude."""
        zi = int(np.argmin(self.tl.min(axis=1)))
        return self.tl[zi]


def _canonical_dz(env: OceanEnvironment) -> float:
    return env.zmax / env.num_depth_points


def _interp_to_canonical(
    depth_canonical: np.ndarray,
    depth_native: np.ndarray,
    grid_native: np.ndarray,
) -> np.ndarray:
    """Interpolate a (depth_native x range) grid onto the canonical depth axis."""
    out = np.empty((depth_canonical.size, grid_native.shape[1]), dtype=grid_native.dtype)
    for j in range(grid_native.shape[1]):
        out[:, j] = np.interp(depth_canonical, depth_native, grid_native[:, j])
    return out


def pyram_reference(env: OceanEnvironment) -> ReferenceField:
    """Run ``pyram`` on the Munk case and reconcile output to the common grid.

    pyram chooses its own (non-power-of-two) grid; we drive it with an explicit
    ``dz`` at the canonical resolution and interpolate its TL grid onto the U2
    power-of-two depth axis over the shared extent.
    """
    from pyram.PyRAM import PyRAM

    depth_canonical = env.depth_grid()
    dz = _canonical_dz(env)

    # Water sound-speed profile: Munk over the water column, sampled at the
    # canonical resolution. pyram interpolates internally onto its own depth
    # grid, so the seabed half-space below water_depth is supplied separately.
    z_ss = np.arange(0.0, env.water_depth + dz, dz)
    cw = munk_sound_speed(z_ss)[:, None]  # (Nz_water, 1)
    rp_ss = np.array([0.0])

    # Seabed half-space (relative depths; pyram offsets by the deepest water
    # point internally). Bathymetry is flat at the water depth.
    z_sb = np.array([0.0])
    rp_sb = np.array([0.0])
    cb = np.array([[env.seabed_c]])
    rhob = np.array([[env.seabed_rho]])
    attn = np.array([[env.seabed_attn]])
    rbzb = np.array([[0.0, env.water_depth]])

    pyram = PyRAM(
        env.freq,
        env.source_depth,
        env.receiver_depth,
        z_ss,
        rp_ss,
        cw,
        z_sb,
        rp_sb,
        cb,
        rhob,
        attn,
        rbzb,
        dz=dz,
        zmplt=env.water_depth,
        rmax=env.range_max,
        lyrw=env.absorber_wavelengths,
    )
    results = pyram.run()

    vz = results["Depths"]
    vr = results["Ranges"]
    tlg = results["TL Grid"]
    tl = _interp_to_canonical(depth_canonical, vz, tlg)
    return ReferenceField("pyram", depth_canonical, vr, tl)


def pykrak_reference(env: OceanEnvironment, ranges: np.ndarray) -> ReferenceField:
    """Independent KRAKEN normal-mode TL on the same Munk case (R10).

    Evaluated on the canonical depth axis and the supplied range axis so the
    field shares axes with :func:`pyram_reference` exactly.
    """
    from pykrak import field as pk_field
    from pykrak.pykrak_env import FluidEnv

    depth_canonical = env.depth_grid()
    dz = _canonical_dz(env)

    # Water layer: Munk profile over a fluid bottom half-space.
    z_water = np.arange(0.0, env.water_depth + dz, dz)
    cp_water = munk_sound_speed(z_water)
    rho_water = np.ones_like(z_water)
    attn_water = np.zeros_like(z_water)

    krak_env = FluidEnv(
        z_list=[z_water],
        cp_list=[cp_water],
        rho_list=[rho_water],
        attnp_list=[attn_water],
        cp_top=0.0,
        rho_top=0.0,
        attnp_top=0.0,
        cp_bott=env.seabed_c,
        rho_bott=env.seabed_rho,
        attnp_bott=env.seabed_attn,
        attn_units="dbplam",
    )
    krs, zmesh, phi, _ugs = krak_env.get_modes(
        env.freq, [], rmax=env.range_max, c_low=0.0, c_high=env.seabed_c
    )

    # field shape (n_src, n_zr, n_rr); single source -> drop the first axis.
    pressure = pk_field.get_pressure(
        krs,
        zmesh,
        phi,
        env.source_depth,
        depth_canonical,
        ranges,
        0.0,
        env.freq,
    )[0]
    # Modal sum already includes cylindrical spreading (ranges=None); shift onto
    # the re-1 m TL convention pyram uses (see _PYKRAK_TL_OFFSET_DB).
    tl = transmission_loss(pressure) - _PYKRAK_TL_OFFSET_DB
    return ReferenceField("pykrak", depth_canonical, np.asarray(ranges), tl)


# --------------------------------------------------------------------------- #
# Amplitude mask + agreement (R10)
# --------------------------------------------------------------------------- #
def amplitude_mask(tl_reference: np.ndarray, db_below_peak: float) -> np.ndarray:
    """Validity mask from the *reference amplitude alone*.

    Bins whose amplitude is within ``db_below_peak`` of the field's peak
    amplitude -- equivalently TL within ``db_below_peak`` of the minimum TL.
    Computed solely from the reference field, never from the field under test
    (this is the anti-gerrymandering invariant carried into U6/R5).
    """
    finite = np.isfinite(tl_reference)
    floor = np.min(tl_reference[finite]) if finite.any() else 0.0
    return finite & (tl_reference <= floor + db_below_peak)


@dataclass(frozen=True)
class AgreementResult:
    """Outcome of comparing two TL fields over the reference-amplitude mask."""

    agree: bool
    median_db: float
    p95_db: float
    tol_db: float
    n_masked: int


def references_agree(
    reference: ReferenceField,
    other: ReferenceField,
    *,
    tol_db: float = 5.0,
    mask_db_below_peak: float = 30.0,
) -> AgreementResult:
    """Do two TL fields agree over the reference-amplitude-masked region?

    The mask is taken from ``reference`` (pyram is the designated reference). The
    gate is the **median** ``|dTL|`` over that region: PE (pyram) and normal-mode
    (pykrak) fields differ sharply at interference nulls -- a one-bin null shift
    is tens of dB -- so the 95th percentile is null-driven and reported for
    transparency rather than gated (the same robust-statistic reasoning U6 uses
    with its median + linear-|dp| + CZ-position metrics). ``pyram`` must clear
    this median bar against the independent ``pykrak`` before it is trusted as
    the MPS reference (R10).
    """
    if reference.tl.shape != other.tl.shape:
        raise ValueError(
            f"Reference fields are on different grids: "
            f"{reference.tl.shape} vs {other.tl.shape}."
        )
    mask = amplitude_mask(reference.tl, mask_db_below_peak)
    delta = np.abs(reference.tl - other.tl)[mask]
    if delta.size == 0:
        return AgreementResult(False, float("nan"), float("nan"), tol_db, 0)
    median_db = float(np.median(delta))
    p95_db = float(np.percentile(delta, 95))
    return AgreementResult(median_db <= tol_db, median_db, p95_db, tol_db, int(delta.size))


@dataclass(frozen=True)
class ReferenceBundle:
    """The trusted reference plus the independent cross-check and its verdict."""

    pyram: ReferenceField
    pykrak: ReferenceField
    agreement: AgreementResult

    @property
    def reference(self) -> ReferenceField:
        """The field used downstream as the MPS reference (pyram)."""
        return self.pyram

    @property
    def trustworthy(self) -> bool:
        return self.agreement.agree


def reference_tl(
    env: OceanEnvironment,
    *,
    tol_db: float = 5.0,
    mask_db_below_peak: float = 30.0,
) -> ReferenceBundle:
    """Produce the trusted reference TL field with the ``pykrak`` cross-check.

    Runs ``pyram`` (the reference) and ``pykrak`` (the independent check) on the
    common grid and records whether they agree. The caller (U7) must refuse to
    report an MPS verdict when ``trustworthy`` is False (R10); this function
    reports the verdict rather than raising, so both fields stay inspectable.
    """
    pyram_field = pyram_reference(env)
    pykrak_field = pykrak_reference(env, pyram_field.ranges)
    agreement = references_agree(
        pyram_field,
        pykrak_field,
        tol_db=tol_db,
        mask_db_below_peak=mask_db_below_peak,
    )
    return ReferenceBundle(pyram_field, pykrak_field, agreement)
