"""U2 tests -- ingestion parsing and leakage-safe anomaly normalization."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qrc_enso.data import MonthlyAnomalyNormalizer, parse_nino34_data


SAMPLE_DATA = """ 1950 1952
 1950  25.0 25.1 25.2 25.3 25.4 25.5 25.6 25.7 25.8 25.9 26.0 26.1
 1951  26.0 26.1 26.2 26.3 26.4 26.5 26.6 26.7 26.8 26.9 27.0 27.1
 1952  27.0 27.1 27.2 -99.99 -99.99 -99.99 -99.99 -99.99 -99.99 -99.99 -99.99 -99.99
  -99.99
  Nino 3.4 SST provenance line that must be ignored
"""


def test_parse_produces_monthly_gapfree_series():
    s = parse_nino34_data(SAMPLE_DATA)
    assert isinstance(s.index, pd.DatetimeIndex)
    # 1950 (12) + 1951 (12) + 1952 (3 real) = 27 months after sentinels dropped.
    assert len(s) == 27
    assert s.index[0] == pd.Timestamp("1950-01-01")
    assert s.index[-1] == pd.Timestamp("1952-03-01")


def test_parse_drops_sentinels_and_future_months():
    s = parse_nino34_data(SAMPLE_DATA)
    # No sentinel value survives, and the trailing (future) months of 1952 are gone.
    assert not np.isclose(s.to_numpy(), -99.99, atol=1e-2).any()
    assert pd.Timestamp("1952-04-01") not in s.index


def _series(years):
    idx = pd.date_range("1950-01-01", periods=12 * years, freq="MS")
    # A seasonal cycle plus a slow trend so calendar-month climatology is non-trivial.
    vals = 27 + np.sin(2 * np.pi * (idx.month - 1) / 12) + 0.01 * np.arange(len(idx))
    return pd.Series(vals, index=idx, name="nino34_sst")


def test_climatology_uses_training_window_only():
    full = _series(70)  # 1950-2019
    train = full.loc[:"1999-12-01"]

    norm_from_slice = MonthlyAnomalyNormalizer().fit(train)
    # Fitting on the same window taken from the full series must be identical --
    # the later (test-span) months cannot influence the climatology.
    norm_from_full_slice = MonthlyAnomalyNormalizer().fit(full.loc["1950-01-01":"1999-12-01"])

    assert norm_from_slice.month_mean_ == norm_from_full_slice.month_mean_
    assert norm_from_slice.month_std_ == norm_from_full_slice.month_std_


def test_transform_on_disjoint_window_uses_training_stats():
    full = _series(70)
    train = full.loc[:"1999-12-01"]
    norm = MonthlyAnomalyNormalizer(standardize=False).fit(train)

    test_window = full.loc["2000-01-01":"2000-12-01"]
    anom = norm.transform(test_window)
    # Hand-check January 2000: anomaly = value - training January mean.
    jan_train_mean = train[train.index.month == 1].mean()
    expected = full.loc["2000-01-01"] - jan_train_mean
    assert anom.loc["2000-01-01"] == pytest.approx(expected)


def test_transform_raises_for_unseen_calendar_month():
    idx = pd.date_range("1950-01-01", periods=1, freq="MS")  # January only
    jan_only = pd.Series([27.0], index=idx)
    norm = MonthlyAnomalyNormalizer().fit(jan_only)
    feb = pd.Series([27.0], index=pd.date_range("1950-02-01", periods=1, freq="MS"))
    with pytest.raises(ValueError):
        norm.transform(feb)
