"""U6 -- matched-comparison runner and sanity gate.

Wires models through the U3 harness (with per-fold leakage-safe normalization),
emits skill tables and the spring-barrier heatmap, and asserts the
walking-skeleton success bar (R9): QRC beats persistence at short lead and lands
within tolerance of damped persistence. A failing or degenerate gate is recorded
in the manifest, never hidden.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation import Fold, Model, evaluate_model, skill_by_lead, spring_barrier_heatmap


@dataclass
class ExperimentResult:
    skill: dict[str, pd.DataFrame]
    heatmaps: dict[str, pd.DataFrame]
    manifest: dict
    sanity: dict


def _mean_acc(skill: pd.DataFrame) -> float:
    return float(np.nanmean(skill["acc"].to_numpy()))


def _acc_at_lead(skill: pd.DataFrame, lead: int) -> float:
    row = skill[skill["lead"] == lead]
    return float(row["acc"].iloc[0]) if len(row) else float("nan")


def run_experiment(
    series: pd.Series,
    models: dict[str, Model],
    folds: list[Fold],
    *,
    seed: int = 0,
    require_matched_dims: bool = True,
    damped_tolerance: float = 0.1,
    normalize: bool = True,
    results_dir: Path | str | None = None,
    qrc_key: str = "qrc",
    persistence_key: str = "persistence",
    damped_key: str = "damped",
) -> ExperimentResult:
    manifest: dict = {"seed": seed, "n_folds": len(folds), "models": {}}

    # Matched-dimension check (R6) across *every* model that reports a readout
    # dimension -- not two hard-coded keys. Always record the map; on a mismatch
    # leave it visible and (when required) refuse to report.
    dims = {
        name: int(m.readout_dim)
        for name, m in models.items()
        if hasattr(m, "readout_dim")
    }
    if dims:
        manifest["readout_dims"] = dims
        distinct = set(dims.values())
        manifest["matched_dims"] = len(distinct) <= 1
        if len(distinct) > 1 and require_matched_dims:
            raise ValueError(
                f"Readout dimensions differ across models {dims}; match them or "
                "pass require_matched_dims=False to record the mismatch."
            )

    skill: dict[str, pd.DataFrame] = {}
    heatmaps: dict[str, pd.DataFrame] = {}
    for name, model in models.items():
        rows = evaluate_model(model, series, folds, normalize=normalize)
        skill[name] = skill_by_lead(rows)
        heatmaps[name] = spring_barrier_heatmap(rows)
        manifest["models"][name] = {
            "type": type(model).__name__,
            "readout_dim": getattr(model, "readout_dim", None),
            "params": getattr(model, "params_", None),
        }

    sanity = _sanity_gate(skill, damped_tolerance, qrc_key, persistence_key, damped_key)
    manifest["sanity"] = sanity

    if results_dir is not None:
        _write_results(results_dir, skill, heatmaps, manifest)

    return ExperimentResult(skill=skill, heatmaps=heatmaps, manifest=manifest, sanity=sanity)


def _finite(value: float) -> bool:
    return value is not None and not math.isnan(value)


def _sanity_gate(
    skill: dict[str, pd.DataFrame],
    damped_tolerance: float,
    qrc_key: str,
    persistence_key: str,
    damped_key: str,
) -> dict:
    """R9 walking-skeleton bar. Never raises -- records a verdict.

    A degenerate run (NaN ACC anywhere a check depends on it) is recorded as a
    failure with ``invalid: true`` rather than passing silently, since
    ``nan > x`` is always False.
    """
    out: dict = {"checks": {}, "passed": None, "invalid": False}
    if qrc_key not in skill or persistence_key not in skill:
        out["note"] = f"{qrc_key} and {persistence_key} required for the sanity gate"
        return out

    qrc_l1 = _acc_at_lead(skill[qrc_key], 1)
    pers_l1 = _acc_at_lead(skill[persistence_key], 1)
    valid = _finite(qrc_l1) and _finite(pers_l1)
    out["invalid"] = out["invalid"] or not valid
    beats_persistence = valid and qrc_l1 > pers_l1
    out["checks"]["qrc_beats_persistence_lead1"] = {
        "qrc_acc": qrc_l1,
        "persistence_acc": pers_l1,
        "passed": bool(beats_persistence),
    }

    checks = [beats_persistence]
    if damped_key in skill:
        qrc_mean = _mean_acc(skill[qrc_key])
        damped_mean = _mean_acc(skill[damped_key])
        valid_d = _finite(qrc_mean) and _finite(damped_mean)
        out["invalid"] = out["invalid"] or not valid_d
        within = valid_d and qrc_mean >= damped_mean - damped_tolerance
        out["checks"]["qrc_within_damped"] = {
            "qrc_mean_acc": qrc_mean,
            "damped_mean_acc": damped_mean,
            "tolerance": damped_tolerance,
            "passed": bool(within),
        }
        checks.append(within)

    out["passed"] = bool(all(checks)) and not out["invalid"]
    return out


def _write_results(
    results_dir: Path | str,
    skill: dict[str, pd.DataFrame],
    heatmaps: dict[str, pd.DataFrame],
    manifest: dict,
) -> None:
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, table in skill.items():
        table.to_csv(out / f"skill_{name}.csv", index=False)
    for name, hm in heatmaps.items():
        hm.to_csv(out / f"heatmap_{name}.csv")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
