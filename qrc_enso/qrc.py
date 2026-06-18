"""U5 -- quantum reservoir adapter with a ridge readout.

Implements the Fujii-Nakajima encode -> evolve -> observe scheme with temporal
multiplexing, on a fixed disordered circuit. The reservoir is never trained;
only a linear (ridge) readout is, and a **separate readout per lead** gives
direct (origin, lead) forecasting.

The adapter builds the reservoir directly on qiskit + Aer rather than wrapping
quantumreservoirpy: that package (v0.2) predates qiskit 2.x and exposes only a
shot-based ``get_counts`` path. Building here gives an exact-expectation
(seeded, deterministic) feature path plus a seeded shot path, isolates the
quantum dependency behind one class, and keeps a PennyLane swap open. All qiskit
imports are lazy so the data/evaluation/baseline core imports without the
``quantum`` extra installed.

Determinism: exact-expectation features come from the statevector and are
deterministic by construction; the seeded shot path is for the shot-variance
check only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class QRCReservoir:
    """Fixed quantum reservoir + per-lead ridge readout (direct forecasting).

    Readout feature dimension is ``n_qubits * n_virtual`` (1-qubit Z observables),
    plus ``C(n_qubits, 2) * n_virtual`` when ``correlators`` is set. The dimension
    is reported so :mod:`qrc_enso.experiment` can match it against the ESN (R6).
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
        exact: bool = True,
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
        self.exact = exact
        self.seed = seed
        self._reservoir_angles = self._init_reservoir_angles(seed)
        self._readouts: dict[int, tuple[np.ndarray, float]] = {}
        self._last_features: np.ndarray | None = None

    # -- public dimensions --------------------------------------------------
    @property
    def readout_dim(self) -> int:
        base = self.n_qubits
        if self.correlators:
            base += self.n_qubits * (self.n_qubits - 1) // 2
        return base * self.n_virtual

    # -- reservoir definition ----------------------------------------------
    def _init_reservoir_angles(self, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        # Fixed disordered single-qubit rotation angles, one (ry, rz) pair per qubit.
        return rng.uniform(0, 2 * np.pi, size=(self.n_qubits, 2))

    def _reservoir_circuit(self):
        from qiskit import QuantumCircuit

        qc = QuantumCircuit(self.n_qubits)
        for q in range(self.n_qubits):
            qc.ry(float(self._reservoir_angles[q, 0]), q)
            qc.rz(float(self._reservoir_angles[q, 1]), q)
        for q in range(self.n_qubits):  # ring of entanglers
            qc.cx(q, (q + 1) % self.n_qubits)
        return qc

    def _encode_circuit(self, u: float):
        from qiskit import QuantumCircuit

        qc = QuantumCircuit(self.n_qubits)
        angle = float(np.arctan(self.input_scale * u))  # bounded encoding
        for q in range(self.n_qubits):
            qc.rx(2.0 * angle, q)
        return qc

    # -- exact feature extraction (statevector) ----------------------------
    @staticmethod
    def _z_expectations(state: np.ndarray, n_qubits: int, correlators: bool) -> np.ndarray:
        probs = np.abs(state) ** 2
        idx = np.arange(len(probs))
        bits = ((idx[:, None] >> np.arange(n_qubits)[None, :]) & 1).astype(float)
        signs = 1.0 - 2.0 * bits  # (-1)^bit  -> +1 for |0>, -1 for |1>
        z = probs @ signs  # <Z_i> per qubit
        feats = [z]
        if correlators:
            corr = []
            for i in range(n_qubits):
                for j in range(i + 1, n_qubits):
                    corr.append(probs @ (signs[:, i] * signs[:, j]))
            feats.append(np.array(corr))
        return np.concatenate(feats)

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
                virtual.append(
                    self._z_expectations(state.data, self.n_qubits, self.correlators)
                )
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

    # -- ridge readout ------------------------------------------------------
    def _fit_ridge(self, feats: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
        fc = feats - feats.mean(axis=0, keepdims=True)
        tc = target - target.mean()
        w = np.linalg.solve(
            fc.T @ fc + self.ridge * np.eye(fc.shape[1]), fc.T @ tc
        )
        bias = float(target.mean() - feats.mean(axis=0) @ w)
        return w, bias

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
            f = feats[w0:-lead]
            y = x[w0 + lead:]
            self._readouts[lead] = self._fit_ridge(f, y)
        return self

    def predict(self, origin: pd.Timestamp, lead: int) -> float:
        if self._last_features is None or lead not in self._readouts:
            return 0.0
        w, b = self._readouts[lead]
        return float(self._last_features @ w + b)
