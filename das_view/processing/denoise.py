"""Traditional DAS denoising and signal-enhancement helpers.

The functions in this module are intentionally small, deterministic, and
GUI-independent.  They operate on numpy arrays or DASData inputs and preserve
the internal DAS convention of (n_samples, n_channels).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class EnhancementReport:
    """Audit report for a traditional denoising workflow."""

    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    steps: tuple[dict[str, Any], ...]
    before: dict[str, float | int]
    after: dict[str, float | int]


@dataclass(frozen=True, slots=True)
class DenoiseResult:
    """Denoised array plus workflow metrics."""

    data: np.ndarray
    report: EnhancementReport


@dataclass(frozen=True, slots=True)
class DenoiseStep:
    """One named denoising operation and its keyword parameters."""

    name: str
    params: Mapping[str, Any] = field(default_factory=dict)


def common_mode_removal(
    data,
    *,
    axis: int = 0,
    method: Literal["median", "mean"] = "median",
    channels: Sequence[int] | None = None,
    preserve_mean: bool = False,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Remove sample-wise common mode across channels.

    With the default DAS convention, axis=0 is time and the common mode is
    estimated across channels for each time sample.
    """

    array, axis = _as_float_array(data, axis=axis, nan_policy=nan_policy)
    if array.ndim == 1:
        center = _center(array, method=method, axis=0, keepdims=True)
        output = array - center
        if preserve_mean:
            output = output + _finite_mean(center, axis=None, keepdims=False)
        return _restore_nonfinite(output, array)

    moved = np.moveaxis(array, axis, 0)
    selected = moved if channels is None else moved[:, _normalize_channels(channels, moved.shape[1])]
    common = _center(selected, method=method, axis=1, keepdims=True)
    output = moved - common
    if preserve_mean:
        output = output + _finite_mean(common, axis=0, keepdims=True)
    return _restore_nonfinite(np.moveaxis(output, 0, axis), array)


