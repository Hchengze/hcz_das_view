import json

import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.cli import qc
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "qc_cli.h5"
    data = np.arange(128, dtype=np.float32).reshape(32, 4)
    data[:, 1] = 0.0
    create_zd_h5(path, data)
    return path


def test_qc_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        qc.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_qc_cli_quality_report_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "qc.json"

    assert qc.main([str(path), "--quality-report", "--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "quality_report" in payload


def test_qc_cli_bad_channels_csv(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "bad.csv"

    assert qc.main([str(path), "--bad-channels", "--output", str(output)]) == 0

    text = output.read_text(encoding="utf-8")
    assert "bad_channel" in text


def test_qc_cli_multiband_and_coherence_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "features.json"

    assert (
        qc.main(
            [
                str(path),
                "--multiband",
                "1",
                "80",
                "80",
                "200",
                "--window-samples",
                "16",
                "--step-samples",
                "8",
                "--coherence",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "multiband" in payload
    assert "coherence" in payload


def test_parse_band_pairs_rejects_odd_limits():
    with pytest.raises(ValueError):
        qc.parse_band_pairs([1, 2, 3])
