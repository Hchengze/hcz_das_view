import json
from argparse import Namespace

import numpy as np
import pytest

pytest.importorskip("h5py")
pytest.importorskip("scipy")

from examples.event_detection_file import (
    build_channel_slice_from_args,
    build_parser,
    build_time_slice_from_args,
    main,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_args(**overrides):
    values = {
        "time_start": 0,
        "time_stop": None,
        "time_step": 1,
        "max_samples": 4096,
        "channel_start": 0,
        "channel_stop": None,
        "channel_step": 1,
        "max_channels": 512,
    }
    values.update(overrides)
    return Namespace(**values)


def make_zd_file(tmp_path):
    path = tmp_path / "event_detection_example.h5"
    data = np.zeros((200, 2), dtype=np.float32)
    data[80:100, 1] = 6.0
    create_zd_h5(path, data)
    return path


def test_event_detection_example_builds_bounded_default_slices():
    args = make_args()

    assert build_time_slice_from_args(args) == slice(0, 4096, 1)
    assert build_channel_slice_from_args(args) == slice(0, 512, 1)


def test_event_detection_parser_accepts_stalta_args():
    args = build_parser().parse_args(
        ["input.h5", "--method", "stalta", "--sta", "25", "--lta", "250", "--trigger-on", "3.0"]
    )

    assert args.method == "stalta"
    assert args.sta == 25
    assert args.lta == 250
    assert args.trigger_on == 3.0


def test_event_detection_parser_accepts_envelope_args():
    args = build_parser().parse_args(["input.h5", "--method", "envelope", "--threshold", "0.8"])

    assert args.method == "envelope"
    assert args.threshold == 0.8


def test_event_detection_example_writes_stalta_json_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "events.json"

    assert (
        main(
            [
                str(path),
                "--method",
                "stalta",
                "--sta",
                "4",
                "--lta",
                "25",
                "--trigger-on",
                "2.0",
                "--trigger-off",
                "1.0",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reader_name"] == "zd_hdf5"
    assert payload["event_detection"]["method"] == "stalta"
    assert "candidates" in payload["event_detection"]


def test_event_detection_example_writes_envelope_json_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "envelope_events.json"

    assert main([str(path), "--method", "envelope", "--threshold", "2.0", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["event_detection"]["method"] == "envelope"
    assert payload["event_detection"]["candidate_count"] >= 1


def test_event_detection_example_writes_csv_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "events.csv"

    assert main([str(path), "--method", "envelope", "--threshold", "2.0", "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "event_id" in text
    assert "peak_value" in text