def despike(
    data,
    *,
    axis: int = 0,
    z_threshold: float = 8.0,
    window_samples: int | None = None,
    method: Literal["median"] = "median",
    replace: Literal["median", "nan"] = "median",
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Replace robust z-score outliers with a median baseline."""

    _validate_positive_finite(z_threshold, "z_threshold")
    if method != "median":
        raise ValueError("only method='median' is currently supported")
    if replace not in {"median", "nan"}:
        raise ValueError("replace must be 'median' or 'nan'")
    array, axis = _as_float_array(data, axis=axis, nan_policy=nan_policy)
    working = _nonfinite_to_nan(array)
    if window_samples is None:
        baseline = _finite_median(working, axis=axis, keepdims=True)
        residual = working - baseline
        scale = 1.4826 * _finite_median(np.abs(residual), axis=axis, keepdims=True)
    else:
        baseline = running_median_filter(working, size=window_samples, axis=axis, nan_policy="omit")
        residual = working - baseline
        scale = _running_mad(residual, size=window_samples, axis=axis)
    valid_scale = (scale > 0) & np.isfinite(scale)
    safe = np.where(valid_scale, scale, np.inf)
    spike_mask = (np.abs(residual) / safe > z_threshold) | (~valid_scale & (np.abs(residual) > 0))
    output = working.copy()
    replacement = np.broadcast_to(baseline, output.shape)
    output[spike_mask] = np.nan if replace == "nan" else replacement[spike_mask]
    return _restore_nonfinite(output, array)


def running_median_filter(
    data,
    *,
    size: int,
    axis: int = 0,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Apply a centered running median along one axis."""

    size = _validate_window(size, "size")
    array, axis = _as_float_array(data, axis=axis, nan_policy=nan_policy)
    filtered = _running_reduce(_nonfinite_to_nan(array), size=size, axis=axis, reducer=np.nanmedian)
    return _restore_nonfinite(filtered, array)


def channel_balance(
    data,
    *,
    axis: int = 0,
    target: Literal["rms", "std", "maxabs"] = "rms",
    eps: float = 1e-12,
    clip_gain: float | None = None,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Scale channels so their finite amplitudes have comparable level."""

    _validate_positive_finite(eps, "eps")
    if clip_gain is not None:
        _validate_positive_finite(clip_gain, "clip_gain")
    array, axis = _as_float_array(data, axis=axis, nan_policy=nan_policy)
    metric = _level_metric(_nonfinite_to_nan(array), axis=axis, target=target)
    finite_metric = metric[np.isfinite(metric) & (metric > eps)]
    if finite_metric.size == 0:
        return array.copy()
    reference = float(np.median(finite_metric))
    gains = np.divide(reference, metric, out=np.ones_like(metric), where=(metric > eps) & np.isfinite(metric))
    if clip_gain is not None:
        gains = np.clip(gains, 1.0 / clip_gain, clip_gain)
    return _restore_nonfinite(array * gains, array)


def local_normalize(
    data,
    *,
    axis: int = 0,
    window_samples: int,
    mode: Literal["rms", "std", "maxabs"] = "rms",
    eps: float = 1e-12,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Normalize by a local running amplitude scale."""

    window_samples = _validate_window(window_samples, "window_samples")
    _validate_positive_finite(eps, "eps")
    array, axis = _as_float_array(data, axis=axis, nan_policy=nan_policy)
    working = _nonfinite_to_nan(array)
    if mode == "rms":
        scale = np.sqrt(_running_reduce(np.square(working), size=window_samples, axis=axis, reducer=np.nanmean))
    elif mode == "std":
        mean = _running_reduce(working, size=window_samples, axis=axis, reducer=np.nanmean)
        scale = np.sqrt(_running_reduce(np.square(working - mean), size=window_samples, axis=axis, reducer=np.nanmean))
    elif mode == "maxabs":
        scale = _running_reduce(np.abs(working), size=window_samples, axis=axis, reducer=np.nanmax)
    else:
        raise ValueError("mode must be 'rms', 'std', or 'maxabs'")
    safe = np.where((scale > eps) & np.isfinite(scale), scale, 1.0)
    return _restore_nonfinite(working / safe, array)


def time_space_median_filter(
    data,
    *,
    time_size: int = 3,
    channel_size: int = 3,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Apply a small 2-D median filter over time and channel dimensions."""

    time_size = _validate_window(time_size, "time_size")
    channel_size = _validate_window(channel_size, "channel_size")
    array, _ = _as_float_array(data, axis=0, nan_policy=nan_policy)
    if array.ndim == 1:
        return running_median_filter(array, size=time_size, axis=0, nan_policy=nan_policy)
    if array.ndim != 2:
        raise ValueError("time_space_median_filter expects a 1-D or 2-D array")
    working = _nonfinite_to_nan(array)
    pad_t = _pad_width(time_size)
    pad_c = _pad_width(channel_size)
    padded = np.pad(working, (pad_t, pad_c), mode="edge")
    output = np.empty_like(working, dtype=float)
    for i in range(working.shape[0]):
        for j in range(working.shape[1]):
            window = padded[i : i + time_size, j : j + channel_size]
            output[i, j] = _safe_nanmedian(window)
    return _restore_nonfinite(output, array)


def robust_clip(
    data,
    *,
    lower_percentile: float = 1.0,
    upper_percentile: float = 99.0,
    axis: int | None = None,
    nan_policy: NanPolicy = "omit",
) -> np.ndarray:
    """Winsorize finite values using robust percentile limits."""

    lower = float(lower_percentile)
    upper = float(upper_percentile)
    if not (np.isfinite(lower) and np.isfinite(upper) and 0.0 <= lower <= upper <= 100.0):
        raise ValueError("percentiles must satisfy 0 <= lower <= upper <= 100")
    array, _ = _as_float_array(data, axis=0, nan_policy=nan_policy)
    axis = _validate_axis_or_none(axis, array.ndim)
    working = _nonfinite_to_nan(array)
    with np.errstate(all="ignore"):
        low = np.nanpercentile(working, lower, axis=axis, keepdims=True)
        high = np.nanpercentile(working, upper, axis=axis, keepdims=True)
    low = np.where(np.isfinite(low), low, -np.inf)
    high = np.where(np.isfinite(high), high, np.inf)
    return _restore_nonfinite(np.clip(working, low, high), array)


def apply_denoise_workflow(
    data,
    steps: Sequence[DenoiseStep | tuple[str, Mapping[str, Any]] | str],
    *,
    axis: int = 0,
    return_report: bool = True,
) -> DenoiseResult | np.ndarray:
    """Apply a compact sequence of traditional denoising steps."""

    array, axis = _as_float_array(data, axis=axis, nan_policy="omit")
    normalized_steps = tuple(_normalize_step(step) for step in steps)
    output = array.copy()
    history: list[dict[str, Any]] = []
    initial = _summary_metrics(output)

    for step in normalized_steps:
        func = _STEP_FUNCTIONS.get(step.name)
        if func is None:
            raise ValueError(f"unknown denoise step: {step.name}")
        before = _summary_metrics(output)
        params = dict(step.params)
        params.setdefault("axis", axis)
        try:
            output = func(output, **params)
        except TypeError as exc:
            raise ValueError(f"invalid parameters for denoise step {step.name}: {exc}") from exc
        after = _summary_metrics(output)
        history.append(
            {
                "name": step.name,
                "params": _json_friendly_params(step.params),
                "before": before,
                "after": after,
            }
        )

    if not return_report:
        return output
    report = EnhancementReport(
        input_shape=tuple(int(v) for v in array.shape),
        output_shape=tuple(int(v) for v in output.shape),
        steps=tuple(history),
        before=initial,
        after=_summary_metrics(output),
    )
    return DenoiseResult(data=output, report=report)


def denoise_workflow(
    data,
    steps: Sequence[DenoiseStep | tuple[str, Mapping[str, Any]] | str],
    *,
    axis: int = 0,
    return_report: bool = True,
) -> DenoiseResult | np.ndarray:
    """Compatibility alias for apply_denoise_workflow."""

    return apply_denoise_workflow(data, steps, axis=axis, return_report=return_report)


def _as_float_array(data, *, axis: int, nan_policy: NanPolicy) -> tuple[np.ndarray, int]:
    if nan_policy not in {"omit", "raise"}:
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    source = data.data if isinstance(data, DASData) else data
    array = np.array(source, dtype=float, copy=True)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
    axis = _normalize_axis(axis, array.ndim)
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("data contains NaN or Inf values")
    return array, axis


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


def _validate_axis_or_none(axis: int | None, ndim: int) -> int | None:
    if axis is None:
        return None
    return _normalize_axis(axis, ndim)


def _validate_window(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _validate_positive_finite(value: float, name: str) -> None:
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite value")


def _normalize_channels(channels: Sequence[int], n_channels: int) -> np.ndarray:
    if not channels:
        raise ValueError("channels must not be empty")
    result = np.array([int(ch) for ch in channels], dtype=int)
    result = np.where(result < 0, result + n_channels, result)
    if np.any((result < 0) | (result >= n_channels)):
        raise ValueError("channels contains out-of-range indices")
    return result


def _center(array: np.ndarray, *, method: str, axis: int, keepdims: bool) -> np.ndarray:
    if method == "median":
        return _finite_median(array, axis=axis, keepdims=keepdims)
    if method == "mean":
        return _finite_mean(array, axis=axis, keepdims=keepdims)
    raise ValueError("method must be 'median' or 'mean'")


def _finite_mean(array: np.ndarray, *, axis: int | None, keepdims: bool) -> np.ndarray:
    with np.errstate(all="ignore"):
        result = np.nanmean(_nonfinite_to_nan(array), axis=axis, keepdims=keepdims)
    return np.where(np.isfinite(result), result, 0.0)


def _finite_median(array: np.ndarray, *, axis: int | None, keepdims: bool) -> np.ndarray:
    with np.errstate(all="ignore"):
        result = np.nanmedian(_nonfinite_to_nan(array), axis=axis, keepdims=keepdims)
    return np.where(np.isfinite(result), result, 0.0)


def _level_metric(array: np.ndarray, *, axis: int, target: str) -> np.ndarray:
    if target == "rms":
        return np.sqrt(_finite_mean(np.square(array), axis=axis, keepdims=True))
    if target == "std":
        mean = _finite_mean(array, axis=axis, keepdims=True)
        return np.sqrt(_finite_mean(np.square(array - mean), axis=axis, keepdims=True))
    if target == "maxabs":
        with np.errstate(all="ignore"):
            result = np.nanmax(np.abs(array), axis=axis, keepdims=True)
        return np.where(np.isfinite(result), result, 0.0)
    raise ValueError("target must be 'rms', 'std', or 'maxabs'")


def _nonfinite_to_nan(array: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(array), array, np.nan)


def _restore_nonfinite(output: np.ndarray, original: np.ndarray) -> np.ndarray:
    return np.where(np.isfinite(original), output, original)


def _pad_width(size: int) -> tuple[int, int]:
    before = size // 2
    after = size - 1 - before
    return before, after


def _running_reduce(array: np.ndarray, *, size: int, axis: int, reducer) -> np.ndarray:
    moved = np.moveaxis(array, axis, 0)
    pad = [(0, 0)] * moved.ndim
    pad[0] = _pad_width(size)
    padded = np.pad(moved, pad, mode="edge")
    output = np.empty_like(moved, dtype=float)
    for i in range(moved.shape[0]):
        with np.errstate(all="ignore"):
            values = reducer(padded[i : i + size], axis=0)
        output[i] = np.where(np.isfinite(values), values, 0.0)
    return np.moveaxis(output, 0, axis)


def _running_mad(array: np.ndarray, *, size: int, axis: int) -> np.ndarray:
    median = _running_reduce(array, size=size, axis=axis, reducer=np.nanmedian)
    mad = _running_reduce(np.abs(array - median), size=size, axis=axis, reducer=np.nanmedian)
    return 1.4826 * mad


def _safe_nanmedian(array: np.ndarray) -> float:
    with np.errstate(all="ignore"):
        result = np.nanmedian(array)
    return float(result) if np.isfinite(result) else 0.0


def _summary_metrics(array: np.ndarray) -> dict[str, float | int]:
    finite = np.isfinite(array)
    finite_values = array[finite]
    if finite_values.size == 0:
        return {"rms": 0.0, "energy": 0.0, "finite_count": 0}
    return {
        "rms": float(np.sqrt(np.mean(np.square(finite_values)))),
        "energy": float(np.sum(np.square(finite_values))),
        "finite_count": int(finite_values.size),
    }


def _normalize_step(step: DenoiseStep | tuple[str, Mapping[str, Any]] | str) -> DenoiseStep:
    if isinstance(step, DenoiseStep):
        return step
    if isinstance(step, str):
        return DenoiseStep(name=step, params={})
    if isinstance(step, tuple) and len(step) == 2:
        name, params = step
        if not isinstance(name, str):
            raise ValueError("denoise step name must be a string")
        if not isinstance(params, Mapping):
            raise ValueError("denoise step params must be a mapping")
        return DenoiseStep(name=name, params=dict(params))
    raise ValueError("steps must contain DenoiseStep, step names, or (name, params) tuples")


def _json_friendly_params(params: Mapping[str, Any]) -> dict[str, Any]:
    friendly: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, np.generic):
            friendly[key] = value.item()
        elif isinstance(value, np.ndarray):
            friendly[key] = value.tolist()
        elif isinstance(value, tuple):
            friendly[key] = list(value)
        else:
            friendly[key] = value
    return friendly


_STEP_FUNCTIONS = {
    "common_mode_removal": common_mode_removal,
    "despike": despike,
    "running_median_filter": running_median_filter,
    "channel_balance": channel_balance,
    "local_normalize": local_normalize,
    "time_space_median_filter": time_space_median_filter,
    "robust_clip": robust_clip,
}
