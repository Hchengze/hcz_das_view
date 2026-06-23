"""Formatting helpers for displaying DAS metadata.

These helpers are intentionally dependency-light so they can be reused by CLI
tools and GUI models without importing plotting or GUI libraries.
"""

from __future__ import annotations

from typing import Any

from das_view.core.data_model import DASMetadata
from das_view.utils.memory import estimate_array_nbytes, format_nbytes


def metadata_to_dict(metadata: DASMetadata) -> dict[str, Any]:
    """Return a stable dictionary representation for display and tests."""

    duration_s = _duration_s(metadata)
    result: dict[str, Any] = {
        "source_format": metadata.source_format,
        "source_path": metadata.source_path,
        "n_samples": metadata.n_samples,
        "n_channels": metadata.n_channels,
        "sample_rate_hz": metadata.sample_rate_hz,
        "dt_s": metadata.dt_s,
        "dx_m": metadata.dx_m,
        "gauge_length_m": metadata.gauge_length_m,
        "start_channel": metadata.start_channel,
        "start_time": metadata.start_time,
        "duration_s": duration_s,
        "estimated_full_array_size": format_nbytes(
            estimate_array_nbytes(metadata.n_samples, metadata.n_channels)
        ),
    }
    if metadata.dx_m is not None:
        result["distance_range_m"] = _distance_range_m(metadata)
    else:
        result["channel_range"] = _channel_range(metadata)
    return result


def metadata_summary_lines(metadata: DASMetadata) -> list[str]:
    """Build user-facing summary lines with friendly missing-value display."""

    values = metadata_to_dict(metadata)
    keys = [
        "source_format",
        "source_path",
        "n_samples",
        "n_channels",
        "sample_rate_hz",
        "dt_s",
        "dx_m",
        "gauge_length_m",
        "start_channel",
        "start_time",
        "duration_s",
        "estimated_full_array_size",
    ]
    if "distance_range_m" in values:
        keys.append("distance_range_m")
    else:
        keys.append("channel_range")
    return [f"{key}: {_format_value(values.get(key))}" for key in keys]


def format_metadata(metadata: DASMetadata, *, style: str = "text") -> str:
    """Format metadata for CLI or GUI text display."""

    if style != "text":
        raise ValueError("Only style='text' is currently supported")
    return "\n".join(metadata_summary_lines(metadata))


def _duration_s(metadata: DASMetadata) -> float | None:
    if metadata.dt_s is not None:
        return metadata.n_samples * metadata.dt_s
    if metadata.sample_rate_hz is not None:
        return metadata.n_samples / metadata.sample_rate_hz
    return None


def _distance_range_m(metadata: DASMetadata) -> tuple[float, float]:
    dx = 0.0 if metadata.dx_m is None else metadata.dx_m
    return 0.0, dx * max(metadata.n_channels - 1, 0)


def _channel_range(metadata: DASMetadata) -> tuple[int, int]:
    start = 0 if metadata.start_channel is None else metadata.start_channel
    return start, start + max(metadata.n_channels - 1, 0)


def _format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(item) for item in value) + ")"
    return str(value)
