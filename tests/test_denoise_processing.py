import numpy as np
import pytest

from das_view.core import DASData, DASMetadata
from das_view.processing.denoise import (
    DenoiseResult,
    apply_denoise_workflow,
    channel_balance,
    common_mode_removal,
    despike,
    local_normalize,
    robust_clip,
    running_median_filter,
    time_space_median_filter,
)


def test_common_mode_removal_suppresses_shared_signal():
    common = np.arange(8, dtype=float)
    data = np.column_stack([common + 1.0, common - 1.0, common + 0.5])

    output = common_mode_removal(data)

    assert output.shape == data.shape
    assert np.max(np.abs(np.median(output, axis=1))) < 1e-12


def test_despike_replaces_outlier():
    data = np.zeros((21, 2), dtype=float)
    data[10, 0] = 100.0

    output = despike(data, z_threshold=8.0)

    assert output[10, 0] == 0.0
    assert output.shape == data.shape


def test_running_median_filter_shape_and_no_inplace():
    data = np.arange(12, dtype=float).reshape(6, 2)
    original = data.copy()

    output = running_median_filter(data, size=3)

    assert output.shape == data.shape
    np.testing.assert_array_equal(data, original)


def test_channel_balance_makes_rms_closer():
    t = np.linspace(0, 2 * np.pi, 64)
    data = np.column_stack([np.sin(t), 10.0 * np.sin(t)])

    output = channel_balance(data, target="rms")
    rms = np.sqrt(np.mean(output**2, axis=0))

    assert np.max(rms) / np.min(rms) < 1.1


def test_local_normalize_and_time_space_filter_are_stable():
    data = np.ones((8, 3), dtype=float)

    normalized = local_normalize(data, window_samples=3)
    filtered = time_space_median_filter(data, time_size=3, channel_size=3)

    assert normalized.shape == data.shape
    assert filtered.shape == data.shape
    assert np.all(np.isfinite(normalized))


def test_robust_clip_limits_extreme_values():
    data = np.array([0.0, 1.0, 2.0, 100.0])

    output = robust_clip(data, lower_percentile=0, upper_percentile=75)

    assert output[-1] < 100.0


def test_dasdata_input_and_nan_policy():
    data = np.column_stack([np.arange(8, dtype=float), np.arange(8, dtype=float)])
    das_data = DASData(data=data, metadata=DASMetadata(n_samples=8, n_channels=2))

    output = common_mode_removal(das_data)

    assert output.shape == data.shape
    with pytest.raises(ValueError):
        robust_clip(np.array([1.0, np.nan]), nan_policy="raise")


def test_invalid_parameters_raise():
    with pytest.raises(ValueError):
        running_median_filter(np.ones((4, 2)), size=0)
    with pytest.raises(ValueError):
        channel_balance(np.ones((4, 2)), target="bad")
    with pytest.raises(ValueError):
        robust_clip(np.ones(4), lower_percentile=90, upper_percentile=10)


def test_apply_denoise_workflow_history_and_shape():
    data = np.column_stack([np.ones(16), 2.0 * np.ones(16)])

    result = apply_denoise_workflow(
        data,
        [
            ("common_mode_removal", {"method": "median"}),
            ("channel_balance", {"target": "rms"}),
        ],
    )

    assert isinstance(result, DenoiseResult)
    assert result.data.shape == data.shape
    assert len(result.report.steps) == 2
    assert "rms" in result.report.before
    assert "energy" in result.report.after


def test_apply_denoise_workflow_rejects_unknown_step():
    with pytest.raises(ValueError):
        apply_denoise_workflow(np.ones((4, 2)), ["not_a_step"])
