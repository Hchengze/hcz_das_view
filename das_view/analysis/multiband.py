"""Windowed multiband and spectral-attribute feature maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from das_view.analysis.spectral_attributes import band_energy, spectral_attributes
from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class MultibandFeatureMap:
    """Windowed DAS feature map.

    ``values`` is shaped as ``(n_windows, n_channels, n_features)`` for
    multiband energy maps, or ``(n_windows, n_channels)`` for one spectral
    attribute.
    """

    values: np.ndarray
    feature_names: tuple[str, ...]
    time_windows: tuple[tuple[int, int], ...]
    sample_rate_hz: float
    window_samples: int
    step_samples: int
    axis: int
    metadata: dict


def multiband_energy_map(
    data,
    *,
    sample_rate_hz: float | None = None,
    bands,
    window_samples: int,
    step_samples: int,
    axis: int = 0,
    average_channels: bool = False,
    normalize: Literal["total", "max"] | None = None,
    nan_policy: NanPolicy = "raise",
    backend: str = "cpu",
) -> MultibandFeatureMap:
    """Compute a time-window x channel x band energy map."""

    array, sample_rate_hz, axis = _as_array_and_sample_rate(data, sample_rate_hz, axis=axis, nan_policy=nan_policy)
    window_samples = _positive_int(window_samples, "window_samples")
    step_samples = _positive_int(step_samples, "step_samples")
    if window_samples > array.shape[0]:
        raise ValueError("window_samples must not exceed the number of samples")
    windows = _windows(array.shape[0], window_samples, step_samples)
    values = []
    normalized_bands = None
    for start, stop in windows:
        result = band_energy(
            array[start:stop],
            sample_rate_hz=sample_rate_hz,
            bands=bands,
            axis=0,
            average_channels=average_channels,
            nan_policy=nan_policy,
            backend=backend,
        )
        normalized_bands = result.bands
        band_values = np.asarray(result.band_energy, dtype=float)
        if average_channels or band_values.ndim == 1:
            band_values = band_values.reshape(1, -1)
        else:
            band_values = band_values.T
        values.append(band_values)
    output = np.stack(values, axis=0)
    if normalize == "total":
        denom = np.sum(output, axis=2, keepdims=True)
        output = np.divide(output, denom, out=np.zeros_like(output), where=denom > 0)
    elif normalize == "max":
        denom = np.nanmax(output, axis=(0, 1, 2), keepdims=True)
        output = np.divide(output, denom, out=np.zeros_like(output), where=denom > 0)
    elif normalize is not None:
        raise ValueError("normalize must be None, 'total', or 'max'")
    assert normalized_bands is not None
    names = tuple(f"{low:g}-{high:g}Hz" for low, high in normalized_bands)
    return MultibandFeatureMap(
        values=output,
        feature_names=names,
        time_windows=windows,
        sample_rate_hz=sample_rate_hz,
        window_samples=window_samples,
        step_samples=step_samples,
        axis=axis,
        metadata={"bands": normalized_bands, "normalize": normalize, "average_channels": average_channels},
    )


def spectral_attribute_map(
    data,
    *,
    sample_rate_hz: float | None = None,
    window_samples: int,
    step_samples: int,
    frequency_range=None,
    attributes=("dominant_frequency", "centroid", "bandwidth", "rolloff"),
    axis: int = 0,
    nan_policy: NanPolicy = "raise",
    backend: str = "cpu",
) -> dict[str, MultibandFeatureMap]:
    """Compute windowed spectral attribute maps."""

    array, sample_rate_hz, axis = _as_array_and_sample_rate(data, sample_rate_hz, axis=axis, nan_policy=nan_policy)
    window_samples = _positive_int(window_samples, "window_samples")
    step_samples = _positive_int(step_samples, "step_samples")
    if window_samples > array.shape[0]:
        raise ValueError("window_samples must not exceed the number of samples")
    requested = tuple(attributes)
    key_map = {
        "dominant_frequency": "dominant_frequency_hz",
        "centroid": "spectral_centroid_hz",
        "bandwidth": "spectral_bandwidth_hz",
        "rolloff": "spectral_rolloff_hz",
    }
    for name in requested:
        if name not in key_map:
            raise ValueError(f"unsupported spectral attribute: {name}")
    windows = _windows(array.shape[0], window_samples, step_samples)
    values = {name: [] for name in requested}
    for start, stop in windows:
        result = spectral_attributes(
            array[start:stop],
            sample_rate_hz=sample_rate_hz,
            axis=0,
            frequency_range=frequency_range,
            average_channels=False,
            nan_policy=nan_policy,
            backend=backend,
        )
        for name in requested:
            values[name].append(np.asarray(getattr(result, key_map[name]), dtype=float).reshape(-1))
    return {
        name: MultibandFeatureMap(
            values=np.stack(items, axis=0),
            feature_names=(name,),
            time_windows=windows,
            sample_rate_hz=sample_rate_hz,
            window_samples=window_samples,
            step_samples=step_samples,
            axis=axis,
            metadata={"frequency_range": frequency_range, "attribute": name},
        )
        for name, items in values.items()
    }


def _as_array_and_sample_rate(data, sample_rate_hz: float | None, *, axis: int, nan_policy: NanPolicy):
    if nan_policy not in ("omit", "raise"):
        raise ValueError("nan_policy must be 'omit' or 'raise'")
    if isinstance(data, DASData):
        if sample_rate_hz is None:
            sample_rate_hz = data.metadata.sample_rate_hz
        array = np.array(data.data, dtype=float, copy=True)
    else:
        array = np.array(data, dtype=float, copy=True)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    if array.ndim != 2:
        raise ValueError("multiband feature maps expect 1-D or 2-D numeric data")
    axis = int(axis)
    if axis < 0:
        axis += array.ndim
    if axis not in (0, 1):
        raise ValueError("axis must be 0 or 1")
    if axis != 0:
        array = np.moveaxis(array, axis, 0)
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError("multiband input contains NaN or Inf values")
    if nan_policy == "omit":
        array = np.where(np.isfinite(array), array, 0.0)
    if sample_rate_hz is None:
        raise ValueError("sample_rate_hz is required when input is not DASData metadata")
    sample_rate_hz = float(sample_rate_hz)
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be a positive finite value")
    return array, sample_rate_hz, axis


def _positive_int(value, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _windows(n_samples: int, window_samples: int, step_samples: int) -> tuple[tuple[int, int], ...]:
    values = tuple((start, start + window_samples) for start in range(0, n_samples - window_samples + 1, step_samples))
    if not values:
        raise ValueError("window/step combination produced no windows")
    return values
