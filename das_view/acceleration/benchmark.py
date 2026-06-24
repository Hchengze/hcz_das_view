"""Synthetic CPU/GPU benchmark helpers for optional acceleration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Sequence

import numpy as np

from das_view.acceleration.backend import (
    as_backend_array,
    estimate_gpu_array_memory,
    get_acceleration_backend,
    is_cupy_available,
    to_numpy,
    AccelerationRuntimeError,
)
from das_view.utils.memory import estimate_array_nbytes


DEFAULT_OPERATIONS = ("mean", "std", "rms", "energy", "fft_time", "fft2", "band_power_like")


class GpuRuntimeError(RuntimeError):
    """GPU backend imported, but a runtime kernel operation failed."""


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Timing result for one synthetic backend operation."""

    operation: str
    backend: str
    shape: tuple[int, int]
    dtype: str
    elapsed_seconds: float
    repeats: int
    warmup: int
    estimated_memory_bytes: int
    status: str = "ok"
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_array_backend_benchmark(
    *,
    shape=(4096, 512),
    dtype="float32",
    operations: Sequence[str] = DEFAULT_OPERATIONS,
    backend="cpu",
    warmup: int = 1,
    repeats: int = 3,
    seed: int = 0,
) -> list[BenchmarkResult]:
    """Run synthetic array operations on the selected backend."""

    normalized_shape = _normalize_shape(shape)
    dtype_value = np.dtype(dtype)
    operation_names = _normalize_operations(operations)
    warmup = _nonnegative_int(warmup, "warmup")
    repeats = _positive_int(repeats, "repeats")
    resolved = get_acceleration_backend(backend)
    rng = np.random.default_rng(seed)
    cpu_data = rng.normal(size=normalized_shape).astype(dtype_value, copy=False)
    data = as_backend_array(cpu_data, backend=resolved.name, dtype=dtype_value)
    estimated_memory = estimate_array_nbytes(normalized_shape[0], normalized_shape[1], dtype=dtype_value)
    results: list[BenchmarkResult] = []
    for operation in operation_names:
        callback = _operation_callback(operation, data, resolved.array_module)
        try:
            for _ in range(warmup):
                _sync(callback(), resolved.array_module, resolved.name)
            started = time.perf_counter()
            for _ in range(repeats):
                _sync(callback(), resolved.array_module, resolved.name)
        except Exception as exc:
            if resolved.name == "gpu":
                raise GpuRuntimeError(
                    f"GPU benchmark operation {operation!r} failed at runtime: {exc}"
                ) from exc
            raise
        elapsed = (time.perf_counter() - started) / float(repeats)
        results.append(
            BenchmarkResult(
                operation=operation,
                backend=resolved.name,
                shape=normalized_shape,
                dtype=str(dtype_value),
                elapsed_seconds=float(elapsed),
                repeats=repeats,
                warmup=warmup,
                estimated_memory_bytes=int(estimated_memory),
            )
        )
    return results


def compare_cpu_gpu_benchmark(
    *,
    shape=(4096, 512),
    dtype="float32",
    operations: Sequence[str] = DEFAULT_OPERATIONS,
    warmup: int = 1,
    repeats: int = 3,
    seed: int = 0,
    require_gpu: bool = False,
) -> dict[str, object]:
    """Compare CPU and GPU benchmark timings, skipping GPU if unavailable."""

    normalized_shape = _normalize_shape(shape)
    dtype_value = np.dtype(dtype)
    cpu = run_array_backend_benchmark(
        shape=normalized_shape,
        dtype=str(dtype_value),
        operations=operations,
        backend="cpu",
        warmup=warmup,
        repeats=repeats,
        seed=seed,
    )
    estimated = estimate_gpu_array_memory(normalized_shape, str(dtype_value), arrays=3)
    if not is_cupy_available():
        if require_gpu:
            raise ImportError(
                "GPU benchmark requested but CuPy is not available. Install a CuPy CUDA wheel or use CPU."
            )
        return {
            "status": "skipped",
            "reason": "CuPy is not available; GPU benchmark was skipped.",
            "shape": normalized_shape,
            "dtype": str(dtype_value),
            "estimated_memory": estimated,
            "cpu": [item.to_dict() for item in cpu],
            "gpu": [],
            "speedup": {},
        }
    try:
        gpu = run_array_backend_benchmark(
            shape=normalized_shape,
            dtype=str(dtype_value),
            operations=operations,
            backend="gpu",
            warmup=warmup,
            repeats=repeats,
            seed=seed,
        )
    except (AccelerationRuntimeError, GpuRuntimeError) as exc:
        if require_gpu:
            raise
        return {
            "status": "gpu_runtime_error",
            "reason": str(exc),
            "shape": normalized_shape,
            "dtype": str(dtype_value),
            "estimated_memory": estimated,
            "cpu": [item.to_dict() for item in cpu],
            "gpu": [],
            "speedup": {},
        }
    speedup = {}
    cpu_by_op = {item.operation: item for item in cpu}
    for item in gpu:
        cpu_elapsed = cpu_by_op[item.operation].elapsed_seconds
        speedup[item.operation] = cpu_elapsed / item.elapsed_seconds if item.elapsed_seconds > 0 else float("inf")
    return {
        "status": "ok",
        "reason": None,
        "shape": normalized_shape,
        "dtype": str(dtype_value),
        "estimated_memory": estimated,
        "cpu": [item.to_dict() for item in cpu],
        "gpu": [item.to_dict() for item in gpu],
        "speedup": speedup,
    }


def _operation_callback(operation: str, data, xp):
    if operation == "mean":
        return lambda: xp.mean(data, axis=0)
    if operation == "std":
        return lambda: xp.std(data, axis=0)
    if operation == "rms":
        return lambda: xp.sqrt(xp.mean(data * data, axis=0))
    if operation == "energy":
        return lambda: xp.sum(data * data, axis=0)
    if operation == "fft_time":
        return lambda: xp.fft.rfft(data, axis=0)
    if operation == "fft2":
        return lambda: xp.fft.rfft2(data)
    if operation == "band_power_like":
        def _band_power():
            spectrum = xp.abs(xp.fft.rfft(data, axis=0)) ** 2
            upper = max(2, min(16, spectrum.shape[0]))
            return xp.sum(spectrum[1:upper], axis=0)

        return _band_power
    raise ValueError(f"unsupported benchmark operation: {operation}")


def _sync(result, xp, backend: str) -> None:
    if backend == "gpu":
        stream = getattr(getattr(xp, "cuda", None), "Stream", None)
        if stream is not None:
            stream.null.synchronize()
        return
    np.asarray(to_numpy(result))


def _normalize_shape(shape) -> tuple[int, int]:
    try:
        values = tuple(int(value) for value in shape)
    except TypeError as exc:
        raise ValueError("shape must be a pair of positive integers") from exc
    if len(values) != 2 or values[0] <= 0 or values[1] <= 0:
        raise ValueError("shape must be a pair of positive integers")
    return values


def _normalize_operations(operations: Sequence[str]) -> tuple[str, ...]:
    names = tuple(str(value).strip().lower() for value in operations if str(value).strip())
    if not names:
        raise ValueError("operations must include at least one operation")
    unsupported = sorted(set(names) - set(DEFAULT_OPERATIONS))
    if unsupported:
        raise ValueError(f"unsupported benchmark operations: {', '.join(unsupported)}")
    return names


def _positive_int(value, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _nonnegative_int(value, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return result
