from argparse import Namespace

import pytest

from examples.filter_file import build_filter_steps_from_args


def make_args(**overrides):
    values = {
        "lowpass": None,
        "highpass": None,
        "bandpass": None,
        "bandstop": None,
        "notch": None,
        "quality": 30.0,
        "order": 4,
        "causal": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_build_filter_steps_lowpass():
    steps = build_filter_steps_from_args(make_args(lowpass=80.0), sample_rate_hz=500.0)

    assert steps == [
        (
            "lowpass",
            {
                "sample_rate_hz": 500.0,
                "axis": 0,
                "zero_phase": True,
                "cutoff_hz": 80.0,
                "order": 4,
            },
        )
    ]


def test_build_filter_steps_bandpass_causal():
    steps = build_filter_steps_from_args(
        make_args(bandpass=[1.0, 50.0], causal=True),
        sample_rate_hz=250.0,
    )

    assert steps[0][0] == "bandpass"
    assert steps[0][1]["freqmin_hz"] == 1.0
    assert steps[0][1]["freqmax_hz"] == 50.0
    assert steps[0][1]["zero_phase"] is False


def test_build_filter_steps_notch():
    steps = build_filter_steps_from_args(make_args(notch=50.0, quality=20.0), sample_rate_hz=500.0)

    assert steps[0][0] == "notch"
    assert steps[0][1]["notch_hz"] == 50.0
    assert steps[0][1]["quality"] == 20.0


def test_build_filter_steps_requires_filter_option():
    with pytest.raises(ValueError, match="filter option"):
        build_filter_steps_from_args(make_args(), sample_rate_hz=500.0)
