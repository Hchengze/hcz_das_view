"""ROI and annotation helpers for DAS time-channel analysis.

ROIs use half-open intervals: ``[start_sample, end_sample)`` and, when
present, ``[channel_start, channel_end)``.  These helpers are GUI-independent
and do not store local data paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from das_view.analysis.events import EventCandidate


@dataclass(frozen=True, slots=True)
class TimeChannelROI:
    """A time-channel region of interest."""

    roi_id: str
    start_sample: int
    end_sample: int
    channel_start: int | None = None
    channel_end: int | None = None
    label: str = "roi"
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "roi_id", str(self.roi_id))
        if not self.roi_id:
            raise ValueError("roi_id is required")
        object.__setattr__(self, "start_sample", _int_value(self.start_sample, "start_sample"))
        object.__setattr__(self, "end_sample", _int_value(self.end_sample, "end_sample"))
        if self.start_sample >= self.end_sample:
            raise ValueError("ROI sample range must satisfy start_sample < end_sample")
        if self.channel_start is None and self.channel_end is not None:
            raise ValueError("channel_start is required when channel_end is provided")
        if self.channel_start is not None and self.channel_end is None:
            raise ValueError("channel_end is required when channel_start is provided")
        if self.channel_start is not None and self.channel_end is not None:
            channel_start = _int_value(self.channel_start, "channel_start")
            channel_end = _int_value(self.channel_end, "channel_end")
            if channel_start >= channel_end:
                raise ValueError("ROI channel range must satisfy channel_start < channel_end")
            object.__setattr__(self, "channel_start", channel_start)
            object.__setattr__(self, "channel_end", channel_end)
        object.__setattr__(self, "label", str(self.label))
        if self.score is not None:
            object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def duration_samples(self) -> int:
        """Return ROI duration in samples."""

        return self.end_sample - self.start_sample

    @property
    def n_channels(self) -> int | None:
        """Return ROI channel count, or None for time-only ROIs."""

        if self.channel_start is None or self.channel_end is None:
            return None
        return self.channel_end - self.channel_start

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""

        return {
            "roi_id": self.roi_id,
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "channel_start": self.channel_start,
            "channel_end": self.channel_end,
            "label": self.label,
            "score": self.score,
            "metadata": dict(self.metadata),
            "duration_samples": self.duration_samples,
            "n_channels": self.n_channels,
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "TimeChannelROI":
        """Build an ROI from a dictionary."""

        return cls(
            roi_id=values["roi_id"],
            start_sample=values["start_sample"],
            end_sample=values["end_sample"],
            channel_start=values.get("channel_start"),
            channel_end=values.get("channel_end"),
            label=values.get("label", "roi"),
            score=values.get("score"),
            metadata=values.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class Annotation:
    """A user or workflow annotation associated with an optional ROI."""

    annotation_id: str
    roi_id: str | None
    label: str
    description: str | None = None
    category: str | None = None
    confidence: float | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotation_id", str(self.annotation_id))
        if not self.annotation_id:
            raise ValueError("annotation_id is required")
        if self.label is None or not str(self.label):
            raise ValueError("annotation label is required")
        object.__setattr__(self, "label", str(self.label))
        if self.roi_id is not None:
            object.__setattr__(self, "roi_id", str(self.roi_id))
        if self.confidence is not None:
            confidence = float(self.confidence)
            if confidence < 0.0 or confidence > 1.0:
                raise ValueError("annotation confidence must be in [0, 1]")
            object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""

        return {
            "annotation_id": self.annotation_id,
            "roi_id": self.roi_id,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "confidence": self.confidence,
            "created_by": self.created_by,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "Annotation":
        """Build an annotation from a dictionary."""

        return cls(
            annotation_id=values["annotation_id"],
            roi_id=values.get("roi_id"),
            label=values["label"],
            description=values.get("description"),
            category=values.get("category"),
            confidence=values.get("confidence"),
            created_by=values.get("created_by"),
            metadata=values.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class ROIAnalysisResult:
    """Analysis output associated with one ROI."""

    roi: TimeChannelROI
    result: Any
    reader_name: str
    metadata: Any
    selection: Any
    preprocessing_history: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "roi": self.roi.to_dict(),
            "reader_name": self.reader_name,
            "selection": _selection_to_dict(self.selection),
            "metadata": _metadata_to_dict(self.metadata),
            "preprocessing_history": self.preprocessing_history,
            "result": self.result,
        }


class ROISet:
    """A small container for TimeChannelROI objects."""

    def __init__(self, rois: Iterable[TimeChannelROI] | None = None):
        self._rois: list[TimeChannelROI] = []
        if rois is not None:
            for roi in rois:
                self.add(roi)

    def __iter__(self):
        return iter(self._rois)

    def __len__(self) -> int:
        return len(self._rois)

    def __getitem__(self, index):
        return self._rois[index]

    def add(self, roi: TimeChannelROI) -> None:
        if not isinstance(roi, TimeChannelROI):
            raise TypeError("ROISet.add expects a TimeChannelROI")
        self._rois.append(roi)

    def remove(self, roi_id: str) -> TimeChannelROI:
        for index, roi in enumerate(self._rois):
            if roi.roi_id == roi_id:
                return self._rois.pop(index)
        raise KeyError(f"ROI id not found: {roi_id}")

    def filter_by_label(self, label: str) -> "ROISet":
        return ROISet(roi for roi in self._rois if roi.label == label)

    def sorted_by_score(self, *, reverse: bool = True) -> "ROISet":
        return ROISet(
            sorted(
                self._rois,
                key=lambda roi: float("-inf") if roi.score is None else roi.score,
                reverse=reverse,
            )
        )

    def limited(self, max_rois: int | None) -> "ROISet":
        if max_rois is None:
            return ROISet(self._rois)
        max_rois = _positive_int(max_rois, "max_rois")
        return ROISet(self._rois[:max_rois])

    def to_list(self) -> list[dict[str, Any]]:
        return [roi.to_dict() for roi in self._rois]

    def to_dict(self) -> dict[str, Any]:
        return {"rois": self.to_list(), "count": len(self._rois)}

    @classmethod
    def from_list(cls, values: Iterable[dict[str, Any]]) -> "ROISet":
        return cls(TimeChannelROI.from_dict(value) for value in values)

    @classmethod
    def from_event_candidates(cls, candidates, **kwargs) -> "ROISet":
        return rois_from_event_candidates(candidates, **kwargs)


def rois_from_event_candidates(
    candidates,
    *,
    padding_samples: int = 0,
    padding_channels: int = 0,
    label: str = "event_candidate",
    max_rois: int | None = None,
) -> ROISet:
    """Convert EventCandidate objects into padded time-channel ROIs."""

    padding_samples = _nonnegative_int(padding_samples, "padding_samples")
    padding_channels = _nonnegative_int(padding_channels, "padding_channels")
    max_rois_value = None if max_rois is None else _positive_int(max_rois, "max_rois")
    rois: list[TimeChannelROI] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, EventCandidate):
            raise TypeError("rois_from_event_candidates expects EventCandidate objects")
        if max_rois_value is not None and len(rois) >= max_rois_value:
            break
        start_sample = max(0, candidate.start_sample - padding_samples)
        end_sample = candidate.end_sample + padding_samples
        if candidate.channel_start is None or candidate.channel_end is None:
            channel_start = None
            channel_end = None
        else:
            channel_start = max(0, candidate.channel_start - padding_channels)
            channel_end = candidate.channel_end + 1 + padding_channels
        rois.append(
            TimeChannelROI(
                roi_id=f"roi_{index + 1:03d}",
                start_sample=start_sample,
                end_sample=end_sample,
                channel_start=channel_start,
                channel_end=channel_end,
                label=label,
                score=candidate.score,
                metadata={"source_event_id": candidate.event_id},
            )
        )
    return ROISet(rois)


def _int_value(value: int, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _positive_int(value: int, name: str) -> int:
    result = _int_value(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _nonnegative_int(value: int, name: str) -> int:
    return _int_value(value, name)


def _selection_to_dict(selection) -> dict[str, Any] | None:
    if selection is None:
        return None
    return {
        "time_slice": _slice_to_dict(selection.time_slice),
        "channel_slice": _slice_to_dict(selection.channel_slice),
        "downsample": list(selection.downsample),
    }


def _metadata_to_dict(metadata) -> dict[str, Any] | None:
    if metadata is None:
        return None
    return {
        "n_samples": metadata.n_samples,
        "n_channels": metadata.n_channels,
        "sample_rate_hz": metadata.sample_rate_hz,
        "dt_s": metadata.dt_s,
        "dx_m": metadata.dx_m,
        "source_format": metadata.source_format,
    }


def _slice_to_dict(value: slice) -> dict[str, int | None]:
    return {"start": value.start, "stop": value.stop, "step": value.step}
