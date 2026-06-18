"""U3 -- evaluation harness: rolling-origin CV, skill metrics, spring barrier.

Every model is scored through this harness. A *model* is anything implementing
``fit(train) / predict(origin, lead)`` where ``predict`` returns a **direct**
forecast at the requested lead (not a recursive rollout). Metrics are computed
directly with numpy/pandas -- ACC is a correlation, RMSE a two-liner, and the
spring-barrier heatmap a groupby-pivot -- so no xarray/hindcast framework is
pulled in.

Leakage safety (R2) is enforced *here*, not left to caller discipline: folds
carry the raw training series and ``evaluate_model`` fits a fresh anomaly
normalizer on each fold's training window, transforming both the training data
and the verification targets with that window's climatology alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from .data import MonthlyAnomalyNormalizer


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

    def apply(self, series: pd.Series, folds: list["Fold"]) -> pd.DataFrame: ...


@dataclass(frozen=True)
class Fold:
    """One rolling-origin fold (training data is *raw*, normalized per fold)."""

    train: pd.Series  # raw series up to and including the origin month
    origin: pd.Timestamp  # last observed month
    targets: dict[int, pd.Timestamp]  # lead -> target month

    @property
    def earliest_target(self) -> pd.Timestamp:
        return min(self.targets.values())


def fit_ridge(features: np.ndarray, target: np.ndarray, ridge: float) -> tuple[np.ndarray, float]:
    """Closed-form ridge regression with a bias term.

    Shared by the ESN and QRC readouts so the two reservoirs are scored through
    an identical linear map (fairness) and the math lives in one place.
    """
    fc = features - features.mean(axis=0, keepdims=True)
    tc = target - target.mean()
    w = np.linalg.solve(fc.T @ fc + ridge * np.eye(fc.shape[1]), fc.T @ tc)
    bias = float(target.mean() - features.mean(axis=0) @ w)
    return w, bias


def make_folds(
    series: pd.Series,
    *,
    initial_train_months: int = 300,
    stride_months: int = 1,
    leads: tuple[int, ...] = (1, 3, 6, 9, 12),
) -> list[Fold]:
    """Expanding-window rolling-origin folds over the *raw* series.

    Training window is the series up to and including the origin; targets are
    strictly after the origin. By construction ``train`` never overlaps any
    target month, so there is no temporal leakage. Shuffled / k-fold splits are
    intentionally not provided -- ENSO's multi-year autocorrelation makes them
    leak.

    ``stride_months`` defaults to 1 so origins cycle through all 12 calendar
    months and the spring-barrier heatmap (init x target month) is fully
    populated. A stride that divides 12 (e.g. 6) collapses origins onto only a
    couple of init months -- use 1, or a stride coprime with 12. Larger strides
    bound cost for the heavier QRC runs at the price of coverage.
    """
    index = series.index
    if len(index) <= initial_train_months:
        raise ValueError("Series shorter than the initial training window.")

    max_lead = max(leads)
    folds: list[Fold] = []
    origin_pos = initial_train_months - 1
    while origin_pos + max_lead < len(index):
        origin = index[origin_pos]
        targets = {lead: index[origin_pos + lead] for lead in leads}
        folds.append(
            Fold(train=series.iloc[: origin_pos + 1], origin=origin, targets=targets)
        )
        origin_pos += stride_months
    if not folds:
        raise ValueError("No folds produced; widen the series or shrink the window.")
    return folds


def split_folds(
    folds: list[Fold], dev_fraction: float = 0.7
) -> tuple[list[Fold], list[Fold]]:
    """Split folds into an earlier development set and a sealed reporting set.

    The two sets are disjoint by origin (a contiguous split), so a design search
    run on the development folds never sees the reporting folds it will later be
    judged on -- preventing the search from overfitting the reporting set.
    """
    k = int(round(len(folds) * dev_fraction))
    k = max(1, min(k, len(folds) - 1)) if len(folds) > 1 else len(folds)
    return folds[:k], folds[k:]


def evaluate_model(
    model: Model,
    series: pd.Series,
    folds: list[Fold],
    *,
    normalize: bool = True,
    normalizer_factory: Callable[[], MonthlyAnomalyNormalizer] = MonthlyAnomalyNormalizer,
) -> pd.DataFrame:
    """Run a model across folds, returning tidy (origin, lead, pred, obs) rows.

    With ``normalize`` (the default), a fresh normalizer is fit on each fold's
    raw training window and used to transform both the training input and the
    verification target -- so the climatology a fold sees is strictly causal
    (R2). Pass ``normalize=False`` only when the series is already an
    anomaly/feature series that must not be renormalized.
    """
    rows: list[dict] = []
    for fold in folds:
        norm = normalizer_factory().fit(fold.train) if normalize else None
        train_in = norm.transform(fold.train) if norm is not None else fold.train
        model.fit(train_in)
        for lead, target in fold.targets.items():
            if target not in series.index:
                continue
            raw_obs = series.loc[target]
            obs = (
                float(norm.transform(series.loc[[target]]).iloc[0])
                if norm is not None
                else float(raw_obs)
            )
            rows.append(
                {
                    "origin": fold.origin,
                    "init_month": int(fold.origin.month),
                    "lead": int(lead),
                    "target_month": int(target.month),
                    "pred": float(model.predict(fold.origin, lead)),
                    "obs": obs,
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


def run_axis(axis: AdvantageAxis, series: pd.Series, folds: list[Fold]) -> pd.DataFrame:
    """Round-trip a caller-supplied advantage axis through the harness."""
    return axis.apply(series, folds)
