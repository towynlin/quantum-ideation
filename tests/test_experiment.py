"""U6 tests -- matched comparison, sanity gate, reproducible outputs."""

from __future__ import annotations

import pandas as pd
import pytest

from qrc_enso.baselines import DampedPersistence, EchoStateNetwork, Persistence
from qrc_enso.evaluation import make_folds
from qrc_enso.experiment import run_experiment
from qrc_enso.qrc import QRCReservoir

from tests.conftest import ar1_series


class ConstantModel:
    """A model that always predicts zero -- worse than persistence on anomalies."""

    readout_dim = 8

    def fit(self, train):
        return self

    def predict(self, origin, lead):
        return 0.0


def _short_setup(leads=(1, 3)):
    s = ar1_series(140, phi=0.85)
    folds = make_folds(s, initial_train_months=80, stride_months=12, leads=leads)
    return s, folds


def test_matched_dimension_mismatch_is_refused_then_recordable():
    s, folds = _short_setup()
    qrc = QRCReservoir(n_qubits=4, n_virtual=2, leads=(1, 3))  # readout_dim 8
    esn = EchoStateNetwork(units=10, leads=(1, 3), tune=False)  # readout_dim 10

    with pytest.raises(ValueError):
        run_experiment(s, {"qrc": qrc, "esn": esn}, folds, require_matched_dims=True)

    res = run_experiment(s, {"qrc": qrc, "esn": esn}, folds, require_matched_dims=False)
    assert res.manifest["matched_dims"] is False
    assert res.manifest["qrc_readout_dim"] == 8
    assert res.manifest["esn_readout_dim"] == 10


def test_sanity_gate_records_failure_without_raising():
    s, folds = _short_setup()
    res = run_experiment(
        s, {"qrc": ConstantModel(), "persistence": Persistence()}, folds
    )
    assert res.sanity["passed"] is False
    assert res.sanity["checks"]["qrc_beats_persistence_lead1"]["passed"] is False


def test_full_run_writes_tables_and_heatmap(tmp_path):
    s, folds = _short_setup()
    qrc = QRCReservoir(n_qubits=4, n_virtual=2, leads=(1, 3))
    models = {
        "persistence": Persistence(),
        "damped": DampedPersistence(),
        "qrc": qrc,
    }
    run_experiment(s, models, folds, results_dir=tmp_path)
    assert (tmp_path / "skill_qrc.csv").exists()
    assert (tmp_path / "heatmap_persistence.csv").exists()
    assert (tmp_path / "manifest.json").exists()


def test_run_is_reproducible():
    s, folds = _short_setup()

    def run():
        qrc = QRCReservoir(n_qubits=4, n_virtual=2, leads=(1, 3), seed=7)
        return run_experiment(s, {"qrc": qrc, "persistence": Persistence()}, folds)

    a, b = run(), run()
    pd.testing.assert_frame_equal(a.skill["qrc"], b.skill["qrc"])
