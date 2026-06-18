"""U3 tests -- CV leakage, skill metrics, spring barrier, advantage axis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qrc_enso.evaluation import (
    make_folds,
    run_axis,
    skill_by_lead,
    spring_barrier_heatmap,
    _acc,
    _rmse,
)


def test_folds_have_no_temporal_leakage(anomalies):
    folds = make_folds(anomalies, initial_train_months=240, stride_months=1)
    for fold in folds:
        assert fold.train.index.max() == fold.origin
        # Every target is strictly after the last training month -> no leakage.
        assert fold.train.index.max() < fold.earliest_target
        assert fold.earliest_target == fold.origin + pd.DateOffset(months=1)


def test_folds_cover_all_init_months(anomalies):
    folds = make_folds(anomalies, initial_train_months=240, stride_months=1)
    counts = pd.Series([f.origin.month for f in folds]).value_counts()
    assert set(counts.index) == set(range(1, 13))
    assert counts.min() >= 3  # at least 3 samples per initialization month


def test_acc_and_rmse_match_hand_values():
    pred = np.array([0.0, 1.0, 2.0, 3.0])
    obs = np.array([0.0, 1.0, 2.0, 3.0])
    assert _acc(pred, obs) == pytest.approx(1.0)
    assert _rmse(pred, obs) == pytest.approx(0.0)
    assert _rmse(pred, obs + 1.0) == pytest.approx(1.0)


def test_spring_barrier_trough_on_degraded_target_months():
    rng = np.random.default_rng(0)
    rows = []
    for init_month in range(1, 13):
        for target_month in range(1, 13):
            for _ in range(12):
                truth = rng.normal()
                if target_month in (3, 4, 5):  # degrade spring targets
                    pred = rng.normal()
                else:
                    pred = truth + rng.normal(scale=0.1)
                rows.append(
                    {
                        "init_month": init_month,
                        "target_month": target_month,
                        "pred": pred,
                        "obs": truth,
                    }
                )
    hm = spring_barrier_heatmap(pd.DataFrame(rows))
    spring = hm[[3, 4, 5]].to_numpy()
    non_spring = hm[[1, 7, 11]].to_numpy()
    assert np.nanmean(spring) < np.nanmean(non_spring)


def test_advantage_axis_protocol_round_trips(anomalies):
    folds = make_folds(anomalies, initial_train_months=240, stride_months=12)

    class CountAxis:  # caller-supplied one-method object (no concrete axis in v1)
        def apply(self, anomalies, folds):
            return pd.DataFrame({"n_folds": [len(folds)]})

    out = run_axis(CountAxis(), anomalies, folds)
    assert out["n_folds"].iloc[0] == len(folds)
