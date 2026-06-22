import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.analysis.service import compute_statistics_for_file
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "statistics_service.h5"
    data = np.arange(60, dtype=np.float32).reshape(10, 6)
    create_zd_h5(path, data)
    return path, data


def test_compute_statistics_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, data = make_zd_file(tmp_path)

    service_result = compute_statistics_for_file(path)

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.n_samples == 10
    assert service_result.metadata.n_channels == 6
    assert service_result.selection.time_slice == slice(0, 10, 1)
    assert service_result.selection.channel_slice == slice(0, 6, 1)
    assert service_result.result.mean == pytest.approx(np.mean(data))


def test_compute_statistics_for_file_respects_time_and_channel_slice(tmp_path):
    path, data = make_zd_file(tmp_path)

    service_result = compute_statistics_for_file(
        path,
        time_slice=slice(2, 8),
        channel_slice=slice(1, 5),
    )

    expected = data[2:8, 1:5]
    assert service_result.das_data.data.shape == expected.shape
    assert service_result.result.mean == pytest.approx(np.mean(expected))
    assert service_result.result.count == expected.size


def test_compute_statistics_for_file_applies_preprocessing_steps(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_statistics_for_file(
        path,
        time_slice=slice(0, 10),
        channel_slice=slice(0, 3),
        axis=0,
        preprocessing_steps=[("demean", {"axis": 0})],
    )

    assert service_result.preprocessing_history
    assert service_result.preprocessing_history[0]["name"] == "demean"
    np.testing.assert_allclose(service_result.result.mean, np.zeros(3), atol=1e-12)


def test_compute_statistics_for_file_axis_zero_and_one(tmp_path):
    path, data = make_zd_file(tmp_path)

    axis0 = compute_statistics_for_file(path, time_slice=slice(0, 5), channel_slice=slice(0, 4), axis=0)
    axis1 = compute_statistics_for_file(path, time_slice=slice(0, 5), channel_slice=slice(0, 4), axis=1)

    assert axis0.result.mean.shape == (4,)
    assert axis1.result.mean.shape == (5,)
    np.testing.assert_allclose(axis0.result.mean, np.mean(data[:5, :4], axis=0))
    np.testing.assert_allclose(axis1.result.mean, np.mean(data[:5, :4], axis=1))


def test_compute_statistics_for_file_result_has_metadata_reader_and_selection(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_statistics_for_file(path, time_slice=slice(0, 4), channel_slice=slice(0, 2))

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.source_format == "zd_hdf5"
    assert service_result.selection.downsample == (1, 1)
    assert service_result.result.source_metadata["n_samples"] == 4
    assert service_result.result.source_metadata["n_channels"] == 2
