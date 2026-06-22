import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.roi import ROISet, TimeChannelROI
from das_view.analysis.service import (
    compute_roi_spectral_attributes_for_file,
    compute_roi_statistics_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "roi_service.h5"
    sample_rate_hz = 1000.0
    t = np.arange(200, dtype=float) / sample_rate_hz
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 10.0 * t),
            np.sin(2 * np.pi * 20.0 * t),
            np.ones_like(t) * 2.0,
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path, data


def test_compute_roi_statistics_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, data = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 0, 50, 0, 2)

    service_result = compute_roi_statistics_for_file(path, [roi])

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.analysis_kind == "statistics"
    assert len(service_result.results) == 1
    assert service_result.results[0].result.mean == pytest.approx(np.mean(data[:50, :2]))


def test_roi_statistics_respects_time_and_channel_selection(tmp_path):
    path, _ = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 10, 60, 1, 3)

    service_result = compute_roi_statistics_for_file(path, [roi])
    item = service_result.results[0]

    assert item.selection.time_slice == slice(10, 60, 1)
    assert item.selection.channel_slice == slice(1, 3, 1)
    assert item.metadata.n_samples == 50
    assert item.metadata.n_channels == 2


def test_roi_statistics_applies_preprocessing_steps(tmp_path):
    path, _ = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 0, 100, 0, 2)

    service_result = compute_roi_statistics_for_file(
        path,
        [roi],
        preprocessing_steps=[("demean", {"axis": 0})],
    )

    assert service_result.results[0].preprocessing_history
    assert service_result.results[0].preprocessing_history[0]["name"] == "demean"
    assert abs(service_result.results[0].result.mean) < 1e-12


def test_roi_statistics_supports_multiple_rois_and_roiset(tmp_path):
    path, _ = make_zd_file(tmp_path)
    rois = ROISet(
        [
            TimeChannelROI("r1", 0, 50, 0, 1),
            TimeChannelROI("r2", 50, 100, 1, 3),
        ]
    )

    service_result = compute_roi_statistics_for_file(path, rois)

    assert len(service_result.results) == 2
    assert service_result.results[1].roi.roi_id == "r2"


def test_roi_service_result_has_metadata_reader_and_selection(tmp_path):
    path, _ = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 0, 20, 0, 1)

    service_result = compute_roi_statistics_for_file(path, [roi])
    item = service_result.results[0]

    assert item.reader_name == "zd_hdf5"
    assert item.metadata.source_format == "zd_hdf5"
    assert item.selection.downsample == (1, 1)


def test_compute_roi_spectral_attributes_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 0, 200, 0, 1)

    service_result = compute_roi_spectral_attributes_for_file(path, [roi])

    assert service_result.analysis_kind == "spectral_attributes"
    assert service_result.results[0].result.dominant_frequency_hz == pytest.approx(10.0)


def test_compute_roi_band_energy_for_file(tmp_path):
    path, _ = make_zd_file(tmp_path)
    roi = TimeChannelROI("r1", 0, 200, 0, 1)

    service_result = compute_roi_spectral_attributes_for_file(path, [roi], bands=[(8.0, 12.0)])

    assert service_result.analysis_kind == "band_energy"
    assert service_result.results[0].result.band_energy.shape == (1,)
