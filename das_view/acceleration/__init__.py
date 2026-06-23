"""Optional array acceleration helpers.

The acceleration layer is CPU-first.  Importing this package does not import
CuPy; GPU support is discovered lazily only when callers explicitly request it.
"""

from das_view.acceleration.backend import (
    AccelerationBackend,
    as_backend_array,
    describe_acceleration,
    get_acceleration_backend,
    get_array_module,
    is_cupy_available,
    to_numpy,
)

__all__ = [
    "AccelerationBackend",
    "as_backend_array",
    "describe_acceleration",
    "get_acceleration_backend",
    "get_array_module",
    "is_cupy_available",
    "to_numpy",
]
