"""JSON/CSV export helpers for DAS analysis objects."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def to_jsonable(obj):
    """Convert common analysis objects to JSON-friendly builtin containers."""

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return to_jsonable(obj.to_dict())
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, slice):
        return {"start": obj.start, "stop": obj.stop, "step": obj.step}
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(value) for value in obj]
    return obj


def save_json(obj, path, *, indent: int = 2) -> Path:
    """Save an object as UTF-8 JSON, creating parent directories as needed."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(to_jsonable(obj), indent=indent), encoding="utf-8")
    return output


def save_csv_rows(rows: Iterable[dict[str, Any]], path, *, fieldnames=None) -> Path:
    """Save dictionaries as CSV with Windows-compatible newline handling."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    row_list = [to_jsonable(row) for row in rows]
    if fieldnames is None:
        fieldnames = _fieldnames_from_rows(row_list)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(row_list)
    return output


def event_candidates_to_rows(candidates) -> list[dict[str, Any]]:
    return [
        {
            "event_id": candidate.event_id,
            "start_sample": candidate.start_sample,
            "end_sample": candidate.end_sample,
            "duration_samples": candidate.duration_samples,
            "channel_start": candidate.channel_start,
            "channel_end": candidate.channel_end,
            "peak_sample": candidate.peak_sample,
            "peak_channel": candidate.peak_channel,
            "peak_value": candidate.peak_value,
            "mean_value": candidate.mean_value,
            "max_value": candidate.max_value,
            "score": candidate.score,
        }
        for candidate in candidates
    ]


def rois_to_rows(rois) -> list[dict[str, Any]]:
    iterable = rois if not hasattr(rois, "__iter__") else rois
    return [
        {
            "roi_id": roi.roi_id,
            "start_sample": roi.start_sample,
            "end_sample": roi.end_sample,
            "duration_samples": roi.duration_samples,
            "channel_start": roi.channel_start,
            "channel_end": roi.channel_end,
            "n_channels": roi.n_channels,
            "label": roi.label,
            "score": roi.score,
        }
        for roi in iterable
    ]


def annotations_to_rows(annotations) -> list[dict[str, Any]]:
    return [
        {
            "annotation_id": annotation.annotation_id,
            "roi_id": annotation.roi_id,
            "label": annotation.label,
            "description": annotation.description,
            "category": annotation.category,
            "confidence": annotation.confidence,
            "created_by": annotation.created_by,
        }
        for annotation in annotations
    ]


def analysis_summary_to_rows(summary) -> list[dict[str, Any]]:
    """Flatten ROI analysis summaries into one row per ROI."""

    rows = []
    for item in summary:
        if hasattr(item, "roi") and hasattr(item, "result"):
            row = {
                "roi_id": item.roi.roi_id,
                "label": item.roi.label,
                "reader_name": item.reader_name,
            }
            result = item.result
            if hasattr(result, "mean"):
                row.update(
                    {
                        "mean": _scalar_or_repr(result.mean),
                        "std": _scalar_or_repr(result.std),
                        "rms": _scalar_or_repr(result.rms),
                        "energy": _scalar_or_repr(result.energy),
                        "min": _scalar_or_repr(result.min),
                        "max": _scalar_or_repr(result.max),
                    }
                )
            elif hasattr(result, "dominant_frequency_hz"):
                row.update(
                    {
                        "dominant_frequency_hz": _scalar_or_repr(result.dominant_frequency_hz),
                        "spectral_centroid_hz": _scalar_or_repr(result.spectral_centroid_hz),
                        "spectral_bandwidth_hz": _scalar_or_repr(result.spectral_bandwidth_hz),
                        "spectral_rolloff_hz": _scalar_or_repr(result.spectral_rolloff_hz),
                    }
                )
            elif hasattr(result, "band_energy"):
                row.update(
                    {
                        "band_energy": _scalar_or_repr(result.band_energy),
                        "band_energy_ratio": _scalar_or_repr(result.band_energy_ratio),
                    }
                )
            rows.append(row)
        else:
            rows.append(to_jsonable(item))
    return rows


def _fieldnames_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _scalar_or_repr(value):
    value = to_jsonable(value)
    if isinstance(value, list):
        return json.dumps(value)
    return value
