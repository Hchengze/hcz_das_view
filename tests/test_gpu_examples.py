import numpy as np
import pytest

pytest.importorskip("h5py")

from examples import gpu_benchmark, performance_smoke
from tests.test_hdf5_zd_reader import create_zd_h5


def _make_zd_file(tmp_path):
    path = tmp_path / "gpu_example.h5"
    data = np.arange(256, dtype=np.float32).reshape(32, 8)
    create_zd_h5(path, data)
    return path


def test_gpu_benchmark_example_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        gpu_benchmark.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_gpu_benchmark_example_info_and_cpu_benchmark(capsys):
    assert gpu_benchmark.main(["--info"]) == 0
    assert "cupy_available:" in capsys.readouterr().out

    assert gpu_benchmark.main(["--benchmark", "--backend", "cpu", "--shape", "16", "4", "--operations", "mean", "--warmup", "0", "--repeats", "1"]) == 0
    assert "mean:" in capsys.readouterr().out


def test_performance_smoke_backend_cpu_and_gpu_info(capsys, tmp_path):
    path = _make_zd_file(tmp_path)

    assert performance_smoke.main([str(path), "--operations", "statistics", "--backend", "cpu"]) == 0
    output = capsys.readouterr().out
    assert "backend=cpu" in output

    assert performance_smoke.main([str(path), "--operations", "statistics", "--gpu-info"]) == 0
    output = capsys.readouterr().out
    assert "cupy_available:" in output


def test_performance_smoke_compare_backends_skips_gpu_without_cupy(capsys, tmp_path):
    path = _make_zd_file(tmp_path)

    assert performance_smoke.main([str(path), "--operations", "statistics", "--compare-backends"]) == 0
    output = capsys.readouterr().out
    assert "backend=cpu" in output
