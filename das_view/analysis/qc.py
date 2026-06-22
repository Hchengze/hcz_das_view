"""DAS data quality and local channel-coherence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class ChannelQualityResult:
    """Per-channel QC metrics for DAS arrays."""

    rms: np.ndarray
    std: np.ndarray
    abs_mean: np.ndarray
    energy: np.ndarray
    nan_fraction: np.ndarray
    inf_fraction: np.ndarray
    zero_fraction: np.ndarray
    clipping_fraction: np.ndarray
    spike_count: np.ndarray
    dead_channel: np.ndarray
    noisy_channel: np.ndarray
    low_energy_channel: np.ndarray
    quality_score: np.ndarray
    bad_channel: np.ndarray
    axis: int
    n_samples: int
    n_channels: int


@dataclass(frozen=True, slots=True)
class DataQualityReport:
    """QC report with per-channel metrics and global summary."""

    channel_metrics: ChannelQualityResult
    bad_channel_indices: tuple[int, ...]
    global_summary: dict[str, float | int]


@dataclass(frozen=True, slots=True)
class LocalCoherenceResult:
    """Adjacent or lagged channel coherence result."""

    coherence: np.ndarray
    channel_lag: int
    window_samples: int | None
    step_samples: int | None
    axis: int
    metadata: dict[str, int | None]


def channel_quality_metrics(
    data,
    *,
    axis: int = 0,
    nan_policy: NanPolicy = "omit",
    clipping_threshold: float | None = None,
    dead_channel_std_threshold: float = 1e-12,
    spike_z_threshold: float = 8.0,
) -> ChannelQualityResult:
    """Compute per-channel QC metrics along the time/sample axis."""

    array, axis = _as_time_channel(data, axis=axis, nan_policy=nan_policy)
    finite = np.isfinite(array)
    working = np.where(finite, array, np.nan)
    n_samples, n_channels = working.shape

    rms = np.sqrt(_nanmean(np.square(working), axis=0))
    std = np.nanstd(working, axis=0)
    abs_mean = _nanmean(np.abs(working), axis=0)
    energy = np.nansum(np.square(working), axis=0)
    nan_fraction = np.mean(np.isnan(array), axis=0)
    inf_fraction = np.mean(np.isinf(array), axis=0)
    zero_fraction = np.mean(np.where(finite, array == 0.0, False), axis=0)
    clipping_fraction = _clipping_fraction(array, finite, clipping_threshold)
    spike_count = _spike_count(working, threshold=spike_z_threshold)

    finite_rms = rms[np.isfinite(rms)]
    low_cut = float(np.nanquantile(finite_rms, 0.01)) if finite_rms.size else np.inf
    high_cut = float(np.nanquantile(finite_rms, 0.99)) if finite_rms.size else np.inf
    dead_channel = (std <= dead_channel_std_threshold) | (zero_fraction >= 1.0)
    low_energy_channel = rms <= low_cut
    noisy_channel = rms >= high_cut

    penalties = (
        nan_fraction
        + inf_fraction
        + clipping_fraction
        + np.minimum(spike_count / max(n_samples, 1), 1.0)
        + dead_channel.astype(float)
        + noisy_channel.astype(float) * 0.5
        + low_energy_channel.astype(float) * 0.5
    )
    quality_score = np.clip(1.0 - penalties / 4.0, 0.0, 1.0)
    bad_channel = dead_channel | noisy_channel | low_energy_channel | (nan_fraction > 0) | (inf_fraction > 0)

    return ChannelQualityResult(
        rms=np.nan_to_num(rms, nan=0.0),
        std=np.nan_to_num(std, nan=0.0),
        abs_mean=np.nan_to_num(abs_mean, nan=0.0),
        energy=np.nan_to_num(energy, nan=0.0),
        nan_fraction=nan_fraction,
        inf_fraction=inf_fraction,
        zero_fraction=zero_fraction,
        clipping_fraction=clipping_fraction,
        spike_count=spike_count,
        dead_channel=dead_channel,
        noisy_channel=noisy_channel,
        low_energy_channel=low_energy_channel,
        quality_score=quality_score,
        bad_channel=bad_channel,
        axis=axis,
        n_samples=n_samples,
        n_channels=n_channels,
    )


def estimate_noise_floor(
    data,
    *,
    axis: int = 0,
    method: Literal["mad", "std", "rms"] = "mad",
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Estimate per-channel noise floor."""

    array, _ = _as_time_channel(data, axis=axis, nan_policy=nan_policy)
    working = np.where(np.isfinite(array), array, np.nan)
    if method == "mad":
        median = np.nanmedian(working, axis=0)
        return 1.4826 * np.nanmedian(np.abs(working - median.reshape(1, -1)), axis=0)
    if method == "std":
        return np.nanstd(working, axis=0)
    if method == "rms":
        return np.sqrt(_nanmean(np.square(working), axis=0))
    raise ValueError("method must be 'mad', 'std', or 'rms'")


