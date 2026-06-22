"""Matplotlib QC plotting helpers."""

from __future__ import annotations

import numpy as np

from das_view.analysis.qc import ChannelQualityResult, DataQualityReport


def plot_channel_quality(report, *, ax=None):
    """Plot per-channel quality score."""

    import matplotlib.pyplot as plt

    metrics = report.channel_metrics if isinstance(report, DataQualityReport) else report
    if not isinstance(metrics, ChannelQualityResult):
        raise TypeError("plot_channel_quality expects DataQualityReport or ChannelQualityResult")
    if ax is None:
        _, ax = plt.subplots()
    channels = np.arange(metrics.n_channels)
    ax.plot(channels, metrics.quality_score, marker="o", linewidth=1.0)
    ax.set_xlabel("Channel")
    ax.set_ylabel("Quality score")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("DAS channel quality")
    bad = np.flatnonzero(metrics.bad_channel)
    if bad.size:
        ax.scatter(bad, metrics.quality_score[bad], color="tab:red", label="flagged")
        ax.legend(loc="best")
    return ax


def plot_bad_channels(report, *, ax=None):
    """Plot a compact bad-channel mask."""

    import matplotlib.pyplot as plt

    metrics = report.channel_metrics if isinstance(report, DataQualityReport) else report
    if not isinstance(metrics, ChannelQualityResult):
        raise TypeError("plot_bad_channels expects DataQualityReport or ChannelQualityResult")
    if ax is None:
        _, ax = plt.subplots()
    mask = metrics.bad_channel.reshape(1, -1).astype(float)
    ax.imshow(mask, aspect="auto", interpolation="nearest", cmap="Reds", vmin=0, vmax=1)
    ax.set_yticks([])
    ax.set_xlabel("Channel")
    ax.set_title("Flagged DAS channels")
    return ax
