import json
from argparse import Namespace

import numpy as np
import pytest

pytest.importorskip("h5py")
pytest.importorskip("scipy")

from examples.roi_export_file import (
    build_channel_slice_from_args,
    build_parser,
    build_time_slice_from_args,
    main,
    parse_manual_rois,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "roi_export_example.h5"
    data = np.zeros((120, 3), dtype=np.float32)
    data[40:55, 1] = 5.0
    create_zd_h5(path, data)
    return path


def test_parse_manual_rois():
    rois = parse_manual_rois([[0, 10, 1, 3], [20, 30, 0, 1]])

    assert len(rois) == 2
    assert rois[0].roi_id == "manual_001"
    assert rois[0].channel_end == 3


def test_roi_export_parser_accepts_detect_events_args():
    args = build_parser().parse_args(
        ["input.h5", "--detect-events", "--method", "stalta", "--sta", "5", "--lta", "20", "--trigger-on", "2"]
    )

    assert args.detect_events is True
    assert args.method == "stalta"
    assert args.sta == 5


def test_roi_export_builds_default_slices():
    args = Namespace(time_start=0, time_stop=None, max_samples=4096, channel_start=0, channel_stop=None, max_channels=512)

    assert build_time_slice_from_args(args) == slice(0, 4096)
    assert build_channel_slice_from_args(args) == slice(0, 512)


def test_roi_export_writes_rois_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "rois.json"

    assert main([str(path), "--roi", "0", "20", "0", "2", "--output-rois", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload[0]["roi_id"] == "manual_001"


def test_roi_export_writes_summary_csv(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "summary.csv"

    assert main([str(path), "--roi", "0", "20", "0", "2", "--output-summary", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "roi_id" in text
    assert "mean" in text


def test_roi_export_detect_events_writes_events_csv_and_rois_json(tmp_path):
    path = make_zd_file(tmp_path)
    events_output = tmp_path / "events.csv"
    rois_output = tmp_path / "rois.json"

    assert (
        main(
            [
                str(path),
                "--detect-events",
                "--method",
                "envelope",
                "--threshold",
                "2.0",
                "--output-events",
                str(events_output),
                "--output-rois",
                str(rois_output),
            ]
        )
        == 0
    )

    assert "event_id" in events_output.read_text(encoding="utf-8")
    rois = json.loads(rois_output.read_text(encoding="utf-8"))
    assert rois
