import pytest

from das_view.core.exceptions import ReaderError
from das_view.utils.memory import (
    check_selection_memory,
    estimate_array_nbytes,
    estimate_selection_nbytes,
    format_nbytes,
)


def test_estimate_array_nbytes():
    assert estimate_array_nbytes(10, 4, dtype="float32") == 160


def test_estimate_selection_nbytes_with_slice_step_and_downsample():
    estimated = estimate_selection_nbytes(
        n_samples=100,
        n_channels=20,
        time_slice=slice(0, 80, 2),
        channel_slice=slice(0, 10),
        downsample=(2, 5),
        dtype="float64",
    )

    assert estimated == 20 * 2 * 8


def test_format_nbytes():
    assert format_nbytes(512) == "512 B"
    assert format_nbytes(1024) == "1.00 KiB"
    assert format_nbytes(1024 * 1024) == "1.00 MiB"


def test_check_selection_memory_passes_without_limit():
    result = check_selection_memory(n_samples=10, n_channels=2)

    assert result.within_limit is True
    assert result.limit_bytes is None
    assert "Estimated selection size" in result.message


def test_check_selection_memory_marks_exceeded_limit():
    result = check_selection_memory(n_samples=100, n_channels=100, max_bytes=10)

    assert result.within_limit is False
    assert result.estimated_bytes > result.limit_bytes
    assert "exceeds" in result.message


def test_invalid_shape_raises_reader_error():
    with pytest.raises(ReaderError, match="n_samples"):
        estimate_array_nbytes(-1, 2)
