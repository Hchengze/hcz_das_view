import numpy as np
import pytest

from das_view.plotting.downsample import downsample_for_display, estimate_display_pixels


def test_downsample_for_display_leaves_small_2d_data_shape_unchanged():
    data = np.arange(24, dtype=float).reshape(6, 4)

    result = downsample_for_display(data, max_samples=10, max_channels=10)

    assert result.data.shape == (6, 4)
    assert result.time_step == 1
    assert result.channel_step == 1
    np.testing.assert_array_equal(result.data, data)


def test_downsample_for_display_reduces_large_2d_data_without_mutating_input():
    data = np.arange(100 * 40, dtype=float).reshape(100, 40)
    original = data.copy()

    result = downsample_for_display(data, max_samples=20, max_channels=10)

    assert result.data.shape[0] <= 20
    assert result.data.shape[1] <= 10
    assert result.time_step == 5
    assert result.channel_step == 4
    np.testing.assert_array_equal(data, original)


def test_downsample_for_display_supports_1d_data():
    data = np.arange(100, dtype=float)

    result = downsample_for_display(data, max_samples=25, max_channels=10)

    assert result.data.shape[0] <= 25
    assert result.time_step == 4
    assert result.channel_step == 1


def test_estimate_display_pixels_reports_steps_and_shape():
    estimate = estimate_display_pixels(100, 40, max_samples=25, max_channels=8)

    assert estimate["original_shape"] == (100, 40)
    assert estimate["display_shape"] == (25, 8)
    assert estimate["time_step"] == 4
    assert estimate["channel_step"] == 5
    assert estimate["pixels"] == 200


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_samples": 0},
        {"max_channels": 0},
    ],
)
def test_downsample_for_display_rejects_invalid_limits(kwargs):
    with pytest.raises(ValueError, match="positive integer"):
        downsample_for_display(np.arange(10), **kwargs)


def test_downsample_for_display_rejects_non_image_rank():
    with pytest.raises(ValueError, match="1-D or 2-D"):
        downsample_for_display(np.zeros((2, 3, 4)))
