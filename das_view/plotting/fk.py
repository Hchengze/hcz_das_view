"""Matplotlib plotting helpers for FK analysis results."""

from __future__ import annotations

from typing import Any

import numpy as np

from das_view.analysis.fk import FKResult


def plot_fk(
    result: FKResult,
    *,
    ax: Any | None = None,
    title: str | None = None,
    db: bool = False,
    cmap: str = "viridis",
    show_colorbar: bool = True,
    frequency_limits: tuple[float, float] | None = None,
    wavenumber_limits: tuple[float, float] | None = None,
):
    """Plot an FK amplitude or power result and return (fig, ax)."""

    import matplotlib.pyplot as plt

    if not isinstance(result, FKResult):
        raise ValueError("plot_fk expects an FKResult")
    frequencies = np.asarray(result.frequencies_hz)
    wavenumbers = np.asarray(result.wavenumbers_cycles_per_m)
    values = np.asarray(result.values, dtype=float)
    if frequencies.ndim != 1 or frequencies.size == 0:
        raise ValueError("FKResult.frequencies_hz must be a non-empty 1-D array")
    if wavenumbers.ndim != 1 or wavenumbers.size == 0:
        raise ValueError("FKResult.wavenumbers_cycles_per_m must be a non-empty 1-D array")
    if values.shape != (frequencies.size, wavenumbers.size):
        raise ValueError("FKResult.values must be shaped as (n_frequencies, n_wavenumbers)")
    if values.size == 0:
        raise ValueError("FKResult.values must not be empty")
    if not np.all(np.isfinite(values)):
        raise ValueError("FKResult.values must contain only finite values")

    values_for_plot = values
    if db:
        tiny = np.finfo(float).tiny
        factor = 20.0 if result.output == "amplitude" else 10.0
        values_for_plot = factor * np.log10(np.maximum(values_for_plot, tiny))

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    mesh = ax.pcolormesh(wavenumbers, frequencies, values_for_plot, shading="auto", cmap=cmap)
    ax.set_xlabel("Wavenumber (cycles/m)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title if title is not None else _default_title(result, db=db))
    if wavenumber_limits is not None:
        ax.set_xlim(*wavenumber_limits)
    if frequency_limits is not None:
        ax.set_ylim(*frequency_limits)
    if show_colorbar:
        fig.colorbar(mesh, ax=ax, label=_colorbar_label(result, db=db))
    return fig, ax


def _default_title(result: FKResult, *, db: bool) -> str:
    label = "FK amplitude" if result.output == "amplitude" else "FK power"
    return f"{label} (dB)" if db else label


def _colorbar_label(result: FKResult, *, db: bool) -> str:
    if db:
        return "Amplitude (dB)" if result.output == "amplitude" else "Power (dB)"
    return "Amplitude" if result.output == "amplitude" else "Power"
