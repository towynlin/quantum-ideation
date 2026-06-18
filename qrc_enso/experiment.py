"""U6 -- matched-comparison runner and sanity gate.

Wires models through the U3 harness at matched readout dimension, emits skill
tables and the spring-barrier heatmap, and asserts the walking-skeleton success
bar (R9): QRC beats persistence at short lead and lands within tolerance of
damped persistence. A failing gate is recorded in the manifest, never hidden.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation import Fold, evaluate_model, skill_by_lead, spring_barrier_heatmap


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
    anomalies: pd.Series,
    models: dict[str, object],
    folds: list[Fold],
    *,
    seed: int = 0,
    require_matched_dims: bool = True,
    damped_tolerance: float = 0.1,
    results_dir: Path | str | None = None,
) -> ExperimentResult:
    manifest: dict = {
        "seed": seed,
        "n_folds": len(folds),
        "models": {},
    }

    # Matched-dimension check (R6): record both dims; refuse to report on
    # mismatch when required, but always leave the mismatch visible in the manifest.
    qrc_dim = getattr(models.get("qrc"), "readout_dim", None)
    esn_dim = getattr(models.get("esn"), "readout_dim", None)
    if qrc_dim is not None and esn_dim is not None:
        manifest["qrc_readout_dim"] = qrc_dim
        manifest["esn_readout_dim"] = esn_dim
        manifest["matched_dims"] = qrc_dim == esn_dim
        if qrc_dim != esn_dim and require_matched_dims:
            raise ValueError(
                f"QRC readout dim {qrc_dim} != ESN readout dim {esn_dim}; "
                "match them or pass require_matched_dims=False to record the mismatch."
            )

    skill: dict[str, pd.DataFrame] = {}
    heatmaps: dict[str, pd.DataFrame] = {}
    for name, model in models.items():
        rows = evaluate_model(model, anomalies, folds)
        skill[name] = skill_by_lead(rows)
        heatmaps[name] = spring_barrier_heatmap(rows)
        manifest["models"][name] = {
            "type": type(model).__name__,
            "readout_dim": getattr(model, "readout_dim", None),
            "params": getattr(model, "params_", None),
        }

    sanity = _sanity_gate(skill, damped_tolerance)
    manifest["sanity"] = sanity

    if results_dir is not None:
        _write_results(results_dir, skill, heatmaps, manifest)

    return ExperimentResult(skill=skill, heatmaps=heatmaps, manifest=manifest, sanity=sanity)


def _sanity_gate(skill: dict[str, pd.DataFrame], damped_tolerance: float) -> dict:
    """R9 walking-skeleton bar. Never raises -- records a verdict."""
    out: dict = {"checks": {}, "passed": None}
    if "qrc" not in skill or "persistence" not in skill:
        out["note"] = "qrc and persistence required for the sanity gate"
        return out

    qrc_l1 = _acc_at_lead(skill["qrc"], 1)
    pers_l1 = _acc_at_lead(skill["persistence"], 1)
    beats_persistence = qrc_l1 > pers_l1
    out["checks"]["qrc_beats_persistence_lead1"] = {
        "qrc_acc": qrc_l1,
        "persistence_acc": pers_l1,
        "passed": bool(beats_persistence),
    }

    checks = [beats_persistence]
    if "damped" in skill:
        qrc_mean = _mean_acc(skill["qrc"])
        damped_mean = _mean_acc(skill["damped"])
        within = qrc_mean >= damped_mean - damped_tolerance
        out["checks"]["qrc_within_damped"] = {
            "qrc_mean_acc": qrc_mean,
            "damped_mean_acc": damped_mean,
            "tolerance": damped_tolerance,
            "passed": bool(within),
        }
        checks.append(within)

    out["passed"] = bool(all(checks))
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
