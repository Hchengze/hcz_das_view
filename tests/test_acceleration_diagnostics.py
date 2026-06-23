import sys

import pytest

from das_view.acceleration import (
    estimate_gpu_array_memory,
    format_acceleration_report,
    get_cupy_build_info,
    get_gpu_device_info,
    is_cupy_available,
    validate_gpu_backend,
)


def test_import_acceleration_diagnostics_does_not_import_cupy():
    sys.modules.pop("cupy", None)

    import das_view
    import das_view.acceleration as acceleration

    assert das_view
    assert acceleration
    assert "cupy" not in sys.modules


def test_format_acceleration_report_no_cupy_does_not_crash():
    report = format_acceleration_report("auto")
    text = format_acceleration_report("auto", as_text=True)

    assert report["default_backend"] == "cpu"
    assert report["auto_backend"] == "cpu"
    assert "cupy_available" in report
    assert "installation_hint" in report
    assert "selected_backend:" in text


def test_gpu_device_and_build_info_are_status_dicts():
    build = get_cupy_build_info()
    device = get_gpu_device_info()

    assert "cupy_available" in build
    assert "cupy_available" in device
    assert isinstance(build["cupy_available"], bool)
    assert isinstance(device["cupy_available"], bool)


def test_validate_gpu_backend_no_cupy_returns_clear_status():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    status = validate_gpu_backend()

    assert status["ok"] is False
    assert status["status"] == "unavailable"
    assert "CuPy" in status["message"]


def test_estimate_gpu_array_memory_reports_bytes_and_shape():
    result = estimate_gpu_array_memory(shape=(16, 8), dtype="float32", arrays=2)

    assert result["shape"] == (16, 8)
    assert result["dtype"] == "float32"
    assert result["arrays"] == 2
    assert result["estimated_bytes"] == 16 * 8 * 4 * 2
    assert "estimated_human" in result


def test_estimate_gpu_array_memory_rejects_bad_shape():
    with pytest.raises(ValueError, match="shape"):
        estimate_gpu_array_memory(shape=(0, 8))
