"""Quantum reservoir computing for ENSO / Nino 3.4 forecasting (walking skeleton).

Module map (see docs/plans/2026-06-17-001-feat-qrc-enso-forecasting-pipeline-plan.md):

- data        U2  ingestion + leakage-safe anomalies
- evaluation  U3  rolling-origin CV, ACC/RMSE, spring-barrier, advantage-axis protocol
- baselines   U4  persistence, damped persistence, tuned ESN
- qrc         U5  quantum reservoir adapter + ridge readout (optional `quantum` extra)
- experiment  U6  matched-comparison runner + sanity gate
- search      U7  agent design-search loop + leaderboard
"""

__version__ = "0.1.0"
