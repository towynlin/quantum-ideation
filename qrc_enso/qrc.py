"""U5 -- quantum reservoir adapter with a ridge readout.

Implements the Fujii-Nakajima encode -> evolve -> observe scheme with temporal
multiplexing, on a fixed disordered circuit. The reservoir is never trained;
only a linear (ridge) readout is, and a **separate readout per lead** gives
direct (origin, lead) forecasting.

The adapter builds the reservoir directly on qiskit + Aer rather than wrapping
quantumreservoirpy: that package (v0.2) predates qiskit 2.x and exposes only a
shot-based ``get_counts`` path. Building here gives an exact-expectation
(deterministic, statevector) feature path plus a seeded shot path, isolates the
quantum dependency behind one class, and keeps a PennyLane swap open. All qiskit
imports are lazy so the data/evaluation/baseline core imports without the
``quantum`` extra installed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluation import fit_ridge


class QRCReservoir:
    """Fixed quantum reservoir + per-lead ridge readout (direct forecasting).

    Readout feature dimension is ``n_qubits * n_virtual`` (1-qubit Z observables),
    plus ``C(n_qubits, 2) * n_virtual`` when ``correlators`` is set. The dimension
    is reported so :mod:`qrc_enso.experiment` can match it against the ESN (R6).

    Features come from the exact statevector and are deterministic by
    construction; :meth:`shot_expectation` is a seeded shot path for the
    shot-variance check only.
    """

    def __init__(
        self,
        n_qubits: int = 5,
        n_virtual: int = 4,
        leads: tuple[int, ...] = (1, 3, 6, 9, 12),
        *,
        input_scale: float = 1.0,
        correlators: bool = False,
        washout: int = 12,
        ridge: float = 1e-4,
        shots: int = 1024,
        seed: int = 0,
    ) -> None:
        self.n_qubits = n_qubits
        self.n_virtual = n_virtual
        self.leads = leads
        self.input_scale = input_scale
        self.correlators = correlators
        self.washout = washout
        self.ridge = ridge
        self.shots = shots
        self.seed = seed
        self._reservoir_angles = self._init_reservoir_angles(seed)
        self._signs, self._corr_pairs = self._precompute_observables()
        self._cached_reservoir = None  # built lazily, reused across all steps/folds
        self._readouts: dict[int, tuple[np.ndarray, float]] = {}
        self._last_features: np.ndarray | None = None

    # -- public dimensions --------------------------------------------------
    @property
    def readout_dim(self) -> int:
        base = self.n_qubits + len(self._corr_pairs)
        return base * self.n_virtual

    # -- precomputed observable basis --------------------------------------
    def _precompute_observables(self) -> tuple[np.ndarray, list[tuple[int, int]]]:
        idx = np.arange(2 ** self.n_qubits)
        bits = ((idx[:, None] >> np.arange(self.n_qubits)[None, :]) & 1).astype(float)
        signs = 1.0 - 2.0 * bits  # (-1)^bit  -> +1 for |0>, -1 for |1>; shape (2^n, n)
        pairs = (
            [(i, j) for i in range(self.n_qubits) for j in range(i + 1, self.n_qubits)]
            if self.correlators
            else []
        )
        return signs, pairs

    def _z_expectations(self, state: np.ndarray) -> np.ndarray:
        probs = np.abs(state) ** 2
        z = probs @ self._signs  # <Z_i> per qubit
        if not self._corr_pairs:
            return z
        corr = np.array([probs @ (self._signs[:, i] * self._signs[:, j]) for i, j in self._corr_pairs])
        return np.concatenate([z, corr])

    # -- reservoir definition ----------------------------------------------
    def _init_reservoir_angles(self, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        # Fixed disordered single-qubit rotation angles, one (ry, rz) pair per qubit.
        return rng.uniform(0, 2 * np.pi, size=(self.n_qubits, 2))

    def _reservoir_circuit(self):
        if self._cached_reservoir is None:
            from qiskit import QuantumCircuit

            qc = QuantumCircuit(self.n_qubits)
            for q in range(self.n_qubits):
                qc.ry(float(self._reservoir_angles[q, 0]), q)
                qc.rz(float(self._reservoir_angles[q, 1]), q)
            for q in range(self.n_qubits):  # ring of entanglers
                qc.cx(q, (q + 1) % self.n_qubits)
            self._cached_reservoir = qc
        return self._cached_reservoir

    def _encode_circuit(self, u: float):
        from qiskit import QuantumCircuit

        qc = QuantumCircuit(self.n_qubits)
        angle = float(np.arctan(self.input_scale * u))  # bounded encoding
        for q in range(self.n_qubits):
            qc.rx(2.0 * angle, q)
        return qc

    # -- exact feature extraction (statevector) ----------------------------
    def _feature_series(self, anomalies: np.ndarray) -> np.ndarray:
        """Continuous-injection reservoir features, one row per input timestep."""
        from qiskit.quantum_info import Statevector

        state = Statevector.from_int(0, 2 ** self.n_qubits)
        reservoir = self._reservoir_circuit()
        rows = []
        for u in anomalies:
            state = state.evolve(self._encode_circuit(u))
            virtual = []
            for _ in range(self.n_virtual):
                state = state.evolve(reservoir)
                virtual.append(self._z_expectations(state.data))
            rows.append(np.concatenate(virtual))
        return np.asarray(rows)

    # -- seeded shot path (for the shot-variance test) ---------------------
    def shot_expectation(self, u: float, qubit: int = 0) -> float:
        """Estimate <Z_qubit> after one encode+reservoir step via seeded shots."""
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator

        qc = QuantumCircuit(self.n_qubits, 1)
        qc.compose(self._encode_circuit(u), inplace=True)
        qc.compose(self._reservoir_circuit(), inplace=True)
        qc.measure(qubit, 0)
        sim = AerSimulator(seed_simulator=self.seed)
        counts = sim.run(transpile(qc, sim), shots=self.shots).result().get_counts()
        p1 = counts.get("1", 0) / self.shots
        return 1.0 - 2.0 * p1

    # -- readout ------------------------------------------------------------
    def features(self, series: pd.Series) -> np.ndarray:
        """Exact reservoir feature matrix for a series (washout not yet dropped)."""
        return self._feature_series(series.to_numpy(dtype=float))

    def fit(self, train: pd.Series) -> "QRCReservoir":
        x = train.to_numpy(dtype=float)
        feats = self._feature_series(x)
        self._last_features = feats[-1]
        w0 = self.washout
        self._readouts = {}
        for lead in self.leads:
            if len(x) <= w0 + lead:
                continue
            self._readouts[lead] = fit_ridge(feats[w0:-lead], x[w0 + lead:], self.ridge)
        return self

    def predict(self, origin: pd.Timestamp, lead: int) -> float:
        if self._last_features is None or lead not in self._readouts:
            return 0.0
        w, b = self._readouts[lead]
        return float(self._last_features @ w + b)
