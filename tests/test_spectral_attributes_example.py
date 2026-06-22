import json
from argparse import Namespace

import numpy as np
import pytest

pytest.importorskip("h5py")

from examples.spectral_attributes_file import (
    build_channel_slice_from_args,
    build_parser,
    build_time_slice_from_args,
    main,
    parse_band_pairs,
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
    path = tmp_path / "spectral_attributes_example.h5"
    sample_rate_hz = 1000.0
    t = np.arange(1000, dtype=float) / sample_rate_hz
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 10.0 * t),
            np.sin(2 * np.pi * 40.0 * t),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_spectral_attributes_example_builds_bounded_default_slices():
    args = make_args()

    assert build_time_slice_from_args(args) == slice(0, 4096, 1)
    assert build_channel_slice_from_args(args) == slice(0, 512, 1)


def test_parse_band_pairs():
    assert parse_band_pairs([1.0, 5.0, 5.0, 20.0]) == ((1.0, 5.0), (5.0, 20.0))
    with pytest.raises(ValueError, match="even number"):
        parse_band_pairs([1.0, 5.0, 20.0])


def test_spectral_attributes_parser_accepts_attributes_mode():
    args = build_parser().parse_args(["input.h5", "--attributes", "--frequency-range", "1", "80"])

    assert args.attributes is True
    assert args.frequency_range == [1.0, 80.0]


def test_spectral_attributes_example_writes_band_json_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "bands.json"

    assert main([str(path), "--bands", "8", "12", "35", "45", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["reader_name"] == "zd_hdf5"
    assert "band_energy" in payload
    assert payload["band_energy"]["bands"] == [[8.0, 12.0], [35.0, 45.0]]


def test_spectral_attributes_example_writes_attributes_json_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "attrs.json"

    assert main([str(path), "--attributes", "--channel-stop", "1", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "spectral_attributes" in payload
    assert payload["spectral_attributes"]["dominant_frequency_hz"] == pytest.approx(10.0)


def test_spectral_attributes_example_writes_csv_output(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "band_energy.csv"

    assert main([str(path), "--bands", "8", "12", "--average-channels", "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "band_energy" in text
    assert "band_energy_ratio" in text
