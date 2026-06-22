"""Band energy and spectral attribute helpers for DAS data.

The default DAS convention is ``data.shape == (n_samples, n_channels)``:
axis 0 is time and axis 1 is channel/space.  These helpers are
GUI-independent and accept numpy arrays or DASData.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]
SpectrumScaling = Literal["power", "density"]


@dataclass(frozen=True, slots=True)
class BandEnergyResult:
    """Frequency-band energy summary for one or more DAS traces."""

    bands: tuple[tuple[float, float], ...]
    band_energy: np.ndarray
    band_power: np.ndarray
    total_energy: float | np.ndarray
    band_energy_ratio: np.ndarray
    frequencies_hz: np.ndarray
    sample_rate_hz: float
    axis: int
    nfft: int
    scaling: SpectrumScaling
    average_channels: bool = False


@dataclass(frozen=True, slots=True)
class SpectralAttributesResult:
    """Core spectral attributes for one or more DAS traces."""

    dominant_frequency_hz: float | np.ndarray
    peak_amplitude_or_power: float | np.ndarray
    spectral_centroid_hz: float | np.ndarray
    spectral_bandwidth_hz: float | np.ndarray
    spectral_rolloff_hz: float | np.ndarray
    low_frequency_hz: float
    high_frequency_hz: float
    total_energy: float | np.ndarray
    frequencies_hz: np.ndarray
    sample_rate_hz: float
    axis: int
    nfft: int
    rolloff: float
    frequency_range: tuple[float, float] | None = None
    average_channels: bool = False
    scaling: SpectrumScaling = "power"


def band_energy(
    data,
    *,
    sample_rate_hz: float | None = None,
    bands,
    axis: int = 0,
    nfft: int | None = None,
    average_channels: bool = False,
    scaling: SpectrumScaling = "power",
    nan_policy: NanPolicy = "raise",
) -> BandEnergyResult:
    """Compute energy and power summaries for frequency bands."""

    spectrum = _power_spectrum_matrix(
        data,
        sample_rate_hz=sample_rate_hz,
        axis=axis,
        nfft=nfft,
        average_channels=average_channels,
        scaling=scaling,
        nan_policy=nan_policy,
    )
    normalized_bands = _normalize_bands(bands, nyquist=spectrum.sample_rate_hz / 2.0)
    band_values: list[np.ndarray | float] = []
    band_power_values: list[np.ndarray | float] = []

    for fmin, fmax in normalized_bands:
        mask = (spectrum.frequencies_hz >= fmin) & (spectrum.frequencies_hz <= fmax)
        if not np.any(mask):
            raise ValueError(f"band {fmin:g}-{fmax:g} Hz does not include any frequency bins")
        selected = spectrum.values[mask]
        band_values.append(np.sum(selected, axis=0))
        band_power_values.append(np.mean(selected, axis=0))

    band_energy_values = np.asarray(band_values, dtype=float)
    band_power_array = np.asarray(band_power_values, dtype=float)
    total_energy = np.sum(spectrum.values, axis=0)
    ratio = np.divide(
        band_energy_values,
        total_energy,
        out=np.full_like(band_energy_values, np.nan, dtype=float),
        where=np.asarray(total_energy) > 0,
    )

    if average_channels or spectrum.n_traces == 1:
        band_energy_values = np.asarray(band_energy_values, dtype=float).reshape(len(normalized_bands))
        band_power_array = np.asarray(band_power_array, dtype=float).reshape(len(normalized_bands))
        ratio = np.asarray(ratio, dtype=float).reshape(len(normalized_bands))
        total: float | np.ndarray = float(np.asarray(total_energy).reshape(-1)[0])
    else:
        total = np.asarray(total_energy, dtype=float)

    return BandEnergyResult(
        bands=normalized_bands,
        band_energy=band_energy_values,
        band_power=band_power_array,
        total_energy=total,
        band_energy_ratio=ratio,
        frequencies_hz=spectrum.frequencies_hz,
        sample_rate_hz=spectrum.sample_rate_hz,
        axis=spectrum.axis,
        nfft=spectrum.nfft,
        scaling=scaling,
        average_channels=bool(average_channels),
    )


def spectral_attributes(
    data,
    *,
    sample_rate_hz: float | None = None,
    axis: int = 0,
    nfft: int | None = None,
    frequency_range=None,
    rolloff: float = 0.95,
    average_channels: bool = False,
    nan_policy: NanPolicy = "raise",
) -> SpectralAttributesResult:
    """Compute dominant frequency, centroid, bandwidth, and rolloff."""

    rolloff = _normalize_rolloff(rolloff)
    spectrum = _power_spectrum_matrix(
        data,
        sample_rate_hz=sample_rate_hz,
        axis=axis,
        nfft=nfft,
        average_channels=average_channels,
        scaling="power",
        nan_policy=nan_policy,
    )
    frequency_range_value = _normalize_frequency_range(
        frequency_range,
        nyquist=spectrum.sample_rate_hz / 2.0,
    )
    frequencies = spectrum.frequencies_hz
    if frequency_range_value is None:
        mask = np.ones_like(frequencies, dtype=bool)
    else:
        low, high = frequency_range_value
        mask = (frequencies >= low) & (frequencies <= high)
        if not np.any(mask):
            raise ValueError("frequency_range does not include any frequency bins")

    selected_frequencies = frequencies[mask]
    values = spectrum.values[mask]
    total_energy = np.sum(values, axis=0)
    peak_index = np.argmax(values, axis=0)
    peak_power = np.take_along_axis(values, peak_index.reshape(1, -1), axis=0).reshape(-1)
    dominant = selected_frequencies[peak_index]

    frequency_column = selected_frequencies.reshape(-1, 1)
    centroid = _divide_or_nan(np.sum(values * frequency_column, axis=0), total_energy)
    bandwidth = np.sqrt(
        _divide_or_nan(
            np.sum(values * np.square(frequency_column - centroid.reshape(1, -1)), axis=0),
            total_energy,
        )
    )
    rolloff_frequency = _rolloff_frequency(values, selected_frequencies, total_energy, rolloff)

    zero_energy = np.asarray(total_energy) <= 0
    dominant = np.where(zero_energy, np.nan, dominant)
    centroid = np.where(zero_energy, np.nan, centroid)
    bandwidth = np.where(zero_energy, np.nan, bandwidth)
    rolloff_frequency = np.where(zero_energy, np.nan, rolloff_frequency)

    if average_channels or spectrum.n_traces == 1:
        dominant_out: float | np.ndarray = float(np.asarray(dominant).reshape(-1)[0])
        peak_out: float | np.ndarray = float(np.asarray(peak_power).reshape(-1)[0])
        centroid_out: float | np.ndarray = float(np.asarray(centroid).reshape(-1)[0])
        bandwidth_out: float | np.ndarray = float(np.asarray(bandwidth).reshape(-1)[0])
        rolloff_out: float | np.ndarray = float(np.asarray(rolloff_frequency).reshape(-1)[0])
        total_out: float | np.ndarray = float(np.asarray(total_energy).reshape(-1)[0])
    else:
        dominant_out = np.asarray(dominant, dtype=float)
        peak_out = np.asarray(peak_power, dtype=float)
        centroid_out = np.asarray(centroid, dtype=float)
        bandwidth_out = np.asarray(bandwidth, dtype=float)
        rolloff_out = np.asarray(rolloff_frequency, dtype=float)
        total_out = np.asarray(total_energy, dtype=float)

    return SpectralAttributesResult(
        dominant_frequency_hz=dominant_out,
        peak_amplitude_or_power=peak_out,
        spectral_centroid_hz=centroid_out,
        spectral_bandwidth_hz=bandwidth_out,
        spectral_rolloff_hz=rolloff_out,
        low_frequency_hz=float(selected_frequencies[0]),
        high_frequency_hz=float(selected_frequencies[-1]),
        total_energy=total_out,
        frequencies_hz=selected_frequencies,
        sample_rate_hz=spectrum.sample_rate_hz,
        axis=spectrum.axis,
        nfft=spectrum.nfft,
        rolloff=rolloff,
        frequency_range=frequency_range_value,
        average_channels=bool(average_channels),
    )


@dataclass(frozen=True, slots=True)
class _SpectrumMatrix:
    values: np.ndarray
    frequencies_hz: np.ndarray
    sample_rate_hz: float
    axis: int
    nfft: int
    n_traces: int


def _power_spectrum_matrix(
    data,
    *,
    sample_rate_hz: float | None,
    axis: int,
    nfft: int | None,
    average_channels: bool,
    scaling: SpectrumScaling,
    nan_policy: NanPolicy,
) -> _SpectrumMatrix:
    if scaling not in ("power", "density"):
        raise ValueError("scaling must be 'power' or 'density'")
    if nan_policy not in ("omit", "raise"):
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    array, sample_rate_hz = _as_array_and_sample_rate(data, sample_rate_hz)
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("spectral attribute input contains NaN or Inf values")
    array = np.where(np.isfinite(array), array, 0.0)
    axis = _normalize_axis(axis, array.ndim)
    n_samples = array.shape[axis]
    if n_samples < 1:
        raise ValueError("data must contain at least one sample along the analysis axis")
    nfft = _normalize_nfft(nfft, n_samples)
    working = np.moveaxis(array, axis, 0).reshape(n_samples, -1)
    n_traces = working.shape[1]

    fft_values = np.fft.rfft(working, n=nfft, axis=0)
    amplitude = np.abs(fft_values) / float(n_samples)
    if nfft > 1:
        multiplier = np.ones(amplitude.shape[0], dtype=float)
        if nfft % 2 == 0:
            multiplier[1:-1] = 2.0
        else:
            multiplier[1:] = 2.0
        amplitude = amplitude * multiplier.reshape(-1, 1)
    values = np.square(amplitude)
    if scaling == "density":
        values = values / (sample_rate_hz / nfft)
    if average_channels:
        values = np.mean(values, axis=1, keepdims=True)
        n_traces = 1

    return _SpectrumMatrix(
        values=values,
        frequencies_hz=np.fft.rfftfreq(nfft, d=1.0 / sample_rate_hz),
        sample_rate_hz=sample_rate_hz,
        axis=axis,
        nfft=nfft,
        n_traces=n_traces,
    )


def _as_array_and_sample_rate(data, sample_rate_hz: float | None) -> tuple[np.ndarray, float]:
    if isinstance(data, DASData):
        if sample_rate_hz is None:
            sample_rate_hz = data.metadata.sample_rate_hz
        array = np.array(data.data, copy=True)
    else:
        array = np.array(data, copy=True)
    if array.size == 0:
        raise ValueError("data must not be empty")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError("spectral attribute input must be a real numeric array")
    array = np.asarray(array, dtype=float)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
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


def _normalize_bands(bands, *, nyquist: float) -> tuple[tuple[float, float], ...]:
    try:
        normalized = tuple((float(fmin), float(fmax)) for fmin, fmax in bands)
    except (TypeError, ValueError) as exc:
        raise ValueError("bands must be an iterable of (fmin_hz, fmax_hz) pairs") from exc
    if not normalized:
        raise ValueError("bands must contain at least one frequency band")
    for fmin, fmax in normalized:
        if not np.isfinite(fmin) or not np.isfinite(fmax):
            raise ValueError("band limits must be finite")
        if fmin < 0 or fmin >= fmax:
            raise ValueError("each band must satisfy 0 <= fmin < fmax")
        if fmax > nyquist:
            raise ValueError("band fmax must be less than or equal to Nyquist")
    return normalized


def _normalize_frequency_range(value, *, nyquist: float) -> tuple[float, float] | None:
    if value is None:
        return None
    try:
        low, high = value
    except (TypeError, ValueError) as exc:
        raise ValueError("frequency_range must be a (low_hz, high_hz) pair") from exc
    low = float(low)
    high = float(high)
    if not np.isfinite(low) or not np.isfinite(high):
        raise ValueError("frequency_range limits must be finite")
    if low < 0 or low >= high:
        raise ValueError("frequency_range must satisfy 0 <= low < high")
    if high > nyquist:
        raise ValueError("frequency_range high must be less than or equal to Nyquist")
    return (low, high)


def _normalize_rolloff(value: float) -> float:
    value = float(value)
    if not np.isfinite(value) or value <= 0.0 or value > 1.0:
        raise ValueError("rolloff must be in the interval (0, 1]")
    return value


def _divide_or_nan(numerator, denominator):
    return np.divide(
        numerator,
        denominator,
        out=np.full_like(np.asarray(numerator, dtype=float), np.nan, dtype=float),
        where=np.asarray(denominator) > 0,
    )


def _rolloff_frequency(
    values: np.ndarray,
    frequencies: np.ndarray,
    total_energy: np.ndarray,
    rolloff: float,
) -> np.ndarray:
    cumulative = np.cumsum(values, axis=0)
    thresholds = np.asarray(total_energy, dtype=float).reshape(1, -1) * rolloff
    reached = cumulative >= thresholds
    first_indices = np.argmax(reached, axis=0)
    return frequencies[first_indices]
