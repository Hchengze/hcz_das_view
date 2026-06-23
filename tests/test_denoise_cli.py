import json

import numpy as np
import pytest

pytest.importorskip("h5py")

from das_view.cli import denoise
from tests.test_hdf5_zd_reader import create_zd_h5


def make_zd_file(tmp_path):
    path = tmp_path / "denoise_cli.h5"
    data = np.arange(128, dtype=np.float32).reshape(32, 4)
    create_zd_h5(path, data)
    return path


def test_denoise_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        denoise.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_denoise_cli_common_mode_report_json(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "report.json"

    assert denoise.main([str(path), "--common-mode", "median", "--output-report", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "steps" in payload


def test_denoise_cli_parses_multiple_steps(tmp_path):
    path = make_zd_file(tmp_path)
    output = tmp_path / "workflow.json"

    assert (
        denoise.main(
            [
                str(path),
                "--despike",
                "--z-threshold",
                "8.0",
                "--channel-balance",
                "rms",
                "--output-report",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    names = [step["name"] for step in payload["steps"]]
    assert "despike" in names
    assert "channel_balance" in names


def test_denoise_build_steps_workflow_names():
    args = denoise.build_parser().parse_args(["input.h5", "--workflow", "common_mode_removal,despike"])

    steps = denoise.build_steps(args)

    assert steps == [("common_mode_removal", {}), ("despike", {})]
