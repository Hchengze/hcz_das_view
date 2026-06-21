import argparse
from pathlib import Path

from examples.fk_filter_file import (
    build_channel_slice_from_args,
    build_processing_steps_from_args,
    build_time_slice_from_args,
    fk_output_path_from_args,
)


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
        "bandpass": None,
        "order": 4,
        "causal": False,
        "output": Path("filtered.png"),
        "fk_output": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_fk_filter_example_builds_bounded_default_slices():
    args = make_args()

    assert build_time_slice_from_args(args) == slice(0, 4096, 1)
    assert build_channel_slice_from_args(args) == slice(0, 512, 1)


def test_fk_filter_example_builds_explicit_slices():
    args = make_args(time_start=10, time_stop=100, time_step=2, channel_start=3, channel_stop=33, channel_step=3)

    assert build_time_slice_from_args(args) == slice(10, 100, 2)
    assert build_channel_slice_from_args(args) == slice(3, 33, 3)


def test_fk_filter_example_bandpass_step_uses_processing_service_params():
    args = make_args(bandpass=[1.0, 50.0], order=6, causal=True)

    steps = build_processing_steps_from_args(args, sample_rate_hz=1000.0)

    assert steps == [
        (
            "bandpass",
            {
                "sample_rate_hz": 1000.0,
                "freqmin_hz": 1.0,
                "freqmax_hz": 50.0,
                "axis": 0,
                "order": 6,
                "causal": True,
            },
        )
    ]


def test_fk_filter_example_derives_default_fk_output_path():
    args = make_args(output=Path("filtered_waterfall.png"))

    assert fk_output_path_from_args(args) == Path("filtered_waterfall_fk.png")


def test_fk_filter_example_uses_explicit_fk_output_path():
    args = make_args(output=Path("filtered_waterfall.png"), fk_output=Path("fk.png"))

    assert fk_output_path_from_args(args) == Path("fk.png")
