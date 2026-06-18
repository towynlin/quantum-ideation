"""U4 tests -- persistence, damped persistence, ESN."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qrc_enso.baselines import DampedPersistence, EchoStateNetwork, Persistence
from qrc_enso.evaluation import evaluate_model, make_folds, skill_by_lead

from tests.conftest import ar1_series


def test_persistence_repeats_last_value():
    s = ar1_series(120)
    m = Persistence().fit(s)
    last = s.iloc[-1]
    for lead in (1, 3, 6, 12):
        assert m.predict(s.index[-1], lead) == pytest.approx(last)


def test_damped_persistence_decays_monotonically():
    s = ar1_series(240)
    m = DampedPersistence().fit(s)
    assert 0.0 <= m.phi_ < 1.0
    preds = [abs(m.predict(s.index[-1], lead)) for lead in range(1, 13)]
    assert all(b <= a + 1e-12 for a, b in zip(preds, preds[1:]))  # non-increasing


def test_damped_persistence_phi_from_training_slice_only():
    s = ar1_series(300)
    train = s.iloc[:200]
    phi_train = DampedPersistence().fit(train).phi_
    # Re-deriving on the exact slice reproduces it; appending later months would
    # be a different input -- the model never reaches beyond what it is given.
    expected = float(np.corrcoef(train.to_numpy()[:-1], train.to_numpy()[1:])[0, 1])
    assert phi_train == pytest.approx(min(max(expected, 0.0), 0.999))


def test_damped_beats_persistence_at_long_leads():
    s = ar1_series(480, phi=0.85)
    folds = make_folds(s, initial_train_months=240, stride_months=1, leads=(1, 6, 12))
    pers = skill_by_lead(evaluate_model(Persistence(), s, folds))
    damp = skill_by_lead(evaluate_model(DampedPersistence(), s, folds))
    pers_rmse_12 = pers[pers["lead"] == 12]["rmse"].iloc[0]
    damp_rmse_12 = damp[damp["lead"] == 12]["rmse"].iloc[0]
    assert damp_rmse_12 < pers_rmse_12


def test_esn_fits_and_reports_readout_dim():
    s = ar1_series(180)
    esn = EchoStateNetwork(units=30, leads=(1, 3), tune=False)
    esn.fit(s.iloc[:150])
    assert esn.readout_dim == 30
    pred = esn.predict(s.index[149], 1)
    assert np.isfinite(pred)
