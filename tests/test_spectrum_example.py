from argparse import Namespace

import pytest

from examples.spectrum_file import build_parser, build_processing_steps_from_args, choose_analysis_mode


def make_args(**overrides):
    values = {"bandpass": None, "power": False, "psd": None, "spectrogram": False}
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


def test_choose_analysis_mode_defaults_to_amplitude():
    assert choose_analysis_mode(make_args()) == "amplitude"
    assert choose_analysis_mode(make_args(power=True)) == "power"
    assert choose_analysis_mode(make_args(psd="welch")) == "psd"
    assert choose_analysis_mode(make_args(spectrogram=True)) == "spectrogram"


def test_choose_analysis_mode_rejects_conflicts():
    with pytest.raises(ValueError, match="choose only one"):
        choose_analysis_mode(make_args(power=True, psd="welch"))


def test_parser_accepts_psd_welch_and_db():
    args = build_parser().parse_args(
        ["input.h5", "--channel", "10", "--psd", "welch", "--nperseg", "512", "--db"]
    )

    assert args.psd == "welch"
    assert args.nperseg == 512
    assert args.db is True
