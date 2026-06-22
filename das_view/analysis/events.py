"""Envelope, STA/LTA, and event-candidate helpers for DAS data.

The default DAS convention is ``data.shape == (n_samples, n_channels)``:
axis 0 is time and axis 1 is channel/space.  These helpers are
GUI-independent and report event candidates only; they do not perform
source location, inversion, or interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from das_view.core.data_model import DASData

NanPolicy = Literal["omit", "raise"]


@dataclass(frozen=True, slots=True)
class EnvelopeResult:
    """Amplitude or energy envelope for a DAS array selection."""

    values: np.ndarray
    axis: int
    input_shape: tuple[int, ...]
    method: str
    smooth_samples: int | None = None
    window_samples: int | None = None
    nan_policy: NanPolicy = "raise"
    source_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class STALTARatioResult:
    """STA/LTA ratio computed from squared-amplitude energy."""

    ratio: np.ndarray
    sta: np.ndarray
    lta: np.ndarray
    axis: int
    input_shape: tuple[int, ...]
    sta_samples: int
    lta_samples: int
    mode: str = "classic"
    eps: float = 1e-12
    nan_policy: NanPolicy = "raise"
    source_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EventCandidate:
    """One threshold-derived event candidate.

    ``end_sample`` follows Python slice semantics and is exclusive.
    """

    event_id: int
    start_sample: int
    end_sample: int
    duration_samples: int
    channel_start: int | None
    channel_end: int | None
    peak_sample: int
    peak_channel: int | None
    peak_value: float
    mean_value: float
    max_value: float
    score: float


@dataclass(frozen=True, slots=True)
class EventDetectionResult:
    """Feature array and event-candidate table from threshold detection."""

    feature: np.ndarray
    candidates: tuple[EventCandidate, ...]
    axis: int
    input_shape: tuple[int, ...]
    method: str
    parameters: dict[str, Any]


def amplitude_envelope(
    data,
    *,
    axis: int = 0,
    method: str = "hilbert",
    smooth_samples: int | None = None,
    nan_policy: NanPolicy = "raise",
) -> EnvelopeResult:
    """Compute amplitude envelope.

    ``method="hilbert"`` returns ``abs(scipy.signal.hilbert(x))`` along the
    analysis axis.
    """

    if method != "hilbert":
        raise ValueError("method must be 'hilbert'")
    array, metadata_summary = _as_numeric_array_and_metadata(data, "envelope", nan_policy)
    normalized_axis = _normalize_axis(axis, array.ndim)
    signal = _scipy_signal()
    envelope = np.abs(signal.hilbert(array, axis=normalized_axis))
    if smooth_samples is not None:
        envelope = _moving_average_same(envelope, smooth_samples, axis=normalized_axis)
    return EnvelopeResult(
        values=np.asarray(envelope, dtype=float),
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
        method=method,
        smooth_samples=None if smooth_samples is None else int(smooth_samples),
        nan_policy=nan_policy,
        source_metadata=metadata_summary,
    )


def energy_envelope(
    data,
    *,
    axis: int = 0,
    window_samples: int | None = None,
    smooth_samples: int | None = None,
    nan_policy: NanPolicy = "raise",
) -> EnvelopeResult:
    """Compute point energy or same-shaped sliding-window energy."""

    array, metadata_summary = _as_numeric_array_and_metadata(data, "energy envelope", nan_policy)
    normalized_axis = _normalize_axis(axis, array.ndim)
    energy = np.square(array)
    if window_samples is not None:
        energy = _moving_sum_same(energy, window_samples, axis=normalized_axis)
    if smooth_samples is not None:
        energy = _moving_average_same(energy, smooth_samples, axis=normalized_axis)
    return EnvelopeResult(
        values=np.asarray(energy, dtype=float),
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
        method="energy",
        smooth_samples=None if smooth_samples is None else int(smooth_samples),
        window_samples=None if window_samples is None else int(window_samples),
        nan_policy=nan_policy,
        source_metadata=metadata_summary,
    )


def sta_lta_ratio(
    data,
    *,
    sta_samples: int,
    lta_samples: int,
    axis: int = 0,
    mode: str = "classic",
    eps: float = 1e-12,
    nan_policy: NanPolicy = "raise",
) -> STALTARatioResult:
    """Compute classic STA/LTA ratio from squared-amplitude energy.

    The short- and long-window traces are moving averages of ``x**2``.
    """

    if mode != "classic":
        raise ValueError("mode must be 'classic'")
    sta_samples = _positive_int(sta_samples, "sta_samples")
    lta_samples = _positive_int(lta_samples, "lta_samples")
    if lta_samples <= sta_samples:
        raise ValueError("lta_samples must be greater than sta_samples")
    eps = float(eps)
    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be a positive finite value")

    array, metadata_summary = _as_numeric_array_and_metadata(data, "STA/LTA", nan_policy)
    normalized_axis = _normalize_axis(axis, array.ndim)
    energy = np.square(array)
    sta = _moving_average_same(energy, sta_samples, axis=normalized_axis)
    lta = _moving_average_same(energy, lta_samples, axis=normalized_axis)
    ratio = np.divide(sta, lta + eps)
    return STALTARatioResult(
        ratio=np.asarray(ratio, dtype=float),
        sta=np.asarray(sta, dtype=float),
        lta=np.asarray(lta, dtype=float),
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
        sta_samples=sta_samples,
        lta_samples=lta_samples,
        mode=mode,
        eps=eps,
        nan_policy=nan_policy,
        source_metadata=metadata_summary,
    )


def detect_threshold_events(
    feature,
    *,
    threshold: float,
    axis: int = 0,
    min_duration_samples: int = 1,
    merge_gap_samples: int = 0,
    max_events: int | None = None,
) -> EventDetectionResult:
    """Detect channel-wise threshold crossings in a 1-D or 2-D feature array."""

    array = _as_feature_array(feature)
    normalized_axis = _normalize_axis(axis, array.ndim)
    threshold = _finite_float(threshold, "threshold")
    min_duration_samples = _positive_int(min_duration_samples, "min_duration_samples")
    merge_gap_samples = _nonnegative_int(merge_gap_samples, "merge_gap_samples")
    max_events_value = _optional_positive_int(max_events, "max_events")

    candidates = _threshold_candidates(
        array,
        threshold=threshold,
        axis=normalized_axis,
        min_duration_samples=min_duration_samples,
        merge_gap_samples=merge_gap_samples,
        max_events=max_events_value,
        trigger_off=None,
    )
    return EventDetectionResult(
        feature=np.array(array, copy=True),
        candidates=candidates,
        axis=normalized_axis,
        input_shape=tuple(int(value) for value in array.shape),
        method="threshold",
        parameters={
            "threshold": threshold,
            "min_duration_samples": min_duration_samples,
            "merge_gap_samples": merge_gap_samples,
            "max_events": max_events_value,
        },
    )


def detect_stalta_events(
    data,
    *,
    sta_samples: int,
    lta_samples: int,
    trigger_on: float,
    trigger_off: float | None = None,
    axis: int = 0,
    min_duration_samples: int = 1,
    merge_gap_samples: int = 0,
    max_events: int | None = None,
    nan_policy: NanPolicy = "raise",
) -> EventDetectionResult:
    """Compute STA/LTA and return threshold-derived event candidates."""

    ratio = sta_lta_ratio(
        data,
        sta_samples=sta_samples,
        lta_samples=lta_samples,
        axis=axis,
        nan_policy=nan_policy,
    )
    trigger_on = _finite_float(trigger_on, "trigger_on")
    if trigger_off is None:
        trigger_off_value = trigger_on / 2.0
    else:
        trigger_off_value = _finite_float(trigger_off, "trigger_off")
    if trigger_off_value > trigger_on:
        raise ValueError("trigger_off must be less than or equal to trigger_on")
    min_duration_samples = _positive_int(min_duration_samples, "min_duration_samples")
    merge_gap_samples = _nonnegative_int(merge_gap_samples, "merge_gap_samples")
    max_events_value = _optional_positive_int(max_events, "max_events")

    candidates = _threshold_candidates(
        ratio.ratio,
        threshold=trigger_on,
        axis=ratio.axis,
        min_duration_samples=min_duration_samples,
        merge_gap_samples=merge_gap_samples,
        max_events=max_events_value,
        trigger_off=trigger_off_value,
    )
    return EventDetectionResult(
        feature=np.array(ratio.ratio, copy=True),
        candidates=candidates,
        axis=ratio.axis,
        input_shape=ratio.input_shape,
        method="stalta",
        parameters={
            "sta_samples": ratio.sta_samples,
            "lta_samples": ratio.lta_samples,
            "trigger_on": trigger_on,
            "trigger_off": trigger_off_value,
            "min_duration_samples": min_duration_samples,
            "merge_gap_samples": merge_gap_samples,
            "max_events": max_events_value,
            "nan_policy": nan_policy,
        },
    )


def _threshold_candidates(
    array: np.ndarray,
    *,
    threshold: float,
    axis: int,
    min_duration_samples: int,
    merge_gap_samples: int,
    max_events: int | None,
    trigger_off: float | None,
) -> tuple[EventCandidate, ...]:
    working = np.moveaxis(array, axis, 0)
    n_samples = working.shape[0]
    traces = working.reshape(n_samples, -1)
    raw_candidates: list[EventCandidate] = []

    for trace_index in range(traces.shape[1]):
        trace = traces[:, trace_index]
        segments = (
            _hysteresis_segments(trace, trigger_on=threshold, trigger_off=trigger_off)
            if trigger_off is not None
            else _crossing_segments(trace >= threshold)
        )
        segments = _merge_segments(segments, merge_gap_samples=merge_gap_samples)
        for start, end in segments:
            duration = end - start
            if duration < min_duration_samples:
                continue
            values = trace[start:end]
            peak_offset = int(np.argmax(values))
            peak_value = float(values[peak_offset])
            mean_value = float(np.mean(values))
            channel = None if array.ndim == 1 else int(trace_index)
            raw_candidates.append(
                EventCandidate(
                    event_id=0,
                    start_sample=int(start),
                    end_sample=int(end),
                    duration_samples=int(duration),
                    channel_start=channel,
                    channel_end=channel,
                    peak_sample=int(start + peak_offset),
                    peak_channel=channel,
                    peak_value=peak_value,
                    mean_value=mean_value,
                    max_value=peak_value,
                    score=peak_value,
                )
            )

    raw_candidates.sort(key=lambda candidate: (candidate.score, candidate.duration_samples), reverse=True)
    if max_events is not None:
        raw_candidates = raw_candidates[:max_events]
    return tuple(
        EventCandidate(
            event_id=index + 1,
            start_sample=candidate.start_sample,
            end_sample=candidate.end_sample,
            duration_samples=candidate.duration_samples,
            channel_start=candidate.channel_start,
            channel_end=candidate.channel_end,
            peak_sample=candidate.peak_sample,
            peak_channel=candidate.peak_channel,
            peak_value=candidate.peak_value,
            mean_value=candidate.mean_value,
            max_value=candidate.max_value,
            score=candidate.score,
        )
        for index, candidate in enumerate(raw_candidates)
    )


def _crossing_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            segments.append((start, index))
            start = None
    if start is not None:
        segments.append((start, int(mask.size)))
    return segments


def _hysteresis_segments(
    trace: np.ndarray,
    *,
    trigger_on: float,
    trigger_off: float,
) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    active = False
    start = 0
    for index, value in enumerate(trace):
        if not active and value >= trigger_on:
            active = True
            start = index
        elif active and value <= trigger_off:
            segments.append((start, index + 1))
            active = False
    if active:
        segments.append((start, int(trace.size)))
    return segments


def _merge_segments(segments: list[tuple[int, int]], *, merge_gap_samples: int) -> list[tuple[int, int]]:
    if not segments:
        return []
    merged = [segments[0]]
    for start, end in segments[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= merge_gap_samples:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged


def _moving_sum_same(array: np.ndarray, window_samples: int, *, axis: int) -> np.ndarray:
    window_samples = _positive_int(window_samples, "window_samples")
    kernel = np.ones(window_samples, dtype=float)
    return _convolve_same(array, kernel, axis=axis)


def _moving_average_same(array: np.ndarray, window_samples: int, *, axis: int) -> np.ndarray:
    window_samples = _positive_int(window_samples, "smooth_samples")
    kernel = np.ones(window_samples, dtype=float) / float(window_samples)
    return _convolve_same(array, kernel, axis=axis)


def _convolve_same(array: np.ndarray, kernel: np.ndarray, *, axis: int) -> np.ndarray:
    moved = np.moveaxis(array, axis, 0)
    n_samples = moved.shape[0]
    traces = moved.reshape(n_samples, -1)
    filtered = np.empty_like(traces, dtype=float)
    for index in range(traces.shape[1]):
        filtered[:, index] = np.convolve(traces[:, index], kernel, mode="same")
    restored = filtered.reshape(moved.shape)
    return np.moveaxis(restored, 0, axis)


def _as_numeric_array_and_metadata(data, label: str, nan_policy: NanPolicy) -> tuple[np.ndarray, dict[str, Any] | None]:
    if nan_policy not in ("omit", "raise"):
        raise ValueError("nan_policy must be 'omit' or 'raise'")
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
        raise ValueError(f"{label} input must not be empty")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError(f"{label} input must be a real numeric array")
    array = np.asarray(array, dtype=float)
    if array.ndim == 0:
        raise ValueError(f"{label} input must have at least one dimension")
    if nan_policy == "raise" and not np.all(np.isfinite(array)):
        raise ValueError(f"{label} input contains NaN or Inf values")
    array = np.where(np.isfinite(array), array, 0.0)
    return array, metadata_summary


def _as_feature_array(feature) -> np.ndarray:
    if isinstance(feature, EnvelopeResult):
        array = np.array(feature.values, copy=True)
    elif isinstance(feature, STALTARatioResult):
        array = np.array(feature.ratio, copy=True)
    else:
        array = np.array(feature, copy=True)
    if array.size == 0:
        raise ValueError("feature input must not be empty")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError("feature input must be a real numeric array")
    array = np.asarray(array, dtype=float)
    if array.ndim not in (1, 2):
        raise ValueError("feature input must be 1-D or 2-D")
    if not np.all(np.isfinite(array)):
        raise ValueError("feature input contains NaN or Inf values")
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


def _positive_int(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def _nonnegative_int(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a nonnegative integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return result


def _optional_positive_int(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, name)


def _finite_float(value: float, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not np.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _scipy_signal():
    try:
        from scipy import signal
    except ImportError as exc:  # pragma: no cover - exercised only without scipy installed.
        raise ImportError("scipy is required for envelope analysis") from exc
    return signal
