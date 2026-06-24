"""Backend selection for optional CPU/GPU array operations."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import subprocess
import sys
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
from das_view.utils.memory import estimate_array_nbytes, format_nbytes

BackendName = Literal["cpu", "gpu", "auto"]


@dataclass(frozen=True, slots=True)
class AccelerationBackend:
    """Resolved array backend description."""

    requested: BackendName
    name: Literal["cpu", "gpu"]
    array_module: object
    available: bool
    reason: str


class AccelerationRuntimeError(RuntimeError):
    """GPU backend is importable but cannot run a minimal kernel."""


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
    runtime = validate_gpu_runtime()
    if not runtime.get("ok"):
        raise AccelerationRuntimeError(
            "GPU backend requested but the CuPy/CUDA runtime cannot run a "
            f"minimal kernel: {runtime.get('message')}. Rerun with backend='cpu' "
            "or repair the local CuPy/CUDA runtime."
        )
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
    gpu_info = get_gpu_device_info() if available else {}
    return {
        "default_backend": "cpu",
        "auto_backend": "cpu",
        "gpu_available": available,
        "gpu_library": "cupy" if available else None,
        "gpu_device_count": gpu_info.get("device_count"),
        "gpu_current_device_name": gpu_info.get("current_device_name"),
        "notes": "GPU compute is optional and selected only with backend='gpu'.",
    }


def get_gpu_device_info() -> dict[str, object]:
    """Return CuPy/CUDA device information without failing on CPU-only hosts."""

    try:
        cp = import_cupy()
    except ImportError:
        return {
            "cupy_available": False,
            "device_count": 0,
            "current_device_id": None,
            "current_device_name": None,
            "total_memory_bytes": None,
            "free_memory_bytes": None,
            "error": "CuPy is not installed.",
        }
    info: dict[str, object] = {"cupy_available": True}
    try:
        runtime = cp.cuda.runtime
        count = int(runtime.getDeviceCount())
        info["device_count"] = count
        if count <= 0:
            info.update(
                {
                    "current_device_id": None,
                    "current_device_name": None,
                    "total_memory_bytes": None,
                    "free_memory_bytes": None,
                    "error": "No CUDA devices were reported by CuPy.",
                }
            )
            return info
        device = cp.cuda.Device()
        device_id = int(device.id)
        props = runtime.getDeviceProperties(device_id)
        name = props.get("name", b"")
        if isinstance(name, bytes):
            name = name.decode(errors="replace")
        free_bytes, total_bytes = runtime.memGetInfo()
        info.update(
            {
                "current_device_id": device_id,
                "current_device_name": str(name),
                "total_memory_bytes": int(total_bytes),
                "free_memory_bytes": int(free_bytes),
            }
        )
    except Exception as exc:  # pragma: no cover - depends on CUDA runtime state.
        info.update(
            {
                "device_count": 0,
                "current_device_id": None,
                "current_device_name": None,
                "total_memory_bytes": None,
                "free_memory_bytes": None,
                "error": str(exc),
            }
        )
    return info


def get_cupy_build_info() -> dict[str, object]:
    """Return CuPy build/runtime version information when available."""

    try:
        cp = import_cupy()
    except ImportError:
        return {
            "cupy_available": False,
            "cupy_version": None,
            "cuda_runtime_version": None,
            "cuda_driver_version": None,
            "error": "CuPy is not installed.",
        }
    result: dict[str, object] = {
        "cupy_available": True,
        "cupy_version": getattr(cp, "__version__", None),
    }
    try:
        result["cuda_runtime_version"] = int(cp.cuda.runtime.runtimeGetVersion())
    except Exception as exc:  # pragma: no cover - depends on CUDA runtime state.
        result["cuda_runtime_version"] = None
        result["cuda_runtime_error"] = str(exc)
    try:
        result["cuda_driver_version"] = int(cp.cuda.runtime.driverGetVersion())
    except Exception as exc:  # pragma: no cover - depends on CUDA runtime state.
        result["cuda_driver_version"] = None
        result["cuda_driver_error"] = str(exc)
    return result


def validate_gpu_backend(*, require_device: bool = True) -> dict[str, object]:
    """Validate explicit GPU backend availability and return a status dict."""

    build = get_cupy_build_info()
    device = get_gpu_device_info()
    if not build.get("cupy_available"):
        return {
            "ok": False,
            "status": "unavailable",
            "message": "CuPy is not installed; GPU backend is unavailable.",
            "build": build,
            "device": device,
        }
    if require_device and int(device.get("device_count") or 0) <= 0:
        return {
            "ok": False,
            "status": "no_device",
            "message": "CuPy is installed but no CUDA device is available.",
            "build": build,
            "device": device,
        }
    runtime = validate_gpu_runtime()
    if not runtime.get("ok"):
        return {
            "ok": False,
            "status": "runtime_error",
            "message": str(runtime.get("message")),
            "build": build,
            "device": device,
            "runtime": runtime,
        }
    return {
        "ok": True,
        "status": "available",
        "message": "GPU backend is available.",
        "build": build,
        "device": device,
        "runtime": runtime,
    }


def validate_gpu_runtime() -> dict[str, object]:
    """Run a tiny cached CuPy operation to validate kernel runtime readiness."""

    return dict(_validate_gpu_runtime_cached())


def estimate_gpu_array_memory(shape=(4096, 512), dtype="float32", *, arrays: int = 1) -> dict[str, object]:
    """Estimate GPU bytes needed for one or more dense arrays."""

    normalized_shape = _normalize_shape(shape)
    try:
        count = int(arrays)
    except (TypeError, ValueError) as exc:
        raise ValueError("arrays must be a positive integer") from exc
    if count <= 0:
        raise ValueError("arrays must be a positive integer")
    nbytes = estimate_array_nbytes(normalized_shape[0], normalized_shape[1], dtype=dtype) * count
    device = get_gpu_device_info()
    free = device.get("free_memory_bytes")
    fits_free = None if free is None else int(nbytes) <= int(free)
    return {
        "shape": normalized_shape,
        "dtype": str(np.dtype(dtype)),
        "arrays": count,
        "estimated_bytes": int(nbytes),
        "estimated_human": format_nbytes(int(nbytes)),
        "free_memory_bytes": free,
        "free_memory_human": None if free is None else format_nbytes(int(free)),
        "fits_free_memory": fits_free,
    }


def format_acceleration_report(backend: BackendName = "auto", *, as_text: bool = False):
    """Return acceleration diagnostics as a dict or user-readable text."""

    normalized = _normalize_backend_name(backend)
    build = get_cupy_build_info()
    device = get_gpu_device_info()
    selected = get_acceleration_backend(normalized if normalized != "gpu" else "cpu")
    validation = validate_gpu_backend(require_device=False)
    payload = {
        "selected_backend": selected.name if normalized != "gpu" else "gpu",
        "requested_backend": normalized,
        "default_backend": "cpu",
        "auto_backend": "cpu",
        "cupy_available": bool(build.get("cupy_available")),
        "cupy_version": build.get("cupy_version"),
        "cuda_runtime_version": build.get("cuda_runtime_version"),
        "cuda_driver_version": build.get("cuda_driver_version"),
        "device_count": device.get("device_count"),
        "current_device_name": device.get("current_device_name"),
        "total_gpu_memory_bytes": device.get("total_memory_bytes"),
        "free_gpu_memory_bytes": device.get("free_memory_bytes"),
        "fallback_behavior": "CPU is the default; auto resolves to CPU; gpu must be explicit.",
        "installation_hint": "Install a CuPy wheel matching your CUDA runtime, for example 'cupy-cuda12x'.",
        "gpu_validation": validation,
    }
    if not as_text:
        return payload
    return _format_report_text(payload)


def _normalize_backend_name(name: str) -> BackendName:
    normalized = str(name).lower()
    if normalized not in {"cpu", "gpu", "auto"}:
        raise ValueError("backend must be 'cpu', 'gpu', or 'auto'")
    return normalized  # type: ignore[return-value]


def _normalize_shape(shape) -> tuple[int, int]:
    try:
        values = tuple(int(value) for value in shape)
    except TypeError as exc:
        raise ValueError("shape must be a pair of positive integers") from exc
    if len(values) != 2 or values[0] <= 0 or values[1] <= 0:
        raise ValueError("shape must be a pair of positive integers")
    return values


def _format_report_text(payload: dict[str, object]) -> str:
    total = payload.get("total_gpu_memory_bytes")
    free = payload.get("free_gpu_memory_bytes")
    total_text = "N/A" if total is None else format_nbytes(int(total))
    free_text = "N/A" if free is None else format_nbytes(int(free))
    lines = [
        f"requested_backend: {payload['requested_backend']}",
        f"selected_backend: {payload['selected_backend']}",
        f"cupy_available: {payload['cupy_available']}",
        f"cupy_version: {payload.get('cupy_version')}",
        f"cuda_runtime_version: {payload.get('cuda_runtime_version')}",
        f"cuda_driver_version: {payload.get('cuda_driver_version')}",
        f"device_count: {payload.get('device_count')}",
        f"current_device_name: {payload.get('current_device_name')}",
        f"total_gpu_memory: {total_text}",
        f"free_gpu_memory: {free_text}",
        f"fallback_behavior: {payload['fallback_behavior']}",
        f"installation_hint: {payload['installation_hint']}",
    ]
    validation = payload.get("gpu_validation")
    if isinstance(validation, dict):
        lines.append(f"gpu_status: {validation.get('status')}")
        lines.append(f"gpu_message: {validation.get('message')}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _validate_gpu_runtime_cached() -> tuple[tuple[str, object], ...]:
    try:
        import_cupy()
    except ImportError:
        return tuple(
            {
                "ok": False,
                "status": "unavailable",
                "message": "CuPy is not installed.",
            }.items()
        )
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import cupy as cp; "
                    "x=cp.arange(128,dtype=cp.float32).reshape(32,4); "
                    "y=cp.std(x,axis=0); "
                    "cp.cuda.Stream.null.synchronize(); "
                    "print(cp.asnumpy(y).shape)"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "CuPy runtime probe failed.").strip()
            return tuple(
                {
                    "ok": False,
                    "status": "runtime_error",
                    "message": message,
                }.items()
            )
    except subprocess.TimeoutExpired:
        return tuple(
            {
                "ok": False,
                "status": "runtime_error",
                "message": "CuPy runtime probe timed out while running a reduction kernel.",
            }.items()
        )
    except Exception as exc:  # pragma: no cover - depends on CUDA runtime state.
        return tuple(
            {
                "ok": False,
                "status": "runtime_error",
                "message": str(exc),
            }.items()
        )
    return tuple(
        {
            "ok": True,
            "status": "available",
            "message": "CuPy kernel runtime is available.",
        }.items()
    )


def _cupy_module_if_loaded():
    try:
        return cupy_array_module(only_if_loaded=True)
    except ImportError:
        return None
