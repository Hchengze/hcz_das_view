import numpy as np
import pytest

pytest.importorskip("scipy")

from das_view.core.data_model import DASData, DASMetadata
from das_view.processing.service import apply_preprocess


def make_filtered_das():
    sample_rate_hz = 500.0
    t = np.arange(1000) / sample_rate_hz
    data = (
        np.sin(2 * np.pi * 5.0 * t)
        + np.sin(2 * np.pi * 40.0 * t)
        + np.sin(2 * np.pi * 120.0 * t)
    )[:, None]
    metadata = DASMetadata(
        n_samples=data.shape[0],
        n_channels=data.shape[1],
        sample_rate_hz=sample_rate_hz,
        source_format="synthetic",
    )
    return DASData(data=data, metadata=metadata)


def test_apply_preprocess_supports_lowpass():
    das_data = make_filtered_das()

    result = apply_preprocess(
        das_data,
        [("lowpass", {"sample_rate_hz": 500.0, "cutoff_hz": 20.0})],
    )

    assert result.data.shape == das_data.data.shape
    assert result.metadata.extra_attrs["preprocessing_history"][0]["name"] == "lowpass"


def test_apply_preprocess_supports_bandpass_and_records_params():
    das_data = make_filtered_das()

    result = apply_preprocess(
        das_data,
        [
            (
                "bandpass",
                {"sample_rate_hz": 500.0, "freqmin_hz": 20.0, "freqmax_hz": 60.0},
            )
        ],
    )

    history = result.metadata.extra_attrs["preprocessing_history"]
    assert history[0]["name"] == "bandpass"
    assert history[0]["params"]["freqmin_hz"] == 20.0
    assert history[0]["params"]["freqmax_hz"] == 60.0


def test_apply_preprocess_mixed_preprocess_filter_normalize_steps():
    das_data = make_filtered_das()

    result = apply_preprocess(
        das_data,
        [
            ("demean", {"axis": 0}),
            (
                "bandpass",
                {"sample_rate_hz": 500.0, "freqmin_hz": 20.0, "freqmax_hz": 60.0},
            ),
            ("normalize", {"axis": None, "mode": "maxabs"}),
        ],
    )

    assert [entry["name"] for entry in result.metadata.extra_attrs["preprocessing_history"]] == [
        "demean",
        "bandpass",
        "normalize",
    ]
    assert np.max(np.abs(result.data)) == pytest.approx(1.0)


def test_unknown_step_still_raises():
    with pytest.raises(ValueError, match="unknown preprocessing step"):
        apply_preprocess(make_filtered_das(), ["unknown"])
