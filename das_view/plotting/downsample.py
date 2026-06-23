"""Small display downsampling helpers shared by plotting and GUI backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np


@dataclass(frozen=True, slots=True)
class DisplayDownsampleResult:
    """Array prepared for display plus the stride applied on each axis."""

    data: np.ndarray
    time_step: int
    channel_step: int
    original_shape: tuple[int, ...]


def estimate_display_pixels(
    n_samples: int,
    n_channels: int,
    *,
    max_samples: int | None = None,
    max_channels: int | None = None,
) -> dict[str, int | tuple[int, int]]:
    """Estimate output display shape and pixel count for a 2-D DAS image."""

    samples = _positive_int(n_samples, name="n_samples")
    channels = _positive_int(n_channels, name="n_channels")
    sample_limit = samples if max_samples is None else _positive_int(max_samples, name="max_samples")
    channel_limit = channels if max_channels is None else _positive_int(max_channels, name="max_channels")
    time_step = max(1, int(np.ceil(samples / sample_limit)))
    channel_step = max(1, int(np.ceil(channels / channel_limit)))
    out_samples = int(np.ceil(samples / time_step))
    out_channels = int(np.ceil(channels / channel_step))
    return {
        "original_shape": (samples, channels),
        "display_shape": (out_samples, out_channels),
        "time_step": time_step,
        "channel_step": channel_step,
        "pixels": out_samples * out_channels,
    }


def downsample_for_display(
    data: Any,
    *,
    max_samples: int = 2048,
    max_channels: int = 1024,
    method: Literal["stride"] = "stride",
) -> DisplayDownsampleResult:
    """Return a non-mutating display-sized view/copy for 1-D or 2-D data."""

    if method != "stride":
        raise ValueError("method must be 'stride'")
    sample_limit = _positive_int(max_samples, name="max_samples")
    channel_limit = _positive_int(max_channels, name="max_channels")
    array = np.asarray(data)
    if array.ndim == 1:
        time_step = max(1, int(np.ceil(array.shape[0] / sample_limit)))
        return DisplayDownsampleResult(
            data=np.array(array[::time_step], copy=True),
            time_step=time_step,
            channel_step=1,
            original_shape=tuple(int(v) for v in array.shape),
        )
    if array.ndim != 2:
        raise ValueError("display downsampling expects a 1-D or 2-D array")
    estimate = estimate_display_pixels(
        array.shape[0],
        array.shape[1],
        max_samples=sample_limit,
        max_channels=channel_limit,
    )
    time_step = int(estimate["time_step"])
    channel_step = int(estimate["channel_step"])
    return DisplayDownsampleResult(
        data=np.array(array[::time_step, ::channel_step], copy=True),
        time_step=time_step,
        channel_step=channel_step,
        original_shape=tuple(int(v) for v in array.shape),
    )


def _positive_int(value: Any, *, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed
