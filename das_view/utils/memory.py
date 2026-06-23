"""Memory-estimation helpers for bounded DAS selections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from das_view.core.exceptions import ReaderError
from das_view.utils.slicing import SliceLike, normalize_downsample, normalize_slice, slice_length


@dataclass(frozen=True, slots=True)
class MemoryEstimate:
    """Result from checking a planned selection against an optional limit."""

    estimated_bytes: int
    limit_bytes: int | None
    within_limit: bool
    message: str


def estimate_array_nbytes(
    n_samples: int,
    n_channels: int,
    dtype: str | np.dtype[Any] = "float64",
) -> int:
    """Estimate bytes for a dense ``(n_samples, n_channels)`` array."""

    samples = _normalize_dimension(n_samples, "n_samples")
    channels = _normalize_dimension(n_channels, "n_channels")
    return int(samples * channels * np.dtype(dtype).itemsize)


def estimate_selection_nbytes(
    *,
    n_samples: int,
    n_channels: int,
    time_slice: SliceLike = None,
    channel_slice: SliceLike = None,
    downsample: int | tuple[int, int] | None = None,
    dtype: str | np.dtype[Any] = "float64",
) -> int:
    """Estimate bytes for a reader selection without reading data."""

    total_samples = _normalize_dimension(n_samples, "n_samples")
    total_channels = _normalize_dimension(n_channels, "n_channels")
    normalized_time = normalize_slice(time_slice, total_samples, axis_name="time")
    normalized_channel = normalize_slice(channel_slice, total_channels, axis_name="channel")
    time_step, channel_step = normalize_downsample(downsample)
    selected_samples = _stepped_length(normalized_time, time_step)
    selected_channels = _stepped_length(normalized_channel, channel_step)
    return estimate_array_nbytes(selected_samples, selected_channels, dtype=dtype)


def format_nbytes(nbytes: int) -> str:
    """Format a byte count for user-facing messages."""

    value = _normalize_bytes(nbytes, "nbytes")
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.2f} {unit}"
        amount /= 1024.0
    return f"{amount:.2f} TiB"


def check_selection_memory(
    *,
    n_samples: int,
    n_channels: int,
    time_slice: SliceLike = None,
    channel_slice: SliceLike = None,
    downsample: int | tuple[int, int] | None = None,
    dtype: str | np.dtype[Any] = "float64",
    max_bytes: int | None = None,
) -> MemoryEstimate:
    """Check whether a planned selection is within an optional byte limit."""

    estimated = estimate_selection_nbytes(
        n_samples=n_samples,
        n_channels=n_channels,
        time_slice=time_slice,
        channel_slice=channel_slice,
        downsample=downsample,
        dtype=dtype,
    )
    limit = None if max_bytes is None else _normalize_bytes(max_bytes, "max_bytes")
    if limit is None:
        return MemoryEstimate(
            estimated_bytes=estimated,
            limit_bytes=None,
            within_limit=True,
            message=f"Estimated selection size is {format_nbytes(estimated)}.",
        )
    within_limit = estimated <= limit
    if within_limit:
        message = (
            f"Estimated selection size is {format_nbytes(estimated)}, "
            f"within the {format_nbytes(limit)} limit."
        )
    else:
        message = (
            f"Estimated selection size is {format_nbytes(estimated)}, "
            f"which exceeds the {format_nbytes(limit)} limit. "
            "Reduce the time/channel range or increase downsampling."
        )
    return MemoryEstimate(
        estimated_bytes=estimated,
        limit_bytes=limit,
        within_limit=within_limit,
        message=message,
    )


def _stepped_length(value: slice, downsample_step: int) -> int:
    base_step = 1 if value.step is None else int(value.step)
    effective = slice(value.start, value.stop, base_step * int(downsample_step))
    return slice_length(effective)


def _normalize_dimension(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ReaderError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise ReaderError(f"{name} must be a non-negative integer")
    return result


def _normalize_bytes(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ReaderError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise ReaderError(f"{name} must be a non-negative integer")
    return result
