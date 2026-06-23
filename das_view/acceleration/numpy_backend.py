"""NumPy implementation of the acceleration backend contract."""

from __future__ import annotations

import numpy as np


def numpy_array_module():
    """Return NumPy as the CPU array module."""

    return np


def as_numpy_array(data, *, dtype=float):
    """Convert input to a NumPy array."""

    return np.asarray(data, dtype=dtype)
