import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import compute_denoised_selection_for_file, compute_enhancement_report_for_file
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "denoise_service.h5"
    t = np.linspace(0, 1, 64, endpoint=False)
    common = np.sin(2 * np.pi * 5 * t)
    data = np.column_stack([common + np.sin(2 * np.pi * 20 * t), common, common * 2]).astype(np.float32)
    create_zd_h5(path, data)
    return path, data


def test_compute_denoised_selection_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_denoised_selection_for_file(
        path,
        denoise_steps=[("common_mode_removal", {"method": "median"})],
    )

    assert result.reader_name == "zd_hdf5"
    assert result.result.data.shape == (64, 3)
    assert result.denoise_history
    assert result.metadata.n_channels == 3


def test_denoise_service_respects_slices_and_preprocessing(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_denoised_selection_for_file(
        path,
        time_slice=slice(0, 32),
        channel_slice=slice(0, 2),
        preprocessing_steps=[("demean", {"axis": 0})],
        denoise_steps=[("channel_balance", {"target": "rms"})],
    )

    assert result.das_data.data.shape == (32, 2)
    assert result.preprocessing_history
    assert result.denoise_history[0]["name"] == "channel_balance"
    assert result.selection.time_slice == slice(0, 32, 1)


def test_compute_enhancement_report_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)

    result = compute_enhancement_report_for_file(
        path,
        denoise_steps=[("despike", {"z_threshold": 8.0})],
    )

    assert result.reader_name == "zd_hdf5"
    assert result.result.input_shape == (64, 3)
    assert result.denoise_history
