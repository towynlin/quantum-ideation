"""U7 -- agent reservoir-design search loop.

Drives a search over QRC reservoir configurations, scoring each through the same
leakage-safe harness path as the fixed-config experiment (R11) and recording a
ranked leaderboard (R10). A proposer interface separates *which config to try*
from *how it is scored*; the deterministic sweep is the test scaffold and the
agent proposer is the goal. The agent proposer's mechanism (LLM-driven vs a
Bayesian surrogate) is an implementation choice bounded by the search budget;
either way it sees only training-fold skill scores, never test data.

**Sealed reporting set.** To keep the search from overfitting the reporting
folds, split folds with :func:`qrc_enso.evaluation.split_folds` and score the
search on the *development* folds only; report final skill on the sealed folds
the search never saw.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

import numpy as np
import pandas as pd

from .evaluation import Fold, evaluate_model, skill_by_lead
from .qrc import QRCReservoir


def _is_scored(trial: "Trial") -> bool:
    return trial.score is not None and not math.isnan(trial.score)


@dataclass
class Trial:
    config: dict
    score: float | None  # None or NaN == failed/degenerate evaluation
    error: str | None = None


class Proposer(Protocol):
    def propose(self, log: list["Trial"]) -> dict | None:
        """Return the next config, or None when the proposer is exhausted."""
        ...


class GridSweep:
    """Deterministic proposer over a fixed list of configs (the test scaffold)."""

    def __init__(self, configs: list[dict]) -> None:
        self._configs = list(configs)
        self._i = 0

    def propose(self, log: list[Trial]) -> dict | None:
        if self._i >= len(self._configs):
            return None
        cfg = self._configs[self._i]
        self._i += 1
        return cfg


class PerturbBestProposer:
    """Agent-style proposer: perturb the current best config within a space.

    A stand-in for a richer agent (LLM-driven or Bayesian surrogate); it reads
    the running log, takes the best *validly-scored* config, and jitters its
    integer knobs within the provided ranges. Interchangeable with GridSweep
    through the Proposer interface.
    """

    def __init__(self, base: dict, space: dict[str, tuple[int, int]], seed: int = 0) -> None:
        self.base = base
        self.space = space
        self._rng = np.random.default_rng(seed)

    def propose(self, log: list[Trial]) -> dict | None:
        scored = [t for t in log if _is_scored(t)]
        anchor = max(scored, key=lambda t: t.score).config if scored else self.base
        cfg = dict(anchor)
        for key, (lo, hi) in self.space.items():
            step = int(self._rng.integers(-1, 2))  # -1, 0, +1
            cfg[key] = int(min(max(cfg.get(key, lo) + step, lo), hi))
        return cfg


@dataclass
class SearchResult:
    leaderboard: list[Trial] = field(default_factory=list)
    log: list[Trial] = field(default_factory=list)

    def ranked(self) -> list[Trial]:
        scored = [t for t in self.log if _is_scored(t)]
        return sorted(scored, key=lambda t: t.score, reverse=True)


def make_qrc_score_fn(
    series: pd.Series,
    folds: list[Fold],
    leads: tuple[int, ...] = (1, 3, 6, 9, 12),
) -> Callable[[dict], float]:
    """Black-box objective: mean ACC of a QRC config through the harness (R11).

    Pass the *development* folds here (see module docstring); report on the
    sealed folds separately so the search never optimizes against the reporting
    set.
    """

    def score(config: dict) -> float:
        model = QRCReservoir(leads=leads, **config)
        rows = evaluate_model(model, series, folds)
        table = skill_by_lead(rows)
        return float(np.nanmean(table["acc"].to_numpy()))

    return score


def run_search(
    score_fn: Callable[[dict], float],
    proposer: Proposer,
    *,
    max_trials: int = 20,
    time_budget_s: float | None = None,
) -> SearchResult:
    """Bounded search loop. Failed or degenerate (NaN) evaluations are logged,
    not fatal, and are excluded from the leaderboard."""
    result = SearchResult()
    start = time.monotonic()
    for _ in range(max_trials):
        if time_budget_s is not None and time.monotonic() - start > time_budget_s:
            break
        config = proposer.propose(result.log)
        if config is None:
            break
        try:
            score = score_fn(config)
            if score is None or math.isnan(score):
                trial = Trial(config=config, score=None, error="non-finite score")
            else:
                trial = Trial(config=config, score=float(score))
        except Exception as exc:  # noqa: BLE001 -- a bad config must not abort the loop
            trial = Trial(config=config, score=None, error=f"{type(exc).__name__}: {exc}")
        result.log.append(trial)
    result.leaderboard = result.ranked()
    return result
