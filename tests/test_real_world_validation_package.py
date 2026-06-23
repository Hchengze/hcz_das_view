import json

import numpy as np
import pytest

pytest.importorskip("h5py")

from examples import real_world_validation_package as package
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "private_sample_name.h5"
    t = np.linspace(0, 1, 128, endpoint=False)
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 8 * t),
            np.sin(2 * np.pi * 16 * t),
            np.sin(2 * np.pi * 24 * t),
            np.sin(2 * np.pi * 32 * t),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_real_world_validation_package_import_and_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        package.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_quick_validation_synthetic_zd_summary_is_path_free(tmp_path):
    sample = make_zd_file(tmp_path)
    paths_file = tmp_path / "local_validation_paths.txt"
    paths_file.write_text(str(sample), encoding="utf-8")

    summary = package.run_validation_package(paths_file=paths_file, quick=True)

    assert summary["status"] == "ok"
    assert summary["mode"] == "quick"
    sample_summary = summary["samples"][0]
    assert sample_summary["file_index"] == 1
    assert sample_summary["suffix"] == ".h5"
    assert sample_summary["reader"] == "zd_hdf5"
    operations = {item["operation"]: item for item in sample_summary["operations"]}
    assert {"metadata", "preview", "waveform", "statistics", "qc"}.issubset(operations)
    assert "multiband" not in operations

    encoded = json.dumps(summary)
    assert str(sample) not in encoded
    assert sample.name not in encoded


def test_full_validation_includes_release_candidate_operations(tmp_path):
    sample = make_zd_file(tmp_path)
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(str(sample), encoding="utf-8")

    summary = package.run_validation_package(
        paths_file=paths_file,
        quick=False,
        max_samples=64,
        max_channels=4,
    )

    operations = {item["operation"]: item for item in summary["samples"][0]["operations"]}
    assert operations["multiband"]["status"] == "ok"
    assert operations["denoise_report"]["status"] == "ok"
    assert operations["moveout_summary"]["status"] == "ok"


def test_include_gpu_info_no_cupy_safe_and_json_output_is_explicit(tmp_path):
    sample = make_zd_file(tmp_path)
    paths_file = tmp_path / "paths.txt"
    output = tmp_path / "validation_summary.json"
    paths_file.write_text(str(sample), encoding="utf-8")

    summary = package.run_validation_package(
        paths_file=paths_file,
        quick=True,
        include_gpu_info=True,
        output=output,
    )

    assert "gpu_info" in summary
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert str(sample) not in text
    assert sample.name not in text


def test_missing_paths_file_skips_cleanly(tmp_path):
    summary = package.run_validation_package(paths_file=tmp_path / "missing.txt")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "paths_file_not_found"
