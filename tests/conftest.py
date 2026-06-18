"""Shared synthetic fixtures (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def ar1_series(n_months: int = 480, phi: float = 0.85, seed: int = 0) -> pd.Series:
    """An AR(1) anomaly series -- a stand-in for ENSO's autocorrelated dynamics."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n_months)
    for t in range(1, n_months):
        x[t] = phi * x[t - 1] + rng.normal(scale=0.5)
    idx = pd.date_range("1960-01-01", periods=n_months, freq="MS")
    return pd.Series(x, index=idx, name="nino34_anom")


@pytest.fixture
def anomalies() -> pd.Series:
    return ar1_series()
