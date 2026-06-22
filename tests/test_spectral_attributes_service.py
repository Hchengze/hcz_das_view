import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import (
    compute_band_energy_for_file,
    compute_spectral_attributes_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path, *, sample_rate_hz=1000.0):
    path = tmp_path / "spectral_attributes_service.h5"
    t = np.arange(1000, dtype=float) / sample_rate_hz
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 10.0 * t),
            np.sin(2 * np.pi * 40.0 * t),
            np.sin(2 * np.pi * 80.0 * t),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path, data


def test_compute_band_energy_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_band_energy_for_file(path, bands=[(8.0, 12.0), (35.0, 45.0)])

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.band_energy.shape == (2, 3)
    assert service_result.result.band_energy[0, 0] > service_result.result.band_energy[1, 0]


def test_compute_spectral_attributes_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_spectral_attributes_for_file(path, channel_slice=slice(1, 2))

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.dominant_frequency_hz == pytest.approx(40.0)


def test_spectral_attribute_services_respect_time_and_channel_slice(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_band_energy_for_file(
        path,
        bands=[(35.0, 45.0)],
        time_slice=slice(0, 500),
        channel_slice=slice(1, 3),
    )

    assert service_result.das_data.data.shape == (500, 2)
    assert service_result.selection.time_slice == slice(0, 500, 1)
    assert service_result.selection.channel_slice == slice(1, 3, 1)


def test_spectral_attribute_services_apply_preprocessing_steps(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_spectral_attributes_for_file(
        path,
        channel_slice=slice(0, 1),
        preprocessing_steps=[("demean", {"axis": 0})],
    )

    assert service_result.preprocessing_history
    assert service_result.preprocessing_history[0]["name"] == "demean"
    assert service_result.result.dominant_frequency_hz == pytest.approx(10.0)


def test_spectral_attribute_services_average_channels(tmp_path):
    path, _ = make_zd_file(tmp_path)

    bands = compute_band_energy_for_file(
        path,
        bands=[(8.0, 12.0), (35.0, 45.0)],
        average_channels=True,
    )
    attrs = compute_spectral_attributes_for_file(path, average_channels=True)

    assert bands.result.band_energy.shape == (2,)
    assert isinstance(attrs.result.dominant_frequency_hz, float)


def test_spectral_attribute_service_result_has_metadata_reader_and_selection(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_spectral_attributes_for_file(path, time_slice=slice(0, 100), channel_slice=slice(0, 1))

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.source_format == "zd_hdf5"
    assert service_result.selection.downsample == (1, 1)
    assert service_result.result.sample_rate_hz == 1000.0
