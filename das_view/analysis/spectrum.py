"""Basic frequency-domain analysis helpers for DAS arrays.

The internal DAS convention is (n_samples, n_channels).  The default axis=0
therefore treats rows as time samples and columns as independent channels.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.core.data_model import DASData

SpectrumKind = Literal["amplitude", "power"]


@dataclass(frozen=True, slots=True)
class SpectrumResult:
    """Frequency-domain result for one or more channels."""

    frequencies_hz: np.ndarray
    values: np.ndarray
    kind: SpectrumKind
    sample_rate_hz: float
    axis: int
    nfft: int
    channels: tuple[int, ...] | None = None
    average_channels: bool = False
    scaling: str | None = None

    @property
    def amplitude(self) -> np.ndarray:
        """Alias for amplitude spectra."""

        if self.kind != "amplitude":
            raise ValueError("SpectrumResult does not contain amplitude values")
        return self.values

    @property
    def power(self) -> np.ndarray:
        """Alias for power spectra."""

        if self.kind != "power":
            raise ValueError("SpectrumResult does not contain power values")
        return self.values


@dataclass(frozen=True, slots=True)
class SpectrogramResult:
    """Single-channel spectrogram result."""

    frequencies_hz: np.ndarray
    times_s: np.ndarray
    values: np.ndarray
    sample_rate_hz: float
    channel: int
    nperseg: int
    noverlap: int
    scaling: str


def amplitude_spectrum(
    data,
    *,
    sample_rate_hz: float | None = None,
    axis: int = 0,
    nfft: int | None = None,
    window: str | Sequence[float] | np.ndarray | None = None,
    one_sided: bool = True,
    channels: int | Sequence[int] | None = None,
    average_channels: bool = False,
) -> SpectrumResult:
    """Compute an amplitude spectrum with explicit DAS axis semantics."""

    array, sample_rate_hz = _as_array_and_sample_rate(data, sample_rate_hz)
    axis = _normalize_axis(axis, array.ndim)
    channel_tuple = _channels_for_array(array, axis=axis, channels=channels)
    array = _select_channels(array, axis=axis, channels=channels)
    n_samples = array.shape[axis]
    nfft = _normalize_nfft(nfft, n_samples)
    window_array = _window_values(window, n_samples)
    working = _apply_window(array, window_array, axis=axis)

    if one_sided:
        fft_values = np.fft.rfft(working, n=nfft, axis=axis)
        frequencies = np.fft.rfftfreq(nfft, d=1.0 / sample_rate_hz)
    else:
        fft_values = np.fft.fft(working, n=nfft, axis=axis)
        frequencies = np.fft.fftfreq(nfft, d=1.0 / sample_rate_hz)

    amplitude = np.abs(fft_values) / float(n_samples)
    if one_sided and nfft > 1:
        multiplier = np.ones(amplitude.shape[axis], dtype=float)
        if nfft % 2 == 0:
            multiplier[1:-1] = 2.0
        else:
            multiplier[1:] = 2.0
        amplitude = amplitude * _reshape_for_axis(multiplier, amplitude.ndim, axis)
    amplitude = _maybe_average_channels(amplitude, axis=axis, average_channels=average_channels)

    return SpectrumResult(
        frequencies_hz=frequencies,
        values=amplitude,
        kind="amplitude",
        sample_rate_hz=sample_rate_hz,
        axis=axis,
        nfft=nfft,
        channels=channel_tuple,
        average_channels=average_channels,
    )


def power_spectrum(
    data,
    *,
    sample_rate_hz: float | None = None,
    axis: int = 0,
    nfft: int | None = None,
    window: str | Sequence[float] | np.ndarray | None = None,
    one_sided: bool = True,
    channels: int | Sequence[int] | None = None,
    average_channels: bool = False,
    scaling: Literal["power", "density"] = "power",
) -> SpectrumResult:
    """Compute a simple power spectrum or power spectral density estimate."""

    if scaling not in {"power", "density"}:
        raise ValueError("scaling must be 'power' or 'density'")
    amplitude = amplitude_spectrum(
        data,
        sample_rate_hz=sample_rate_hz,
        axis=axis,
        nfft=nfft,
        window=window,
        one_sided=one_sided,
        channels=channels,
        average_channels=average_channels,
    )
    values = np.square(amplitude.values)
    if scaling == "density":
        frequency_step = amplitude.sample_rate_hz / amplitude.nfft
        values = values / frequency_step
    return SpectrumResult(
        frequencies_hz=amplitude.frequencies_hz,
        values=values,
        kind="power",
        sample_rate_hz=amplitude.sample_rate_hz,
        axis=amplitude.axis,
        nfft=amplitude.nfft,
        channels=amplitude.channels,
        average_channels=amplitude.average_channels,
        scaling=scaling,
    )


def single_channel_spectrogram(
    data,
    *,
    sample_rate_hz: float | None = None,
    channel: int = 0,
    nperseg: int = 256,
    noverlap: int | None = None,
    window: str | Sequence[float] | np.ndarray = "hann",
    scaling: Literal["density", "spectrum"] = "density",
) -> SpectrogramResult:
    """Compute a scipy.signal spectrogram for one DAS channel."""

    array, sample_rate_hz = _as_array_and_sample_rate(data, sample_rate_hz)
    if array.ndim == 1:
        trace = array
        channel = 0
    elif array.ndim == 2:
        channel = _normalize_channel(channel, array.shape[1])
        trace = array[:, channel]
    else:
        raise ValueError("single_channel_spectrogram expects 1-D data or 2-D DAS data")

    nperseg = _normalize_positive_int(nperseg, name="nperseg")
    if nperseg > trace.shape[0]:
        raise ValueError("nperseg must be less than or equal to the trace length")
    if noverlap is None:
        noverlap_value = nperseg // 2
    else:
        noverlap_value = _normalize_nonnegative_int(noverlap, name="noverlap")
    if noverlap_value >= nperseg:
        raise ValueError("noverlap must be less than nperseg")
    if scaling not in {"density", "spectrum"}:
        raise ValueError("scaling must be 'density' or 'spectrum'")

    signal = _scipy_signal()
    frequencies, times, values = signal.spectrogram(
        trace,
        fs=sample_rate_hz,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap_value,
        scaling=scaling,
        mode="magnitude",
    )
    return SpectrogramResult(
        frequencies_hz=frequencies,
        times_s=times,
        values=values,
        sample_rate_hz=sample_rate_hz,
        channel=channel,
        nperseg=nperseg,
        noverlap=noverlap_value,
        scaling=scaling,
    )


def _as_array_and_sample_rate(data, sample_rate_hz: float | None) -> tuple[np.ndarray, float]:
    if isinstance(data, DASData):
        if sample_rate_hz is None:
            sample_rate_hz = data.metadata.sample_rate_hz
        array = np.array(data.data, dtype=float, copy=True)
    else:
        array = np.array(data, dtype=float, copy=True)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
    if array.size == 0:
        raise ValueError("data must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError("spectrum input must contain only finite values; NaN/Inf are not supported")
    if sample_rate_hz is None:
        raise ValueError("sample_rate_hz is required when input is not DASData metadata")
    sample_rate_hz = float(sample_rate_hz)
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be a positive finite value")
    return array, sample_rate_hz


def _normalize_axis(axis: int, ndim: int) -> int:
    try:
        value = int(axis)
    except (TypeError, ValueError) as exc:
        raise ValueError("axis must be an integer") from exc
    if value < 0:
        value += ndim
    if value < 0 or value >= ndim:
        raise ValueError(f"axis {axis} is out of range for {ndim}-D data")
    return value


def _normalize_nfft(nfft: int | None, n_samples: int) -> int:
    if nfft is None:
        return int(n_samples)
    try:
        value = int(nfft)
    except (TypeError, ValueError) as exc:
        raise ValueError("nfft must be a positive integer") from exc
    if value <= 0:
        raise ValueError("nfft must be a positive integer")
    if value < n_samples:
        raise ValueError("nfft must be greater than or equal to the selected data length")
    return value


def _normalize_channel(channel: int, n_channels: int) -> int:
    try:
        value = int(channel)
    except (TypeError, ValueError) as exc:
        raise ValueError("channel must be an integer") from exc
    if value < 0 or value >= n_channels:
        raise ValueError(f"channel index {value} is out of range for data with {n_channels} channels")
    return value


def _normalize_channels(
    channels: int | Sequence[int] | None,
    n_channels: int | None,
) -> tuple[int, ...] | None:
    if n_channels is None:
        return None
    if channels is None:
        return tuple(range(n_channels))
    if isinstance(channels, int):
        return (_normalize_channel(channels, n_channels),)
    if isinstance(channels, Sequence) and not isinstance(channels, (str, bytes)):
        result = tuple(_normalize_channel(value, n_channels) for value in channels)
        if not result:
            raise ValueError("channels must contain at least one channel index")
        return result
    raise ValueError("channels must be None, an int, or a sequence of ints")


def _select_channels(
    array: np.ndarray,
    *,
    axis: int,
    channels: int | Sequence[int] | None,
) -> np.ndarray:
    if channels is None:
        return array
    if array.ndim != 2:
        raise ValueError("channels can only be used with 2-D DAS data")
    channel_axis = 1 if axis == 0 else 0
    normalized = _normalize_channels(channels, array.shape[channel_axis])
    return np.take(array, normalized, axis=channel_axis)


def _channels_for_array(
    array: np.ndarray,
    *,
    axis: int,
    channels: int | Sequence[int] | None,
) -> tuple[int, ...] | None:
    if array.ndim != 2:
        if channels is not None:
            raise ValueError("channels can only be used with 2-D DAS data")
        return None
    channel_axis = 1 if axis == 0 else 0
    return _normalize_channels(channels, array.shape[channel_axis])


def _window_values(window: str | Sequence[float] | np.ndarray | None, n_samples: int) -> np.ndarray | None:
    if window is None:
        return None
    if isinstance(window, str):
        signal = _scipy_signal()
        return np.asarray(signal.get_window(window, n_samples), dtype=float)
    values = np.asarray(window, dtype=float)
    if values.ndim != 1:
        raise ValueError("window array must be one-dimensional")
    if values.shape[0] != n_samples:
        raise ValueError("window length must match the selected data length")
    if not np.all(np.isfinite(values)):
        raise ValueError("window must contain only finite values")
    return values


def _apply_window(array: np.ndarray, window: np.ndarray | None, *, axis: int) -> np.ndarray:
    if window is None:
        return array
    return array * _reshape_for_axis(window, array.ndim, axis)


def _reshape_for_axis(values: np.ndarray, ndim: int, axis: int) -> np.ndarray:
    shape = [1] * ndim
    shape[axis] = values.shape[0]
    return values.reshape(shape)


def _maybe_average_channels(array: np.ndarray, *, axis: int, average_channels: bool) -> np.ndarray:
    if not average_channels or array.ndim < 2:
        return array
    channel_axis = 1 if axis == 0 else 0
    return np.mean(array, axis=channel_axis)


def _normalize_positive_int(value: int, *, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _normalize_nonnegative_int(value: int, *, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return result


def _scipy_signal():
    try:
        from scipy import signal
    except ImportError as exc:  # pragma: no cover - exercised only without scipy installed.
        raise ImportError(
            "scipy is required for windowed spectrum and spectrogram analysis"
        ) from exc
    return signal
