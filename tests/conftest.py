"""Shared test cleanup fixtures."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def close_matplotlib_figures():
    """Close figures created by plotting tests after each test."""

    yield
    if "matplotlib.pyplot" in sys.modules:
        import matplotlib.pyplot as plt

        plt.close("all")
