"""Lightweight wavefield moveout and directional-energy attributes.

These helpers provide DAS wavefield assisted-analysis attributes only.  Apparent
slope and apparent velocity are review features, not source locations, velocity
inversions, imaging results, or geologic interpretations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.analysis.fk import FKResult, fk_transform
from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class DirectionalEnergyResult:
    """FK-domain directional energy summary."""

    positive_wavenumber_energy: float
    negative_wavenumber_energy: float
    zero_wavenumber_energy: float
    directional_ratio: float
    dominant_direction: str
    total_energy: float
    frequencies_hz: np.ndarray
    wavenumbers_cpm: np.ndarray
    velocity_band_energy: dict[str, float]
    fk_result: FKResult


@dataclass(frozen=True, slots=True)
class ApparentSlopeResult:
    """Cross-correlation apparent slope attributes."""

    lag_samples: np.ndarray
    lag_seconds: np.ndarray
    slope_s_per_m: np.ndarray
    apparent_velocity_mps: np.ndarray
    correlation_peak: np.ndarray
    channel_lag: int
    window_samples: int | None
    step_samples: int | None
    max_lag_samples: int
    sample_rate_hz: float
    dx_m: float
    metadata: dict[str, int | float | None]


@dataclass(frozen=True, slots=True)
class ApparentVelocityResult:
    """Apparent velocity attribute converted from slope."""

    apparent_velocity_mps: np.ndarray
    slope_s_per_m: np.ndarray
    eps: float


@dataclass(frozen=True, slots=True)
class MoveoutCoherenceResult:
    """Local moveout coherence and lag attributes."""

    coherence: np.ndarray
    lag_samples: np.ndarray
    apparent_velocity_mps: np.ndarray
    channel_lag: int
    window_samples: int | None
    step_samples: int | None
    metadata: dict[str, int | float | None]


@dataclass(frozen=True, slots=True)
class MoveoutSummaryReport:
    """Combined directional energy and apparent moveout summary."""

    directional_energy: DirectionalEnergyResult
    apparent_slope: ApparentSlopeResult
    moveout_coherence: MoveoutCoherenceResult
    summary: dict[str, float | int | str]


def fk_directional_energy(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    axis_time: int = 0,
    axis_channel: int = 1,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    velocity_bands=None,
    direction: Literal["both", "positive", "negative"] = "both",
    nan_policy: NanPolicy = "raise",
    backend: str = "cpu",
) -> DirectionalEnergyResult:
    """Summarize positive/negative/zero-wavenumber FK energy."""

    array, sample_rate_hz, dx_m = _as_array_sample_rate_dx(data, sample_rate_hz, dx_m, nan_policy=nan_policy)
    fk = fk_transform(
        array,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        time_axis=axis_time,
        channel_axis=axis_channel,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        output="power",
        backend=backend,
    )
    values = np.asarray(fk.values, dtype=float)
    wavenumbers = fk.wavenumbers_cpm
    positive_mask = wavenumbers > 0
    negative_mask = wavenumbers < 0
    zero_mask = wavenumbers == 0
    if direction == "positive":
        negative_mask = np.zeros_like(negative_mask, dtype=bool)
    elif direction == "negative":
        positive_mask = np.zeros_like(positive_mask, dtype=bool)
    elif direction != "both":
        raise ValueError("direction must be 'both', 'positive', or 'negative'")

    positive = _sum_energy(values[:, positive_mask])
    negative = _sum_energy(values[:, negative_mask])
    zero = _sum_energy(values[:, zero_mask])
    total = positive + negative + zero
    directional_ratio_value = (positive - negative) / (positive + negative) if positive + negative > 0 else 0.0
    dominant = _dominant_direction(positive, negative)
    bands = _velocity_band_energy(values, fk.frequencies_hz, wavenumbers, velocity_bands)
    return DirectionalEnergyResult(
        positive_wavenumber_energy=float(positive),
        negative_wavenumber_energy=float(negative),
        zero_wavenumber_energy=float(zero),
        directional_ratio=float(directional_ratio_value),
        dominant_direction=dominant,
        total_energy=float(total),
        frequencies_hz=fk.frequencies_hz,
        wavenumbers_cpm=wavenumbers,
        velocity_band_energy=bands,
        fk_result=fk,
    )


def directional_energy_ratio(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    velocity_split_mps: float | None = None,
    axis_time: int = 0,
    axis_channel: int = 1,
    nan_policy: NanPolicy = "raise",
    backend: str = "cpu",
) -> DirectionalEnergyResult:
    """Return a compact FK directional energy ratio attribute."""

    velocity_bands = None
    if velocity_split_mps is not None:
        split = _positive_float(velocity_split_mps, "velocity_split_mps")
        velocity_bands = ((0.0, split), (split, None))
    return fk_directional_energy(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        axis_time=axis_time,
        axis_channel=axis_channel,
        velocity_bands=velocity_bands,
        nan_policy=nan_policy,
        backend=backend,
    )


def estimate_apparent_slope_xcorr(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    channel_lag: int = 1,
    window_samples: int | None = None,
    step_samples: int | None = None,
    max_lag_samples: int | None = None,
    axis_time: int = 0,
    axis_channel: int = 1,
    nan_policy: NanPolicy = "raise",
) -> ApparentSlopeResult:
    """Estimate apparent time-lag slope between channel pairs by xcorr."""

    array, sample_rate_hz, dx_m = _as_time_channel(data, sample_rate_hz, dx_m, axis_time, axis_channel, nan_policy)
    channel_lag = _positive_int(channel_lag, "channel_lag")
    if channel_lag >= array.shape[1]:
        raise ValueError("channel_lag must be smaller than the number of channels")
    windows = _window_ranges(array.shape[0], window_samples=window_samples, step_samples=step_samples)
    max_lag = _max_lag(max_lag_samples, window_length=windows[0][1] - windows[0][0])
    n_pairs = array.shape[1] - channel_lag
    lag_samples = np.zeros((len(windows), n_pairs), dtype=float)
    corr_peak = np.zeros_like(lag_samples)

    for w_idx, (start, stop) in enumerate(windows):
        segment = array[start:stop]
        for pair in range(n_pairs):
            lag, corr = _xcorr_lag(segment[:, pair], segment[:, pair + channel_lag], max_lag=max_lag)
            lag_samples[w_idx, pair] = lag
            corr_peak[w_idx, pair] = corr

    lag_seconds = lag_samples / sample_rate_hz
    distance_m = dx_m * channel_lag
    slope = lag_seconds / distance_m
    velocity = apparent_velocity_from_slope(slope).apparent_velocity_mps
    if window_samples is None:
        lag_samples = lag_samples.reshape(n_pairs)
        lag_seconds = lag_seconds.reshape(n_pairs)
        slope = slope.reshape(n_pairs)
        velocity = velocity.reshape(n_pairs)
        corr_peak = corr_peak.reshape(n_pairs)
    return ApparentSlopeResult(
        lag_samples=lag_samples,
        lag_seconds=lag_seconds,
        slope_s_per_m=slope,
        apparent_velocity_mps=velocity,
        correlation_peak=corr_peak,
        channel_lag=channel_lag,
        window_samples=window_samples,
        step_samples=step_samples,
        max_lag_samples=max_lag,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        metadata={
            "n_windows": len(windows),
            "n_channel_pairs": n_pairs,
            "distance_m": float(distance_m),
        },
    )


def apparent_velocity_from_slope(slope_s_per_m, *, eps: float = 1e-12) -> ApparentVelocityResult:
    """Convert apparent slope attribute to apparent velocity attribute."""

    _positive_float(eps, "eps")
    slope = np.asarray(slope_s_per_m, dtype=float)
    velocity = np.divide(1.0, slope, out=np.full_like(slope, np.inf, dtype=float), where=np.abs(slope) > eps)
    return ApparentVelocityResult(apparent_velocity_mps=velocity, slope_s_per_m=slope.copy(), eps=float(eps))


def local_moveout_coherence(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    channel_lag: int = 1,
    window_samples: int | None = None,
    step_samples: int | None = None,
    max_lag_samples: int | None = None,
    axis_time: int = 0,
    axis_channel: int = 1,
    nan_policy: NanPolicy = "raise",
) -> MoveoutCoherenceResult:
    """Return local moveout coherence derived from xcorr peaks."""

    slope = estimate_apparent_slope_xcorr(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        channel_lag=channel_lag,
        window_samples=window_samples,
        step_samples=step_samples,
        max_lag_samples=max_lag_samples,
        axis_time=axis_time,
        axis_channel=axis_channel,
        nan_policy=nan_policy,
    )
    return MoveoutCoherenceResult(
        coherence=np.abs(slope.correlation_peak),
        lag_samples=slope.lag_samples,
        apparent_velocity_mps=slope.apparent_velocity_mps,
        channel_lag=slope.channel_lag,
        window_samples=slope.window_samples,
        step_samples=slope.step_samples,
        metadata=slope.metadata,
    )


def moveout_summary_report(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    channel_lag: int = 1,
    window_samples: int | None = None,
    step_samples: int | None = None,
    velocity_bands=None,
    nan_policy: NanPolicy = "raise",
    backend: str = "cpu",
) -> MoveoutSummaryReport:
    """Combine directional energy and apparent moveout attributes."""

    directional = fk_directional_energy(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        velocity_bands=velocity_bands,
        nan_policy=nan_policy,
        backend=backend,
    )
    slope = estimate_apparent_slope_xcorr(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        channel_lag=channel_lag,
        window_samples=window_samples,
        step_samples=step_samples,
        nan_policy=nan_policy,
    )
    coherence = local_moveout_coherence(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        channel_lag=channel_lag,
        window_samples=window_samples,
        step_samples=step_samples,
        nan_policy=nan_policy,
    )
    finite_velocity = slope.apparent_velocity_mps[np.isfinite(slope.apparent_velocity_mps)]
    summary = {
        "dominant_direction": directional.dominant_direction,
        "directional_ratio": directional.directional_ratio,
        "mean_abs_correlation_peak": float(np.mean(np.abs(slope.correlation_peak))) if slope.correlation_peak.size else 0.0,
        "median_apparent_velocity_mps": float(np.median(finite_velocity)) if finite_velocity.size else 0.0,
        "n_channel_pairs": int(slope.metadata["n_channel_pairs"]),
        "n_windows": int(slope.metadata["n_windows"]),
    }
    return MoveoutSummaryReport(
        directional_energy=directional,
        apparent_slope=slope,
        moveout_coherence=coherence,
        summary=summary,
    )


def _as_array_sample_rate_dx(data, sample_rate_hz, dx_m, *, nan_policy: NanPolicy) -> tuple[np.ndarray, float, float]:
    if nan_policy not in {"omit", "raise"}:
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    if isinstance(data, DASData):
        if sample_rate_hz is None:
            sample_rate_hz = data.metadata.sample_rate_hz
        if dx_m is None:
            dx_m = data.metadata.dx_m
        array = np.array(data.data, dtype=float, copy=True)
    else:
        array = np.array(data, dtype=float, copy=True)
    if array.size == 0:
        raise ValueError("moveout input data must not be empty")
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("moveout input must contain only finite values")
    if nan_policy == "omit":
        array = np.where(np.isfinite(array), array, 0.0)
    return array, _positive_float(sample_rate_hz, "sample_rate_hz"), _positive_float(dx_m, "dx_m")


def _as_time_channel(data, sample_rate_hz, dx_m, axis_time, axis_channel, nan_policy) -> tuple[np.ndarray, float, float]:
    array, sample_rate_hz, dx_m = _as_array_sample_rate_dx(data, sample_rate_hz, dx_m, nan_policy=nan_policy)
    if array.ndim != 2:
        raise ValueError("moveout analysis expects 2-D data shaped as (n_samples, n_channels)")
    axis_time = _normalize_axis(axis_time, array.ndim, "axis_time")
    axis_channel = _normalize_axis(axis_channel, array.ndim, "axis_channel")
    if axis_time == axis_channel:
        raise ValueError("axis_time and axis_channel must be different")
    working = np.moveaxis(array, (axis_time, axis_channel), (0, 1))
    if working.shape[0] < 2:
        raise ValueError("moveout analysis requires at least 2 time samples")
    if working.shape[1] < 2:
        raise ValueError("moveout analysis requires at least 2 channels")
    return np.array(working, dtype=float, copy=True), sample_rate_hz, dx_m


def _positive_float(value, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required for moveout analysis")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite value") from exc
    if not np.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a positive finite value")
    return result


def _positive_int(value, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _normalize_axis(axis: int, ndim: int, name: str) -> int:
    try:
        value = int(axis)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 0:
        value += ndim
    if value < 0 or value >= ndim:
        raise ValueError(f"{name} {axis} is out of range for {ndim}-D data")
    return value


def _window_ranges(n_samples: int, *, window_samples: int | None, step_samples: int | None) -> tuple[tuple[int, int], ...]:
    if window_samples is None:
        return ((0, n_samples),)
    window = _positive_int(window_samples, "window_samples")
    step = _positive_int(step_samples if step_samples is not None else window, "step_samples")
    if window > n_samples:
        raise ValueError("window_samples must be <= number of time samples")
    return tuple((start, start + window) for start in range(0, n_samples - window + 1, step))


def _max_lag(max_lag_samples: int | None, *, window_length: int) -> int:
    if max_lag_samples is None:
        return max(1, min(window_length - 1, window_length // 4))
    lag = _positive_int(max_lag_samples, "max_lag_samples")
    if lag >= window_length:
        raise ValueError("max_lag_samples must be smaller than the window length")
    return lag


def _xcorr_lag(left: np.ndarray, right: np.ndarray, *, max_lag: int) -> tuple[int, float]:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    left = left - np.mean(left)
    right = right - np.mean(right)
    best_lag = 0
    best_corr = 0.0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            a = left[-lag:]
            b = right[: lag or None]
        elif lag > 0:
            a = left[:-lag]
            b = right[lag:]
        else:
            a = left
            b = right
        if a.size < 2 or b.size < 2:
            continue
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        corr = 0.0 if denom == 0.0 else float(np.dot(a, b) / denom)
        if abs(corr) > abs(best_corr):
            best_lag = lag
            best_corr = corr
    return best_lag, best_corr


def _sum_energy(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.sum(np.where(np.isfinite(values), values, 0.0)))


def _dominant_direction(positive: float, negative: float, *, tolerance: float = 0.05) -> str:
    total = positive + negative
    if total <= 0:
        return "balanced"
    ratio = abs(positive - negative) / total
    if ratio <= tolerance:
        return "balanced"
    return "positive_k" if positive > negative else "negative_k"


def _velocity_band_energy(values, frequencies, wavenumbers, velocity_bands) -> dict[str, float]:
    if velocity_bands is None:
        return {}
    frequency_grid = np.abs(frequencies).reshape(-1, 1)
    wavenumber_grid = np.abs(wavenumbers).reshape(1, -1)
    velocity = np.divide(
        frequency_grid,
        wavenumber_grid,
        out=np.full((frequencies.size, wavenumbers.size), np.inf, dtype=float),
        where=wavenumber_grid != 0,
    )
    result: dict[str, float] = {}
    for index, band in enumerate(velocity_bands):
        if len(band) != 2:
            raise ValueError("velocity_bands entries must be (vmin, vmax)")
        vmin = 0.0 if band[0] is None else float(band[0])
        vmax = np.inf if band[1] is None else float(band[1])
        if not (np.isfinite(vmin) and vmin >= 0 and vmax > vmin):
            raise ValueError("velocity_bands must satisfy 0 <= vmin < vmax")
        mask = (velocity >= vmin) & (velocity < vmax)
        label = f"band_{index}_{vmin:g}_{vmax:g}_mps"
        result[label] = _sum_energy(values[mask])
    return result
