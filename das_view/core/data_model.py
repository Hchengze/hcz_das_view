"""Core data containers for DAS data and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from das_view.core.exceptions import DataDimensionError


@dataclass(slots=True)
class DASMetadata:
    """Unified metadata for DAS data.

    Internal data arrays are always shaped as (n_samples, n_channels).
    """

    n_samples: int
    n_channels: int
    sample_rate_hz: float | None = None
    dt_s: float | None = None
    dx_m: float | None = None
    gauge_length_m: float | None = None
    start_channel: int | None = None
    start_time: Any | None = None
    source_format: str | None = None
    source_path: str | Path | None = None
    extra_attrs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.n_samples = int(self.n_samples)
        self.n_channels = int(self.n_channels)
        if self.n_samples <= 0:
            raise ValueError("n_samples must be positive")
        if self.n_channels <= 0:
            raise ValueError("n_channels must be positive")

        if self.sample_rate_hz is not None:
            self.sample_rate_hz = float(self.sample_rate_hz)
            if self.sample_rate_hz <= 0:
                raise ValueError("sample_rate_hz must be positive")

        if self.dt_s is not None:
            self.dt_s = float(self.dt_s)
            if self.dt_s <= 0:
                raise ValueError("dt_s must be positive")

        if self.dt_s is None and self.sample_rate_hz is not None:
            self.dt_s = 1.0 / self.sample_rate_hz
        elif self.sample_rate_hz is None and self.dt_s is not None:
            self.sample_rate_hz = 1.0 / self.dt_s

        if self.dx_m is not None:
            self.dx_m = float(self.dx_m)
        if self.gauge_length_m is not None:
            self.gauge_length_m = float(self.gauge_length_m)
        if self.start_channel is not None:
            self.start_channel = int(self.start_channel)
        if self.source_path is not None:
            self.source_path = str(self.source_path)


@dataclass(slots=True)
class DASData:
    """DAS data matrix plus metadata."""

    data: np.ndarray
    metadata: DASMetadata

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data)
        if self.data.ndim != 2:
            raise DataDimensionError(
                "DASData.data must be a 2-D array shaped as (n_samples, n_channels)"
            )
        expected = (self.metadata.n_samples, self.metadata.n_channels)
        if self.data.shape != expected:
            raise DataDimensionError(
                f"DASData shape {self.data.shape} does not match metadata {expected}; "
                "internal convention is (n_samples, n_channels)"
            )

    @property
    def n_samples(self) -> int:
        return self.metadata.n_samples

    @property
    def n_channels(self) -> int:
        return self.metadata.n_channels
