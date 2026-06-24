"""Waterfall / variable-density plotting for DAS data."""

from __future__ import annotations

from typing import Any

import numpy as np

from das_view.core.data_model import DASData


def plot_waterfall(
    das_data: DASData,
    *,
    ax: Any | None = None,
    time_range: tuple[float, float] | None = None,
    channel_range: tuple[float, float] | None = None,
    axis_mode: str = "auto",
    percentile_clip: tuple[float, float] | None = (1, 99),
    cmap: str = "seismic",
    show_colorbar: bool = True,
    title: str | None = None,
):
    """Plot a DAS variable-density image and return (figure, axes).

    The function is intentionally GUI-free and works with non-interactive
    Matplotlib backends.
    """

    import matplotlib.pyplot as plt

    data = np.asarray(das_data.data)
    if data.ndim != 2:
        raise ValueError("plot_waterfall expects DASData.data shaped as (n_samples, n_channels)")
    if data.size == 0 or data.shape[0] == 0 or data.shape[1] == 0:
        raise ValueError("plot_waterfall cannot plot empty DAS data")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    normalized_axis_mode = _normalize_axis_mode(axis_mode, das_data)
    extent = _extent(
        das_data,
        time_range=time_range,
        channel_range=channel_range,
        axis_mode=normalized_axis_mode,
    )
    vmin, vmax = _clip_limits(data, percentile_clip)
    image = ax.imshow(
        data,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
        extent=extent,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )
    ax.set_xlabel(_x_label(normalized_axis_mode))
    ax.set_ylabel("Time (s)" if das_data.metadata.dt_s is not None else "Sample index")
    ax.set_title(title if title is not None else _default_title(das_data))
    if show_colorbar:
        fig.colorbar(image, ax=ax, label="Amplitude")
    return fig, ax


def _clip_limits(data: np.ndarray, percentile_clip: tuple[float, float] | None) -> tuple[float | None, float | None]:
    finite = data[np.isfinite(data)]
    if finite.size == 0 or percentile_clip is None:
        return None, None
    low, high = percentile_clip
    if not (0 <= low < high <= 100):
        raise ValueError("percentile_clip must satisfy 0 <= low < high <= 100")
    vmin, vmax = np.percentile(finite, [low, high])
    if vmin == vmax:
        return None, None
    return float(vmin), float(vmax)


def _extent(
    das_data: DASData,
    *,
    time_range: tuple[float, float] | None,
    channel_range: tuple[float, float] | None,
    axis_mode: str,
) -> tuple[float, float, float, float]:
    n_samples, n_channels = das_data.data.shape
    if channel_range is None:
        if axis_mode == "distance":
            x0 = 0.0
            x1 = das_data.metadata.dx_m * max(n_channels - 1, 0)
        else:
            start = das_data.metadata.start_channel or 0
            x0 = float(start)
            x1 = float(start + max(n_channels - 1, 0))
    else:
        x0, x1 = channel_range

    if time_range is None:
        if das_data.metadata.dt_s is not None:
            y0 = 0.0
            y1 = das_data.metadata.dt_s * max(n_samples - 1, 0)
        else:
            y0 = 0.0
            y1 = float(max(n_samples - 1, 0))
    else:
        y0, y1 = time_range

    return float(x0), float(x1), float(y1), float(y0)


def _normalize_axis_mode(axis_mode: str, das_data: DASData) -> str:
    normalized = str(axis_mode).strip().lower().replace("-", "_")
    if normalized == "auto":
        return "distance" if das_data.metadata.dx_m is not None else "channel"
    if normalized == "distance" and das_data.metadata.dx_m is not None:
        return "distance"
    if normalized in {"distance", "channel"}:
        return "channel"
    raise ValueError("axis_mode must be 'auto', 'channel', or 'distance'")


def _x_label(axis_mode: str) -> str:
    if axis_mode == "distance":
        return "Distance (m)"
    return "Channel"


def _default_title(das_data: DASData) -> str:
    metadata = das_data.metadata
    source = metadata.source_format or "unknown format"
    return f"DAS waterfall - {source} ({metadata.n_samples} x {metadata.n_channels})"
