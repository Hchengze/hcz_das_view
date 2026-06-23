import json

import pytest

from das_view.acceleration import is_cupy_available
from das_view.cli import gpu


def test_gpu_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        gpu.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_gpu_cli_info_no_output_file_by_default(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert gpu.main(["--info"]) == 0

    output = capsys.readouterr().out
    assert "cupy_available:" in output
    assert list(tmp_path.iterdir()) == []


def test_gpu_cli_cpu_benchmark_small_shape(capsys):
    assert gpu.main(["--benchmark", "--backend", "cpu", "--shape", "16", "4", "--operations", "mean", "--warmup", "0", "--repeats", "1"]) == 0

    assert "benchmark operation=mean" in capsys.readouterr().out


def test_gpu_cli_compare_and_validate_skip_without_cupy(capsys):
    assert gpu.main(["--compare", "--shape", "16", "4", "--operations", "mean", "--warmup", "0", "--repeats", "1"]) == 0
    compare_output = capsys.readouterr().out
    assert "compare status=" in compare_output

    assert gpu.main(["--validate-numeric", "--shape", "32", "4", "--functions", "statistics"]) == 0
    validate_output = capsys.readouterr().out
    assert "numeric_validation status=" in validate_output
    if not is_cupy_available():
        assert "skipped" in compare_output
        assert "skipped" in validate_output


def test_gpu_cli_json_output_is_explicit(tmp_path):
    output = tmp_path / "gpu_info.json"

    assert gpu.main(["--info", "--json-output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "info" in payload


def test_gpu_cli_explicit_gpu_errors_cleanly_without_cupy():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    with pytest.raises(SystemExit) as excinfo:
        gpu.main(["--benchmark", "--backend", "gpu", "--shape", "16", "4", "--operations", "mean"])
    assert "CuPy" in str(excinfo.value)
