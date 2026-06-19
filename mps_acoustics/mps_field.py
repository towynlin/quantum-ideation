"""U4 -- MPS (QTT) representation of the depth field and TL extraction.

Encodes a depth-sampled complex acoustic field as a ``quimb`` matrix-product
state over ``log2(Nz)`` sites (the quantized tensor-train / QTT encoding), and
extracts transmission loss back from it via the shared U3 TL function. The state
bond dimension chi -- the quantity the core scientific bet is about (does the
ocean field stay low-chi?) -- is read out here.

All ``quimb`` calls are isolated behind this module with lazy imports, mirroring
the adapter-isolation pattern in ``qrc_enso/qrc.py`` so the package imports
without the ``acoustics`` extra installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .pe_reference import transmission_loss

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quimb.tensor import MatrixProductState


def _n_sites(nz: int) -> int:
    """log2(Nz), requiring a power-of-two depth grid (QTT constraint)."""
    if nz < 2 or (nz & (nz - 1)):
        raise ValueError(f"Field length {nz} is not a power of two >= 2 (QTT requirement).")
    return nz.bit_length() - 1


def encode_field(
    field: np.ndarray,
    *,
    max_bond: int | None = None,
    cutoff: float = 1e-10,
) -> "MatrixProductState":
    """Encode a 1-D complex depth field as a QTT matrix-product state.

    The length-``Nz`` field is reshaped over ``log2(Nz)`` binary sites and split
    by successive SVDs, discarding singular values below ``cutoff`` (relative)
    and capping the bond dimension at ``max_bond`` when given. A smooth
    (low-depth-order) field compresses to low chi; a structureless field does
    not -- the readout from :func:`state_chi` reflects that.
    """
    arr = np.asarray(field)
    if arr.ndim != 1:
        raise ValueError(f"Field must be 1-D over depth; got shape {arr.shape}.")
    n = _n_sites(arr.size)

    from quimb.tensor import MatrixProductState

    return MatrixProductState.from_dense(
        arr.astype(complex),
        dims=[2] * n,
        max_bond=max_bond,
        cutoff=cutoff,
    )


def decode_field(mps: "MatrixProductState") -> np.ndarray:
    """Contract the MPS back to a dense 1-D complex depth field."""
    return np.asarray(mps.to_dense()).ravel()


def state_chi(mps: "MatrixProductState") -> int:
    """The state bond dimension chi (maximum MPS bond)."""
    return int(mps.max_bond())


def extract_tl(
    mps: "MatrixProductState",
    ranges: np.ndarray | float | None = None,
) -> np.ndarray:
    """Transmission loss from the MPS pressure, via the shared U3 TL function.

    Identical to taking the TL of the decoded dense field; ``ranges`` is passed
    through to :func:`mps_acoustics.pe_reference.transmission_loss` for the
    cylindrical-spreading convention (PE pressure excludes the ``1/sqrt(r)``
    term).
    """
    return transmission_loss(decode_field(mps), ranges)


def encode_decode(
    field: np.ndarray,
    *,
    max_bond: int | None = None,
    cutoff: float = 1e-10,
) -> tuple[np.ndarray, int]:
    """Convenience: encode then decode, returning ``(reconstructed, chi)``."""
    mps = encode_field(field, max_bond=max_bond, cutoff=cutoff)
    return decode_field(mps), state_chi(mps)
