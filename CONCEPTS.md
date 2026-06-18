# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or catch-all.

## Evaluation and comparison

### Rolling-origin fold
One unit of cross-validation: a raw training window ending at an *origin* month, plus the verification targets at each forecast lead after that origin.

Folds carry **raw** (un-normalized) data so the harness can normalize each fold on its own training window. Training never overlaps a target month, so a fold is leakage-free by construction. Folds expand (each later origin sees a longer training window); shuffled or k-fold splits are never used because the series is strongly autocorrelated.

### Development folds / Sealed reporting partition
A disjoint split of the folds: the **development** folds are the only ones a design or hyperparameter search may score against, and the **sealed reporting partition** is the later set, held back so final skill numbers come from folds the search never saw.

The split is what keeps a search honest — a config tuned on the development folds is judged on the sealed folds, exposing overfit (strong development skill, collapsed sealed skill) instead of hiding it.

### Leakage-safe anomaly normalization
The per-fold conversion of raw values to anomalies using a climatology computed from that fold's training window alone — never the whole series or any test span.

This guarantee lives in the harness, not in caller convention: the evaluation loop fits the normalizer per fold and applies it to both the training input and the verification target.

### Sanity gate
The honest pass/fail check on a run: whether the quantum model clears the trivial floor and lands within reach of the strong baseline, recorded as a verdict (including an explicit invalid flag for degenerate runs) rather than silently passing.

### Advantage axis
The specific dimension along which the quantum model is claimed to beat classical baselines — e.g. parameter footprint, data efficiency, or skill across the predictability barrier. The harness exposes a pluggable slot for one; a concrete axis is chosen and implemented only when the baseline comparison is trustworthy.

### Matched readout dimension
The fairness invariant requiring the quantum and classical models to expose the same number of readout features before their skill is compared, so a capacity difference cannot masquerade as an architectural advantage.

## Reservoir model

### Reservoir
A fixed, never-trained dynamical system (classical recurrent network, or a quantum circuit) that maps an input time series into a high-dimensional set of features; only the readout on top of it is trained.

### Readout
The single trained component sitting on top of a reservoir — a linear (ridge) regression from reservoir features to the forecast target, trained separately per forecast lead for direct multi-horizon prediction.
