"""Small, GUI-independent preprocessing functions for DAS arrays.

The internal DAS convention is (n_samples, n_channels).  Therefore the default
axis=0 means "operate along time for each channel".
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def demean(data, *, axis: int | None = 0) -> np.ndarray:
    """Remove the finite mean along axis and return a new float array."""

    array = _as_float_copy(data)
    mean = _finite_mean(array, axis=axis)
    return array - mean


def detrend_linear(data, *, axis: int = 0) -> np.ndarray:
    """Remove a linear trend along axis using finite samples only.

    NaN and Inf values are preserved at their original positions.  Slices with
    fewer than two finite samples are returned with their finite mean removed.
    """

    array = _as_float_copy(data)
    axis = _normalize_axis(axis, array.ndim)
    moved = np.moveaxis(array, axis, 0)
    result = np.empty_like(moved, dtype=float)
    x_all = np.arange(moved.shape[0], dtype=float)

    for index in np.ndindex(moved.shape[1:]):
        values = moved[(slice(None), *index)]
        finite = np.isfinite(values)
        output = values.copy()
        if finite.sum() >= 2:
            x = x_all[finite]
            y = values[finite]
            x_mean = x.mean()
            y_mean = y.mean()
            denom = np.sum((x - x_mean) ** 2)
            if denom > 0:
                slope = np.sum((x - x_mean) * (y - y_mean)) / denom
                intercept = y_mean - slope * x_mean
                output[finite] = y - (slope * x + intercept)
            else:
                output[finite] = y - y_mean
        elif finite.sum() == 1:
            output[finite] = 0.0
        result[(slice(None), *index)] = output

    return np.moveaxis(result, 0, axis)


def taper(data, *, axis: int = 0, ratio: float = 0.05, window: str = "hann") -> np.ndarray:
    """Apply a symmetric edge taper along axis."""

    array = _as_float_copy(data)
    axis = _normalize_axis(axis, array.ndim)
    ratio = float(ratio)
    if not np.isfinite(ratio) or ratio < 0 or ratio > 0.5:
        raise ValueError("ratio must be finite and satisfy 0 <= ratio <= 0.5")
    if window != "hann":
        raise ValueError("only window='hann' is currently supported")

    n = array.shape[axis]
    if ratio == 0 or n <= 1:
        return array
    edge = int(round(ratio * n))
    if edge <= 0:
        return array
    edge = min(edge, n // 2)
    weights = np.ones(n, dtype=float)
    theta = np.linspace(0.0, np.pi, edge, endpoint=False)
    left = 0.5 * (1.0 - np.cos(theta))
    weights[:edge] = left
    weights[-edge:] = left[::-1]
    shape = [1] * array.ndim
    shape[axis] = n
    return array * weights.reshape(shape)


def normalize(
    data,
    *,
    axis: int | None = None,
    mode: str = "maxabs",
    eps: float = 1e-12,
) -> np.ndarray:
    """Normalize finite values and return a new float array.

    Supported modes are maxabs and minmax. maxabs divides by the maximum finite
    absolute value; minmax maps finite values to [-1, 1].
    """

    array = _as_float_copy(data)
    _validate_eps(eps)
    if mode == "maxabs":
        scale = _finite_maxabs(array, axis=axis)
        safe = np.where((scale > eps) & np.isfinite(scale), scale, 1.0)
        return array / safe
    if mode == "minmax":
        min_value, max_value = _finite_minmax(array, axis=axis)
        span = max_value - min_value
        valid = (span > eps) & np.isfinite(span)
        safe = np.where(valid, span, 1.0)
        output = 2.0 * ((array - min_value) / safe) - 1.0
        return np.where(valid, output, np.where(np.isfinite(array), 0.0, array))
    raise ValueError("mode must be 'maxabs' or 'minmax'")


def standardize(data, *, axis: int | None = None, eps: float = 1e-12) -> np.ndarray:
    """Return finite-value z-scores while preserving NaN/Inf positions."""

    array = _as_float_copy(data)
    _validate_eps(eps)
    mean = _finite_mean(array, axis=axis)
    std = _finite_std(array, axis=axis)
    valid = (std > eps) & np.isfinite(std)
    safe = np.where(valid, std, 1.0)
    output = (array - mean) / safe
    return np.where(valid, output, np.where(np.isfinite(array), 0.0, array))


def clip(
    data,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    percentile: float | Sequence[float] | None = None,
) -> np.ndarray:
    """Clip a copy of data using explicit limits or finite percentiles."""

    array = _as_float_copy(data)
    low = min_value
    high = max_value
    if percentile is not None:
        pct_low, pct_high = _normalize_percentile(percentile)
        finite = array[np.isfinite(array)]
        if finite.size:
            pct_values = np.percentile(finite, [pct_low, pct_high])
            low = pct_values[0] if low is None else max(float(low), float(pct_values[0]))
            high = pct_values[1] if high is None else min(float(high), float(pct_values[1]))
    if low is not None and not np.isfinite(low):
        raise ValueError("min_value must be finite when provided")
    if high is not None and not np.isfinite(high):
        raise ValueError("max_value must be finite when provided")
    if low is not None and high is not None and low > high:
        raise ValueError("clip lower bound must be <= upper bound")
    return np.clip(array, low, high)


def _as_float_copy(data) -> np.ndarray:
    array = np.array(data, dtype=float, copy=True)
    if array.ndim == 0:
        raise ValueError("data must have at least one dimension")
    return array


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


def _validate_eps(eps: float) -> None:
    if not np.isfinite(eps) or eps <= 0:
        raise ValueError("eps must be a positive finite value")


def _finite_mean(array: np.ndarray, *, axis: int | None) -> np.ndarray:
    axis = _validate_axis_or_none(axis, array.ndim)
    finite = np.isfinite(array)
    count = finite.sum(axis=axis, keepdims=True)
    total = np.where(finite, array, 0.0).sum(axis=axis, keepdims=True)
    return np.divide(total, count, out=np.zeros_like(total, dtype=float), where=count > 0)


def _finite_std(array: np.ndarray, *, axis: int | None) -> np.ndarray:
    axis = _validate_axis_or_none(axis, array.ndim)
    mean = _finite_mean(array, axis=axis)
    finite = np.isfinite(array)
    count = finite.sum(axis=axis, keepdims=True)
    squared = np.where(finite, (array - mean) ** 2, 0.0).sum(axis=axis, keepdims=True)
    variance = np.divide(squared, count, out=np.zeros_like(squared, dtype=float), where=count > 0)
    return np.sqrt(variance)


def _finite_maxabs(array: np.ndarray, *, axis: int | None) -> np.ndarray:
    axis = _validate_axis_or_none(axis, array.ndim)
    values = np.where(np.isfinite(array), np.abs(array), np.nan)
    with np.errstate(all="ignore"):
        result = np.nanmax(values, axis=axis, keepdims=True)
    return np.where(np.isfinite(result), result, 0.0)


def _finite_minmax(array: np.ndarray, *, axis: int | None) -> tuple[np.ndarray, np.ndarray]:
    axis = _validate_axis_or_none(axis, array.ndim)
    values = np.where(np.isfinite(array), array, np.nan)
    with np.errstate(all="ignore"):
        min_value = np.nanmin(values, axis=axis, keepdims=True)
        max_value = np.nanmax(values, axis=axis, keepdims=True)
    return (
        np.where(np.isfinite(min_value), min_value, 0.0),
        np.where(np.isfinite(max_value), max_value, 0.0),
    )


def _normalize_percentile(percentile: float | Sequence[float]) -> tuple[float, float]:
    if isinstance(percentile, Sequence) and not isinstance(percentile, (str, bytes)):
        if len(percentile) != 2:
            raise ValueError("percentile sequence must contain exactly two values")
        low, high = float(percentile[0]), float(percentile[1])
    else:
        value = float(percentile)
        low, high = value, 100.0 - value
    if not (np.isfinite(low) and np.isfinite(high)):
        raise ValueError("percentile values must be finite")
    if not (0.0 <= low <= high <= 100.0):
        raise ValueError("percentile must satisfy 0 <= low <= high <= 100")
    return low, high
