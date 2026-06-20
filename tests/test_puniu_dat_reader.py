import numpy as np
import pytest

from das_view.core.exceptions import ReaderError
from das_view.io.puniu_dat import PUNIU_HEADER_BYTES, PuniuDATReader, parse_puniu_dat_header


def write_puniu_dat(path, data, *, n_samples=None, n_channels=None):
    n_samples = data.shape[0] if n_samples is None else n_samples
    n_channels = data.shape[1] if n_channels is None else n_channels
    header = np.array(
        [
            n_channels,
            0.4,
            n_samples,
            0.001,
            1,
            1_700_000_000.0,
            500_000_000.0,
            10,
            PUNIU_HEADER_BYTES,
            99,
        ],
        dtype=np.float64,
    )
    with path.open("wb") as f:
        header.tofile(f)
        data.astype(np.float32).tofile(f)


def write_puniu_header(path, values, payload=b""):
    with path.open("wb") as f:
        np.array(values, dtype=np.float64).tofile(f)
        f.write(payload)


def test_parse_puniu_dat_header_and_read_synthetic_file(tmp_path):
    path = tmp_path / "synthetic.dat"
    data = np.arange(6, dtype=np.float32).reshape(3, 2)
    write_puniu_dat(path, data)

    parsed = parse_puniu_dat_header(path)
    assert parsed.channel_count == 2
    assert parsed.n_samples == 3
    assert parsed.sample_rate_hz == 1000.0
    assert parsed.start_time is not None

    das_data = PuniuDATReader().read(path)
    assert das_data.data.shape == (3, 2)
    np.testing.assert_array_equal(das_data.data, data)
    assert das_data.metadata.source_format == "puniu_dat"


def test_puniu_dat_reader_slice(tmp_path):
    path = tmp_path / "synthetic.dat"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    write_puniu_dat(path, data)

    das_data = PuniuDATReader().read(
        path,
        time_slice=slice(1, 5, 2),
        channel_slice=slice(1, 4, 2),
    )

    np.testing.assert_array_equal(das_data.data, data[1:5:2, 1:4:2])
    assert das_data.metadata.n_samples == 2
    assert das_data.metadata.n_channels == 2
    assert das_data.metadata.start_channel == 11


def test_puniu_dat_reader_downsample(tmp_path):
    path = tmp_path / "synthetic.dat"
    data = np.arange(48, dtype=np.float32).reshape(8, 6)
    write_puniu_dat(path, data)

    das_data = PuniuDATReader().read(path, downsample=(2, 3))

    np.testing.assert_array_equal(das_data.data, data[::2, ::3])
    assert das_data.metadata.sample_rate_hz == 500.0
    assert das_data.metadata.dx_m == pytest.approx(1.2)


def test_puniu_dat_reader_rejects_data_length_mismatch(tmp_path):
    path = tmp_path / "bad.dat"
    data = np.arange(4, dtype=np.float32).reshape(2, 2)
    write_puniu_dat(path, data, n_samples=3, n_channels=2)

    with pytest.raises(ReaderError, match="does not match expected"):
        PuniuDATReader().read(path)


def test_puniu_dat_reader_rejects_incomplete_header(tmp_path):
    path = tmp_path / "short.dat"
    np.array([1.0, 2.0], dtype=np.float64).tofile(path)

    with pytest.raises(ReaderError, match="header is incomplete"):
        parse_puniu_dat_header(path)


def test_puniu_dat_reader_rejects_seek_smaller_than_header(tmp_path):
    path = tmp_path / "bad_seek.dat"
    values = [2, 0.4, 3, 0.001, 1, 0, 0, 0, PUNIU_HEADER_BYTES - 4, 1]
    write_puniu_header(path, values)

    with pytest.raises(ReaderError, match="smaller than header size"):
        parse_puniu_dat_header(path)


def test_puniu_dat_reader_rejects_unaligned_payload(tmp_path):
    path = tmp_path / "unaligned.dat"
    values = [2, 0.4, 3, 0.001, 1, 0, 0, 0, PUNIU_HEADER_BYTES, 1]
    write_puniu_header(path, values, payload=b"abc")

    with pytest.raises(ReaderError, match="not divisible by float32"):
        parse_puniu_dat_header(path)


def test_puniu_dat_reader_handles_invalid_timestamp_without_crashing(tmp_path):
    path = tmp_path / "bad_timestamp.dat"
    data = np.arange(6, dtype=np.float32).reshape(3, 2)
    values = [2, 0.4, 3, 0.001, 1, 1e300, 0, 10, PUNIU_HEADER_BYTES, 1]
    write_puniu_header(path, values, payload=data.astype(np.float32).tobytes())

    metadata = PuniuDATReader().read_metadata(path)

    assert metadata.start_time is None


def test_puniu_dat_reader_rejects_empty_or_out_of_range_slices(tmp_path):
    path = tmp_path / "synthetic.dat"
    data = np.arange(20, dtype=np.float32).reshape(5, 4)
    write_puniu_dat(path, data)

    with pytest.raises(ReaderError, match="time selection is empty"):
        PuniuDATReader().read(path, time_slice=slice(2, 2))
    with pytest.raises(ReaderError, match="channel selection is empty"):
        PuniuDATReader().read(path, channel_slice=slice(4, 9))
