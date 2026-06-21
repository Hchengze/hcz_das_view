from argparse import Namespace

from examples.spectrum_file import build_processing_steps_from_args


def make_args(**overrides):
    values = {"bandpass": None}
    values.update(overrides)
    return Namespace(**values)


def test_build_processing_steps_without_filter():
    assert build_processing_steps_from_args(make_args(), sample_rate_hz=500.0) == []


def test_build_processing_steps_with_bandpass():
    steps = build_processing_steps_from_args(
        make_args(bandpass=[1.0, 50.0]),
        sample_rate_hz=500.0,
    )

    assert steps == [
        (
            "bandpass",
            {
                "sample_rate_hz": 500.0,
                "freqmin_hz": 1.0,
                "freqmax_hz": 50.0,
                "axis": 0,
            },
        )
    ]
