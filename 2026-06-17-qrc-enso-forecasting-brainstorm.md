# Quantum Reservoir Computing for ENSO Forecasting — Brainstorm Summary

**Date:** 2026-06-17
**Origin:** Seeded from ce-ideate idea "Quantum reservoir computing for chaotic ocean forecasting"
(`/tmp/compound-engineering/ce-ideate/95183e24/2026-06-17-quantum-ocean-acoustics-ideation.html`),
itself inspired by The New Quantum Era E97 (Maniscalco / Algorithmiq) and the NISQ-era
hybrid quantum-classical philosophy.
**Status:** Direction chosen — a walking-skeleton first experiment.

---

## What we're building

A walking-skeleton experiment that tests whether a **quantum reservoir** can produce a sane
**Niño 3.4 (ENSO) forecast**, wrapped from the start in an **AI-agent design-search loop**, with an
evaluation harness built so any "advantage axis" can be plugged in next without rework.

The goal is sequenced: **understand the idea space first, then land one runnable experiment.**
This document captures the second half — the concrete experiment.

## Why this idea, briefly

- **Reservoir computing** uses a *fixed* (untrained) nonlinear dynamical system to create a
  high-dimensional echo of an input time series; only a **linear readout** is trained. Cheap to
  train, strong on chaotic short-horizon forecasting. The classical workhorse is the Echo State
  Network (ESN).
- **Quantum reservoir computing (QRC)** swaps in a few qubits under fixed dynamics; the 2ⁿ state
  space is the bet for a richer feature space from few qubits. Because the reservoir is never
  trained, QRC is unusually **noise-tolerant** — one of the few quantum-ML ideas honestly plausible
  on today's hardware.
- **The gap is real but the bar is honest:** classical ESNs already forecast ENSO well and cheaply.
  Most published QRC wins are on *synthetic* benchmarks (NARMA, Lorenz), not real geophysical data.
  So this is "first test of whether the synthetic-benchmark advantage survives contact with messy
  ocean data," **not** "build a better ENSO forecaster."

## Target signal: Niño 3.4

Chosen for tractability and a clean comparison: low-dimensional monthly index, ~70-year reliable
record, strong public baselines, and a built-in hard sub-problem — the **boreal-spring
predictability barrier** (forecasts initialized before spring degrade sharply).

## The pieces

- **Data** — NOAA Niño 3.4 monthly index (ERSSTv5), reliable ~1950–present. Univariate to start.
  Time-ordered train/test split, no leakage (e.g., rolling-origin).
- **Task** — predict the Niño 3.4 anomaly at lead times of 1 / 3 / 6 / 9 / 12 months.
- **QRC core** — a few qubits (~4–8) under fixed dynamics (e.g., transverse-field Ising or a fixed
  random circuit); inject the index as input-dependent rotations; temporal multiplexing for memory;
  measure 1- and 2-qubit observables as features; train a **linear (ridge) readout** only.
  Noiseless simulator → noisy simulator → optional cloud-QPU spot check.
- **Baselines (built first — the floor and the real competitor)**
  - Persistence + damped persistence (trivial floors)
  - A tuned **classical ESN** with a *matched* readout — the head-to-head that decides whether the
    quantum reservoir adds anything
  - A simple AR / linear model for context
- **Evaluation harness** — Anomaly Correlation Coefficient (ACC) + RMSE vs lead time,
  **stratified by initialization month** so the spring barrier is visible. Matched-fairness rules:
  same split, same readout, same inputs for QRC and ESN.
- **AI-agent loop** — the harness's skill score is the objective for an agent that proposes reservoir
  configurations (qubit count, dynamics parameters, input encoding, observable set, multiplexing)
  and iterates. This is the Algorithmiq-style active-learning loop pointed at *reservoir design*
  instead of drug variants.

## Success criterion (deliberately honest)

v1 succeeds if QRC:
1. clearly **beats persistence**, and
2. lands in the **neighborhood of the tuned ESN**, and
3. the harness cleanly supports plugging in an advantage axis next.

Explicitly **not** a goal for v1: beating operational dynamical ENSO models.

## Sequencing (the one non-obvious dependency)

"Baseline first" and "bake in the agent loop now" nest rather than conflict: the design-search loop
needs a working QRC forward pass **and** a skill metric to rank configs. So build the skeleton
(QRC forward pass + baselines + metric) *designed from day one to be the loop's inner scoring
function*, then switch the loop on the moment the skeleton runs — don't retrofit it.

## Open threads / assumptions

- **Advantage axis deferred** — choose *after* the baseline runs. Candidates:
  - *Footprint efficiency* — match ESN skill with far fewer reservoir features/parameters (fix skill,
    compare size). Cleanest first result.
  - *Data efficiency* — keep more skill than an ESN when the training window is shortened (relevant:
    only ~70 yr of reliable record).
  - *Spring-barrier skill* — hold skill across the spring predictability barrier better than classical
    baselines (skill stratified by initialization month). Most ocean-science-interesting.
- **Simulator-first** — Qiskit / PennyLane simulator is sufficient for v1; a cloud QPU run (e.g. IBM
  free tier) is optional validation, not a blocker.
- **Credibility check** — have an ENSO-literate colleague vet the train/test split and metrics before
  claiming any "win," so the comparison survives scrutiny. Natural on-ramp to bringing a collaborator
  in later.
- **Scope discipline** — univariate Niño 3.4 only for v1; resist adding predictors, spatial fields, or
  other indices until the skeleton + baseline are trustworthy.
