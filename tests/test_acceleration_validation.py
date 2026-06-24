import pytest

from das_view.acceleration import is_cupy_available
from das_view.acceleration.validation import validate_cpu_gpu_numeric_consistency


def test_numeric_validation_skips_without_cupy():
    result = validate_cpu_gpu_numeric_consistency(shape=(32, 8), functions=("statistics",))

    if is_cupy_available():
        assert result["status"] in {"ok", "failed"}
    else:
        assert result["status"] == "skipped"
        assert result["checks"][0]["status"] == "skipped"


def test_numeric_validation_require_gpu_errors_without_cupy():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    with pytest.raises(ImportError, match="CuPy"):
        validate_cpu_gpu_numeric_consistency(shape=(32, 8), require_gpu=True)


def test_numeric_validation_rejects_bad_function_and_shape():
    with pytest.raises(ValueError, match="unsupported"):
        validate_cpu_gpu_numeric_consistency(shape=(32, 8), functions=("unknown",))
    with pytest.raises(ValueError, match="shape"):
        validate_cpu_gpu_numeric_consistency(shape=(1, 8))


def test_numeric_validation_reports_gpu_runtime_error(monkeypatch):
    monkeypatch.setattr("das_view.acceleration.validation.is_cupy_available", lambda: True)
    monkeypatch.setattr(
        "das_view.acceleration.validation.validate_gpu_runtime",
        lambda: {"ok": True, "message": "ok"},
    )

    def fail_outputs(name, data):
        raise RuntimeError("kernel compile failed")

    monkeypatch.setattr("das_view.acceleration.validation._function_outputs", fail_outputs)

    result = validate_cpu_gpu_numeric_consistency(shape=(32, 8), functions=("statistics",))

    assert result["status"] == "failed"
    assert result["checks"][0]["status"] == "gpu_runtime_error"
    assert "kernel compile failed" in result["checks"][0]["message"]


def test_numeric_validation_reports_runtime_preflight_error(monkeypatch):
    monkeypatch.setattr("das_view.acceleration.validation.is_cupy_available", lambda: True)
    monkeypatch.setattr(
        "das_view.acceleration.validation.validate_gpu_runtime",
        lambda: {"ok": False, "message": "runtime missing"},
    )

    result = validate_cpu_gpu_numeric_consistency(shape=(32, 8), functions=("statistics",))

    assert result["status"] == "failed"
    assert result["reason"] == "runtime missing"
    assert result["checks"][0]["status"] == "gpu_runtime_error"
