"""U1 -- environment / import smoke test (no behavioral assertions)."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "qrc_enso",
        "qrc_enso.data",
        "qrc_enso.evaluation",
        "qrc_enso.baselines",
        "qrc_enso.qrc",
        "qrc_enso.experiment",
        "qrc_enso.search",
    ],
)
def test_module_imports(module):
    assert importlib.import_module(module) is not None


def test_core_third_party_imports():
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import reservoirpy  # noqa: F401
    import sklearn  # noqa: F401
