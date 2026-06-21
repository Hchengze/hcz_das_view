"""Basic scipy.signal filters for DAS arrays.

The internal DAS convention is (n_samples, n_channels).  Therefore the default
axis=0 filters each channel independently along time.
"""

from __future__ import annotations

import numpy as np


def lowpass(
    data,
    *,
    sample_rate_hz: float,
    cutoff_hz: float,
    axis: int = 0,
    order: int = 4,
    zero_phase: bool = True,
) -> np.ndarray:
    """Apply a Butterworth low-pass filter."""

    array, axis, sample_rate_hz, order = _validate_common(
        data, sample_rate_hz=sample_rate_hz, axis=axis, order=order
    )
    cutoff_hz = _validate_single_cutoff(cutoff_hz, sample_rate_hz, name="cutoff_hz")
    signal = _scipy_signal()
    sos = signal.butter(order, cutoff_hz, btype="lowpass", fs=sample_rate_hz, output="sos")
    return _apply_sos(sos, array, axis=axis, zero_phase=zero_phase)


def highpass(
    data,
    *,
    sample_rate_hz: float,
    cutoff_hz: float,
    axis: int = 0,
    order: int = 4,
    zero_phase: bool = True,
) -> np.ndarray:
    """Apply a Butterworth high-pass filter."""

    array, axis, sample_rate_hz, order = _validate_common(
        data, sample_rate_hz=sample_rate_hz, axis=axis, order=order
    )
    cutoff_hz = _validate_single_cutoff(cutoff_hz, sample_rate_hz, name="cutoff_hz")
    signal = _scipy_signal()
    sos = signal.butter(order, cutoff_hz, btype="highpass", fs=sample_rate_hz, output="sos")
    return _apply_sos(sos, array, axis=axis, zero_phase=zero_phase)


def bandpass(
    data,
    *,
    sample_rate_hz: float,
    freqmin_hz: float,
    freqmax_hz: float,
    axis: int = 0,
    order: int = 4,
    zero_phase: bool = True,
) -> np.ndarray:
    """Apply a Butterworth band-pass filter."""

    array, axis, sample_rate_hz, order = _validate_common(
        data, sample_rate_hz=sample_rate_hz, axis=axis, order=order
    )
    freqmin_hz, freqmax_hz = _validate_frequency_pair(freqmin_hz, freqmax_hz, sample_rate_hz)
    signal = _scipy_signal()
    sos = signal.butter(
        order,
        [freqmin_hz, freqmax_hz],
        btype="bandpass",
        fs=sample_rate_hz,
        output="sos",
    )
    return _apply_sos(sos, array, axis=axis, zero_phase=zero_phase)


def bandstop(
    data,
    *,
    sample_rate_hz: float,
    freqmin_hz: float,
    freqmax_hz: float,
    axis: int = 0,
    order: int = 4,
    zero_phase: bool = True,
) -> np.ndarray:
    """Apply a Butterworth band-stop filter."""

    array, axis, sample_rate_hz, order = _validate_common(
        data, sample_rate_hz=sample_rate_hz, axis=axis, order=order
    )
    freqmin_hz, freqmax_hz = _validate_frequency_pair(freqmin_hz, freqmax_hz, sample_rate_hz)
    signal = _scipy_signal()
    sos = signal.butter(
        order,
        [freqmin_hz, freqmax_hz],
        btype="bandstop",
        fs=sample_rate_hz,
        output="sos",
    )
    return _apply_sos(sos, array, axis=axis, zero_phase=zero_phase)


def notch(
    data,
    *,
    sample_rate_hz: float,
    notch_hz: float,
    quality: float = 30.0,
    axis: int = 0,
    zero_phase: bool = True,
) -> np.ndarray:
    """Apply an IIR notch filter at notch_hz."""

    array, axis, sample_rate_hz, _ = _validate_common(
        data, sample_rate_hz=sample_rate_hz, axis=axis, order=1
    )
    notch_hz = _validate_single_cutoff(notch_hz, sample_rate_hz, name="notch_hz")
    quality = float(quality)
    if not np.isfinite(quality) or quality <= 0:
        raise ValueError("quality must be a positive finite value")
    signal = _scipy_signal()
    b, a = signal.iirnotch(notch_hz, quality, fs=sample_rate_hz)
    sos = signal.tf2sos(b, a)
    return _apply_sos(sos, array, axis=axis, zero_phase=zero_phase)


def _scipy_signal():
    try:
        from scipy import signal
    except ImportError as exc:  # pragma: no cover - exercised only without scipy installed.
        raise ImportError(
            "scipy is required for das_view.processing.filters; install das-view with scipy"
        ) from exc
    return signal


def _validate_common(
    data,
    *,
    sample_rate_hz: float,
    axis: int,
    order: int,
) -> tuple[np.ndarray, int, float, int]:
    array = np.array(data, dtype=float, copy=True)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
    if not np.all(np.isfinite(array)):
        raise ValueError("filter input must contain only finite values; NaN/Inf are not supported")
    axis = _normalize_axis(axis, array.ndim)
    sample_rate_hz = float(sample_rate_hz)
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be a positive finite value")
    try:
        order = int(order)
    except (TypeError, ValueError) as exc:
        raise ValueError("order must be a positive integer") from exc
    if order <= 0:
        raise ValueError("order must be a positive integer")
    return array, axis, sample_rate_hz, order


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


def _validate_single_cutoff(value: float, sample_rate_hz: float, *, name: str) -> float:
    value = float(value)
    nyquist = sample_rate_hz / 2.0
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite value")
    if value >= nyquist:
        raise ValueError(f"{name} must be less than Nyquist frequency ({nyquist:g} Hz)")
    return value


def _validate_frequency_pair(
    freqmin_hz: float,
    freqmax_hz: float,
    sample_rate_hz: float,
) -> tuple[float, float]:
    freqmin_hz = _validate_single_cutoff(freqmin_hz, sample_rate_hz, name="freqmin_hz")
    freqmax_hz = _validate_single_cutoff(freqmax_hz, sample_rate_hz, name="freqmax_hz")
    if freqmin_hz >= freqmax_hz:
        raise ValueError("freqmin_hz must be less than freqmax_hz")
    return freqmin_hz, freqmax_hz


def _apply_sos(
    sos: np.ndarray,
    array: np.ndarray,
    *,
    axis: int,
    zero_phase: bool,
) -> np.ndarray:
    signal = _scipy_signal()
    if array.shape[axis] < _minimum_length(sos, zero_phase=zero_phase):
        raise ValueError(
            "data is too short for this filter along the selected axis; "
            f"got {array.shape[axis]} samples"
        )
    if zero_phase:
        return signal.sosfiltfilt(sos, array, axis=axis)
    return signal.sosfilt(sos, array, axis=axis)


def _minimum_length(sos: np.ndarray, *, zero_phase: bool) -> int:
    if not zero_phase:
        return 1
    # scipy.signal.sosfiltfilt uses a default pad length derived from the number
    # of SOS sections. Require one more sample than that pad length so callers
    # get a stable, project-level error message before scipy raises its own.
    sections = int(np.asarray(sos).shape[0])
    return 3 * (2 * sections + 1) + 1
