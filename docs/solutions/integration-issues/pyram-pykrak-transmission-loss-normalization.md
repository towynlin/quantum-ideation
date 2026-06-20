---
title: "pyram vs pykrak transmission loss differ by a constant 4pi (~22 dB) reference-convention offset"
date: 2026-06-19
category: docs/solutions/integration-issues
module: mps_acoustics
problem_type: integration_issue
component: tooling
symptoms:
  - "pyram (RAM PE) and pykrak (KRAKEN normal modes) TL fields differ by a near-constant ~22 dB median over the amplitude-masked region"
  - "the references_agree cross-check gate fails (median ~24.6 dB) even though both fields show identical convergence-zone structure"
  - "pykrak TL is ~22 dB higher (more loss) than physically plausible near-source values (e.g. ~84 dB vs ~58 dB at 1 km)"
root_cause: wrong_api
resolution_type: code_fix
severity: high
tags: [ocean-acoustics, transmission-loss, normalization, pyram, pykrak, cross-validation, reference-convention]
related_components: [testing]
---

# pyram vs pykrak transmission loss differ by a constant 4pi (~22 dB) reference-convention offset

## Problem
When cross-checking the RAM parabolic-equation solver (`pyram`) against the independent KRAKEN normal-mode solver (`pykrak`) on the same range-independent Munk case (U3, R10), the two transmission-loss (TL) fields disagreed by a near-constant ~22 dB even though their convergence-zone structure matched exactly. Taken at face value this fails the `references_agree` trust gate and would block `pyram` from being used as the MPS reference.

## Symptoms
- `pyram` and `pykrak` TL fields differ by a near-constant ~22 dB median over the reference-amplitude-masked region (residual scatter only ~4 dB after removing the offset).
- The `references_agree` median gate fails (~24.6 dB vs a few-dB tolerance) while the *shape* (convergence-zone positions, mode interference) clearly agrees.
- `pykrak` TL is implausibly lossy near the source: ~84 dB at 1 km where cylindrical spreading + duct physics give ~58 dB (which `pyram` produces).

## What Didn't Work
- **Assuming a fitted offset and subtracting `median(pyram - pykrak)`.** This "works" numerically but is exactly the leakage/gerrymandering the project's evaluation discipline forbids: a tuned offset can absorb genuine disagreement and turn a null result into a movable target. An offset is only admissible if it is derived from first principles, not fitted to the data.
- **Suspecting `pyram`'s normalization.** `pyram`'s near-source values are the physically plausible ones; the offset is in `pykrak`, so "correcting" `pyram` would have been wrong.

## Solution
The offset is a first-principles **free-field reference-pressure convention** difference, not a bug in either solver and not a fittable parameter:

- RAM/`pyram` report **TL re 1 m**: `p_ref` is the source's free-field pressure at 1 m.
- `pykrak`'s modal sum returns the pressure of the `1/(4*pi*R)` free-field Green's function, whose 1 m reference pressure is `1/(4*pi)`.

So `TL_correct = -20*log10|p| - 20*log10(4*pi)`. Verify it is a constant (not fitted) by measuring it on **two independent environments** — it was ~21.9 dB on an isovelocity Pekeris waveguide and ~22.4 dB at the source depth on Munk, both matching `20*log10(4*pi) = 21.984 dB`. Then bake the correction into the `pykrak` adapter:

```python
# mps_acoustics/pe_reference.py
_PYKRAK_TL_OFFSET_DB = 20.0 * np.log10(4.0 * np.pi)  # ~21.98 dB

# inside pykrak_reference(...):
# modal sum already includes cylindrical spreading (ranges=None); shift onto
# the re-1 m TL convention pyram uses.
tl = transmission_loss(pressure) - _PYKRAK_TL_OFFSET_DB
```

After the correction the masked **median** `|dTL|` drops to ~3.2 dB (literature-consistent PE-vs-modes agreement) and the trust gate passes.

## Why This Works
`20*log10(4*pi)` is the dB ratio between the two reference pressures (`1` vs `1/(4*pi)`). Because it is a property of the *conventions* the codes use — independent of frequency, profile, or geometry — it reproduces identically across unrelated environments, which is what distinguishes it from a fitted offset. The residual ~3 dB after correction is the genuine pointwise PE-vs-normal-mode disagreement, dominated by interference nulls (a one-bin null shift is tens of dB), which is why the gate uses the robust **median** rather than a null-sensitive p95.

## Prevention
- **When reconciling two physics codes, distinguish a first-principles normalization constant from a fitted offset.** Admit a correction only if you can derive it (here, `4*pi`) and confirm it is invariant across at least two independent test cases. Document the derivation next to the constant so a reviewer can see it was not tuned to pass.
- **Sanity-check absolute levels against simple physics** (near-source cylindrical spreading) to decide *which* code carries the offset, instead of guessing.
- **Gate cross-method agreement on the median**, not the p95 — PE-vs-modes fields legitimately differ by tens of dB at nulls; a null-sensitive statistic will reject a correct reference.
- **Related dependency gotcha (same integration work):** `pykrak`'s Numba kernels call `np.trapz`, removed in NumPy >= 2.0; it raises `AttributeError: module 'numpy' has no attribute 'trapz'` at JIT-compile time. A module-level shim `if not hasattr(np, "trapz"): np.trapz = np.trapezoid` restores it on the shared numpy module object so compilation resolves.

## Related Issues
- `docs/solutions/architecture-patterns/leakage-safe-sealed-evaluation-harness.md` — the pre-registration / no-fitted-goalposts discipline this learning applies (fitted offset = leakage).
- Plan: `docs/plans/2026-06-19-001-feat-mps-pe-ocean-acoustics-plan.md` (U3 / R10, the `pyram`-vs-`pykrak` cross-check).
