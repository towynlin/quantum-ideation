---
title: Enforce leakage-safety and a sealed reporting partition in the evaluation harness
date: 2026-06-17
category: architecture-patterns
module: qrc_enso/evaluation
problem_type: architecture_pattern
component: testing_framework
severity: high
applies_when:
  - Cross-validating an autocorrelated time series (climate, geophysics, finance)
  - Comparing a reservoir or quantum model against tuned classical baselines
  - Running a hyperparameter or design search whose objective is held-out skill
  - A normalization or climatology step precedes the cross-validation split
related_components:
  - tooling
tags:
  - leakage-safety
  - time-series-cv
  - reservoir-computing
  - evaluation-harness
  - sealed-partition
  - quantum-ml
  - overfitting
  - fair-comparison
---

# Enforce leakage-safety and a sealed reporting partition in the evaluation harness

## Context

Building a quantum-reservoir-computing pipeline to forecast the ENSO / Nino 3.4 index, the whole point was a *trustworthy* comparison: no train/test leakage, and a fair fight against tuned classical baselines. The first build passed 38 tests and produced plausible skill numbers — yet a code review surfaced two silent ways the scientific claim could be false, and the first real tuning run confirmed one of them dramatically. The lesson generalizes to any ML evaluation harness for autocorrelated data: the guarantees that make results trustworthy must be **structural properties of the harness**, not conventions the caller is trusted to follow.

## Guidance

Two guarantees belong *inside* the harness, enforced by its data flow, and each needs a test that fails when the guarantee is violated.

**1. Normalize per fold, inside the evaluation loop — never globally before splitting.**
Folds carry the **raw** series. The harness fits a fresh normalizer on each fold's *training window only* and uses it to transform both the training input and the verification target. A normalizer that is correct in isolation but is never called per fold leaves leakage-safety to caller discipline — and it will eventually be called wrong (fit on the whole series), with no crash and believable output.

**2. Seal a reporting partition away from any search.**
When a hyperparameter or design search optimizes held-out skill, split folds into a **development** set (the search sees these) and a **sealed reporting** set (final numbers come from these; the search never touches them). Otherwise the search overfits the very folds you report on, and the headline number is inflated.

**3. Test both by contradiction.** Perturb a future (test-span) value and assert an earlier fold's training values and predictions are unchanged. Assert the dev and reporting fold sets are disjoint. Unit-testing the normalizer alone does not prove the assembled pipeline is leakage-free.

The same "enforce, don't trust" stance covers comparison fairness: matched readout dimension, equal washout, and an equally-tuned baseline are harness invariants, not reviewer goodwill.

## Why This Matters

In research and ML pipelines the dangerous failures are **silent**. Leakage and search-overfit do not throw — they produce optimistic, wrong results behind a green test suite. A pipeline whose only leakage guard is "the caller passes raw data and remembers to renormalize per fold" is one convenient helper call away from invalidating every conclusion it produces, and nothing will tell you.

The sealed partition is what catches the overfit before you publish it: in this project the design search reached **+0.67 mean ACC on the development folds but −0.99 on the sealed folds** with the same config. Without the split, the +0.67 would have been reported as success. With it, the harness exposed that the tuned quantum reservoir does not generalize — the honest, correct result.

## When to Apply

- Cross-validating any autocorrelated series (shuffled / k-fold splits leak; use expanding-window rolling-origin).
- Any normalization, standardization, or climatology step that could see the test span.
- Any automated search (grid, Bayesian, or agent-driven) whose objective is held-out performance.
- Comparing a new method against baselines where an untuned or differently-preprocessed baseline would be an unfair foil.

## Examples

Leakage moved from caller discipline into the harness:

```python
# BEFORE — leakage-safety depends on the caller doing the right thing:
anom = MonthlyAnomalyNormalizer().fit(sst.loc[:"2000"]).transform(sst)  # one fixed split
folds = make_folds(anom)                 # folds built on globally-normalized data
evaluate_model(model, anom, folds)       # harness never renormalizes per fold

# AFTER — the harness owns the guarantee; folds carry RAW data:
folds = make_folds(sst)                  # raw SST
def evaluate_model(model, series, folds, *, normalize=True):
    for fold in folds:
        norm = MonthlyAnomalyNormalizer().fit(fold.train)   # train window only
        model.fit(norm.transform(fold.train))
        for lead, target in fold.targets.items():
            obs = norm.transform(series.loc[[target]]).iloc[0]   # target uses train climatology
            ...  # record model.predict(fold.origin, lead) vs obs
```

Sealed reporting partition for a search:

```python
dev, sealed = split_folds(folds, dev_fraction=0.7)   # disjoint by origin; dev earlier
best = run_search(make_qrc_score_fn(series, dev), proposer).ranked()[0].config
# Report the chosen config on the SEALED folds the search never saw:
run_experiment(series, {"persistence": ..., "qrc": QRCReservoir(**best)}, sealed)
```

The leakage test that makes the guarantee real:

```python
raw2 = raw.copy()
raw2.iloc[future_pos] += 10.0   # perturb a month after fold0's targets
r1 = evaluate_model(Persistence(), raw,  [fold0])
r2 = evaluate_model(Persistence(), raw2, [fold0])
pd.testing.assert_frame_equal(r1, r2)   # a future change cannot reach an earlier fold
```

## Related

- Adjacent corollary captured in the same work: a pre-anomalized data source (`nina34.anom.csv`) silently defeats per-fold normalization — source the raw series so each fold has a real value to anomalize.
