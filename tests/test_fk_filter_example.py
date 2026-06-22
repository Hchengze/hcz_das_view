import argparse
from pathlib import Path

from examples.fk_filter_file import (
    build_channel_slice_from_args,
    build_fk_filter_kwargs_from_args,
    build_processing_steps_from_args,
    build_time_slice_from_args,
    fk_output_path_from_args,
)
import pytest


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
        "vmin_mps": None,
        "vmax_mps": None,
        "reject": False,
        "exclude_zero_wavenumber": False,
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


def test_fk_filter_example_builds_velocity_range_kwargs():
    args = make_args(vmin_mps=300.0, vmax_mps=3000.0)

    kwargs = build_fk_filter_kwargs_from_args(args)

    assert kwargs == {
        "vmin_mps": 300.0,
        "vmax_mps": 3000.0,
        "pass_inside": True,
        "include_zero_wavenumber": True,
    }


def test_fk_filter_example_allows_only_vmin_or_only_vmax():
    assert build_fk_filter_kwargs_from_args(make_args(vmin_mps=300.0))["vmin_mps"] == 300.0
    assert build_fk_filter_kwargs_from_args(make_args(vmax_mps=3000.0))["vmax_mps"] == 3000.0


def test_fk_filter_example_reject_flag_maps_to_pass_inside_false():
    kwargs = build_fk_filter_kwargs_from_args(make_args(vmin_mps=300.0, reject=True))

    assert kwargs["pass_inside"] is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "at least one"),
        ({"vmin_mps": 0.0}, "--vmin must be positive"),
        ({"vmax_mps": -1.0}, "--vmax must be positive"),
        ({"vmin_mps": 3000.0, "vmax_mps": 300.0}, "--vmin must be smaller"),
    ],
)
def test_fk_filter_example_rejects_invalid_velocity_range(kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_fk_filter_kwargs_from_args(make_args(**kwargs))
