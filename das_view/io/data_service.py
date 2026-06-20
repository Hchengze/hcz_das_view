"""Reader-independent data selection helpers for CLI and GUI workflows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import ReaderError, UnsupportedFormatError
from das_view.io.registry import ReaderRegistry, default_registry
from das_view.utils.slicing import (
    SliceLike,
    normalize_downsample,
    normalize_slice,
    slice_length,
)


@dataclass(frozen=True, slots=True)
class DataSelection:
    """Requested data selection in internal coordinates."""

    path: str | Path
    time_slice: SliceLike = None
    channel_slice: SliceLike = None
    downsample: int | tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Data returned by a reader-independent selection request."""

    das_data: DASData
    reader_name: str
    time_slice: slice
    channel_slice: slice
    downsample: tuple[int, int]
    requested_channels: tuple[int, ...] | None = None

    @property
    def metadata(self) -> DASMetadata:
        return self.das_data.metadata


def read_selection(
    path: str | Path,
    *,
    time_slice: SliceLike = None,
    channel_slice: SliceLike = None,
    downsample: int | tuple[int, int] | None = None,
    reader_registry: ReaderRegistry | None = None,
) -> SelectionResult:
    """Read a bounded DAS data selection through the registered reader."""

    reader = _select_reader(path, reader_registry=reader_registry)
    metadata = _read_metadata(reader, path)
    normalized_time = _non_empty_slice(
        normalize_slice(time_slice, metadata.n_samples, axis_name="time"),
        axis_name="time",
    )
    normalized_channel = _non_empty_slice(
        normalize_slice(channel_slice, metadata.n_channels, axis_name="channel"),
        axis_name="channel",
    )
    normalized_downsample = normalize_downsample(downsample)

    try:
        das_data = reader.read(
            path,
            time_slice=normalized_time,
            channel_slice=normalized_channel,
            downsample=normalized_downsample,
        )
    except ReaderError:
        raise
    except Exception as exc:  # noqa: BLE001 - service boundary wraps unexpected reader failures.
        raise ReaderError(f"{reader.name} failed to read selection from {path}: {exc}") from exc

    return SelectionResult(
        das_data=das_data,
        reader_name=reader.name,
        time_slice=normalized_time,
        channel_slice=normalized_channel,
        downsample=normalized_downsample,
    )


def read_trace(
    path: str | Path,
    *,
    channel: int | Sequence[int],
    time_slice: SliceLike = None,
    downsample: int | tuple[int, int] | None = None,
    reader_registry: ReaderRegistry | None = None,
) -> SelectionResult:
    """Read one or a few channels as a waveform-friendly selection."""

    reader = _select_reader(path, reader_registry=reader_registry)
    metadata = _read_metadata(reader, path)
    channels = _normalize_trace_channels(channel, metadata.n_channels)
    time_step, _ = normalize_downsample(downsample)

    if _is_arithmetic_progression(channels):
        channel_step = channels[1] - channels[0] if len(channels) > 1 else 1
        channel_slice = slice(channels[0], channels[-1] + channel_step, channel_step)
        result = read_selection(
            path,
            time_slice=time_slice,
            channel_slice=channel_slice,
            downsample=(time_step, 1),
            reader_registry=reader_registry,
        )
        return SelectionResult(
            das_data=_with_trace_attrs(result.das_data, channels, contiguous=True),
            reader_name=result.reader_name,
            time_slice=result.time_slice,
            channel_slice=result.channel_slice,
            downsample=result.downsample,
            requested_channels=tuple(channels),
        )

    start = min(channels)
    stop = max(channels) + 1
    result = read_selection(
        path,
        time_slice=time_slice,
        channel_slice=slice(start, stop),
        downsample=(time_step, 1),
        reader_registry=reader_registry,
    )
    relative_columns = [channel_index - start for channel_index in channels]
    selected = np.asarray(result.das_data.data)[:, relative_columns]
    selected_data = _with_trace_attrs(result.das_data, channels, contiguous=False, data=selected)
    return SelectionResult(
        das_data=selected_data,
        reader_name=result.reader_name,
        time_slice=result.time_slice,
        channel_slice=result.channel_slice,
        downsample=result.downsample,
        requested_channels=tuple(channels),
    )


def _select_reader(path: str | Path, *, reader_registry: ReaderRegistry | None):
    registry = default_registry() if reader_registry is None else reader_registry
    try:
        return registry.get_reader(path)
    except UnsupportedFormatError:
        raise
    except ReaderError as exc:
        raise ReaderError(f"Could not select a reader for {path}: {exc}") from exc


def _read_metadata(reader, path: str | Path) -> DASMetadata:
    try:
        return reader.read_metadata(path)
    except ReaderError:
        raise
    except Exception as exc:  # noqa: BLE001 - service boundary wraps unexpected reader failures.
        raise ReaderError(f"{reader.name} failed to read metadata for {path}: {exc}") from exc


def _non_empty_slice(value: slice, *, axis_name: str) -> slice:
    if slice_length(value) <= 0:
        raise ReaderError(f"{axis_name} selection is empty")
    return value


def _normalize_trace_channels(channel: int | Sequence[int], n_channels: int) -> list[int]:
    if isinstance(channel, int):
        channels = [channel]
    elif isinstance(channel, Sequence) and not isinstance(channel, (str, bytes)):
        channels = [int(value) for value in channel]
    else:
        raise ReaderError("channel must be an int or a sequence of ints")

    if not channels:
        raise ReaderError("channel selection must contain at least one channel")
    for value in channels:
        if value < 0 or value >= n_channels:
            raise ReaderError(
                f"channel index {value} is out of range for data with {n_channels} channels"
            )
    return channels


def _is_arithmetic_progression(channels: Sequence[int]) -> bool:
    if len(channels) <= 1:
        return True
    step = channels[1] - channels[0]
    if step <= 0:
        return False
    if len(channels) == 2:
        return True
    return all((channels[index] - channels[index - 1]) == step for index in range(2, len(channels)))


def _with_trace_attrs(
    das_data: DASData,
    channels: Sequence[int],
    *,
    contiguous: bool,
    data: np.ndarray | None = None,
) -> DASData:
    data_array = np.asarray(das_data.data if data is None else data)
    original_start = None
    if das_data.metadata.start_channel is not None and channels:
        original_start = das_data.metadata.start_channel - min(channels)
    channel_numbers = None
    if original_start is not None:
        channel_numbers = tuple(int(original_start + value) for value in channels)
    extra_attrs = dict(das_data.metadata.extra_attrs)
    extra_attrs.update(
        {
            "selected_channel_indices": tuple(int(value) for value in channels),
            "selected_channel_numbers": channel_numbers,
            "trace_selection_contiguous": bool(contiguous),
        }
    )
    start_channel = das_data.metadata.start_channel
    if start_channel is not None and channels:
        start_channel = start_channel + int(channels[0] - min(channels))
    dx_m = das_data.metadata.dx_m if contiguous else None
    metadata = replace(
        das_data.metadata,
        n_channels=data_array.shape[1],
        start_channel=start_channel,
        dx_m=dx_m,
        extra_attrs=extra_attrs,
    )
    return DASData(data=data_array, metadata=metadata)
