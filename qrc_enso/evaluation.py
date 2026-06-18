"""U3 -- evaluation harness: rolling-origin CV, skill metrics, spring barrier.

Every model is scored through this harness. A *model* is anything implementing
``fit(train) / predict(origin, lead)`` where ``predict`` returns a **direct**
forecast at the requested lead (not a recursive rollout). Metrics are computed
directly with numpy/pandas -- ACC is a correlation, RMSE a two-liner, and the
spring-barrier heatmap a groupby-pivot -- so no xarray/hindcast framework is
pulled in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd


@runtime_checkable
class Model(Protocol):
    """Forecast model contract consumed by the harness."""

    def fit(self, train: pd.Series) -> "Model": ...

    def predict(self, origin: pd.Timestamp, lead: int) -> float: ...


@runtime_checkable
class AdvantageAxis(Protocol):
    """Pluggable advantage-axis (R12).

    Ships as a protocol only in v1 -- no concrete axis (footprint /
    data-efficiency / spring-barrier) is implemented until one is chosen. A
    caller-supplied one-method object round-trips through :func:`run_axis`
    without harness edits.
    """

    def apply(self, anomalies: pd.Series, folds: list["Fold"]) -> pd.DataFrame: ...


@dataclass(frozen=True)
class Fold:
    """One rolling-origin fold."""

    train: pd.Series  # anomalies up to and including the origin month
    origin: pd.Timestamp  # last observed month
    targets: dict[int, pd.Timestamp]  # lead -> target month

    @property
    def earliest_target(self) -> pd.Timestamp:
        return min(self.targets.values())


def make_folds(
    anomalies: pd.Series,
    *,
    initial_train_months: int = 300,
    stride_months: int = 1,
    leads: tuple[int, ...] = (1, 3, 6, 9, 12),
) -> list[Fold]:
    """Expanding-window rolling-origin folds.

    Training window is the anomaly series up to and including the origin; targets
    are strictly after the origin. By construction ``train`` never overlaps any
    target month, so there is no temporal leakage. Shuffled / k-fold splits are
    intentionally not provided -- ENSO's multi-year autocorrelation makes them
    leak.

    ``stride_months`` defaults to 1 so origins cycle through all 12 calendar
    months and the spring-barrier heatmap (init x target month) is fully
    populated. A stride that divides 12 (e.g. 6) collapses origins onto only a
    couple of init months -- use 1, or a stride coprime with 12, to keep
    init-month coverage. Larger strides bound cost for the heavier QRC runs at
    the price of coverage.
    """
    index = anomalies.index
    if len(index) <= initial_train_months:
        raise ValueError("Series shorter than the initial training window.")

    max_lead = max(leads)
    folds: list[Fold] = []
    origin_pos = initial_train_months - 1
    while origin_pos + max_lead < len(index):
        origin = index[origin_pos]
        targets = {lead: index[origin_pos + lead] for lead in leads}
        folds.append(
            Fold(train=anomalies.iloc[: origin_pos + 1], origin=origin, targets=targets)
        )
        origin_pos += stride_months
    if not folds:
        raise ValueError("No folds produced; widen the series or shrink the window.")
    return folds


def evaluate_model(model: Model, anomalies: pd.Series, folds: list[Fold]) -> pd.DataFrame:
    """Run a model across folds, returning tidy (origin, lead, pred, obs) rows."""
    rows: list[dict] = []
    for fold in folds:
        model.fit(fold.train)
        for lead, target in fold.targets.items():
            if target not in anomalies.index:
                continue
            rows.append(
                {
                    "origin": fold.origin,
                    "init_month": int(fold.origin.month),
                    "lead": int(lead),
                    "target_month": int(target.month),
                    "pred": float(model.predict(fold.origin, lead)),
                    "obs": float(anomalies.loc[target]),
                }
            )
    return pd.DataFrame(rows)


def _acc(pred: np.ndarray, obs: np.ndarray) -> float:
    """Anomaly Correlation Coefficient (Pearson) between forecast and obs."""
    if len(pred) < 2 or np.std(pred) == 0 or np.std(obs) == 0:
        return np.nan
    return float(np.corrcoef(pred, obs)[0, 1])


def _rmse(pred: np.ndarray, obs: np.ndarray) -> float:
    return float(np.sqrt(np.mean((pred - obs) ** 2)))


def skill_by_lead(rows: pd.DataFrame) -> pd.DataFrame:
    """ACC and RMSE as a function of lead time."""
    out = []
    for lead, grp in rows.groupby("lead"):
        out.append(
            {
                "lead": int(lead),
                "acc": _acc(grp["pred"].to_numpy(), grp["obs"].to_numpy()),
                "rmse": _rmse(grp["pred"].to_numpy(), grp["obs"].to_numpy()),
                "n": len(grp),
            }
        )
    return pd.DataFrame(out).sort_values("lead").reset_index(drop=True)


def spring_barrier_heatmap(rows: pd.DataFrame) -> pd.DataFrame:
    """ACC stratified by (init month x target month).

    The spring predictability barrier shows as an ACC trough along the
    March-May target columns regardless of init month.
    """
    cells = (
        rows.groupby(["init_month", "target_month"])
        .apply(
            lambda g: _acc(g["pred"].to_numpy(), g["obs"].to_numpy()),
            include_groups=False,
        )
        .reset_index(name="acc")
    )
    return cells.pivot(index="init_month", columns="target_month", values="acc")


def run_axis(axis: AdvantageAxis, anomalies: pd.Series, folds: list[Fold]) -> pd.DataFrame:
    """Round-trip a caller-supplied advantage axis through the harness."""
    return axis.apply(anomalies, folds)
