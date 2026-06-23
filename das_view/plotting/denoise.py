"""Matplotlib helpers for traditional DAS signal enhancement."""

from __future__ import annotations

import numpy as np

from das_view.core.data_model import DASData
from das_view.processing.denoise import EnhancementReport


def plot_before_after_waterfall(
    before,
    after,
    *,
    ax=None,
    max_samples: int | None = None,
    max_channels: int | None = None,
    title: str | None = None,
):
    """Plot compact before/after waterfall panels and return the axes."""

    import matplotlib.pyplot as plt

    before_array = _bounded_array(before, max_samples=max_samples, max_channels=max_channels)
    after_array = _bounded_array(after, max_samples=max_samples, max_channels=max_channels)
    if before_array.ndim == 1:
        before_array = before_array[:, None]
    if after_array.ndim == 1:
        after_array = after_array[:, None]
    if before_array.size == 0 or after_array.size == 0:
        raise ValueError("before and after arrays must not be empty")
    if ax is None:
        _, axes = plt.subplots(1, 2, sharey=True)
    else:
        axes = np.asarray(ax).ravel()
        if axes.size != 2:
            raise ValueError("ax must contain exactly two axes")
    vmin, vmax = _clip_limits(np.concatenate([before_array.ravel(), after_array.ravel()]))
    images = [
        axes[0].imshow(before_array, aspect="auto", origin="upper", interpolation="nearest", cmap="seismic", vmin=vmin, vmax=vmax),
        axes[1].imshow(after_array, aspect="auto", origin="upper", interpolation="nearest", cmap="seismic", vmin=vmin, vmax=vmax),
    ]
    axes[0].set_title("Before")
    axes[1].set_title("After")
    for item in axes:
        item.set_xlabel("Channel")
    axes[0].set_ylabel("Sample")
    if title:
        axes[0].figure.suptitle(title)
    axes[1].figure.colorbar(images[-1], ax=list(axes), label="Amplitude")
    return tuple(axes)


def plot_enhancement_metrics(report, *, ax=None):
    """Plot before/after RMS and energy from an EnhancementReport."""

    import matplotlib.pyplot as plt

    if not isinstance(report, EnhancementReport):
        raise TypeError("plot_enhancement_metrics expects EnhancementReport")
    if ax is None:
        _, ax = plt.subplots()
    labels = ["before", "after"]
    rms = [float(report.before.get("rms", 0.0)), float(report.after.get("rms", 0.0))]
    energy = [float(report.before.get("energy", 0.0)), float(report.after.get("energy", 0.0))]
    x = np.arange(2)
    ax.bar(x - 0.18, rms, width=0.36, label="RMS")
    ax.bar(x + 0.18, energy, width=0.36, label="Energy")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Metric value")
    ax.set_title("Enhancement metrics")
    ax.legend(loc="best")
    return ax


def _bounded_array(data, *, max_samples: int | None, max_channels: int | None) -> np.ndarray:
    array = np.asarray(data.data if isinstance(data, DASData) else data, dtype=float)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
    if array.ndim > 2:
        raise ValueError("plot_before_after_waterfall expects 1-D or 2-D data")
    sample_slice = slice(0, max_samples) if max_samples is not None else slice(None)
    if array.ndim == 1:
        return array[sample_slice]
    channel_slice = slice(0, max_channels) if max_channels is not None else slice(None)
    return array[sample_slice, channel_slice]


def _clip_limits(values: np.ndarray) -> tuple[float | None, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None, None
    low, high = np.percentile(finite, [1, 99])
    if low == high:
        return None, None
    return float(low), float(high)
