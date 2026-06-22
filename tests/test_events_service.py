import numpy as np
import pytest

pytest.importorskip("h5py")
pytest.importorskip("scipy")

from das_view.analysis.service import (
    compute_envelope_for_file,
    compute_stalta_for_file,
    detect_events_for_file,
)
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "events_service.h5"
    data = np.zeros((200, 4), dtype=np.float32)
    data[80:100, 2] = 8.0
    data += 0.1
    create_zd_h5(path, data)
    return path, data


def test_compute_envelope_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, data = make_zd_file(tmp_path)

    service_result = compute_envelope_for_file(path, time_slice=slice(0, 120), channel_slice=slice(0, 3))

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.values.shape == (120, 3)
    assert service_result.metadata.n_samples == 120
    assert service_result.metadata.extra_attrs["original_n_samples"] == data.shape[0]


def test_compute_stalta_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_stalta_for_file(
        path,
        time_slice=slice(0, 150),
        channel_slice=slice(1, 3),
        sta_samples=4,
        lta_samples=20,
    )

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.result.ratio.shape == (150, 2)


def test_detect_events_for_file_with_synthetic_zd_hdf5(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = detect_events_for_file(
        path,
        time_slice=slice(0, 150),
        channel_slice=slice(0, 4),
        method="stalta",
        sta_samples=4,
        lta_samples=25,
        trigger_on=1.5,
        trigger_off=1.0,
        min_duration_samples=2,
    )

    assert service_result.result.candidates
    assert service_result.result.method == "stalta"


def test_event_services_respect_time_and_channel_slice(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = detect_events_for_file(
        path,
        time_slice=slice(50, 120),
        channel_slice=slice(2, 3),
        method="envelope",
        threshold=2.0,
    )

    assert service_result.das_data.data.shape == (70, 1)
    assert service_result.selection.time_slice == slice(50, 120, 1)
    assert service_result.selection.channel_slice == slice(2, 3, 1)


def test_event_services_apply_preprocessing_steps(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_stalta_for_file(
        path,
        time_slice=slice(0, 100),
        channel_slice=slice(0, 2),
        sta_samples=4,
        lta_samples=20,
        preprocessing_steps=[("demean", {"axis": 0})],
    )

    assert service_result.preprocessing_history
    assert service_result.preprocessing_history[0]["name"] == "demean"


def test_event_service_result_has_metadata_reader_and_selection(tmp_path):
    path, _ = make_zd_file(tmp_path)

    service_result = compute_envelope_for_file(path, time_slice=slice(0, 20), channel_slice=slice(0, 1))

    assert service_result.reader_name == "zd_hdf5"
    assert service_result.metadata.source_format == "zd_hdf5"
    assert service_result.selection.downsample == (1, 1)
    assert service_result.result.source_metadata["n_samples"] == 20
    assert service_result.result.source_metadata["n_channels"] == 1
