"""Basic frequency-wavenumber (FK) transform helpers.

The internal DAS convention is ``data.shape == (n_samples, n_channels)``.
By default, axis 0 is time and axis 1 is the spatial/channel axis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.core.data_model import DASData

FKOutput = Literal["amplitude", "power"]


@dataclass(frozen=True, slots=True)
class FKResult:
    """Frequency-wavenumber transform result.

    ``values`` is always shaped as ``(n_frequencies, n_wavenumbers)``.
    """

    frequencies_hz: np.ndarray
    wavenumbers_cycles_per_m: np.ndarray
    values: np.ndarray
    sample_rate_hz: float
    dx_m: float
    output: FKOutput
    nfft_time: int
    nfft_space: int
    time_axis: int = 0
    channel_axis: int = 1
    shift_wavenumber: bool = True

    @property
    def wavenumbers_cpm(self) -> np.ndarray:
        """Short alias for cycles-per-metre wavenumbers."""

        return self.wavenumbers_cycles_per_m


def fk_transform(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    time_axis: int = 0,
    channel_axis: int = 1,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    window_time: str | Sequence[float] | np.ndarray | None = None,
    window_space: str | Sequence[float] | np.ndarray | None = None,
    shift_wavenumber: bool = True,
    output: FKOutput = "amplitude",
) -> FKResult:
    """Compute a minimal FK transform for 2-D DAS data.

    The transform uses a one-sided real FFT along time and a full complex FFT
    along space.  The resulting matrix has shape
    ``(nfft_time // 2 + 1, nfft_space)``.
    """

    array, sample_rate_hz, dx_m = _as_array_sample_rate_and_dx(data, sample_rate_hz, dx_m)
    if array.ndim != 2:
        raise ValueError("fk_transform expects 2-D data shaped as (n_samples, n_channels)")
    if not np.all(np.isfinite(array)):
        raise ValueError("FK input must contain only finite values; NaN/Inf are not supported")

    time_axis = _normalize_axis(time_axis, array.ndim, name="time_axis")
    channel_axis = _normalize_axis(channel_axis, array.ndim, name="channel_axis")
    if time_axis == channel_axis:
        raise ValueError("time_axis and channel_axis must be different")

    working = np.array(np.moveaxis(array, (time_axis, channel_axis), (0, 1)), dtype=float, copy=True)
    n_samples, n_channels = working.shape
    if n_samples < 2:
        raise ValueError("FK transform requires at least 2 time samples")
    if n_channels < 2:
        raise ValueError("FK transform requires at least 2 channels")

    nfft_time = _normalize_nfft(nfft_time, minimum=n_samples, name="nfft_time")
    nfft_space = _normalize_nfft(nfft_space, minimum=n_channels, name="nfft_space")
    if output not in {"amplitude", "power"}:
        raise ValueError("output must be 'amplitude' or 'power'")

    time_window = _window_values(window_time, n_samples, name="window_time")
    space_window = _window_values(window_space, n_channels, name="window_space")
    if time_window is not None:
        working = working * time_window.reshape(-1, 1)
    if space_window is not None:
        working = working * space_window.reshape(1, -1)

    frequency_space = np.fft.rfft(working, n=nfft_time, axis=0)
    fk_values = np.fft.fft(frequency_space, n=nfft_space, axis=1)
    wavenumbers = np.fft.fftfreq(nfft_space, d=dx_m)
    if shift_wavenumber:
        fk_values = np.fft.fftshift(fk_values, axes=1)
        wavenumbers = np.fft.fftshift(wavenumbers)

    values = np.abs(fk_values) / float(n_samples * n_channels)
    if nfft_time > 1:
        multiplier = np.ones(values.shape[0], dtype=float)
        if nfft_time % 2 == 0:
            multiplier[1:-1] = 2.0
        else:
            multiplier[1:] = 2.0
        values = values * multiplier.reshape(-1, 1)
    if output == "power":
        values = np.square(values)

    return FKResult(
        frequencies_hz=np.fft.rfftfreq(nfft_time, d=1.0 / sample_rate_hz),
        wavenumbers_cycles_per_m=wavenumbers,
        values=values,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        output=output,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        time_axis=time_axis,
        channel_axis=channel_axis,
        shift_wavenumber=bool(shift_wavenumber),
    )


def _as_array_sample_rate_and_dx(
    data,
    sample_rate_hz: float | None,
    dx_m: float | None,
) -> tuple[np.ndarray, float, float]:
    if isinstance(data, DASData):
        if sample_rate_hz is None:
            sample_rate_hz = data.metadata.sample_rate_hz
        if dx_m is None:
            dx_m = data.metadata.dx_m
        array = np.array(data.data, dtype=float, copy=True)
    else:
        array = np.array(data, dtype=float, copy=True)
    sample_rate_hz = _positive_float(sample_rate_hz, name="sample_rate_hz")
    dx_m = _positive_float(dx_m, name="dx_m")
    if array.size == 0:
        raise ValueError("FK input data must not be empty")
    return array, sample_rate_hz, dx_m


def _positive_float(value: float | None, *, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required for FK analysis")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite value") from exc
    if not np.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a positive finite value")
    return result


def _normalize_axis(axis: int, ndim: int, *, name: str) -> int:
    try:
        value = int(axis)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 0:
        value += ndim
    if value < 0 or value >= ndim:
        raise ValueError(f"{name} {axis} is out of range for {ndim}-D data")
    return value


def _normalize_nfft(value: int | None, *, minimum: int, name: str) -> int:
    if value is None:
        return int(minimum)
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    if result < minimum:
        raise ValueError(f"{name} must be greater than or equal to the selected data length")
    return result


def _window_values(
    window: str | Sequence[float] | np.ndarray | None,
    length: int,
    *,
    name: str,
) -> np.ndarray | None:
    if window is None:
        return None
    if isinstance(window, str):
        signal = _scipy_signal()
        return np.asarray(signal.get_window(window, length), dtype=float)
    values = np.asarray(window, dtype=float)
    if values.ndim != 1:
        raise ValueError(f"{name} array must be one-dimensional")
    if values.shape[0] != length:
        raise ValueError(f"{name} length must match the selected data length")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain only finite values")
    return values


def _scipy_signal():
    try:
        from scipy import signal
    except ImportError as exc:  # pragma: no cover - exercised only without scipy installed.
        raise ImportError("scipy is required for named FK windows") from exc
    return signal
