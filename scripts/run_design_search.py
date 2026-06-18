"""Tune the QRC via the design-search loop (U7), then report on the sealed set.

The search scores QRC configs on the *development* folds only; the chosen config
is then evaluated on the *sealed* reporting folds the search never saw, so the
reported skill is not overfit. A larger search stride bounds cost.

Usage: python scripts/run_design_search.py [--max-trials N]
"""

from __future__ import annotations

import argparse

import numpy as np

from qrc_enso.baselines import EchoStateNetwork, Persistence
from qrc_enso.data import load_nino34
from qrc_enso.evaluation import evaluate_model, make_folds, skill_by_lead, split_folds
from qrc_enso.experiment import run_experiment
from qrc_enso.qrc import QRCReservoir
from qrc_enso.search import GridSweep, make_qrc_score_fn, run_search

LEADS = (1, 3, 6)

# Config space for the sweep: inject more signal (input_scale), more qubits /
# virtual nodes, and 2-qubit correlators -- the knobs most likely to lift a
# reservoir that is currently under-injecting.
CONFIG_SPACE = [
    {"n_qubits": q, "n_virtual": v, "input_scale": s, "correlators": c, "washout": 12}
    for q in (4, 6)
    for v in (3, 5)
    for s in (3.0, 6.0)
    for c in (False, True)
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-trials", type=int, default=len(CONFIG_SPACE))
    ap.add_argument("--stride", type=int, default=36, help="fold stride (cost knob)")
    args = ap.parse_args()

    sst = load_nino34()
    folds = make_folds(sst, initial_train_months=360, stride_months=args.stride, leads=LEADS)
    dev, sealed = split_folds(folds, dev_fraction=0.7)
    print(f"folds={len(folds)} dev={len(dev)} sealed={len(sealed)}  "
          f"(search on dev, report on sealed)")

    score = make_qrc_score_fn(sst, dev, leads=LEADS)
    result = run_search(score, GridSweep(CONFIG_SPACE), max_trials=args.max_trials)

    print("\nTop configs by dev mean-ACC:")
    for trial in result.ranked()[:5]:
        print(f"  {trial.score:+.3f}  {trial.config}")
    failed = [t for t in result.log if t.score is None]
    if failed:
        print(f"({len(failed)} configs failed to evaluate)")

    if not result.ranked():
        print("No config produced a finite score.")
        return

    best = result.ranked()[0].config
    print(f"\nBest dev config: {best}")

    # Honest report: evaluate the chosen config on the SEALED folds, alongside
    # baselines, with the same matched-dimension comparison.
    qrc = QRCReservoir(leads=LEADS, **best)
    esn = EchoStateNetwork(units=qrc.readout_dim, leads=LEADS, tune=True)
    res = run_experiment(
        sst, {"persistence": Persistence(), "esn": esn, "qrc": qrc}, sealed,
        require_matched_dims=True,
    )
    print("\nSealed-set skill (the honest number):")
    for name, table in res.skill.items():
        print(f"  {name:12s} {dict(zip(table['lead'], table['acc'].round(3)))}")
    print(f"  sanity_passed={res.sanity['passed']} invalid={res.sanity['invalid']}")


if __name__ == "__main__":
    main()
