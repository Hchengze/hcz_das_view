"""Basic DAS statistics helpers.

The default DAS convention is ``data.shape == (n_samples, n_channels)``:
axis 0 is time and axis 1 is channel/space.  These functions are
GUI-independent and accept either numpy arrays or DASData.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
import warnings

import numpy as np

from das_view.acceleration import as_backend_array, get_acceleration_backend, to_numpy
from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class FiniteSummary:
    """Finite/NaN/Inf counts for a statistics input or reduction."""

    count: int | np.ndarray
    finite_count: int | np.ndarray
    nan_count: int | np.ndarray
    posinf_count: int | np.ndarray
    neginf_count: int | np.ndarray
    axis: int | None
    input_shape: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class StatisticsResult:
    """Basic statistical attributes for a DAS array selection."""

    axis: int | None
    input_shape: tuple[int, ...]
    count: int | np.ndarray
    finite_count: int | np.ndarray
    nan_count: int | np.ndarray
    posinf_count: int | np.ndarray
    neginf_count: int | np.ndarray
    mean: float | np.ndarray
    std: float | np.ndarray
    min: float | np.ndarray
    max: float | np.ndarray
    median: float | np.ndarray
    percentiles: dict[float, float | np.ndarray]
    rms: float | np.ndarray
    abs_mean: float | np.ndarray
    peak_to_peak: float | np.ndarray
    energy: float | np.ndarray
    nan_policy: NanPolicy
    source_metadata: dict[str, Any] | None = None

    @property
    def finite_summary(self) -> FiniteSummary:
        """Return the finite-value summary associated with this result."""

        return FiniteSummary(
            count=self.count,
            finite_count=self.finite_count,
            nan_count=self.nan_count,
            posinf_count=self.posinf_count,
            neginf_count=self.neginf_count,
            axis=self.axis,
            input_shape=self.input_shape,
        )


def finite_summary(data, *, axis: int | None = None) -> FiniteSummary:
    """Count finite, NaN, +Inf, and -Inf values."""

    array, _ = _as_numeric_array_and_metadata(data)
    normalized_axis = _normalize_axis(axis, array.ndim)
    finite = np.isfinite(array)
    nan = np.isnan(array)
    posinf = np.isposinf(array)
    neginf = np.isneginf(array)

    if normalized_axis is None:
        count: int | np.ndarray = int(array.size)
        finite_count: int | np.ndarray = int(np.count_nonzero(finite))
        nan_count: int | np.ndarray = int(np.count_nonzero(nan))
        posinf_count: int | np.ndarray = int(np.count_nonzero(posinf))
        neginf_count: int | np.ndarray = int(np.count_nonzero(neginf))
    else:
        count = np.full(_reduced_shape(array.shape, normalized_axis), array.shape[normalized_axis], dtype=int)
        finite_count = np.sum(finite, axis=normalized_axis)
        nan_count = np.sum(nan, axis=normalized_axis)
        posinf_count = np.sum(posinf, axis=normalized_axis)
        neginf_count = np.sum(neginf, axis=normalized_axis)

    return FiniteSummary(
        count=count,
        finite_count=finite_count,
        nan_count=nan_count,
        posinf_count=posinf_count,
        neginf_count=neginf_count,
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
    )


def basic_statistics(
    data,
    *,
    axis: int | None = None,
    percentiles=(1, 5, 25, 50, 75, 95, 99),
    nan_policy: NanPolicy = "omit",
    backend: str = "cpu",
) -> StatisticsResult:
    """Compute basic statistics for an array or DASData.

    ``axis=None`` computes one global summary.  ``axis=0`` reduces the time
    axis and returns one value per channel for 2-D DAS arrays.  ``axis=1``
    reduces the channel axis and returns one value per sample.
    """

    array, metadata_summary = _as_numeric_array_and_metadata(data)
    normalized_axis = _normalize_axis(axis, array.ndim)
    percentile_values = _normalize_percentiles(percentiles)
    if nan_policy not in ("omit", "raise"):
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("statistics input contains NaN or Inf values")

    resolved_backend = get_acceleration_backend(backend)
    if resolved_backend.name == "gpu":
        stats_result = _basic_statistics_backend(
            array,
            metadata_summary=metadata_summary,
            axis=normalized_axis,
            percentiles=percentile_values,
            nan_policy=nan_policy,
            backend=backend,
        )
        if stats_result is not None:
            return stats_result

    summary = finite_summary(array, axis=normalized_axis)
    clean = np.where(np.isfinite(array), array, np.nan)

    if normalized_axis is None:
        values = clean[np.isfinite(clean)]
        stats = _global_statistics(values, percentile_values)
    else:
        stats = _axis_statistics(clean, summary.finite_count, normalized_axis, percentile_values)

    return StatisticsResult(
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
        count=summary.count,
        finite_count=summary.finite_count,
        nan_count=summary.nan_count,
        posinf_count=summary.posinf_count,
        neginf_count=summary.neginf_count,
        mean=stats["mean"],
        std=stats["std"],
        min=stats["min"],
        max=stats["max"],
        median=stats["median"],
        percentiles=stats["percentiles"],
        rms=stats["rms"],
        abs_mean=stats["abs_mean"],
        peak_to_peak=stats["peak_to_peak"],
        energy=stats["energy"],
        nan_policy=nan_policy,
        source_metadata=metadata_summary,
    )


def _basic_statistics_backend(
    array: np.ndarray,
    *,
    metadata_summary: dict[str, Any] | None,
    axis: int | None,
    percentiles: tuple[float, ...],
    nan_policy: NanPolicy,
    backend: str,
) -> StatisticsResult | None:
    xp = get_acceleration_backend(backend).array_module
    if not np.all(np.isfinite(array)):
        return None
    values = as_backend_array(array, backend=backend, dtype=float)
    clean = values

    if axis is None:
        count: int | np.ndarray = int(values.size)
        finite_count: int | np.ndarray = int(values.size)
        nan_count: int | np.ndarray = 0
        posinf_count: int | np.ndarray = 0
        neginf_count: int | np.ndarray = 0
        minimum = float(to_numpy(xp.min(clean)))
        maximum = float(to_numpy(xp.max(clean)))
        clean_numpy = np.asarray(to_numpy(clean), dtype=float)
        percentile_values = np.percentile(clean_numpy, percentiles)
        stats = {
            "mean": float(to_numpy(xp.mean(clean))),
            "std": float(to_numpy(xp.std(clean))),
            "min": minimum,
            "max": maximum,
            "median": float(np.percentile(clean_numpy, 50)),
            "percentiles": {
                float(percentile): float(percentile_value)
                for percentile, percentile_value in zip(percentiles, percentile_values, strict=True)
            },
            "rms": float(to_numpy(xp.sqrt(xp.mean(clean * clean)))),
            "abs_mean": float(to_numpy(xp.mean(xp.abs(clean)))),
            "peak_to_peak": float(maximum - minimum),
            "energy": float(to_numpy(xp.sum(clean * clean))),
        }
    else:
        count = np.full(_reduced_shape(array.shape, axis), array.shape[axis], dtype=int)
        finite_count = np.full(_reduced_shape(array.shape, axis), array.shape[axis], dtype=int)
        nan_count = np.zeros(_reduced_shape(array.shape, axis), dtype=int)
        posinf_count = np.zeros(_reduced_shape(array.shape, axis), dtype=int)
        neginf_count = np.zeros(_reduced_shape(array.shape, axis), dtype=int)
        backend_stats = _axis_statistics_backend(clean, finite_count, axis, percentiles, xp)
        if backend_stats is None:
            return None
        stats = backend_stats

    return StatisticsResult(
        axis=axis,
        input_shape=tuple(int(value) for value in array.shape),
        count=count,
        finite_count=finite_count,
        nan_count=nan_count,
        posinf_count=posinf_count,
        neginf_count=neginf_count,
        mean=stats["mean"],
        std=stats["std"],
        min=stats["min"],
        max=stats["max"],
        median=stats["median"],
        percentiles=stats["percentiles"],
        rms=stats["rms"],
        abs_mean=stats["abs_mean"],
        peak_to_peak=stats["peak_to_peak"],
        energy=stats["energy"],
        nan_policy=nan_policy,
        source_metadata=metadata_summary,
    )


def _axis_statistics_backend(
    clean,
    finite_count: np.ndarray,
    axis: int,
    percentiles: tuple[float, ...],
    xp,
) -> dict[str, Any] | None:
    values = clean
    count = xp.asarray(finite_count, dtype=float)

    summed = xp.sum(values, axis=axis)
    summed_sq = xp.sum(values * values, axis=axis)
    abs_summed = xp.sum(xp.abs(values), axis=axis)

    mean = _divide_or_nan(to_numpy(summed), finite_count.astype(float))
    mean_sq = _divide_or_nan(to_numpy(summed_sq), finite_count.astype(float))
    variance = np.maximum(mean_sq - mean * mean, 0.0)
    std = np.where(finite_count > 0, np.sqrt(variance), np.nan)
    rms = np.where(finite_count > 0, np.sqrt(mean_sq), np.nan)
    abs_mean = _divide_or_nan(to_numpy(abs_summed), finite_count.astype(float))
    energy = to_numpy(summed_sq)

    min_values = to_numpy(xp.min(clean, axis=axis))
    max_values = to_numpy(xp.max(clean, axis=axis))
    min_values = np.where(finite_count > 0, min_values, np.nan)
    max_values = np.where(finite_count > 0, max_values, np.nan)
    peak_to_peak = np.where(finite_count > 0, max_values - min_values, np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        clean_numpy = np.asarray(to_numpy(clean), dtype=float)
        percentile_stack = np.nanpercentile(clean_numpy, percentiles, axis=axis)
        median = np.nanpercentile(clean_numpy, 50, axis=axis)

    percentile_map = {
        float(percentile): np.asarray(to_numpy(percentile_stack[index]))
        for index, percentile in enumerate(percentiles)
    }
    return {
        "mean": mean,
        "std": std,
        "min": min_values,
        "max": max_values,
        "median": np.asarray(to_numpy(median)),
        "percentiles": percentile_map,
        "rms": rms,
        "abs_mean": abs_mean,
        "peak_to_peak": peak_to_peak,
        "energy": energy,
    }


def window_statistics(
    data,
    *,
    time_slice=None,
    channel_slice=None,
    axis: int | None = None,
    percentiles=(1, 5, 25, 50, 75, 95, 99),
    nan_policy: NanPolicy = "omit",
) -> StatisticsResult:
    """Compute statistics for a local time/channel window."""

    array, metadata_summary = _as_numeric_array_and_metadata(data)
    if array.ndim != 2:
        raise ValueError("window_statistics expects 2-D data shaped as (n_samples, n_channels)")
    time_slice = slice(None) if time_slice is None else time_slice
    channel_slice = slice(None) if channel_slice is None else channel_slice
    window = np.array(array[time_slice, channel_slice], copy=True)
    if window.size == 0:
        raise ValueError("statistics window selection must not be empty")
    result = basic_statistics(
        window,
        axis=axis,
        percentiles=percentiles,
        nan_policy=nan_policy,
    )
    if metadata_summary is None:
        return result
    return StatisticsResult(
        axis=result.axis,
        input_shape=result.input_shape,
        count=result.count,
        finite_count=result.finite_count,
        nan_count=result.nan_count,
        posinf_count=result.posinf_count,
        neginf_count=result.neginf_count,
        mean=result.mean,
        std=result.std,
        min=result.min,
        max=result.max,
        median=result.median,
        percentiles=result.percentiles,
        rms=result.rms,
        abs_mean=result.abs_mean,
        peak_to_peak=result.peak_to_peak,
        energy=result.energy,
        nan_policy=result.nan_policy,
        source_metadata=metadata_summary,
    )


def _global_statistics(values: np.ndarray, percentiles: tuple[float, ...]) -> dict[str, Any]:
    if values.size == 0:
        nan = float("nan")
        return {
            "mean": nan,
            "std": nan,
            "min": nan,
            "max": nan,
            "median": nan,
            "percentiles": {float(value): nan for value in percentiles},
            "rms": nan,
            "abs_mean": nan,
            "peak_to_peak": nan,
            "energy": 0.0,
        }

    minimum = float(np.min(values))
    maximum = float(np.max(values))
    percentile_values = np.percentile(values, percentiles)
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": minimum,
        "max": maximum,
        "median": float(np.percentile(values, 50)),
        "percentiles": {
            float(percentile): float(percentile_value)
            for percentile, percentile_value in zip(percentiles, percentile_values, strict=True)
        },
        "rms": float(np.sqrt(np.mean(values * values))),
        "abs_mean": float(np.mean(np.abs(values))),
        "peak_to_peak": float(maximum - minimum),
        "energy": float(np.sum(values * values)),
    }


def _axis_statistics(
    clean: np.ndarray,
    finite_count: np.ndarray,
    axis: int,
    percentiles: tuple[float, ...],
) -> dict[str, Any]:
    finite = np.isfinite(clean)
    values = np.where(finite, clean, 0.0)
    count = np.asarray(finite_count, dtype=float)

    summed = np.sum(values, axis=axis)
    summed_sq = np.sum(values * values, axis=axis)
    abs_summed = np.sum(np.abs(values), axis=axis)

    mean = _divide_or_nan(summed, count)
    mean_sq = _divide_or_nan(summed_sq, count)
    variance = np.maximum(mean_sq - mean * mean, 0.0)
    std = np.where(count > 0, np.sqrt(variance), np.nan)
    rms = np.where(count > 0, np.sqrt(mean_sq), np.nan)
    abs_mean = _divide_or_nan(abs_summed, count)
    energy = summed_sq

    min_values = np.min(np.where(finite, clean, np.inf), axis=axis)
    max_values = np.max(np.where(finite, clean, -np.inf), axis=axis)
    min_values = np.where(count > 0, min_values, np.nan)
    max_values = np.where(count > 0, max_values, np.nan)
    peak_to_peak = np.where(count > 0, max_values - min_values, np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        percentile_stack = np.nanpercentile(clean, percentiles, axis=axis)
        median = np.nanpercentile(clean, 50, axis=axis)

    percentile_map = {
        float(percentile): np.asarray(percentile_stack[index])
        for index, percentile in enumerate(percentiles)
    }
    return {
        "mean": mean,
        "std": std,
        "min": min_values,
        "max": max_values,
        "median": median,
        "percentiles": percentile_map,
        "rms": rms,
        "abs_mean": abs_mean,
        "peak_to_peak": peak_to_peak,
        "energy": energy,
    }


def _divide_or_nan(numerator, denominator):
    return np.divide(
        numerator,
        denominator,
        out=np.full_like(np.asarray(numerator, dtype=float), np.nan, dtype=float),
        where=np.asarray(denominator) > 0,
    )


def _as_numeric_array_and_metadata(data) -> tuple[np.ndarray, dict[str, Any] | None]:
    metadata_summary = None
    if isinstance(data, DASData):
        array = np.array(data.data, copy=True)
        metadata = data.metadata
        metadata_summary = {
            "n_samples": metadata.n_samples,
            "n_channels": metadata.n_channels,
            "sample_rate_hz": metadata.sample_rate_hz,
            "dt_s": metadata.dt_s,
            "dx_m": metadata.dx_m,
            "source_format": metadata.source_format,
            "source_path": metadata.source_path,
        }
    else:
        array = np.array(data, copy=True)

    if array.size == 0:
        raise ValueError("statistics input must not be empty")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError("statistics input must be a real numeric array")
    return np.asarray(array, dtype=float), metadata_summary


def _normalize_axis(axis: int | None, ndim: int) -> int | None:
    if axis is None:
        return None
    try:
        normalized = int(axis)
    except (TypeError, ValueError) as exc:
        raise ValueError("axis must be None, 0, or 1 for DAS data") from exc
    if normalized < 0:
        normalized += ndim
    if normalized < 0 or normalized >= ndim:
        raise ValueError(f"axis {axis} is out of range for {ndim}-D data")
    return normalized


def _normalize_percentiles(percentiles) -> tuple[float, ...]:
    try:
        values = tuple(float(value) for value in percentiles)
    except TypeError as exc:
        raise ValueError("percentiles must be an iterable of values between 0 and 100") from exc
    if not values:
        raise ValueError("percentiles must contain at least one value")
    for value in values:
        if value < 0.0 or value > 100.0:
            raise ValueError("percentiles must be between 0 and 100")
    return values


def _reduced_shape(shape: tuple[int, ...], axis: int) -> tuple[int, ...]:
    return tuple(value for index, value in enumerate(shape) if index != axis)
