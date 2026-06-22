import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from das_view.analysis.events import EventCandidate
from das_view.analysis.roi import Annotation, TimeChannelROI
from das_view.io.export import (
    annotations_to_rows,
    event_candidates_to_rows,
    rois_to_rows,
    save_csv_rows,
    save_json,
    to_jsonable,
)


@dataclass
class SmallData:
    value: int
    path: Path


def make_candidate():
    return EventCandidate(
        event_id=1,
        start_sample=0,
        end_sample=5,
        duration_samples=5,
        channel_start=2,
        channel_end=2,
        peak_sample=3,
        peak_channel=2,
        peak_value=4.0,
        mean_value=2.0,
        max_value=4.0,
        score=4.0,
    )


def test_to_jsonable_handles_dataclass_numpy_and_path():
    payload = to_jsonable(
        {
            "dataclass": SmallData(1, Path("sample.h5")),
            "scalar": np.float32(2.5),
            "array": np.array([1, 2]),
        }
    )

    assert payload["dataclass"]["value"] == 1
    assert payload["dataclass"]["path"] == "sample.h5"
    assert payload["scalar"] == np.float32(2.5).item()
    assert payload["array"] == [1, 2]


def test_save_json_writes_temp_directory(tmp_path):
    output = tmp_path / "nested" / "summary.json"

    save_json({"value": np.array([1, 2])}, output)

    assert json.loads(output.read_text(encoding="utf-8"))["value"] == [1, 2]


def test_save_csv_rows_writes_temp_directory(tmp_path):
    output = tmp_path / "nested" / "rows.csv"

    save_csv_rows([{"a": 1, "b": "x"}], output)

    text = output.read_text(encoding="utf-8")
    assert "a,b" in text
    assert "1,x" in text


def test_event_candidates_to_rows():
    rows = event_candidates_to_rows([make_candidate()])

    assert rows[0]["event_id"] == 1
    assert rows[0]["peak_value"] == 4.0


def test_rois_and_annotations_to_rows():
    roi_rows = rois_to_rows([TimeChannelROI("r1", 0, 10, 1, 3, score=0.5)])
    annotation_rows = annotations_to_rows([Annotation("a1", "r1", "label", confidence=0.8)])

    assert roi_rows[0]["roi_id"] == "r1"
    assert roi_rows[0]["n_channels"] == 2
    assert annotation_rows[0]["confidence"] == 0.8
