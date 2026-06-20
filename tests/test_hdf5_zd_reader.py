import numpy as np
import pytest

from das_view.core.exceptions import ReaderError
from das_view.io.hdf5_zd import ZD_RAW_DATASET, ZDHDF5Reader

h5py = pytest.importorskip("h5py")


def create_zd_h5(path, data, *, count=None, number_of_loci=None):
    with h5py.File(path, "w") as handle:
        raw_group = handle.create_group("/Acquisition/Raw[0]")
        raw_group.attrs["NumberOfLoci"] = data.shape[1] if number_of_loci is None else number_of_loci
        raw_group.attrs["OutputDataRate"] = 1000.0
        acquisition = handle["/Acquisition"]
        acquisition.attrs["SpatialSamplingInterval"] = 0.4
        acquisition.attrs["GaugeLength"] = 1.6
        time_group = handle.create_group("/Acquisition/Raw[0]/RawDataTime")
        time_group.attrs["Count"] = data.shape[0] if count is None else count
        dataset = handle.create_dataset(ZD_RAW_DATASET, data=data)
        dataset.attrs["PartStartTime"] = "synthetic-start"


def test_zd_hdf5_reader_reads_metadata(tmp_path):
    path = tmp_path / "synthetic.h5"
    create_zd_h5(path, np.arange(6, dtype=np.float32).reshape(3, 2))

    metadata = ZDHDF5Reader().read_metadata(path)

    assert metadata.n_samples == 3
    assert metadata.n_channels == 2
    assert metadata.sample_rate_hz == 1000.0
    assert metadata.dx_m == 0.4
    assert metadata.extra_attrs["raw_shape"] == (3, 2)
    assert metadata.extra_attrs["raw_orientation"] == "time_channel"


def test_zd_hdf5_reader_accepts_numpy_scalar_and_bytes_attrs(tmp_path):
    path = tmp_path / "scalar_attrs.h5"
    data = np.arange(6, dtype=np.float32).reshape(3, 2)
    with h5py.File(path, "w") as handle:
        raw_group = handle.create_group("/Acquisition/Raw[0]")
        raw_group.attrs["NumberOfLoci"] = np.array(2, dtype=np.int64)
        raw_group.attrs["OutputDataRate"] = np.array(1000.0, dtype=np.float64)
        acquisition = handle["/Acquisition"]
        acquisition.attrs["SpatialSamplingInterval"] = np.array(0.4, dtype=np.float64)
        time_group = handle.create_group("/Acquisition/Raw[0]/RawDataTime")
        time_group.attrs["Count"] = np.array(3, dtype=np.int64)
        dataset = handle.create_dataset(ZD_RAW_DATASET, data=data)
        dataset.attrs["PartStartTime"] = b"synthetic-start"

    metadata = ZDHDF5Reader().read_metadata(path)

    assert metadata.n_samples == 3
    assert metadata.n_channels == 2
    assert metadata.extra_attrs["PartStartTime"] == "synthetic-start"


def test_zd_hdf5_reader_reads_full_time_channel_data(tmp_path):
    path = tmp_path / "synthetic.h5"
    data = np.arange(6, dtype=np.float32).reshape(3, 2)
    create_zd_h5(path, data)

    das_data = ZDHDF5Reader().read(path)

    assert das_data.data.shape == (3, 2)
    np.testing.assert_array_equal(das_data.data, data)


def test_zd_hdf5_reader_reads_time_slice(tmp_path):
    path = tmp_path / "synthetic.h5"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    create_zd_h5(path, data)

    das_data = ZDHDF5Reader().read(path, time_slice=slice(1, 4))

    np.testing.assert_array_equal(das_data.data, data[1:4, :])
    assert das_data.metadata.n_samples == 3
    assert das_data.metadata.extra_attrs["time_slice"] == (1, 4, 1)


def test_zd_hdf5_reader_reads_channel_slice(tmp_path):
    path = tmp_path / "synthetic.h5"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    create_zd_h5(path, data)

    das_data = ZDHDF5Reader().read(path, channel_slice=slice(1, 3))

    np.testing.assert_array_equal(das_data.data, data[:, 1:3])
    assert das_data.metadata.n_channels == 2
    assert das_data.metadata.extra_attrs["channel_slice"] == (1, 3, 1)


def test_zd_hdf5_reader_downsamples(tmp_path):
    path = tmp_path / "synthetic.h5"
    data = np.arange(48, dtype=np.float32).reshape(8, 6)
    create_zd_h5(path, data)

    das_data = ZDHDF5Reader().read(path, downsample=(2, 3))

    np.testing.assert_array_equal(das_data.data, data[::2, ::3])
    assert das_data.metadata.sample_rate_hz == 500.0
    assert das_data.metadata.dt_s == pytest.approx(0.002)
    assert das_data.metadata.dx_m == pytest.approx(1.2)


def test_zd_hdf5_reader_transposes_channel_time_data(tmp_path):
    path = tmp_path / "synthetic_channel_time.h5"
    internal = np.arange(12, dtype=np.float32).reshape(4, 3)
    raw = internal.T
    create_zd_h5(path, raw, count=4, number_of_loci=3)

    das_data = ZDHDF5Reader().read(path)

    assert das_data.metadata.extra_attrs["raw_orientation"] == "channel_time"
    np.testing.assert_array_equal(das_data.data, internal)


def test_zd_hdf5_reader_transposes_channel_time_slice(tmp_path):
    path = tmp_path / "synthetic_channel_time.h5"
    internal = np.arange(30, dtype=np.float32).reshape(5, 6)
    raw = internal.T
    create_zd_h5(path, raw, count=5, number_of_loci=6)

    das_data = ZDHDF5Reader().read(
        path,
        time_slice=slice(1, 5, 2),
        channel_slice=slice(2, 6, 2),
    )

    np.testing.assert_array_equal(das_data.data, internal[1:5:2, 2:6:2])
    assert das_data.metadata.n_samples == 2
    assert das_data.metadata.n_channels == 2


def test_zd_hdf5_reader_missing_raw_dataset_has_clear_error(tmp_path):
    path = tmp_path / "missing.h5"
    with h5py.File(path, "w") as handle:
        handle.create_group("/Acquisition")

    with pytest.raises(ReaderError, match="/Acquisition/Raw\\[0\\]/RawData"):
        ZDHDF5Reader().read_metadata(path)


def test_zd_hdf5_reader_rejects_mismatched_shape_hints(tmp_path):
    path = tmp_path / "mismatch.h5"
    data = np.zeros((3, 2), dtype=np.float32)
    create_zd_h5(path, data, count=99, number_of_loci=2)

    with pytest.raises(ReaderError, match="Cannot infer"):
        ZDHDF5Reader().read_metadata(path)


def test_zd_hdf5_reader_rejects_ambiguous_orientation(tmp_path):
    path = tmp_path / "ambiguous.h5"
    data = np.zeros((4, 4), dtype=np.float32)
    create_zd_h5(path, data, count=4, number_of_loci=4)

    with pytest.raises(ReaderError, match="Ambiguous"):
        ZDHDF5Reader().read_metadata(path)


def test_zd_hdf5_reader_rejects_empty_time_or_channel_slice(tmp_path):
    path = tmp_path / "synthetic.h5"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    create_zd_h5(path, data)

    with pytest.raises(ReaderError, match="time selection is empty"):
        ZDHDF5Reader().read(path, time_slice=slice(2, 2))
    with pytest.raises(ReaderError, match="channel selection is empty"):
        ZDHDF5Reader().read(path, channel_slice=slice(3, 3))
