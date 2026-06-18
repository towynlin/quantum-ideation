"""U4 -- classical baselines: persistence, damped persistence, tuned ESN.

These are the comparison floor (persistence) and the real competitor (a tuned
Echo State Network). All expose the harness ``fit(train) / predict(origin, lead)``
contract with **direct per-lead** forecasting. The harness always calls
``predict`` with ``origin`` equal to the last month of the ``train`` slice just
fitted, so models key off the fitted window's final state.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluation import fit_ridge


class Persistence:
    """Repeat the last observed anomaly across all leads (the trivial floor)."""

    def __init__(self) -> None:
        self._last: float = 0.0

    def fit(self, train: pd.Series) -> "Persistence":
        self._last = float(train.iloc[-1])
        return self

    def predict(self, origin: pd.Timestamp, lead: int) -> float:
        return self._last


class DampedPersistence:
    """Persistence decayed toward climatology by a per-fold autocorrelation.

    The decay timescale is fitted from the **training window only** (R2): the
    lag-1 autocorrelation ``phi`` is estimated on the fitted slice, and the
    forecast at ``lead`` is ``x_origin * phi**lead`` -- a monotonic decay toward
    zero anomaly that beats raw persistence at longer leads.
    """

    def __init__(self) -> None:
        self._last: float = 0.0
        self.phi_: float = 0.0

    def fit(self, train: pd.Series) -> "DampedPersistence":
        x = train.to_numpy()
        self._last = float(x[-1])
        if len(x) > 2 and np.std(x) > 0:
            phi = float(np.corrcoef(x[:-1], x[1:])[0, 1])
        else:
            phi = 0.0
        # Clip into [0, 0.999) so the forecast decays monotonically toward zero.
        self.phi_ = float(min(max(phi, 0.0), 0.999))
        return self

    @property
    def tau_(self) -> float:
        """Decay timescale in months (informational)."""
        return float("inf") if self.phi_ <= 0 else -1.0 / np.log(self.phi_)

    def predict(self, origin: pd.Timestamp, lead: int) -> float:
        return self._last * (self.phi_ ** lead)


_ESN_GRID = [
    {"sr": sr, "lr": lr, "ridge": ridge}
    for sr in (0.9, 1.1)
    for lr in (0.3, 0.7)
    for ridge in (1e-4, 1e-2)
]


class EchoStateNetwork:
    """reservoirpy ESN with a ridge readout and direct per-lead forecasting.

    A separate ridge readout is trained per lead horizon (not reservoirpy's
    recursive rollout). Hyperparameters are tuned on a leakage-safe inner split
    of the training window so the baseline is not left untuned -- the primary
    fairness failure mode. A ``washout`` transient is dropped before fitting
    each readout, matching the QRC reservoir's washout so the two readouts train
    on equally-warmed windows. ``units`` sets the readout feature dimension,
    which :mod:`qrc_enso.experiment` matches against the QRC readout dim (R6).
    """

    def __init__(
        self,
        units: int = 100,
        leads: tuple[int, ...] = (1, 3, 6, 9, 12),
        seed: int = 0,
        tune: bool = True,
        washout: int = 12,
    ) -> None:
        self.units = units
        self.leads = leads
        self.seed = seed
        self.tune = tune
        self.washout = washout
        self.params_: dict = dict(_ESN_GRID[0])
        self.tuned_: bool = False
        self._readouts: dict[int, tuple[np.ndarray, float]] = {}
        self._last_state: np.ndarray | None = None

    @property
    def readout_dim(self) -> int:
        return self.units

    # -- reservoir plumbing -------------------------------------------------
    def _states(self, x: np.ndarray, params: dict) -> np.ndarray:
        from reservoirpy.nodes import Reservoir

        res = Reservoir(
            units=self.units,
            sr=params["sr"],
            lr=params["lr"],
            input_scaling=1.0,
            seed=self.seed,
        )
        # A fresh Reservoir starts from zero state; run() over the full series
        # re-derives the trajectory deterministically.
        return np.asarray(res.run(x.reshape(-1, 1)))

    def _score_params(self, x: np.ndarray, params: dict) -> float:
        """Mean validation ACC across leads on a leakage-safe 70/30 inner split.

        Scoring across all leads (not just lead 1) matches the outer metric.
        """
        cut = int(len(x) * 0.7)
        w0 = self.washout
        if cut <= w0 + 1 or len(x) - cut <= 1:
            return -np.inf
        states = self._states(x, params)
        accs = []
        for lead in self.leads:
            if cut - lead <= w0 or len(x) - cut <= lead:
                continue
            w, b = fit_ridge(states[w0:cut - lead], x[w0 + lead:cut], params["ridge"])
            pred = states[cut:len(x) - lead] @ w + b
            obs = x[cut + lead:]
            m = min(len(pred), len(obs))
            if m >= 2 and np.std(pred[:m]) > 0:
                accs.append(np.corrcoef(pred[:m], obs[:m])[0, 1])
        return float(np.mean(accs)) if accs else -np.inf

    def fit(self, train: pd.Series) -> "EchoStateNetwork":
        x = train.to_numpy(dtype=float)
        if self.tune:
            scored = [(p, self._score_params(x, p)) for p in _ESN_GRID]
            best, best_score = max(scored, key=lambda ps: ps[1])
            if np.isfinite(best_score):
                self.params_, self.tuned_ = dict(best), True
            else:  # series too short to tune -- fall back to the default config
                self.params_, self.tuned_ = dict(_ESN_GRID[0]), False
        states = self._states(x, self.params_)
        self._last_state = states[-1]
        self._readouts = {}
        w0 = self.washout
        for lead in self.leads:
            if len(x) <= w0 + lead:
                continue
            self._readouts[lead] = fit_ridge(states[w0:-lead], x[w0 + lead:], self.params_["ridge"])
        return self

    def predict(self, origin: pd.Timestamp, lead: int) -> float:
        if self._last_state is None or lead not in self._readouts:
            return 0.0
        w, b = self._readouts[lead]
        return float(self._last_state @ w + b)
