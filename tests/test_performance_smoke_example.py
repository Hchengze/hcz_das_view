import numpy as np
import pytest

pytest.importorskip("h5py")

from examples import performance_smoke
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "performance_smoke.h5"
    data = np.arange(512, dtype=np.float32).reshape(64, 8)
    create_zd_h5(path, data)
    return path


def test_performance_smoke_parser_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        performance_smoke.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_performance_smoke_small_hdf5_outputs_elapsed_and_estimated(capsys, tmp_path):
    path = make_zd_file(tmp_path)

    assert performance_smoke.main([str(path), "--operations", "preview,statistics,qc"]) == 0

    output = capsys.readouterr().out
    assert "operation=preview" in output
    assert "operation=statistics" in output
    assert "operation=qc" in output
    assert "elapsed=" in output
    assert "estimated=" in output


def test_performance_smoke_rejects_unknown_operation():
    with pytest.raises(ValueError, match="unsupported"):
        performance_smoke._parse_operations("preview,unknown")
