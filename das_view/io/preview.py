"""Reader-independent preview workflow for GUI and CLI use."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import ReaderError, UnsupportedFormatError
from das_view.io.registry import ReaderRegistry, default_registry
from das_view.utils.slicing import SliceLike, normalize_slice, slice_length


@dataclass(frozen=True, slots=True)
class PreviewRequest:
    """Options for creating a small preview from a DAS file."""

    path: str | Path
    time_slice: SliceLike = None
    channel_slice: SliceLike = None
    max_samples: int = 2000
    max_channels: int = 500


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Result returned by create_preview."""

    metadata: DASMetadata
    preview: DASData
    reader_name: str
    time_slice: slice
    channel_slice: slice
    downsample: tuple[int, int]
    warnings: list[str] = field(default_factory=list)


def create_preview(
    path: str | Path,
    *,
    reader_registry: ReaderRegistry | None = None,
    time_slice: SliceLike = None,
    channel_slice: SliceLike = None,
    max_samples: int = 2000,
    max_channels: int = 500,
) -> PreviewResult:
    """Create a downsampled preview without blindly loading the full file."""

    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    if max_channels <= 0:
        raise ValueError("max_channels must be positive")

    registry = default_registry() if reader_registry is None else reader_registry
    try:
        reader = registry.get_reader(path)
    except UnsupportedFormatError:
        raise
    except ReaderError as exc:
        raise ReaderError(f"Could not select a reader for {path}: {exc}") from exc

    try:
        metadata = reader.read_metadata(path)
    except ReaderError as exc:
        raise ReaderError(f"{reader.name} failed to read metadata for {path}: {exc}") from exc

    normalized_time = normalize_slice(time_slice, metadata.n_samples, axis_name="time")
    normalized_channel = normalize_slice(
        channel_slice, metadata.n_channels, axis_name="channel"
    )
    selected_samples = slice_length(normalized_time)
    selected_channels = slice_length(normalized_channel)
    if selected_samples <= 0:
        raise ReaderError("time selection is empty")
    if selected_channels <= 0:
        raise ReaderError("channel selection is empty")
    time_step = _preview_step(selected_samples, max_samples)
    channel_step = _preview_step(selected_channels, max_channels)
    downsample = (time_step, channel_step)
    warnings: list[str] = []
    if time_step > 1 or channel_step > 1:
        warnings.append(
            "Preview data was downsampled with "
            f"time_step={time_step}, channel_step={channel_step}."
        )

    try:
        preview = reader.read(
            path,
            time_slice=normalized_time,
            channel_slice=normalized_channel,
            downsample=downsample,
        )
    except ReaderError as exc:
        raise ReaderError(f"{reader.name} failed to read preview data for {path}: {exc}") from exc

    return PreviewResult(
        metadata=metadata,
        preview=preview,
        reader_name=reader.name,
        time_slice=normalized_time,
        channel_slice=normalized_channel,
        downsample=downsample,
        warnings=warnings,
    )


def _preview_step(selected: int, maximum: int) -> int:
    if selected <= maximum:
        return 1
    return (selected + maximum - 1) // maximum
