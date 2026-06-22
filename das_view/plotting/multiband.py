"""Matplotlib multiband and coherence plotting helpers."""

from __future__ import annotations

import numpy as np

from das_view.analysis.multiband import MultibandFeatureMap
from das_view.analysis.qc import LocalCoherenceResult


def plot_multiband_energy_map(result: MultibandFeatureMap, *, band_index: int = 0, ax=None):
    """Plot one band from a time-window x channel x band feature map."""

    import matplotlib.pyplot as plt

    if not isinstance(result, MultibandFeatureMap):
        raise TypeError("plot_multiband_energy_map expects MultibandFeatureMap")
    values = np.asarray(result.values)
    if values.size == 0:
        raise ValueError("multiband feature map is empty")
    if values.ndim != 3:
        raise ValueError("multiband energy map values must be 3-D")
    if band_index < 0 or band_index >= values.shape[2]:
        raise ValueError("band_index is out of range")
    if ax is None:
        _, ax = plt.subplots()
    image = ax.imshow(values[:, :, band_index], aspect="auto", origin="lower", interpolation="nearest")
    ax.set_xlabel("Channel")
    ax.set_ylabel("Time window")
    label = result.feature_names[band_index] if band_index < len(result.feature_names) else f"band {band_index}"
    ax.set_title(f"Multiband energy: {label}")
    ax.figure.colorbar(image, ax=ax, label="Energy")
    return ax


def plot_coherence_map(result: LocalCoherenceResult, *, ax=None):
    """Plot local channel coherence."""

    import matplotlib.pyplot as plt

    if not isinstance(result, LocalCoherenceResult):
        raise TypeError("plot_coherence_map expects LocalCoherenceResult")
    values = np.asarray(result.coherence)
    if values.size == 0:
        raise ValueError("coherence map is empty")
    if ax is None:
        _, ax = plt.subplots()
    image = ax.imshow(values, aspect="auto", origin="lower", interpolation="nearest", vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xlabel("Channel pair")
    ax.set_ylabel("Time window")
    ax.set_title(f"Local channel coherence lag={result.channel_lag}")
    ax.figure.colorbar(image, ax=ax, label="Correlation")
    return ax
