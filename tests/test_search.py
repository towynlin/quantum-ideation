"""U7 tests -- design-search loop, leaderboard, budget, fault tolerance."""

from __future__ import annotations

import pytest

from qrc_enso.evaluation import make_folds
from qrc_enso.search import (
    GridSweep,
    PerturbBestProposer,
    make_qrc_score_fn,
    run_search,
)

from tests.conftest import ar1_series


def test_leaderboard_ranked_and_logged():
    configs = [{"n_qubits": q} for q in (3, 6, 4)]
    res = run_search(lambda c: float(c["n_qubits"]), GridSweep(configs), max_trials=10)
    assert len(res.log) == 3
    assert [t.config["n_qubits"] for t in res.leaderboard] == [6, 4, 3]


def test_budget_halts_loop():
    configs = [{"n_qubits": q} for q in range(10)]
    res = run_search(lambda c: float(c["n_qubits"]), GridSweep(configs), max_trials=2)
    assert len(res.log) == 2


def test_grid_exhaustion_stops_loop():
    configs = [{"n_qubits": 3}, {"n_qubits": 4}]
    res = run_search(lambda c: 1.0, GridSweep(configs), max_trials=10)
    assert len(res.log) == 2


def test_failed_config_is_logged_not_fatal():
    configs = [{"n_qubits": 3}, {"n_qubits": -1}, {"n_qubits": 5}]

    def score(c):
        if c["n_qubits"] < 0:
            raise ValueError("invalid qubit count")
        return float(c["n_qubits"])

    res = run_search(score, GridSweep(configs), max_trials=10)
    assert len(res.log) == 3
    failed = [t for t in res.log if t.score is None]
    assert len(failed) == 1 and "invalid qubit count" in failed[0].error
    assert len(res.leaderboard) == 2  # failed trial excluded from ranking


def test_proposers_are_interchangeable():
    space = {"n_qubits": (3, 6), "n_virtual": (1, 4)}
    proposer = PerturbBestProposer(base={"n_qubits": 4, "n_virtual": 2}, space=space, seed=0)
    res = run_search(lambda c: float(c["n_qubits"] + c["n_virtual"]), proposer, max_trials=5)
    assert len(res.log) == 5
    for trial in res.log:
        assert 3 <= trial.config["n_qubits"] <= 6
        assert 1 <= trial.config["n_virtual"] <= 4


def test_score_fn_runs_through_real_harness_path():
    s = ar1_series(120)
    folds = make_folds(s, initial_train_months=80, stride_months=12, leads=(1, 3))
    score = make_qrc_score_fn(s, folds, leads=(1, 3))
    val = score({"n_qubits": 4, "n_virtual": 2, "washout": 6})
    assert isinstance(val, float)
