"""Optional array acceleration helpers.

The acceleration layer is CPU-first.  Importing this package does not import
CuPy; GPU support is discovered lazily only when callers explicitly request it.
"""

from das_view.acceleration.backend import (
    AccelerationBackend,
    as_backend_array,
    describe_acceleration,
    estimate_gpu_array_memory,
    format_acceleration_report,
    get_acceleration_backend,
    get_array_module,
    get_cupy_build_info,
    get_gpu_device_info,
    is_cupy_available,
    to_numpy,
    validate_gpu_backend,
)
from das_view.acceleration.benchmark import (
    BenchmarkResult,
    compare_cpu_gpu_benchmark,
    run_array_backend_benchmark,
)

__all__ = [
    "AccelerationBackend",
    "BenchmarkResult",
    "as_backend_array",
    "compare_cpu_gpu_benchmark",
    "describe_acceleration",
    "estimate_gpu_array_memory",
    "format_acceleration_report",
    "get_acceleration_backend",
    "get_array_module",
    "get_cupy_build_info",
    "get_gpu_device_info",
    "is_cupy_available",
    "run_array_backend_benchmark",
    "to_numpy",
    "validate_gpu_backend",
]
