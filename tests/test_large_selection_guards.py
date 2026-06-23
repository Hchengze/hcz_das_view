import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import compute_quality_report_for_file, compute_statistics_for_file
from das_view.cli import denoise, moveout, qc, statistics
from das_view.core.data_model import DASMetadata
from das_view.core.exceptions import ReaderError
from das_view.core.metadata_format import format_metadata, metadata_to_dict
from das_view.io.data_service import read_selection
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "large_guard.h5"
    data = np.arange(1000, dtype=np.float32).reshape(100, 10)
    create_zd_h5(path, data)
    return path


def test_read_selection_default_call_keeps_working(tmp_path):
    path = make_zd_file(tmp_path)

    result = read_selection(path, time_slice=slice(0, 10), channel_slice=slice(0, 2))

    assert result.das_data.data.shape == (10, 2)
    assert result.estimated_nbytes == 10 * 2 * 8
    assert result.warnings == ()


def test_read_selection_rejects_over_limit_before_data_read(tmp_path):
    path = make_zd_file(tmp_path)

    with pytest.raises(ReaderError, match="exceeds"):
        read_selection(path, max_estimated_bytes=1)


def test_analysis_service_guard_does_not_break_default(tmp_path):
    path = make_zd_file(tmp_path)

    result = compute_statistics_for_file(path)

    assert result.selection.das_data.data.shape == (100, 10)


def test_analysis_service_guard_rejects_large_selection(tmp_path):
    path = make_zd_file(tmp_path)

    with pytest.raises(ReaderError, match="exceeds"):
        compute_quality_report_for_file(path, max_estimated_bytes=1)


def test_key_cli_parsers_accept_max_estimated_mb():
    assert statistics.build_parser().parse_args(["input.h5", "--max-estimated-mb", "1"]).max_estimated_mb == 1
    assert qc.build_parser().parse_args(["input.h5", "--max-estimated-mb", "1"]).max_estimated_mb == 1
    assert denoise.build_parser().parse_args(["input.h5", "--max-estimated-mb", "1"]).max_estimated_mb == 1
    assert moveout.build_parser().parse_args(["input.h5", "--max-estimated-mb", "1"]).max_estimated_mb == 1


def test_cli_guard_error_is_user_readable(tmp_path):
    path = make_zd_file(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        statistics.main([str(path), "--max-estimated-mb", "0.000001"])

    assert "statistics error:" in str(excinfo.value)
    assert "exceeds" in str(excinfo.value)


def test_metadata_format_includes_estimated_full_array_size():
    metadata = DASMetadata(n_samples=100, n_channels=10)

    values = metadata_to_dict(metadata)
    text = format_metadata(metadata)

    assert values["estimated_full_array_size"] == "7.81 KiB"
    assert "estimated_full_array_size: 7.81 KiB" in text
