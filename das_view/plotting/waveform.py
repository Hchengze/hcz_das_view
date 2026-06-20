"""Waveform plotting helpers for DAS traces."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import numpy as np

from das_view.core.data_model import DASData

OffsetMode = Literal["auto", "none", "index"]


def plot_waveform(
    das_data: DASData,
    *,
    channels: int | Sequence[int] | None = None,
    ax: Any | None = None,
    time_unit: str = "s",
    offset_mode: OffsetMode = "auto",
    normalize: bool = True,
    title: str | None = None,
):
    """Plot one or more DAS channel waveforms and return (fig, ax).

    Parameters use internal channel indices after reader slicing. The input
    data must follow the project convention (n_samples, n_channels).
    """

    import matplotlib.pyplot as plt

    data = np.asarray(das_data.data)
    if data.ndim != 2:
        raise ValueError("plot_waveform expects DASData.data shaped as (n_samples, n_channels)")
    if data.size == 0 or data.shape[0] == 0 or data.shape[1] == 0:
        raise ValueError("plot_waveform cannot plot empty DAS data")

    channel_indices = _normalize_channels(channels, data.shape[1])
    traces = data[:, channel_indices].astype(float, copy=False)
    display = _prepare_traces(traces, normalize=normalize)
    offsets = _offsets(display, channel_indices, offset_mode=offset_mode)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    x = _time_axis(das_data, time_unit=time_unit)
    for position, channel in enumerate(channel_indices):
        label = _channel_label(das_data, channel)
        ax.plot(x, display[:, position] + offsets[position], label=label)

    ax.set_xlabel(_time_label(time_unit, das_data))
    ax.set_ylabel(_y_label(offset_mode=offset_mode, normalize=normalize))
    ax.set_title(title if title is not None else _default_title(das_data, channel_indices))
    if len(channel_indices) > 1:
        ax.legend(loc="best")
    return fig, ax


def _normalize_channels(channels: int | Sequence[int] | None, n_channels: int) -> list[int]:
    if channels is None:
        result = [0]
    elif isinstance(channels, int):
        result = [channels]
    elif isinstance(channels, Sequence) and not isinstance(channels, (str, bytes)):
        result = [int(channel) for channel in channels]
    else:
        raise ValueError("channels must be None, an int, or a sequence of ints")

    if not result:
        raise ValueError("channels must contain at least one channel index")
    for channel in result:
        if channel < 0 or channel >= n_channels:
            raise ValueError(
                f"channel index {channel} is out of range for data with {n_channels} channels"
            )
    return result


def _prepare_traces(traces: np.ndarray, *, normalize: bool) -> np.ndarray:
    display = np.asarray(traces, dtype=float)
    if not normalize:
        return display.copy()

    display = display.copy()
    for column in range(display.shape[1]):
        trace = display[:, column]
        finite = trace[np.isfinite(trace)]
        if finite.size == 0:
            display[:, column] = 0.0
            continue
        center = float(np.nanmean(finite))
        centered = trace - center
        finite_centered = centered[np.isfinite(centered)]
        scale = float(np.nanmax(np.abs(finite_centered))) if finite_centered.size else 0.0
        if not np.isfinite(scale) or scale == 0.0:
            display[:, column] = 0.0
        else:
            display[:, column] = centered / scale
    return display


def _offsets(
    display: np.ndarray,
    channels: Sequence[int],
    *,
    offset_mode: OffsetMode,
) -> np.ndarray:
    if offset_mode == "none":
        return np.zeros(display.shape[1], dtype=float)
    if offset_mode == "index":
        return np.asarray(channels, dtype=float)
    if offset_mode != "auto":
        raise ValueError("offset_mode must be 'auto', 'none', or 'index'")

    if display.shape[1] <= 1:
        return np.zeros(display.shape[1], dtype=float)
    finite = display[np.isfinite(display)]
    amplitude = float(np.nanmax(np.abs(finite))) if finite.size else 0.0
    spacing = 1.5 * amplitude if amplitude > 0.0 else 1.0
    return np.arange(display.shape[1], dtype=float) * spacing


def _time_axis(das_data: DASData, *, time_unit: str) -> np.ndarray:
    n_samples = das_data.data.shape[0]
    dt_s = das_data.metadata.dt_s
    if dt_s is None:
        return np.arange(n_samples, dtype=float)
    if time_unit == "s":
        scale = 1.0
    elif time_unit == "ms":
        scale = 1000.0
    else:
        raise ValueError("time_unit must be 's' or 'ms'")
    return np.arange(n_samples, dtype=float) * dt_s * scale


def _time_label(time_unit: str, das_data: DASData) -> str:
    if das_data.metadata.dt_s is None:
        return "Sample index"
    if time_unit == "s":
        return "Time (s)"
    if time_unit == "ms":
        return "Time (ms)"
    raise ValueError("time_unit must be 's' or 'ms'")


def _channel_label(das_data: DASData, channel: int) -> str:
    selected_numbers = das_data.metadata.extra_attrs.get("selected_channel_numbers")
    if selected_numbers is not None and channel < len(selected_numbers):
        return f"channel {selected_numbers[channel]}"
    selected_indices = das_data.metadata.extra_attrs.get("selected_channel_indices")
    if selected_indices is not None and channel < len(selected_indices):
        return f"channel {selected_indices[channel]}"
    start = das_data.metadata.start_channel
    if start is None:
        return f"channel {channel}"
    return f"channel {start + channel}"


def _y_label(*, offset_mode: OffsetMode, normalize: bool) -> str:
    if offset_mode == "none":
        return "Normalized amplitude" if normalize else "Amplitude"
    return "Trace amplitude + offset"


def _default_title(das_data: DASData, channels: Sequence[int]) -> str:
    source = das_data.metadata.source_format or "unknown format"
    if len(channels) == 1:
        return f"DAS waveform - {source} - {_channel_label(das_data, channels[0])}"
    return f"DAS waveforms - {source} - {len(channels)} channels"
