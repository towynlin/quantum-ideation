"""U2 tests -- Munk profile, seabed, full vertical domain, grid sizing."""

from __future__ import annotations

import numpy as np
import pytest

from mps_acoustics.environment import (
    MUNK_C1,
    MUNK_Z_AXIS,
    OceanEnvironment,
    munk_sound_speed,
)


def _env(**kw) -> OceanEnvironment:
    base = dict(freq=50.0, source_depth=1000.0, receiver_depth=800.0, range_max=100_000.0)
    base.update(kw)
    return OceanEnvironment(**base)


def test_munk_minimum_is_on_the_axis():
    z = np.linspace(0.0, 5000.0, 5001)
    c = munk_sound_speed(z)
    assert abs(z[int(np.argmin(c))] - MUNK_Z_AXIS) < 2.0
    # Sound speed increases above and below the axis.
    assert munk_sound_speed(0.0) > munk_sound_speed(MUNK_Z_AXIS)
    assert munk_sound_speed(4000.0) > munk_sound_speed(MUNK_Z_AXIS)


def test_munk_axis_value_is_c1():
    assert munk_sound_speed(MUNK_Z_AXIS) == pytest.approx(MUNK_C1)
    # Hand-check one off-axis depth (z=0 -> eta=-2).
    eta = 2.0 * (0.0 - MUNK_Z_AXIS) / 1300.0
    expected = MUNK_C1 * (1.0 + 7.37e-3 * (eta + np.exp(-eta) - 1.0))
    assert munk_sound_speed(0.0) == pytest.approx(expected)


def test_environment_carries_seabed_parameters():
    env = _env()
    assert env.seabed_c > 0 and env.seabed_rho > 0 and env.seabed_attn >= 0


def test_depth_grid_is_power_of_two_and_spans_full_domain():
    env = _env()
    grid = env.depth_grid()
    nz = len(grid)
    assert nz & (nz - 1) == 0  # power of two
    assert env.sites == nz.bit_length() - 1
    # Domain spans water column + absorbing layer below the seabed.
    assert env.zmax > env.water_depth
    assert grid[-1] >= env.water_depth


def test_water_column_only_domain_is_rejected():
    with pytest.raises(ValueError):
        _env(absorber_wavelengths=0.0)


def test_sound_speed_profile_is_munk_in_water_seabed_below():
    env = _env(n_sites=12)
    z = env.depth_grid()
    c = env.sound_speed_profile()
    assert c[z <= env.water_depth][0] == pytest.approx(munk_sound_speed(z[0]))
    assert np.all(c[z > env.water_depth] == env.seabed_c)


def test_geometry_round_trips():
    env = _env(freq=75.0, source_depth=1200.0, receiver_depth=600.0, range_max=50_000.0)
    assert (env.freq, env.source_depth, env.receiver_depth, env.range_max) == (
        75.0, 1200.0, 600.0, 50_000.0,
    )
