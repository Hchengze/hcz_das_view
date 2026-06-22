import json
from argparse import Namespace

import numpy as np
import pytest

pytest.importorskip("h5py")

from examples.statistics_file import (
    axis_from_arg,
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
    path = tmp_path / "statistics_example.h5"
    data = np.arange(24, dtype=np.float32).reshape(6, 4)
    create_zd_h5(path, data)
    return path


def test_statistics_example_builds_bounded_default_slices():
    args = make_args()

    assert build_time_slice_from_args(args) == slice(0, 4096, 1)
    assert build_channel_slice_from_args(args) == slice(0, 512, 1)


def test_statistics_example_builds_explicit_slices():
    args = make_args(time_start=2, time_stop=8, time_step=2, channel_start=1, channel_stop=5, channel_step=2)

    assert build_time_slice_from_args(args) == slice(2, 8, 2)
    assert build_channel_slice_from_args(args) == slice(1, 5, 2)


def test_statistics_example_axis_parser():
    assert axis_from_arg("global") is None
    assert axis_from_arg("time") == 0
    assert axis_from_arg("channel") == 1
    with pytest.raises(ValueError, match="axis"):
        axis_from_arg("bad")


def test_statistics_parser_accepts_axis_and_percentiles():
    args = build_parser().parse_args(["input.h5", "--axis", "channel", "--percentiles", "1", "50", "99"])

    assert args.axis == "channel"
    assert args.percentiles == [1.0, 50.0, 99.0]


def test_statistics_example_writes_json_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "stats.json"

    assert main([str(path), "--output", str(output), "--percentiles", "50"]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reader_name"] == "zd_hdf5"
    assert payload["statistics"]["axis"] is None
    assert payload["statistics"]["percentiles"]["50.0"] == pytest.approx(11.5)


def test_statistics_example_writes_global_csv_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "stats.csv"

    assert main([str(path), "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "mean" in text
    assert "energy" in text
