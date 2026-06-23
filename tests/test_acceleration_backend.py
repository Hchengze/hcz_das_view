import sys

import numpy as np
import pytest

from das_view.acceleration import (
    as_backend_array,
    describe_acceleration,
    get_acceleration_backend,
    get_array_module,
    is_cupy_available,
    to_numpy,
)


def test_cpu_and_auto_resolve_to_numpy_without_importing_cupy():
    sys.modules.pop("cupy", None)

    cpu = get_acceleration_backend("cpu")
    auto = get_acceleration_backend("auto")

    assert cpu.name == "cpu"
    assert auto.name == "cpu"
    assert cpu.array_module is np
    assert auto.array_module is np
    assert "cupy" not in sys.modules


def test_backend_array_and_to_numpy_cpu_roundtrip():
    data = [[1, 2], [3, 4]]

    array = as_backend_array(data, backend="cpu")
    result = to_numpy(array)

    assert isinstance(array, np.ndarray)
    np.testing.assert_allclose(result, np.asarray(data, dtype=float))


def test_get_array_module_auto_defaults_to_numpy():
    assert get_array_module(np.ones(2), backend="auto") is np


def test_describe_acceleration_is_serializable_and_cpu_first():
    description = describe_acceleration()

    assert description["default_backend"] == "cpu"
    assert description["auto_backend"] == "cpu"
    assert isinstance(description["gpu_available"], bool)


def test_invalid_backend_name_is_rejected():
    with pytest.raises(ValueError, match="backend"):
        get_acceleration_backend("cuda")


def test_gpu_backend_requires_cupy_when_unavailable():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    with pytest.raises(ImportError, match="CuPy"):
        get_acceleration_backend("gpu")