def estimate_snr(
    data,
    *,
    axis: int = 0,
    signal_window=None,
    noise_window=None,
    method: Literal["rms", "peak"] = "rms",
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Estimate per-channel SNR as signal metric divided by noise metric."""

    array, _ = _as_time_channel(data, axis=axis, nan_policy=nan_policy)
    signal = _window(array, signal_window)
    noise = _window(array, noise_window)
    if method == "rms":
        signal_value = np.sqrt(_nanmean(np.square(np.where(np.isfinite(signal), signal, np.nan)), axis=0))
        noise_value = np.sqrt(_nanmean(np.square(np.where(np.isfinite(noise), noise, np.nan)), axis=0))
    elif method == "peak":
        signal_value = np.nanmax(np.abs(np.where(np.isfinite(signal), signal, np.nan)), axis=0)
        noise_value = np.nanmax(np.abs(np.where(np.isfinite(noise), noise, np.nan)), axis=0)
    else:
        raise ValueError("method must be 'rms' or 'peak'")
    return np.divide(signal_value, noise_value, out=np.full_like(signal_value, np.inf), where=noise_value > 0)


def detect_bad_channels(
    data,
    *,
    axis: int = 0,
    rms_low_quantile: float = 0.01,
    rms_high_quantile: float = 0.99,
    std_low_threshold: float | None = None,
    spike_z_threshold: float = 8.0,
    nan_fraction_threshold: float = 0.1,
    clipping_fraction_threshold: float = 0.05,
    nan_policy: NanPolicy = "omit",
) -> tuple[int, ...]:
    """Return channel indices that fail simple QC thresholds."""

    metrics = channel_quality_metrics(
        data,
        axis=axis,
        nan_policy=nan_policy,
        dead_channel_std_threshold=std_low_threshold or 1e-12,
        spike_z_threshold=spike_z_threshold,
    )
    rms = metrics.rms[np.isfinite(metrics.rms)]
    low = float(np.quantile(rms, rms_low_quantile)) if rms.size else np.inf
    high = float(np.quantile(rms, rms_high_quantile)) if rms.size else np.inf
    bad = (
        (metrics.rms <= low)
        | (metrics.rms >= high)
        | (metrics.nan_fraction >= nan_fraction_threshold)
        | (metrics.clipping_fraction >= clipping_fraction_threshold)
        | (metrics.spike_count > 0)
        | metrics.dead_channel
    )
    return tuple(int(i) for i in np.flatnonzero(bad))


def data_quality_report(
    data,
    *,
    axis: int = 0,
    nan_policy: NanPolicy = "omit",
    clipping_threshold: float | None = None,
) -> DataQualityReport:
    """Build a QC report from per-channel metrics."""

    metrics = channel_quality_metrics(
        data,
        axis=axis,
        nan_policy=nan_policy,
        clipping_threshold=clipping_threshold,
    )
    bad = tuple(int(i) for i in np.flatnonzero(metrics.bad_channel))
    summary = {
        "n_samples": metrics.n_samples,
        "n_channels": metrics.n_channels,
        "bad_channel_count": len(bad),
        "mean_quality_score": float(np.mean(metrics.quality_score)) if metrics.quality_score.size else 0.0,
        "mean_rms": float(np.mean(metrics.rms)) if metrics.rms.size else 0.0,
        "mean_std": float(np.mean(metrics.std)) if metrics.std.size else 0.0,
    }
    return DataQualityReport(channel_metrics=metrics, bad_channel_indices=bad, global_summary=summary)


def local_channel_coherence(
    data,
    *,
    axis: int = 0,
    channel_lag: int = 1,
    window_samples: int | None = None,
    step_samples: int | None = None,
    nan_policy: NanPolicy = "omit",
) -> LocalCoherenceResult:
    """Compute local Pearson-correlation coherence between lagged channels."""

    lag = int(channel_lag)
    if lag <= 0:
        raise ValueError("channel_lag must be a positive integer")
    array, axis = _as_time_channel(data, axis=axis, nan_policy=nan_policy)
    if lag >= array.shape[1]:
        raise ValueError("channel_lag must be smaller than the number of channels")

    if window_samples is None:
        values = _coherence_for_window(array, lag).reshape(1, -1)
        window = None
        step = None
    else:
        window = _positive_int(window_samples, "window_samples")
        step = _positive_int(step_samples if step_samples is not None else window, "step_samples")
        if window > array.shape[0]:
            raise ValueError("window_samples must not exceed the number of samples")
        values = np.vstack([_coherence_for_window(array[start : start + window], lag) for start in range(0, array.shape[0] - window + 1, step)])

    return LocalCoherenceResult(
        coherence=np.asarray(values, dtype=float),
        channel_lag=lag,
        window_samples=window,
        step_samples=step,
        axis=axis,
        metadata={
            "n_windows": int(values.shape[0]),
            "n_channel_pairs": int(values.shape[1]),
            "n_samples": int(array.shape[0]),
            "n_channels": int(array.shape[1]),
        },
    )


def channel_quality_rows(report: DataQualityReport | ChannelQualityResult) -> list[dict[str, float | int | bool]]:
    """Convert QC metrics to one row per channel."""

    metrics = report.channel_metrics if isinstance(report, DataQualityReport) else report
    rows = []
    for index in range(metrics.n_channels):
        rows.append(
            {
                "channel": index,
                "rms": float(metrics.rms[index]),
                "std": float(metrics.std[index]),
                "abs_mean": float(metrics.abs_mean[index]),
                "energy": float(metrics.energy[index]),
                "nan_fraction": float(metrics.nan_fraction[index]),
                "inf_fraction": float(metrics.inf_fraction[index]),
                "zero_fraction": float(metrics.zero_fraction[index]),
                "clipping_fraction": float(metrics.clipping_fraction[index]),
                "spike_count": int(metrics.spike_count[index]),
                "dead_channel": bool(metrics.dead_channel[index]),
                "noisy_channel": bool(metrics.noisy_channel[index]),
                "low_energy_channel": bool(metrics.low_energy_channel[index]),
                "quality_score": float(metrics.quality_score[index]),
                "bad_channel": bool(metrics.bad_channel[index]),
            }
        )
    return rows


def _as_time_channel(data, *, axis: int, nan_policy: NanPolicy) -> tuple[np.ndarray, int]:
    if nan_policy not in ("omit", "raise"):
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    array = np.array(data.data if isinstance(data, DASData) else data, dtype=float, copy=True)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    if array.ndim != 2:
        raise ValueError("QC analysis expects a 1-D or 2-D numeric array")
    axis = int(axis)
    if axis < 0:
        axis += array.ndim
    if axis not in (0, 1):
        raise ValueError("axis must be 0 or 1")
    if axis != 0:
        array = np.moveaxis(array, axis, 0)
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("QC input contains NaN or Inf values")
    return array, axis


def _nanmean(values: np.ndarray, *, axis: int):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.nanmean(values, axis=axis)


def _clipping_fraction(array: np.ndarray, finite: np.ndarray, threshold: float | None) -> np.ndarray:
    if threshold is None:
        return np.zeros(array.shape[1], dtype=float)
    threshold = float(threshold)
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("clipping_threshold must be a positive finite value")
    return np.mean(np.where(finite, np.abs(array) >= threshold, False), axis=0)


def _spike_count(array: np.ndarray, *, threshold: float) -> np.ndarray:
    threshold = float(threshold)
    if threshold <= 0 or not np.isfinite(threshold):
        raise ValueError("spike_z_threshold must be a positive finite value")
    median = np.nanmedian(array, axis=0)
    mad = np.nanmedian(np.abs(array - median.reshape(1, -1)), axis=0)
    scale = 1.4826 * mad
    deviation = np.abs(array - median.reshape(1, -1))
    z = np.divide(deviation, scale.reshape(1, -1), out=np.zeros_like(array), where=scale.reshape(1, -1) > 0)
    max_deviation = np.nanmax(deviation, axis=0)
    isolated_on_flat = (scale <= 0) & (max_deviation > 0)
    counts = np.sum(z >= threshold, axis=0).astype(int)
    counts = np.where(isolated_on_flat, np.sum(deviation > 0, axis=0), counts)
    return counts.astype(int)


def _window(array: np.ndarray, value) -> np.ndarray:
    if value is None:
        return array
    if isinstance(value, slice):
        return array[value]
    start, stop = value
    return array[slice(start, stop)]


def _positive_int(value, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _coherence_for_window(array: np.ndarray, lag: int) -> np.ndarray:
    left = array[:, :-lag]
    right = array[:, lag:]
    values = []
    for index in range(left.shape[1]):
        a = left[:, index]
        b = right[:, index]
        mask = np.isfinite(a) & np.isfinite(b)
        if np.sum(mask) < 2:
            values.append(np.nan)
            continue
        a = a[mask] - np.mean(a[mask])
        b = b[mask] - np.mean(b[mask])
        denom = np.sqrt(np.sum(a * a) * np.sum(b * b))
        values.append(float(np.sum(a * b) / denom) if denom > 0 else 0.0)
    return np.asarray(values, dtype=float)
