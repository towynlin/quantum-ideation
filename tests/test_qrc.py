"""U5 tests -- quantum reservoir adapter (small reservoir for speed)."""

from __future__ import annotations

import numpy as np
import pytest

from qrc_enso.qrc import QRCReservoir

from tests.conftest import ar1_series


def _small(**kw):
    return QRCReservoir(n_qubits=4, n_virtual=2, leads=(1, 3), washout=6, **kw)


def test_exact_features_are_deterministic():
    s = ar1_series(60)
    f1 = _small(seed=1).features(s)
    f2 = _small(seed=1).features(s)
    assert np.allclose(f1, f2)


def test_readout_dim_matches_feature_width():
    s = ar1_series(60)
    r = _small(correlators=False)
    feats = r.features(s)
    assert feats.shape[1] == r.readout_dim == 4 * 2  # qubits x virtual nodes


def test_correlators_expand_feature_dim():
    r = _small(correlators=True)
    # 4 single + C(4,2)=6 pair observables, times 2 virtual nodes.
    assert r.readout_dim == (4 + 6) * 2


def test_only_readout_changes_on_fit():
    s = ar1_series(120)
    r = _small(seed=2)
    angles_before = r._reservoir_angles.copy()
    r.fit(s.iloc[:100])
    assert np.array_equal(angles_before, r._reservoir_angles)  # reservoir is fixed
    assert r._readouts  # but a readout was trained
    assert np.isfinite(r.predict(s.index[99], 1))


def test_more_shots_reduce_expectation_variance():
    from qiskit.quantum_info import Statevector

    lo = QRCReservoir(n_qubits=3, n_virtual=1, shots=64, seed=0)
    hi = QRCReservoir(n_qubits=3, n_virtual=1, shots=4096, seed=0)
    inputs = np.linspace(-1, 1, 6)

    def exact_z0(u):
        sv = (
            Statevector.from_int(0, 2 ** 3)
            .evolve(lo._encode_circuit(u))
            .evolve(lo._reservoir_circuit())
        )
        return lo._z_expectations(sv.data)[0]

    truth = np.array([exact_z0(u) for u in inputs])
    lo_err = np.mean((np.array([lo.shot_expectation(u) for u in inputs]) - truth) ** 2)
    hi_err = np.mean((np.array([hi.shot_expectation(u) for u in inputs]) - truth) ** 2)
    assert hi_err <= lo_err + 1e-9
