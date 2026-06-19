# Tensor-Network Ocean-Acoustic Propagation — Brainstorm Summary

**Date:** 2026-06-19
**Origin:** Idea I1 from the quantum × ocean/acoustics ideation
(`2026-06-17-quantum-ocean-acoustics-ideation.html`), "Tensor-network
(quantum-inspired) solver for ocean acoustic propagation."
**Status:** Direction chosen — a walking-skeleton first experiment.

---

## What we're building

A walking-skeleton **MPS parabolic-equation (PE) range-marcher** that reproduces
**RAM's transmission-loss field** on a deep-water, range-dependent benchmark to an
acceptable tolerance, with bond dimension χ and memory instrumented, and a validation
harness built so an "advantage axis" plugs in next without rework.

The goal is sequenced: understand the idea space first, then land one runnable
experiment. This document captures the experiment.

## Why this idea, briefly

- Underwater sound propagation obeys the Helmholtz/wave equation; for long-range,
  range-varying environments the workhorse is the **parabolic equation (PE)**, which
  marches the acoustic field forward in range. Reference solvers: **RAM** (split-step
  Padé PE), **Kraken** (normal modes), **Bellhop** (rays).
- Represent the depth field as a **matrix-product state (MPS)**; the range march becomes
  "apply a matrix-product operator (the depth propagator), truncate small singular
  values, repeat." If the field stays low **bond dimension (χ)**, you represent a domain
  that would be enormous on a dense grid, cheaply. 3-D PE (where grid memory explodes) is
  where compression could pay most.
- Ocean fields are plausibly low-χ: sound speed varies smoothly and a handful of modes
  dominate, so the field compresses like a smooth signal under a wavelet transform.
- **The honest crux — the bond-dimension question.** Favorable regimes (deep water,
  smooth profile, low/mid frequency, gentle bathymetry) stay low-χ → speed/memory win.
  Unfavorable regimes (high frequency, rough bathymetry, strong scattering, shallow-water
  multipath) drive χ up → compression degrades, possibly slower than RAM. χ is the
  built-in diagnostic for which regime you're in — and the high-χ regime is exactly where
  a future QPU would help. Same through-line as the NISQ philosophy that started this.
- **Asset:** the acoustics community has validated benchmarks (ASA test cases) and
  reference solvers (RAM/Kraken via the Acoustics Toolbox, Python wrappers `pyat`/`arlpy`)
  — ready-made ground truth, the analog of NOAA's Niño 3.4 record for QRC. Tensor tooling
  is mature (`quimb`, `TeNPy`).

## Anchor case

**2-D range-dependent PE, deep-water smooth sound-speed profile**, single representative
low/mid frequency (few propagating modes), validated against RAM. The favorable,
likely-win first case where low χ should show up clearly and the baseline is clean.

## The pieces

- **MPS solver core** — represent the depth field as an MPS; build the PE depth-propagation
  step as a matrix-product operator; march in range with SVD truncation to a set tolerance,
  tracking χ. Use a mature tensor library (`quimb` / `TeNPy`), not hand-rolled tensor algebra.
- **Reference baseline** — RAM (split-step Padé PE) via the Acoustics Toolbox Python wrapper
  (`pyat`/`arlpy`), on the same environment and grid. Ground truth.
- **Validation harness** — compare **transmission loss (dB)**, the standard observable:
  |ΔTL| vs range at fixed receiver depths, plus a full depth×range field error (median /
  95th-percentile). "Faithful" = within a stated dB tolerance over the validity region.
  Instrument χ(range) and peak memory.
- **Pluggable advantage-axis interface** — a slot so the next step (compression scaling,
  χ-frontier, or wall-clock) runs without reworking the comparison (mirrors the QRC
  `AdvantageAxis` pattern).

## Honest success criterion

v1 succeeds if the MPS-PE:
1. matches RAM transmission loss within the stated tolerance on the benchmark,
2. the harness cleanly supports plugging in an advantage axis next, and
3. χ is observed to stay low in this favorable regime (confirming the core bet holds here).

Explicitly **not** goals for v1: beating RAM on wall-clock speed, or handling high-χ /
rough / high-frequency regimes.

## Sequencing (the non-obvious nesting effect)

The TL-error-vs-RAM **validation harness is the scoring function** that the later
χ-frontier sweep — and any AI-agent-driven truncation-tolerance / step-size tuner — will
optimize against. Build the skeleton from day one to *be* that scoring function; don't
retrofit. (This is the natural home for the AI-agent angle: an agent sweeping the
χ/accuracy frontier, analogous to the QRC design-search loop.)

## Open threads / assumptions

- **Advantage axis deferred** — compression-memory vs χ-frontier vs wall-clock, chosen
  after the faithful solver works.
- **PE one-way limitation** — the parabolic equation ignores backscatter; fine for
  deep-water forward propagation, a known modeling boundary to state, not a defect.
- **Validation credibility** — anchor on a published deep-water benchmark with known
  reference TL so RAM itself is trustworthy; have an acoustics colleague sanity-check the
  environment setup and the dB tolerance.
- **Frequency scope** — single representative frequency for v1; the frequency sweep (where
  χ grows) is the frontier work.
- **Reuse the captured discipline** — the leakage-safe / fair-comparison harness learning
  from the QRC work applies here as "validate against a trustworthy reference and make the
  comparison fair an invariant of the harness" (see
  `docs/solutions/architecture-patterns/leakage-safe-sealed-evaluation-harness.md`).
