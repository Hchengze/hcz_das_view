import numpy as np
import pytest

from das_view.analysis.statistics import basic_statistics, finite_summary, window_statistics
from das_view.core.data_model import DASData, DASMetadata


def test_basic_statistics_global_values():
    data = np.array([[1.0, 2.0], [3.0, 4.0]])

    result = basic_statistics(data, percentiles=(0, 50, 100))

    assert result.count == 4
    assert result.finite_count == 4
    assert result.mean == pytest.approx(2.5)
    assert result.std == pytest.approx(np.std(data))
    assert result.min == 1.0
    assert result.max == 4.0
    assert result.median == pytest.approx(2.5)
    assert result.percentiles[0.0] == 1.0
    assert result.percentiles[50.0] == pytest.approx(2.5)
    assert result.percentiles[100.0] == 4.0


def test_basic_statistics_rms_energy_abs_mean_and_peak_to_peak():
    data = np.array([-2.0, -1.0, 1.0, 2.0])

    result = basic_statistics(data)

    assert result.rms == pytest.approx(np.sqrt(2.5))
    assert result.energy == pytest.approx(10.0)
    assert result.abs_mean == pytest.approx(1.5)
    assert result.peak_to_peak == pytest.approx(4.0)


def test_basic_statistics_axis_zero_returns_channel_values():
    data = np.arange(12, dtype=float).reshape(3, 4)

    result = basic_statistics(data, axis=0)

    assert result.mean.shape == (4,)
    assert result.std.shape == (4,)
    assert result.energy.shape == (4,)
    np.testing.assert_allclose(result.mean, np.mean(data, axis=0))
    np.testing.assert_allclose(result.energy, np.sum(data * data, axis=0))


def test_basic_statistics_axis_one_returns_time_values():
    data = np.arange(12, dtype=float).reshape(3, 4)

    result = basic_statistics(data, axis=1)

    assert result.mean.shape == (3,)
    assert result.peak_to_peak.shape == (3,)
    np.testing.assert_allclose(result.mean, np.mean(data, axis=1))
    np.testing.assert_allclose(result.peak_to_peak, np.ptp(data, axis=1))


def test_basic_statistics_accepts_dasdata_and_preserves_metadata_summary():
    data = np.arange(6, dtype=float).reshape(3, 2)
    das_data = DASData(
        data=data,
        metadata=DASMetadata(
            n_samples=3,
            n_channels=2,
            sample_rate_hz=1000.0,
            dx_m=0.4,
            source_format="synthetic",
        ),
    )

    result = basic_statistics(das_data, axis=0)

    assert result.source_metadata["n_samples"] == 3
    assert result.source_metadata["n_channels"] == 2
    assert result.source_metadata["sample_rate_hz"] == 1000.0
    np.testing.assert_allclose(result.mean, np.mean(data, axis=0))


def test_basic_statistics_omit_counts_and_ignores_nan_inf():
    data = np.array([1.0, np.nan, np.inf, -np.inf, 3.0])

    result = basic_statistics(data, nan_policy="omit")

    assert result.count == 5
    assert result.finite_count == 2
    assert result.nan_count == 1
    assert result.posinf_count == 1
    assert result.neginf_count == 1
    assert result.mean == pytest.approx(2.0)
    assert result.energy == pytest.approx(10.0)


def test_basic_statistics_raise_rejects_nan_or_inf():
    with pytest.raises(ValueError, match="NaN or Inf"):
        basic_statistics(np.array([1.0, np.nan]), nan_policy="raise")
    with pytest.raises(ValueError, match="NaN or Inf"):
        basic_statistics(np.array([1.0, np.inf]), nan_policy="raise")


def test_basic_statistics_all_nonfinite_is_stable():
    result = basic_statistics(np.array([np.nan, np.inf, -np.inf]))

    assert result.finite_count == 0
    assert result.nan_count == 1
    assert result.posinf_count == 1
    assert result.neginf_count == 1
    assert np.isnan(result.mean)
    assert np.isnan(result.rms)
    assert result.energy == 0.0


def test_basic_statistics_rejects_non_numeric_input():
    with pytest.raises(ValueError, match="real numeric"):
        basic_statistics(np.array(["a", "b"]))


def test_basic_statistics_does_not_modify_input():
    data = np.array([[1.0, np.nan], [3.0, 4.0]])
    original = data.copy()

    basic_statistics(data, axis=0)

    np.testing.assert_array_equal(data, original)


def test_window_statistics_selects_time_and_channel_window():
    data = np.arange(20, dtype=float).reshape(5, 4)

    result = window_statistics(data, time_slice=slice(1, 4), channel_slice=slice(1, 3))

    np.testing.assert_allclose(result.mean, np.mean(data[1:4, 1:3]))
    assert result.input_shape == (3, 2)


def test_finite_summary_axis_counts():
    data = np.array([[1.0, np.nan], [np.inf, -np.inf], [2.0, 3.0]])

    summary = finite_summary(data, axis=0)

    np.testing.assert_array_equal(summary.count, np.array([3, 3]))
    np.testing.assert_array_equal(summary.finite_count, np.array([2, 1]))
    np.testing.assert_array_equal(summary.nan_count, np.array([0, 1]))
    np.testing.assert_array_equal(summary.posinf_count, np.array([1, 0]))
    np.testing.assert_array_equal(summary.neginf_count, np.array([0, 1]))
