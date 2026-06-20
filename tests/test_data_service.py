import numpy as np
import pytest

from das_view.core.exceptions import ReaderError, UnsupportedFormatError
from das_view.io.data_service import read_selection, read_trace
from das_view.io.hdf5_zd import ZD_RAW_DATASET
from das_view.io.puniu_dat import PUNIU_HEADER_BYTES


def write_zd_h5(path, data):
    h5py = pytest.importorskip("h5py")
    with h5py.File(path, "w") as handle:
        raw_group = handle.create_group("/Acquisition/Raw[0]")
        raw_group.attrs["NumberOfLoci"] = data.shape[1]
        raw_group.attrs["OutputDataRate"] = 1000.0
        acquisition = handle["/Acquisition"]
        acquisition.attrs["SpatialSamplingInterval"] = 0.5
        time_group = handle.create_group("/Acquisition/Raw[0]/RawDataTime")
        time_group.attrs["Count"] = data.shape[0]
        handle.create_dataset(ZD_RAW_DATASET, data=data)


def write_puniu_dat(path, data):
    header = np.array(
        [
            data.shape[1],
            0.5,
            data.shape[0],
            0.001,
            1,
            1_700_000_000.0,
            0.0,
            0,
            PUNIU_HEADER_BYTES,
            1,
        ],
        dtype=np.float64,
    )
    with path.open("wb") as handle:
        header.tofile(handle)
        data.astype(np.float32).tofile(handle)


def test_read_selection_synthetic_zd_hdf5(tmp_path):
    path = tmp_path / "sample.h5"
    data = np.arange(120, dtype=np.float32).reshape(12, 10)
    write_zd_h5(path, data)

    result = read_selection(
        path,
        time_slice=slice(2, 10),
        channel_slice=slice(1, 9),
        downsample=(2, 3),
    )

    assert result.reader_name == "zd_hdf5"
    np.testing.assert_array_equal(result.das_data.data, data[2:10:2, 1:9:3])
    assert result.das_data.data.shape == (4, 3)
    assert result.downsample == (2, 3)


def test_read_selection_synthetic_puniu_dat(tmp_path):
    path = tmp_path / "sample.dat"
    data = np.arange(60, dtype=np.float32).reshape(10, 6)
    write_puniu_dat(path, data)

    result = read_selection(path, time_slice=(1, 9), channel_slice=(2, 6), downsample=(2, 2))

    assert result.reader_name == "puniu_dat"
    np.testing.assert_array_equal(result.das_data.data, data[1:9:2, 2:6:2])
    assert result.das_data.data.shape == (4, 2)


def test_read_trace_single_channel_shape_and_values(tmp_path):
    path = tmp_path / "sample.h5"
    data = np.arange(80, dtype=np.float32).reshape(10, 8)
    write_zd_h5(path, data)

    result = read_trace(path, channel=3, time_slice=slice(1, 9), downsample=(2, 1))

    assert result.requested_channels == (3,)
    assert result.das_data.data.shape == (4, 1)
    np.testing.assert_array_equal(result.das_data.data[:, 0], data[1:9:2, 3])


def test_read_trace_multiple_noncontiguous_channels_preserves_order(tmp_path):
    path = tmp_path / "sample.dat"
    data = np.arange(80, dtype=np.float32).reshape(10, 8)
    write_puniu_dat(path, data)

    result = read_trace(path, channel=[5, 1, 3], time_slice=slice(0, 10, 2))

    assert result.requested_channels == (5, 1, 3)
    np.testing.assert_array_equal(result.das_data.data, data[0:10:2][:, [5, 1, 3]])
    assert result.das_data.metadata.extra_attrs["trace_selection_contiguous"] is False
    assert result.das_data.metadata.extra_attrs["selected_channel_indices"] == (5, 1, 3)


def test_read_trace_rejects_invalid_channel(tmp_path):
    path = tmp_path / "sample.dat"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    write_puniu_dat(path, data)

    with pytest.raises(ReaderError, match="out of range"):
        read_trace(path, channel=4)


def test_read_selection_rejects_empty_time_slice(tmp_path):
    path = tmp_path / "sample.dat"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    write_puniu_dat(path, data)

    with pytest.raises(ReaderError, match="time selection is empty"):
        read_selection(path, time_slice=slice(2, 2))


def test_read_selection_rejects_unsupported_format(tmp_path):
    path = tmp_path / "sample.xyz"
    path.write_text("not a supported DAS file", encoding="utf-8")

    with pytest.raises(UnsupportedFormatError, match="No registered DAS reader"):
        read_selection(path)
