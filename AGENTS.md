# AGENTS.md

Quantum reservoir computing for ENSO / Niño 3.4 forecasting — a research pipeline
that scores a quantum reservoir against tuned classical baselines with
leakage-safe, fair cross-validation. The deliverable is the harness and the
honest comparison, not (yet) a model that beats the baselines.

## Layout

```
qrc_enso/            # library: data, evaluation, baselines, qrc, experiment, search (U1-U7)
tests/               # pytest suite (leakage-safety and fairness are the load-bearing tests)
scripts/             # run_baseline_experiment.py, run_design_search.py
docs/plans/          # implementation plans (decision artifacts)
docs/solutions/      # documented learnings (bugs, patterns, conventions), organized by
                     #   category with YAML frontmatter (module, tags, problem_type).
                     #   Relevant when implementing or debugging in a documented area.
CONCEPTS.md          # shared domain vocabulary (Rolling-origin fold, Sealed reporting
                     #   partition, Advantage axis, Sanity gate, Reservoir, Readout, ...).
                     #   Relevant when orienting to the codebase or discussing domain concepts.
```

## Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[quantum,dev]"   # quantum extra pulls qiskit + qiskit-aer
.venv/bin/python -m pytest -q               # 41 tests
```

Verified on Python 3.14 (numpy 2.4, pandas 3.0, scikit-learn 1.6, reservoirpy 0.4.2,
qiskit 2.4, qiskit-aer 0.17). `scikit-learn` is pinned `<1.7` for `reservoirpy[sklearn]`.

## Conventions

- The data/evaluation/baseline core imports without the `quantum` extra; all qiskit
  imports are lazy inside `qrc_enso/qrc.py`.
- Leakage-safety and fair comparison are harness invariants, not caller discipline —
  see `docs/solutions/architecture-patterns/leakage-safe-sealed-evaluation-harness.md`
  before touching `qrc_enso/evaluation.py`, normalization, or the search loop.
- `data/` and `results/` are regenerated and gitignored.
