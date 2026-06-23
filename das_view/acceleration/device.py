"""Device-level helpers for optional acceleration."""

from __future__ import annotations

from das_view.acceleration.backend import describe_acceleration, get_acceleration_backend


def selected_device_name(backend: str = "auto") -> str:
    """Return a human-readable selected device label."""

    resolved = get_acceleration_backend(backend)
    if resolved.name == "cpu":
        return "cpu"
    return "gpu:cupy"


__all__ = ["describe_acceleration", "get_acceleration_backend", "selected_device_name"]
