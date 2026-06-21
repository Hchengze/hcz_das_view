import numpy as np
import pytest

pytest.importorskip("h5py")
pytest.importorskip("scipy")

from das_view.analysis.service import (
    compute_psd_for_file,
    compute_spectrogram_for_file,
    compute_spectrum_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path, *, sample_rate_hz=1000.0):
    path = tmp_path / "spectrum_service.h5"
    t = np.arange(1024, dtype=float) / sample_rate_hz
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 20.0 * t),
            np.sin(2 * np.pi * 40.0 * t),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_compute_spectrum_for_file_with_synthetic_zd_hdf5(tmp_path):
    path = make_zd_file(tmp_path)

    service_result = compute_spectrum_for_file(path, channel=0, max_samples=512)

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.n_channels == 1
    assert service_result.result.kind == "amplitude"
    assert service_result.result.values.size == service_result.result.frequencies_hz.size


def test_compute_psd_for_file_with_synthetic_zd_hdf5(tmp_path):
    path = make_zd_file(tmp_path)

    service_result = compute_psd_for_file(path, channel=1, max_samples=512, method="welch", nperseg=128)

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.method == "welch"
    assert service_result.result.values.size == service_result.result.frequencies_hz.size


def test_compute_spectrogram_for_file_with_synthetic_zd_hdf5(tmp_path):
    path = make_zd_file(tmp_path)

    service_result = compute_spectrogram_for_file(path, channel=0, max_samples=512, nperseg=128)

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.values.shape == (
        service_result.result.frequencies_hz.size,
        service_result.result.times_s.size,
    )


def test_compute_psd_for_file_applies_bandpass_step(tmp_path):
    path = make_zd_file(tmp_path)
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

    service_result = compute_psd_for_file(
        path,
        channel=0,
        max_samples=512,
        method="periodogram",
        preprocessing_steps=steps,
    )

    assert service_result.preprocessing_history
    assert service_result.preprocessing_history[0]["name"] == "bandpass"
    assert service_result.das_data.metadata.extra_attrs["preprocessing_history"][0]["name"] == "bandpass"


def test_compute_services_reject_invalid_max_samples(tmp_path):
    path = make_zd_file(tmp_path)

    with pytest.raises(ValueError, match="max_samples"):
        compute_spectrum_for_file(path, channel=0, max_samples=0)
