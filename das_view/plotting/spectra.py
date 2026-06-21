"""Matplotlib plotting helpers for spectrum analysis results."""

from __future__ import annotations

from typing import Any

import numpy as np

from das_view.analysis.spectrum import PSDResult, SpectrogramResult, SpectrumResult


def plot_spectrum(
    result: SpectrumResult,
    *,
    ax: Any | None = None,
    title: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
):
    """Plot amplitude or power spectrum data and return (fig, ax)."""

    import matplotlib.pyplot as plt

    if not isinstance(result, SpectrumResult):
        raise ValueError("plot_spectrum expects a SpectrumResult")
    frequencies = np.asarray(result.frequencies_hz)
    values = np.asarray(result.values)
    if frequencies.ndim != 1 or frequencies.size == 0:
        raise ValueError("SpectrumResult.frequencies_hz must be a non-empty 1-D array")
    if values.size == 0:
        raise ValueError("SpectrumResult.values must not be empty")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    values_for_plot = _spectrum_values_as_frequency_rows(values, frequencies.size, result.axis)
    if values_for_plot.ndim == 1:
        ax.plot(frequencies, values_for_plot)
    else:
        labels = _channel_labels(result, values_for_plot.shape[1])
        for index in range(values_for_plot.shape[1]):
            ax.plot(frequencies, values_for_plot[:, index], label=labels[index])
        if values_for_plot.shape[1] > 1:
            ax.legend(loc="best")

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel(_spectrum_ylabel(result))
    ax.set_title(title if title is not None else _spectrum_title(result))
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    return fig, ax


def plot_spectrogram(
    result: SpectrogramResult,
    *,
    ax: Any | None = None,
    title: str | None = None,
    cmap: str = "viridis",
    show_colorbar: bool = True,
):
    """Plot a single-channel spectrogram and return (fig, ax)."""

    import matplotlib.pyplot as plt

    if not isinstance(result, SpectrogramResult):
        raise ValueError("plot_spectrogram expects a SpectrogramResult")
    frequencies = np.asarray(result.frequencies_hz)
    times = np.asarray(result.times_s)
    values = np.asarray(result.values)
    if frequencies.ndim != 1 or times.ndim != 1:
        raise ValueError("spectrogram frequencies and times must be 1-D arrays")
    if values.shape != (frequencies.size, times.size):
        raise ValueError("spectrogram values must be shaped as (n_frequencies, n_times)")
    if values.size == 0:
        raise ValueError("spectrogram values must not be empty")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    mesh = ax.pcolormesh(times, frequencies, values, shading="auto", cmap=cmap)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title if title is not None else f"Spectrogram - channel {result.channel}")
    if show_colorbar:
        fig.colorbar(mesh, ax=ax, label="Magnitude")
    return fig, ax


def plot_psd(
    result: PSDResult,
    *,
    ax: Any | None = None,
    title: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    db: bool = False,
):
    """Plot PSD result data and return (fig, ax)."""

    import matplotlib.pyplot as plt

    if not isinstance(result, PSDResult):
        raise ValueError("plot_psd expects a PSDResult")
    frequencies = np.asarray(result.frequencies_hz)
    values = np.asarray(result.values)
    if frequencies.ndim != 1 or frequencies.size == 0:
        raise ValueError("PSDResult.frequencies_hz must be a non-empty 1-D array")
    if values.size == 0:
        raise ValueError("PSDResult.values must not be empty")

    if db:
        tiny = np.finfo(float).tiny
        values = 10.0 * np.log10(np.maximum(values, tiny))

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    values_for_plot = _spectrum_values_as_frequency_rows(values, frequencies.size, result.axis)
    if values_for_plot.ndim == 1:
        ax.plot(frequencies, values_for_plot)
    else:
        labels = _psd_channel_labels(result, values_for_plot.shape[1])
        for index in range(values_for_plot.shape[1]):
            ax.plot(frequencies, values_for_plot[:, index], label=labels[index])
        if values_for_plot.shape[1] > 1:
            ax.legend(loc="best")

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD (dB)" if db else _psd_ylabel(result))
    ax.set_title(title if title is not None else _psd_title(result))
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    return fig, ax


def _spectrum_values_as_frequency_rows(values: np.ndarray, n_frequencies: int, axis: int) -> np.ndarray:
    if values.ndim == 1:
        if values.shape[0] != n_frequencies:
            raise ValueError("1-D spectrum values length must match frequencies")
        return values
    if values.ndim != 2:
        raise ValueError("spectrum values must be 1-D or 2-D")
    if axis == 0:
        if values.shape[0] != n_frequencies:
            raise ValueError("spectrum values first dimension must match frequencies")
        return values
    if axis == 1:
        if values.shape[1] != n_frequencies:
            raise ValueError("spectrum values second dimension must match frequencies")
        return values.T
    raise ValueError("SpectrumResult.axis must be 0 or 1 for plotting")


def _channel_labels(result: SpectrumResult, n_series: int) -> list[str]:
    if result.channels is None:
        return [f"series {index}" for index in range(n_series)]
    return [f"channel {channel}" for channel in result.channels[:n_series]]


def _psd_channel_labels(result: PSDResult, n_series: int) -> list[str]:
    if result.channels is None:
        return [f"series {index}" for index in range(n_series)]
    return [f"channel {channel}" for channel in result.channels[:n_series]]


def _spectrum_ylabel(result: SpectrumResult) -> str:
    if result.kind == "amplitude":
        return "Amplitude"
    if result.scaling == "density":
        return "Power density"
    return "Power"


def _spectrum_title(result: SpectrumResult) -> str:
    if result.kind == "amplitude":
        prefix = "Amplitude spectrum"
    else:
        prefix = "Power spectrum"
    if result.average_channels:
        return f"{prefix} - channel average"
    if result.channels is not None and len(result.channels) == 1:
        return f"{prefix} - channel {result.channels[0]}"
    return prefix


def _psd_ylabel(result: PSDResult) -> str:
    if result.scaling == "density":
        return "PSD"
    return "Power spectrum"


def _psd_title(result: PSDResult) -> str:
    prefix = "Welch PSD" if result.method == "welch" else "Periodogram PSD"
    if result.average_channels:
        return f"{prefix} - channel average"
    if result.channels is not None and len(result.channels) == 1:
        return f"{prefix} - channel {result.channels[0]}"
    return prefix
