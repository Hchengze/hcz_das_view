import numpy as np
import pytest

from das_view.processing.preprocess import (
    clip,
    demean,
    detrend_linear,
    normalize,
    standardize,
    taper,
)


def test_demean_axis_zero_mean_is_near_zero():
    data = np.array([[1.0, 2.0], [3.0, 6.0], [5.0, 10.0]])

    result = demean(data, axis=0)

    np.testing.assert_allclose(np.mean(result, axis=0), [0.0, 0.0], atol=1e-12)


def test_detrend_linear_removes_linear_trend_per_channel():
    x = np.arange(10, dtype=float)
    data = np.column_stack((2.0 * x + 1.0, -3.0 * x + 5.0))

    result = detrend_linear(data, axis=0)

    np.testing.assert_allclose(result, np.zeros_like(data), atol=1e-12)


def test_taper_preserves_shape_and_tapers_edges():
    data = np.ones((10, 3))

    result = taper(data, axis=0, ratio=0.2)

    assert result.shape == data.shape
    assert np.allclose(result[0], 0.0)
    assert np.all(result[2:-2] == 1.0)


def test_taper_ratio_zero_returns_equal_copy():
    data = np.arange(6.0).reshape(3, 2)

    result = taper(data, axis=0, ratio=0.0)

    np.testing.assert_array_equal(result, data)
    assert not np.shares_memory(result, data)


def test_taper_rejects_invalid_ratio_and_axis():
    data = np.ones((4, 2))

    with pytest.raises(ValueError, match="ratio"):
        taper(data, ratio=0.75)
    with pytest.raises(ValueError, match="axis"):
        taper(data, axis=2)


def test_normalize_maxabs_handles_all_zero_data():
    data = np.zeros((4, 2))

    result = normalize(data, mode="maxabs")

    np.testing.assert_array_equal(result, data)


def test_normalize_maxabs_scales_to_one():
    data = np.array([[-2.0, 1.0], [4.0, -8.0]])

    result = normalize(data, mode="maxabs")

    assert np.nanmax(np.abs(result)) == pytest.approx(1.0)


def test_normalize_minmax_maps_to_minus_one_plus_one():
    data = np.array([[0.0, 5.0], [10.0, 15.0]])

    result = normalize(data, mode="minmax")

    assert np.nanmin(result) == pytest.approx(-1.0)
    assert np.nanmax(result) == pytest.approx(1.0)


def test_standardize_mean_and_std_are_reasonable():
    data = np.array([[1.0, 2.0], [3.0, 6.0], [5.0, 10.0]])

    result = standardize(data, axis=0)

    np.testing.assert_allclose(np.mean(result, axis=0), [0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(np.std(result, axis=0), [1.0, 1.0], atol=1e-12)


def test_standardize_constant_data_does_not_crash():
    data = np.ones((5, 2))

    result = standardize(data, axis=0)

    np.testing.assert_array_equal(result, np.zeros_like(data))


def test_clip_min_max_limits_values():
    data = np.array([-5.0, -1.0, 0.0, 3.0])

    result = clip(data, min_value=-1.0, max_value=1.0)

    np.testing.assert_array_equal(result, [-1.0, -1.0, 0.0, 1.0])


def test_clip_percentile_limits_values():
    data = np.array([0.0, 1.0, 2.0, 100.0])

    result = clip(data, percentile=(25.0, 75.0))

    assert result.min() == pytest.approx(0.75)
    assert result.max() == pytest.approx(26.5)


def test_clip_rejects_invalid_percentile():
    with pytest.raises(ValueError, match="percentile"):
        clip(np.arange(4.0), percentile=(90.0, 10.0))


def test_functions_do_not_modify_input():
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    original = data.copy()

    _ = demean(data)
    _ = detrend_linear(data)
    _ = taper(data, ratio=0.25)
    _ = normalize(data)
    _ = standardize(data)
    _ = clip(data, min_value=0.0, max_value=1.0)

    np.testing.assert_array_equal(data, original)


def test_nan_inf_are_preserved_while_finite_values_are_processed():
    data = np.array([[1.0, np.nan], [3.0, np.inf], [5.0, 9.0]])

    demeaned = demean(data, axis=0)
    standardized = standardize(data, axis=0)

    assert np.isnan(demeaned[0, 1])
    assert np.isposinf(demeaned[1, 1])
    assert np.isnan(standardized[0, 1])
    assert np.isposinf(standardized[1, 1])
    finite_col0 = np.isfinite(demeaned[:, 0])
    assert np.mean(demeaned[:, 0][finite_col0]) == pytest.approx(0.0)


def test_normalize_rejects_unknown_mode_and_bad_eps():
    with pytest.raises(ValueError, match="mode"):
        normalize(np.ones((2, 2)), mode="unknown")
    with pytest.raises(ValueError, match="eps"):
        normalize(np.ones((2, 2)), eps=0.0)
