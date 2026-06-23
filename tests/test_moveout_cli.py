import json

import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.cli import moveout
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "moveout_cli.h5"
    t = np.arange(64, dtype=float) / 1000.0
    base = np.sin(2 * np.pi * 50 * t)
    data = np.column_stack([np.roll(base, channel) for channel in range(6)]).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_moveout_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        moveout.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_moveout_cli_directional_energy_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "direction.json"

    assert moveout.main([str(path), "--directional-energy", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "directional_energy" in payload


def test_moveout_cli_apparent_moveout_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "moveout.json"

    assert (
        moveout.main(
            [
                str(path),
                "--apparent-moveout",
                "--channel-lag",
                "1",
                "--window-samples",
                "32",
                "--step-samples",
                "16",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "apparent_moveout" in payload


def test_moveout_cli_summary_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "summary.json"

    assert moveout.main([str(path), "--summary", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "summary" in payload


def test_moveout_cli_missing_dx_error_is_readable(monkeypatch, tmp_path):
    path = make_zd_file(tmp_path)

    def fail_missing_dx(*args, **kwargs):
        raise ValueError("dx_m is required for moveout analysis")

    monkeypatch.setattr(moveout, "compute_moveout_summary_for_file", fail_missing_dx)
    with pytest.raises(SystemExit) as excinfo:
        moveout.main([str(path), "--summary"])

    assert "dx_m is required" in str(excinfo.value)
