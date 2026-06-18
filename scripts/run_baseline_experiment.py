"""Run the fixed-config walking-skeleton experiment on real NOAA data (U6).

Loads the raw Nino 3.4 SST series, builds leakage-safe rolling-origin folds, and
scores persistence, damped persistence, a tuned ESN, and a fixed QRC config
through the harness, writing skill tables + the spring-barrier heatmap +
manifest to results/.

Usage: python scripts/run_baseline_experiment.py
"""

from __future__ import annotations

from qrc_enso.baselines import DampedPersistence, EchoStateNetwork, Persistence
from qrc_enso.data import load_nino34
from qrc_enso.evaluation import make_folds
from qrc_enso.experiment import run_experiment
from qrc_enso.qrc import QRCReservoir

LEADS = (1, 3, 6, 9, 12)


def main() -> None:
    sst = load_nino34()
    print(f"Loaded raw Nino 3.4 SST: {len(sst)} months, "
          f"{sst.index.min().date()} -> {sst.index.max().date()}")

    folds = make_folds(sst, initial_train_months=480, stride_months=12, leads=LEADS)
    qrc = QRCReservoir(n_qubits=5, n_virtual=3, leads=LEADS, washout=12, input_scale=3.0)
    models = {
        "persistence": Persistence(),
        "damped": DampedPersistence(),
        "esn": EchoStateNetwork(units=qrc.readout_dim, leads=LEADS, tune=True),
        "qrc": qrc,
    }
    res = run_experiment(sst, models, folds, require_matched_dims=True, results_dir="results")

    for name, table in res.skill.items():
        accs = dict(zip(table["lead"], table["acc"].round(3)))
        print(f"{name:12s} ACC by lead: {accs}")
    print(f"matched_dims={res.manifest['matched_dims']} "
          f"sanity_passed={res.sanity['passed']} invalid={res.sanity['invalid']}")
    print("Wrote skill tables, heatmaps, and manifest to results/")


if __name__ == "__main__":
    main()
