import pytest

from das_view.acceleration import is_cupy_available
from das_view.acceleration.benchmark import (
    GpuRuntimeError,
    compare_cpu_gpu_benchmark,
    run_array_backend_benchmark,
)


def test_cpu_benchmark_runs_small_shape():
    results = run_array_backend_benchmark(
        shape=(32, 8),
        dtype="float32",
        operations=("mean", "std", "rms", "energy", "fft_time", "band_power_like"),
        backend="cpu",
        warmup=0,
        repeats=1,
    )

    assert len(results) == 6
    for item in results:
        assert item.backend == "cpu"
        assert item.elapsed_seconds >= 0
        assert item.estimated_memory_bytes == 32 * 8 * 4


def test_compare_cpu_gpu_benchmark_skips_without_cupy():
    result = compare_cpu_gpu_benchmark(
        shape=(32, 8),
        operations=("mean",),
        warmup=0,
        repeats=1,
    )

    if is_cupy_available():
        assert result["status"] == "ok"
        assert result["gpu"]
    else:
        assert result["status"] == "skipped"
        assert result["gpu"] == []
        assert "CuPy" in result["reason"]


def test_compare_cpu_gpu_benchmark_reports_runtime_error(monkeypatch):
    monkeypatch.setattr("das_view.acceleration.benchmark.is_cupy_available", lambda: True)

    def fake_run(**kwargs):
        if kwargs["backend"] == "gpu":
            raise GpuRuntimeError("kernel compile failed")
        return run_array_backend_benchmark(**kwargs)

    monkeypatch.setattr("das_view.acceleration.benchmark.run_array_backend_benchmark", fake_run)

    result = compare_cpu_gpu_benchmark(
        shape=(16, 4),
        operations=("mean",),
        warmup=0,
        repeats=1,
    )

    assert result["status"] == "gpu_runtime_error"
    assert result["gpu"] == []
    assert "kernel compile failed" in result["reason"]


def test_gpu_benchmark_reports_runtime_preflight_error(monkeypatch):
    from das_view.acceleration import AccelerationRuntimeError

    monkeypatch.setattr(
        "das_view.acceleration.benchmark.get_acceleration_backend",
        lambda backend: (_ for _ in ()).throw(AccelerationRuntimeError("runtime missing")),
    )

    with pytest.raises(AccelerationRuntimeError, match="runtime missing"):
        run_array_backend_benchmark(shape=(16, 4), operations=("mean",), backend="gpu", warmup=0, repeats=1)


def test_gpu_benchmark_requires_cupy_when_requested():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    with pytest.raises(ImportError, match="CuPy"):
        run_array_backend_benchmark(shape=(16, 4), operations=("mean",), backend="gpu", warmup=0, repeats=1)


def test_benchmark_rejects_invalid_shape_and_operation():
    with pytest.raises(ValueError, match="shape"):
        run_array_backend_benchmark(shape=(0, 8), operations=("mean",), warmup=0, repeats=1)
    with pytest.raises(ValueError, match="unsupported"):
        run_array_backend_benchmark(shape=(16, 8), operations=("unknown",), warmup=0, repeats=1)
