"""Puniu DAT reader.

This module reimplements the useful DAT header layout identified in
old_code3/dy_view.py::read_puniu_dat_file without importing old code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import ReaderError
from das_view.io.base import BaseDASReader
from das_view.utils.slicing import (
    SliceLike,
    apply_step,
    first_index,
    normalize_downsample,
    normalize_slice,
    slice_length,
)

PUNIU_HEADER_DTYPE = np.float64
PUNIU_HEADER_COUNT = 10
PUNIU_HEADER_BYTES = PUNIU_HEADER_DTYPE().nbytes * PUNIU_HEADER_COUNT


@dataclass(frozen=True, slots=True)
class PuniuDATHeader:
    channel_count: int
    dx_m: float
    n_samples: int
    dt_s: float
    data_format: int
    timestamp_seconds: float
    timestamp_nanoseconds: float
    start_channel: int
    seek: int
    light_channel: int

    @property
    def sample_rate_hz(self) -> float:
        return 1.0 / self.dt_s

    @property
    def start_time(self) -> datetime | None:
        try:
            seconds = self.timestamp_seconds + self.timestamp_nanoseconds * 1e-9
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None


class PuniuDATReader(BaseDASReader):
    """Reader for the Puniu DAT layout used by the old GUI prototype."""

    name = "puniu_dat"
    supported_extensions = (".dat",)

    def read_metadata(self, path: str | Path) -> DASMetadata:
        header = parse_puniu_dat_header(path)
        return DASMetadata(
            n_samples=header.n_samples,
            n_channels=header.channel_count,
            sample_rate_hz=header.sample_rate_hz,
            dt_s=header.dt_s,
            dx_m=header.dx_m,
            start_channel=header.start_channel,
            start_time=header.start_time,
            source_format=self.name,
            source_path=path,
            extra_attrs={
                "data_format": header.data_format,
                "timestamp_seconds": header.timestamp_seconds,
                "timestamp_nanoseconds": header.timestamp_nanoseconds,
                "seek": header.seek,
                "light_channel": header.light_channel,
                "raw_header_bytes": PUNIU_HEADER_BYTES,
            },
        )

    def read(
        self,
        path: str | Path,
        time_slice: SliceLike = None,
        channel_slice: SliceLike = None,
        downsample: int | tuple[int, int] | None = None,
    ) -> DASData:
        source = Path(path)
        metadata = self.read_metadata(source)
        time_step, channel_step = normalize_downsample(downsample)
        internal_time_slice = apply_step(
            normalize_slice(time_slice, metadata.n_samples, axis_name="time"),
            time_step,
        )
        internal_channel_slice = apply_step(
            normalize_slice(channel_slice, metadata.n_channels, axis_name="channel"),
            channel_step,
        )
        _ensure_non_empty(internal_time_slice, axis_name="time")
        _ensure_non_empty(internal_channel_slice, axis_name="channel")

        expected_values = metadata.n_samples * metadata.n_channels
        available_values = _available_data_values(source, int(metadata.extra_attrs["seek"]))
        if available_values != expected_values:
            raise ReaderError(
                f"Puniu DAT data length {available_values} does not match expected "
                f"{expected_values} values from header"
            )

        matrix = np.memmap(
            source,
            dtype=np.float32,
            mode="r",
            offset=int(metadata.extra_attrs["seek"]),
            shape=(metadata.n_samples, metadata.n_channels),
        )
        data = np.asarray(matrix[internal_time_slice, internal_channel_slice])
        sliced_metadata = _slice_metadata(
            metadata,
            internal_time_slice=internal_time_slice,
            internal_channel_slice=internal_channel_slice,
            downsample=(time_step, channel_step),
        )
        return DASData(data=data, metadata=sliced_metadata)


def parse_puniu_dat_header(path: str | Path) -> PuniuDATHeader:
    """Parse the fixed 10-float64 Puniu DAT header."""

    source = Path(path)
    if not source.exists():
        raise ReaderError(f"Puniu DAT file does not exist: {source}")

    header = np.fromfile(source, dtype=PUNIU_HEADER_DTYPE, count=PUNIU_HEADER_COUNT)
    if header.size != PUNIU_HEADER_COUNT:
        raise ReaderError(f"Puniu DAT header is incomplete: {source}")

    try:
        channel_count = _finite_int(header[0], "channel_count")
        dx_m = _finite_float(header[1], "dx_m")
        n_samples = _finite_int(header[2], "n_samples")
        dt_s = _finite_float(header[3], "dt_s")
        data_format = _finite_int(header[4], "data_format")
        timestamp_seconds = float(header[5])
        timestamp_nanoseconds = float(header[6])
        start_channel = _finite_int(header[7], "start_channel")
        seek = _finite_int(header[8], "seek")
        light_channel = _finite_int(header[9], "light_channel")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ReaderError(f"Puniu DAT header contains invalid numeric values: {exc}") from exc

    if channel_count <= 0:
        raise ReaderError("Puniu DAT channel count must be positive")
    if n_samples <= 0:
        raise ReaderError("Puniu DAT sample count must be positive")
    if dt_s <= 0:
        raise ReaderError("Puniu DAT dt_s must be positive")
    if seek < PUNIU_HEADER_BYTES:
        raise ReaderError(
            f"Puniu DAT seek offset {seek} is smaller than header size {PUNIU_HEADER_BYTES}"
        )
    file_size = source.stat().st_size
    if seek > file_size:
        raise ReaderError(f"Puniu DAT seek offset {seek} exceeds file size {file_size}")
    payload_bytes = file_size - seek
    if payload_bytes % np.dtype(np.float32).itemsize != 0:
        raise ReaderError("Puniu DAT payload byte length is not divisible by float32 size")

    return PuniuDATHeader(
        channel_count=channel_count,
        dx_m=dx_m,
        n_samples=n_samples,
        dt_s=dt_s,
        data_format=data_format,
        timestamp_seconds=timestamp_seconds,
        timestamp_nanoseconds=timestamp_nanoseconds,
        start_channel=start_channel,
        seek=seek,
        light_channel=light_channel,
    )


def _available_data_values(path: Path, seek: int) -> int:
    return (path.stat().st_size - seek) // np.dtype(np.float32).itemsize


def _finite_int(value: float, name: str) -> int:
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return int(value)


def _finite_float(value: float, name: str) -> float:
    parsed = float(value)
    if not np.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _slice_metadata(
    metadata: DASMetadata,
    *,
    internal_time_slice: slice,
    internal_channel_slice: slice,
    downsample: tuple[int, int],
) -> DASMetadata:
    time_stride = internal_time_slice.step
    channel_stride = internal_channel_slice.step
    extra_attrs = dict(metadata.extra_attrs)
    extra_attrs.update(
        {
            "original_n_samples": metadata.n_samples,
            "original_n_channels": metadata.n_channels,
            "time_slice": _slice_to_tuple(internal_time_slice),
            "channel_slice": _slice_to_tuple(internal_channel_slice),
            "downsample": downsample,
        }
    )
    sample_rate = None if metadata.sample_rate_hz is None else metadata.sample_rate_hz / time_stride
    dt_s = None if metadata.dt_s is None else metadata.dt_s * time_stride
    dx_m = None if metadata.dx_m is None else metadata.dx_m * channel_stride
    start_channel = metadata.start_channel
    if start_channel is not None:
        start_channel = start_channel + first_index(internal_channel_slice)
    return replace(
        metadata,
        n_samples=slice_length(internal_time_slice),
        n_channels=slice_length(internal_channel_slice),
        sample_rate_hz=sample_rate,
        dt_s=dt_s,
        dx_m=dx_m,
        start_channel=start_channel,
        extra_attrs=extra_attrs,
    )


def _slice_to_tuple(value: slice) -> tuple[int, int, int]:
    return int(value.start), int(value.stop), int(value.step)


def _ensure_non_empty(value: slice, *, axis_name: str) -> None:
    if slice_length(value) <= 0:
        raise ReaderError(f"{axis_name} selection is empty")
