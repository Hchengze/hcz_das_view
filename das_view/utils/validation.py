"""Validation helpers."""

from __future__ import annotations

import numpy as np

from das_view.core.exceptions import DataDimensionError


def validate_data_matrix(data: np.ndarray, *, name: str = "data") -> tuple[int, int]:
    """Validate internal DAS data shape and return (n_samples, n_channels)."""

    array = np.asarray(data)
    if array.ndim != 2:
        raise DataDimensionError(f"{name} must be 2-D with shape (n_samples, n_channels)")
    n_samples, n_channels = array.shape
    if n_samples <= 0 or n_channels <= 0:
        raise DataDimensionError(f"{name} dimensions must be positive")
    return int(n_samples), int(n_channels)
