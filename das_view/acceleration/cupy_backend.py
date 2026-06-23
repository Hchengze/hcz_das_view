"""Lazy CuPy helpers for optional GPU acceleration."""

from __future__ import annotations

import sys


def import_cupy():
    """Import CuPy lazily and raise ImportError when unavailable."""

    try:
        import cupy as cp
    except ImportError as exc:
        raise ImportError("CuPy is not installed") from exc
    return cp


def is_cupy_available() -> bool:
    """Return True when CuPy can be imported."""

    try:
        import_cupy()
    except ImportError:
        return False
    return True


def cupy_array_module(*, only_if_loaded: bool = False):
    """Return the CuPy module.

    ``only_if_loaded`` avoids importing CuPy during passive type checks.
    """

    if only_if_loaded:
        module = sys.modules.get("cupy")
        if module is None:
            raise ImportError("CuPy has not been imported")
        return module
    return import_cupy()


def as_cupy_array(data, *, dtype=float):
    """Convert input to a CuPy array."""

    cp = import_cupy()
    return cp.asarray(data, dtype=dtype)


def cupy_to_numpy(array):
    """Copy a CuPy array back to NumPy."""

    cp = import_cupy()
    return cp.asnumpy(array)
