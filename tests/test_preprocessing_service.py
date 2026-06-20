import numpy as np
import pytest

from das_view.core.data_model import DASData, DASMetadata
from das_view.processing.service import PreprocessStep, apply_preprocess


def make_das_data():
    metadata = DASMetadata(
        n_samples=4,
        n_channels=2,
        sample_rate_hz=100.0,
        dx_m=0.5,
        source_format="synthetic",
        extra_attrs={"existing": "kept"},
    )
    data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
    return DASData(data=data, metadata=metadata)


def test_apply_preprocess_returns_new_dasdata_and_preserves_metadata():
    das_data = make_das_data()

    result = apply_preprocess(das_data, [("demean", {"axis": 0})])

    assert result is not das_data
    assert result.metadata is not das_data.metadata
    assert result.metadata.sample_rate_hz == das_data.metadata.sample_rate_hz
    assert result.metadata.dx_m == das_data.metadata.dx_m
    assert result.metadata.extra_attrs["existing"] == "kept"
    np.testing.assert_array_equal(das_data.data, make_das_data().data)


def test_apply_preprocess_records_history():
    das_data = make_das_data()

    result = apply_preprocess(
        das_data,
        [
            PreprocessStep("demean", {"axis": 0}),
            ("taper", {"axis": 0, "ratio": 0.25}),
            "normalize",
        ],
    )

    history = result.metadata.extra_attrs["preprocessing_history"]
    assert [entry["name"] for entry in history] == ["demean", "taper", "normalize"]
    assert history[1]["params"]["ratio"] == 0.25
    assert result.data.shape == das_data.data.shape


def test_apply_preprocess_multi_step_order():
    das_data = make_das_data()

    result = apply_preprocess(
        das_data,
        [
            ("demean", {"axis": 0}),
            ("normalize", {"axis": None, "mode": "maxabs"}),
        ],
    )

    np.testing.assert_allclose(result.data.mean(axis=0), [0.0, 0.0], atol=1e-12)
    assert np.max(np.abs(result.data)) == pytest.approx(1.0)


def test_apply_preprocess_unknown_step_raises_clear_error():
    with pytest.raises(ValueError, match="unknown preprocessing step"):
        apply_preprocess(make_das_data(), ["not_a_step"])


def test_apply_preprocess_bad_step_params_raise_clear_error():
    with pytest.raises(ValueError, match="ratio"):
        apply_preprocess(make_das_data(), [("taper", {"ratio": 1.0})])


def test_apply_preprocess_rejects_malformed_step():
    with pytest.raises(ValueError, match="preprocessing step name"):
        apply_preprocess(make_das_data(), [(1, {})])
