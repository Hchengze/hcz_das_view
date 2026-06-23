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
