"""U4 tests -- QTT encoding of the depth field and TL extraction (R2, R3)."""

from __future__ import annotations

import numpy as np
import pytest

from mps_acoustics.mps_field import (
    decode_field,
    encode_decode,
    encode_field,
    extract_tl,
    state_chi,
)
from mps_acoustics.pe_reference import transmission_loss


def _smooth_field(nz: int, n_modes: int = 4, seed: int = 0) -> np.ndarray:
    """A smooth depth field: a few low-order sinusoidal modes (low QTT rank)."""
    rng = np.random.default_rng(seed)
    z = np.linspace(0.0, 1.0, nz, endpoint=False)
    field = np.zeros(nz, dtype=complex)
    for k in range(n_modes):
        field += (rng.normal() + 1j * rng.normal()) * np.sin((k + 1) * np.pi * z)
    return field


def _random_field(nz: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(size=nz) + 1j * rng.normal(size=nz)


# --------------------------------------------------------------------------- #
# R2 -- chi reflects field structure
# --------------------------------------------------------------------------- #
def test_smooth_field_encodes_low_chi_and_decodes_within_tolerance():
    nz = 256
    field = _smooth_field(nz)
    recon, chi = encode_decode(field, cutoff=1e-10)
    assert chi <= 8  # a handful of low-order modes -> low bond dimension
    relerr = np.linalg.norm(recon - field) / np.linalg.norm(field)
    assert relerr < 1e-4  # decodes within the cutoff tolerance


def test_random_field_requires_high_chi():
    nz = 256
    smooth_chi = state_chi(encode_field(_smooth_field(nz), cutoff=1e-10))
    random_chi = state_chi(encode_field(_random_field(nz), cutoff=1e-10))
    # A structureless field saturates the bond dimension (2^(n/2) at mid-chain).
    assert random_chi == nz ** 0.5  # 16 for nz=256
    assert random_chi > 2 * smooth_chi


def test_exact_round_trip_without_truncation():
    field = _random_field(128, seed=3)
    recon, _ = encode_decode(field, cutoff=0.0)
    assert np.allclose(recon, field, atol=1e-12)


# --------------------------------------------------------------------------- #
# chi readout correctness
# --------------------------------------------------------------------------- #
def test_reported_chi_equals_actual_max_bond():
    mps = encode_field(_random_field(64, seed=2), max_bond=3, cutoff=0.0)
    # Independently recompute the maximum bond from the per-bond sizes.
    bonds = [mps.bond_size(mps.site_tag(i), mps.site_tag(i + 1)) for i in range(mps.L - 1)]
    assert state_chi(mps) == max(bonds) == 3


def test_max_bond_cap_truncates_random_field():
    field = _random_field(256, seed=5)
    capped = encode_field(field, max_bond=4, cutoff=0.0)
    assert state_chi(capped) == 4
    relerr = np.linalg.norm(decode_field(capped) - field) / np.linalg.norm(field)
    assert relerr > 0.1  # a hard cap below the true rank loses real content


# --------------------------------------------------------------------------- #
# R3 -- TL extractor consistency
# --------------------------------------------------------------------------- #
def test_tl_from_mps_equals_tl_of_decoded_field():
    field = _smooth_field(256, seed=1)
    mps = encode_field(field, cutoff=1e-12)
    decoded = decode_field(mps)
    assert np.allclose(extract_tl(mps), transmission_loss(decoded))
    # The cylindrical-spreading range passthrough is honoured too.
    ranges = np.linspace(1.0, 1000.0, 256)
    assert np.allclose(extract_tl(mps, ranges), transmission_loss(decoded, ranges))


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def test_non_power_of_two_field_is_rejected():
    with pytest.raises(ValueError):
        encode_field(_random_field(48))


def test_non_1d_field_is_rejected():
    with pytest.raises(ValueError):
        encode_field(_random_field(64).reshape(8, 8))
