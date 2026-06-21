import numpy as np
import pytest

pytest.importorskip("h5py")
pytest.importorskip("scipy")

from das_view.analysis.service import compute_fk_for_file
from tests.test_hdf5_zd_reader import create_zd_h5


def make_fk_zd_file(tmp_path):
    path = tmp_path / "fk_service.h5"
    t = np.arange(256, dtype=float) / 1000.0
    x = np.arange(32, dtype=float) * 0.4
    data = np.cos(2 * np.pi * (40.0 * t[:, None] - 0.05 * x[None, :])).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_compute_fk_for_file_with_synthetic_zd_hdf5(tmp_path):
    path = make_fk_zd_file(tmp_path)

    service_result = compute_fk_for_file(
        path,
        time_slice=slice(0, 128),
        channel_slice=slice(0, 16),
    )

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.n_samples == 128
    assert service_result.metadata.n_channels == 16
    assert service_result.result.values.shape == (
        service_result.result.frequencies_hz.size,
        service_result.result.wavenumbers_cycles_per_m.size,
    )


def test_compute_fk_for_file_applies_bandpass_step(tmp_path):
    path = make_fk_zd_file(tmp_path)
    steps = [
        (
            "bandpass",
            {
                "sample_rate_hz": 1000.0,
                "freqmin_hz": 1.0,
                "freqmax_hz": 100.0,
                "axis": 0,
            },
        )
    ]

    service_result = compute_fk_for_file(
        path,
        time_slice=slice(0, 128),
        channel_slice=slice(0, 16),
        preprocessing_steps=steps,
    )

    assert service_result.preprocessing_history
    assert service_result.preprocessing_history[0]["name"] == "bandpass"
    assert service_result.das_data.metadata.extra_attrs["preprocessing_history"][0]["name"] == "bandpass"
