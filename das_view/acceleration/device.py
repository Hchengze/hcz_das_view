"""Device-level helpers for optional acceleration."""

from __future__ import annotations

from das_view.acceleration.backend import (
    describe_acceleration,
    estimate_gpu_array_memory,
    format_acceleration_report,
    get_acceleration_backend,
    get_cupy_build_info,
    get_gpu_device_info,
    validate_gpu_backend,
)


def selected_device_name(backend: str = "auto") -> str:
    """Return a human-readable selected device label."""

    resolved = get_acceleration_backend(backend)
    if resolved.name == "cpu":
        return "cpu"
    return "gpu:cupy"


__all__ = [
    "describe_acceleration",
    "estimate_gpu_array_memory",
    "format_acceleration_report",
    "get_acceleration_backend",
    "get_cupy_build_info",
    "get_gpu_device_info",
    "selected_device_name",
    "validate_gpu_backend",
]
