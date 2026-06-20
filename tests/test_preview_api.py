import numpy as np
import pytest

from das_view.core.exceptions import ReaderError, UnsupportedFormatError
from das_view.io.base import BaseDASReader
from das_view.io.hdf5_zd import ZD_RAW_DATASET
from das_view.io.preview import create_preview
from das_view.io.puniu_dat import PUNIU_HEADER_BYTES
from das_view.io.registry import ReaderRegistry

h5py = pytest.importorskip("h5py")


def write_zd_h5(path, data):
    with h5py.File(path, "w") as handle:
        raw_group = handle.create_group("/Acquisition/Raw[0]")
        raw_group.attrs["NumberOfLoci"] = data.shape[1]
        raw_group.attrs["OutputDataRate"] = 1000.0
        acquisition = handle["/Acquisition"]
        acquisition.attrs["SpatialSamplingInterval"] = 0.5
        acquisition.attrs["GaugeLength"] = 2.0
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


def test_create_preview_reads_synthetic_zd_hdf5(tmp_path):
    path = tmp_path / "sample.h5"
    data = np.arange(120, dtype=np.float32).reshape(12, 10)
    write_zd_h5(path, data)

    result = create_preview(path, time_slice=slice(2, 10), channel_slice=slice(1, 9))

    assert result.reader_name == "zd_hdf5"
    assert result.metadata.n_samples == 12
    assert result.preview.data.shape == (8, 8)
    np.testing.assert_array_equal(result.preview.data, data[2:10, 1:9])
    assert result.downsample == (1, 1)


def test_create_preview_reads_synthetic_puniu_dat(tmp_path):
    path = tmp_path / "sample.dat"
    data = np.arange(60, dtype=np.float32).reshape(10, 6)
    write_puniu_dat(path, data)

    result = create_preview(path, max_samples=20, max_channels=20)

    assert result.reader_name == "puniu_dat"
    assert result.preview.data.shape == (10, 6)
    np.testing.assert_array_equal(result.preview.data, data)


def test_create_preview_downsamples_to_requested_limits(tmp_path):
    path = tmp_path / "large.h5"
    data = np.arange(120, dtype=np.float32).reshape(12, 10)
    write_zd_h5(path, data)

    result = create_preview(path, max_samples=4, max_channels=3)

    assert result.downsample == (3, 4)
    assert result.preview.data.shape == (4, 3)
    np.testing.assert_array_equal(result.preview.data, data[::3, ::4])
    assert result.warnings


def test_create_preview_rejects_unsupported_format(tmp_path):
    path = tmp_path / "sample.xyz"
    path.write_text("not a das file", encoding="utf-8")

    with pytest.raises(UnsupportedFormatError, match="No registered DAS reader"):
        create_preview(path)


def test_create_preview_reports_metadata_errors(tmp_path):
    class BrokenMetadataReader(BaseDASReader):
        name = "broken"
        supported_extensions = (".broken",)

        def read_metadata(self, path):
            raise ReaderError("synthetic metadata failure")

        def read(self, path):
            raise AssertionError("read should not be called")

    path = tmp_path / "sample.broken"
    path.write_text("broken", encoding="utf-8")
    registry = ReaderRegistry()
    registry.register(BrokenMetadataReader())

    with pytest.raises(ReaderError, match="failed to read metadata"):
        create_preview(path, reader_registry=registry)
