"""U2 -- Munk environment, seabed, and full vertical domain.

Defines the deep-water Munk sound-speed profile plus the seabed and absorbing
layer the reference solver (pyram) requires -- pyram has no free-water mode, so
the environment must carry seabed sound speed, density, attenuation, and
bathymetry. The vertical domain spans water column + penetrable seabed +
absorbing layer, discretized on a power-of-two grid (QTT requirement) over that
*total* extent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# Canonical Munk profile constants (Computational Ocean Acoustics, 2nd ed.).
MUNK_C1 = 1500.0  # m/s, sound speed on the channel axis
MUNK_Z_AXIS = 1300.0  # m, channel-axis depth
MUNK_B = 1300.0  # m, profile scale
MUNK_EPS = 7.37e-3


def munk_sound_speed(z: np.ndarray | float, *, c1: float = MUNK_C1,
                     z_axis: float = MUNK_Z_AXIS, b: float = MUNK_B,
                     eps: float = MUNK_EPS) -> np.ndarray | float:
    """Analytic Munk sound-speed profile c(z) in m/s."""
    eta = 2.0 * (np.asarray(z, dtype=float) - z_axis) / b
    return c1 * (1.0 + eps * (eta + np.exp(-eta) - 1.0))


def _next_pow2(n: float) -> int:
    return 1 << max(0, math.ceil(math.log2(n)))


@dataclass(frozen=True)
class OceanEnvironment:
    """A range-independent deep-water ocean-acoustic environment.

    The depth grid spans 0..zmax where zmax = water_depth + absorber, and the
    seabed half-space occupies water_depth..zmax with the bottom
    ``absorber_wavelengths`` of attenuating sediment. Grid size is a power of
    two over the full extent (QTT). Range-independent: a single profile applies
    at every range step.
    """

    freq: float  # Hz, source frequency
    source_depth: float  # m
    receiver_depth: float  # m
    range_max: float  # m
    water_depth: float = 5000.0  # m (deep-water Munk)
    # Seabed half-space (penetrable bottom) -- required by pyram.
    seabed_c: float = 1600.0  # m/s
    seabed_rho: float = 1.5  # g/cm^3
    seabed_attn: float = 0.5  # dB/wavelength
    absorber_wavelengths: float = 20.0  # absorbing layer thickness below seabed
    points_per_wavelength: int = 10  # depth-grid resolution target
    n_sites: int = field(default=0)  # log2(Nz); 0 => auto from resolution target

    @property
    def wavelength(self) -> float:
        return MUNK_C1 / self.freq

    @property
    def zmax(self) -> float:
        """Total computational depth: water + absorbing seabed layer."""
        return self.water_depth + self.absorber_wavelengths * self.wavelength

    @property
    def num_depth_points(self) -> int:
        """Nz = 2 ** n_sites, sized for the resolution target if not given."""
        if self.n_sites:
            return 1 << self.n_sites
        target = self.zmax / (self.wavelength / self.points_per_wavelength)
        return _next_pow2(target)

    @property
    def sites(self) -> int:
        nz = self.num_depth_points
        if nz & (nz - 1):
            raise ValueError(f"Depth grid {nz} is not a power of two (QTT requirement).")
        return nz.bit_length() - 1

    def __post_init__(self) -> None:
        if self.n_sites and (self.n_sites < 1):
            raise ValueError("n_sites must be >= 1 when given explicitly.")
        if self.absorber_wavelengths <= 0:
            raise ValueError(
                "Domain must include an absorbing layer below the seabed; "
                "a water-column-only domain is not allowed."
            )

    def depth_grid(self) -> np.ndarray:
        """Power-of-two depth grid over the full vertical domain [0, zmax]."""
        return np.linspace(0.0, self.zmax, self.num_depth_points, endpoint=False)

    def sound_speed_profile(self) -> np.ndarray:
        """Full-domain sound speed: Munk in the water column, seabed_c below."""
        z = self.depth_grid()
        c = munk_sound_speed(z)
        c[z > self.water_depth] = self.seabed_c
        return c
