from pathlib import Path

from examples.validate_local_samples import parse_path_list, validate_local_samples
from examples.validate_file import preview_summary


def test_parse_path_list_ignores_comments_and_blank_lines():
    paths = parse_path_list(
        [
            "# ZD HDF5",
            "",
            r"E:\data\sample.h5",
            "   # comment with spaces",
            r"E:\data\sample.dat   ",
        ]
    )

    assert paths == [Path(r"E:\data\sample.h5"), Path(r"E:\data\sample.dat")]


def test_validate_local_samples_missing_path_list_exits_cleanly(tmp_path, capsys):
    result = validate_local_samples(path_list=tmp_path / "missing.txt")

    captured = capsys.readouterr()
    assert result == 0
    assert "not found" in captured.out


def test_preview_summary_is_path_safe():
    class Metadata:
        source_format = "synthetic"
        n_samples = 10
        n_channels = 4
        sample_rate_hz = 1000.0
        dx_m = 0.5
        extra_attrs = {"raw_shape": (10, 4), "raw_orientation": "time_channel"}

    class Preview:
        class data:
            shape = (5, 2)

    class Result:
        metadata = Metadata()
        preview = Preview()
        reader_name = "synthetic_reader"
        downsample = (2, 2)
        warnings = ["downsampled"]

    summary = preview_summary(Result())

    assert summary["reader_name"] == "synthetic_reader"
    assert summary["raw_shape"] == (10, 4)
    assert summary["preview_shape"] == (5, 2)
    assert "source_path" not in summary
