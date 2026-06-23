"""Backend selection for optional CPU/GPU array operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.acceleration.cupy_backend import (
    as_cupy_array,
    cupy_array_module,
    cupy_to_numpy,
    import_cupy,
    is_cupy_available,
)
from das_view.acceleration.numpy_backend import as_numpy_array, numpy_array_module

BackendName = Literal["cpu", "gpu", "auto"]


@dataclass(frozen=True, slots=True)
class AccelerationBackend:
    """Resolved array backend description."""

    requested: BackendName
    name: Literal["cpu", "gpu"]
    array_module: object
    available: bool
    reason: str


def get_acceleration_backend(name: BackendName = "auto") -> AccelerationBackend:
    """Resolve an acceleration backend.

    ``auto`` intentionally resolves to CPU in Phase 9A.  GPU is only selected
    when a caller explicitly requests ``name="gpu"``.
    """

    normalized = _normalize_backend_name(name)
    if normalized in ("cpu", "auto"):
        reason = "CPU backend selected" if normalized == "cpu" else "auto defaults to CPU"
        return AccelerationBackend(
            requested=normalized,
            name="cpu",
            array_module=numpy_array_module(),
            available=True,
            reason=reason,
        )

    try:
        xp = import_cupy()
    except ImportError as exc:
        raise ImportError(
            "GPU backend requested but CuPy is not available. Install the CuPy "
            "package matching your CUDA runtime, for example 'cupy-cuda12x', "
            "or rerun with backend='cpu'."
        ) from exc
    return AccelerationBackend(
        requested=normalized,
        name="gpu",
        array_module=xp,
        available=True,
        reason="CuPy GPU backend selected",
    )


def get_array_module(data=None, backend: BackendName = "cpu"):
    """Return NumPy or CuPy for ``backend`` without changing default behavior."""

    if backend == "auto" and data is not None:
        cupy = _cupy_module_if_loaded()
        if cupy is not None and isinstance(data, cupy.ndarray):
            return cupy
    return get_acceleration_backend(backend).array_module


def as_backend_array(data, backend: BackendName = "cpu", *, dtype=float):
    """Convert ``data`` to the requested backend array type."""

    resolved = get_acceleration_backend(backend)
    if resolved.name == "gpu":
        return as_cupy_array(data, dtype=dtype)
    return as_numpy_array(data, dtype=dtype)


def to_numpy(array):
    """Return ``array`` as a NumPy ndarray."""

    cupy = _cupy_module_if_loaded()
    if cupy is not None and isinstance(array, cupy.ndarray):
        return cupy_to_numpy(array)
    return np.asarray(array)


def describe_acceleration() -> dict[str, object]:
    """Return a small, serializable summary of acceleration availability."""

    available = is_cupy_available()
    return {
        "default_backend": "cpu",
        "auto_backend": "cpu",
        "gpu_available": available,
        "gpu_library": "cupy" if available else None,
        "notes": "GPU compute is optional and selected only with backend='gpu'.",
    }


def _normalize_backend_name(name: str) -> BackendName:
    normalized = str(name).lower()
    if normalized not in {"cpu", "gpu", "auto"}:
        raise ValueError("backend must be 'cpu', 'gpu', or 'auto'")
    return normalized  # type: ignore[return-value]


def _cupy_module_if_loaded():
    try:
        return cupy_array_module(only_if_loaded=True)
    except ImportError:
        return None
