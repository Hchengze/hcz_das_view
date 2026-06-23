import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import (
    compute_apparent_moveout_for_file,
    compute_directional_energy_for_file,
    compute_moveout_summary_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "moveout_service.h5"
    n_samples = 64
    n_channels = 6
    sample_rate_hz = 1000.0
    t = np.arange(n_samples, dtype=float) / sample_rate_hz
    base = np.sin(2 * np.pi * 50.0 * t)
    data = np.column_stack([np.roll(base, channel) for channel in range(n_channels)]).astype(np.float32)
    create_zd_h5(path, data)
    return path, data


def test_compute_directional_energy_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_directional_energy_for_file(path)

    assert result.reader_name == "zd_hdf5"
    assert result.result.total_energy >= 0
    assert result.metadata.dx_m == 0.4


def test_compute_apparent_moveout_for_file_respects_slices_and_preprocessing(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_apparent_moveout_for_file(
        path,
        time_slice=slice(0, 32),
        channel_slice=slice(0, 4),
        preprocessing_steps=[("demean", {"axis": 0})],
        denoise_steps=[("channel_balance", {"target": "rms"})],
        max_lag_samples=4,
    )

    assert result.das_data.data.shape == (32, 4)
    assert result.preprocessing_history
    assert result.denoise_history
    assert result.result.lag_samples.shape == (3,)


def test_compute_moveout_summary_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_moveout_summary_for_file(path, window_samples=32, step_samples=16)

    assert result.reader_name == "zd_hdf5"
    assert "directional_ratio" in result.result.summary
    assert result.selection.time_slice == slice(0, 64, 1)
