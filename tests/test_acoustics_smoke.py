"""U1 -- acoustics environment / import smoke test (no behavioral assertions)."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "mps_acoustics",
        "mps_acoustics.environment",
        "mps_acoustics.pe_reference",
        "mps_acoustics.mps_field",
        "mps_acoustics.propagator",
        "mps_acoustics.validation",
        "mps_acoustics.experiment",
    ],
)
def test_module_imports(module):
    assert importlib.import_module(module) is not None


def test_acoustics_third_party_imports():
    import pyram  # noqa: F401
    import pykrak  # noqa: F401
    import quimb  # noqa: F401
