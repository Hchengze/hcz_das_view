import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import (
    compute_coherence_for_file,
    compute_multiband_map_for_file,
    compute_quality_report_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "qc_service.h5"
    t = np.arange(64, dtype=float) / 1000.0
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 50 * t),
            np.sin(2 * np.pi * 50 * t),
            np.zeros_like(t),
            np.sin(2 * np.pi * 120 * t),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path, data


def test_compute_quality_report_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_quality_report_for_file(path)

    assert result.reader_name == "zd_hdf5"
    assert result.metadata.n_samples == 64
    assert result.result.channel_metrics.n_channels == 4
    assert result.selection.time_slice == slice(0, 64, 1)


def test_quality_report_respects_slices_and_preprocessing(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_quality_report_for_file(
        path,
        time_slice=slice(0, 32),
        channel_slice=slice(0, 2),
        preprocessing_steps=[("demean", {"axis": 0})],
    )

    assert result.das_data.data.shape == (32, 2)
    assert result.preprocessing_history
    assert result.result.channel_metrics.n_channels == 2


def test_compute_multiband_map_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_multiband_map_for_file(
        path,
        bands=[(1, 80), (80, 200)],
        window_samples=32,
        step_samples=16,
    )

    assert result.reader_name == "zd_hdf5"
    assert result.result.values.shape == (3, 4, 2)
    assert result.result.sample_rate_hz == 1000.0


def test_compute_coherence_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_coherence_for_file(path, channel_lag=1, window_samples=32, step_samples=16)

    assert result.reader_name == "zd_hdf5"
    assert result.result.coherence.shape == (3, 3)
    assert result.result.channel_lag == 1
