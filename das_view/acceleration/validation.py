"""Synthetic CPU/GPU numerical consistency validation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np

from das_view.acceleration.backend import is_cupy_available
from das_view.analysis.fk import fk_transform
from das_view.analysis.multiband import multiband_energy_map
from das_view.analysis.spectral_attributes import band_energy
from das_view.analysis.statistics import basic_statistics


DEFAULT_FUNCTIONS = ("statistics", "band_energy", "multiband_energy_map", "fk_transform")


@dataclass(frozen=True, slots=True)
class NumericCheckResult:
    """One CPU/GPU consistency check result."""

    function: str
    status: str
    shape: tuple[int, ...]
    max_abs_diff: float | None
    rtol: float
    atol: float
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_cpu_gpu_numeric_consistency(
    *,
    shape=(1024, 128),
    dtype="float32",
    functions: Sequence[str] = DEFAULT_FUNCTIONS,
    rtol: float = 1e-5,
    atol: float = 1e-6,
    seed: int = 0,
    require_gpu: bool = False,
) -> dict[str, object]:
    """Validate selected CPU/GPU paths on synthetic data."""

    normalized_shape = _normalize_shape(shape)
    dtype_value = np.dtype(dtype)
    function_names = _normalize_functions(functions)
    data = _synthetic_data(normalized_shape, dtype_value, seed=seed)
    if not is_cupy_available():
        if require_gpu:
            raise ImportError(
                "GPU numeric validation requested but CuPy is not available. Install a CuPy CUDA wheel or use CPU."
            )
        return {
            "status": "skipped",
            "reason": "CuPy is not available; CPU/GPU numeric validation was skipped.",
            "shape": normalized_shape,
            "dtype": str(dtype_value),
            "checks": [
                NumericCheckResult(
                    function=name,
                    status="skipped",
                    shape=normalized_shape,
                    max_abs_diff=None,
                    rtol=rtol,
                    atol=atol,
                    message="CuPy is not available.",
                ).to_dict()
                for name in function_names
            ],
        }
    checks = [
        _validate_function(name, data, rtol=rtol, atol=atol)
        for name in function_names
    ]
    status = "ok" if all(item.status == "ok" for item in checks) else "failed"
    return {
        "status": status,
        "reason": None if status == "ok" else "At least one CPU/GPU numeric check failed.",
        "shape": normalized_shape,
        "dtype": str(dtype_value),
        "checks": [item.to_dict() for item in checks],
    }


def _validate_function(name: str, data: np.ndarray, *, rtol: float, atol: float) -> NumericCheckResult:
    cpu, gpu = _function_outputs(name, data)
    cpu_array = np.asarray(cpu, dtype=float)
    gpu_array = np.asarray(gpu, dtype=float)
    if cpu_array.shape != gpu_array.shape:
        return NumericCheckResult(
            function=name,
            status="failed",
            shape=cpu_array.shape,
            max_abs_diff=None,
            rtol=rtol,
            atol=atol,
            message=f"shape mismatch: CPU {cpu_array.shape}, GPU {gpu_array.shape}",
        )
    diff = float(np.nanmax(np.abs(cpu_array - gpu_array))) if cpu_array.size else 0.0
    ok = bool(np.allclose(cpu_array, gpu_array, rtol=rtol, atol=atol, equal_nan=True))
    return NumericCheckResult(
        function=name,
        status="ok" if ok else "failed",
        shape=cpu_array.shape,
        max_abs_diff=diff,
        rtol=rtol,
        atol=atol,
        message=None if ok else "CPU and GPU outputs differ beyond tolerance.",
    )


def _function_outputs(name: str, data: np.ndarray):
    if name == "statistics":
        cpu = basic_statistics(data, axis=0, backend="cpu")
        gpu = basic_statistics(data, axis=0, backend="gpu")
        return _stack_stats(cpu), _stack_stats(gpu)
    if name == "band_energy":
        bands = ((1.0, 8.0), (8.0, 20.0))
        cpu = band_energy(data, sample_rate_hz=128.0, bands=bands, axis=0, backend="cpu")
        gpu = band_energy(data, sample_rate_hz=128.0, bands=bands, axis=0, backend="gpu")
        return cpu.band_energy, gpu.band_energy
    if name == "multiband_energy_map":
        bands = ((1.0, 8.0), (8.0, 20.0))
        window = min(256, data.shape[0])
        step = max(1, window // 2)
        cpu = multiband_energy_map(
            data,
            sample_rate_hz=128.0,
            bands=bands,
            window_samples=window,
            step_samples=step,
            backend="cpu",
        )
        gpu = multiband_energy_map(
            data,
            sample_rate_hz=128.0,
            bands=bands,
            window_samples=window,
            step_samples=step,
            backend="gpu",
        )
        return cpu.values, gpu.values
    if name == "fk_transform":
        cpu = fk_transform(data, sample_rate_hz=128.0, dx_m=1.0, backend="cpu")
        gpu = fk_transform(data, sample_rate_hz=128.0, dx_m=1.0, backend="gpu")
        return cpu.values, gpu.values
    raise ValueError(f"unsupported validation function: {name}")


def _stack_stats(result) -> np.ndarray:
    return np.vstack(
        [
            np.asarray(result.mean, dtype=float).reshape(1, -1),
            np.asarray(result.std, dtype=float).reshape(1, -1),
            np.asarray(result.rms, dtype=float).reshape(1, -1),
            np.asarray(result.energy, dtype=float).reshape(1, -1),
        ]
    )


def _synthetic_data(shape: tuple[int, int], dtype: np.dtype, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(shape[0], dtype=float) / 128.0
    channels = np.arange(shape[1], dtype=float)
    base = np.sin(2 * np.pi * 5.0 * t[:, None] + channels.reshape(1, -1) * 0.03)
    noise = rng.normal(scale=0.01, size=shape)
    return np.asarray(base + noise, dtype=dtype)


def _normalize_shape(shape) -> tuple[int, int]:
    try:
        values = tuple(int(value) for value in shape)
    except TypeError as exc:
        raise ValueError("shape must be a pair of positive integers") from exc
    if len(values) != 2 or values[0] < 2 or values[1] < 2:
        raise ValueError("shape must contain at least 2 samples and 2 channels")
    return values


def _normalize_functions(functions: Sequence[str]) -> tuple[str, ...]:
    values = tuple(str(value).strip().lower() for value in functions if str(value).strip())
    if not values:
        raise ValueError("functions must include at least one function")
    unsupported = sorted(set(values) - set(DEFAULT_FUNCTIONS))
    if unsupported:
        raise ValueError(f"unsupported validation functions: {', '.join(unsupported)}")
    return values
