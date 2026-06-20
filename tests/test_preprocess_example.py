from argparse import Namespace

import pytest

from examples.preprocess_file import build_steps_from_args


def make_args(**overrides):
    values = {
        "demean": False,
        "detrend": False,
        "taper": None,
        "normalize": False,
        "standardize": False,
        "clip_min": None,
        "clip_max": None,
        "clip_percentile": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_build_steps_from_args_orders_requested_steps():
    args = make_args(demean=True, taper=0.05, normalize=True)

    steps = build_steps_from_args(args)

    assert steps == [
        ("demean", {"axis": 0}),
        ("taper", {"axis": 0, "ratio": 0.05}),
        ("normalize", {"axis": None, "mode": "maxabs"}),
    ]


def test_build_steps_from_args_supports_clip_percentile_pair():
    args = make_args(clip_min=-2.0, clip_max=2.0, clip_percentile=[1.0, 99.0])

    steps = build_steps_from_args(args)

    assert steps == [
        (
            "clip",
            {"min_value": -2.0, "max_value": 2.0, "percentile": (1.0, 99.0)},
        )
    ]


def test_build_steps_from_args_rejects_too_many_percentiles():
    args = make_args(clip_percentile=[1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="clip-percentile"):
        build_steps_from_args(args)
