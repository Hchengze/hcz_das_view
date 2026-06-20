"""Helpers for reader slicing and simple downsampling."""

from __future__ import annotations

from typing import TypeAlias

from das_view.core.exceptions import ReaderError

SliceLike: TypeAlias = slice | tuple[int | None, int | None] | tuple[int | None, int | None, int | None] | None


def normalize_downsample(downsample: int | tuple[int, int] | None) -> tuple[int, int]:
    """Normalize reader downsampling to (time_step, channel_step)."""

    if downsample is None:
        return 1, 1
    if isinstance(downsample, int):
        time_step = channel_step = downsample
    else:
        if len(downsample) != 2:
            raise ReaderError("downsample must be an int or a (time_step, channel_step) tuple")
        time_step, channel_step = downsample
    time_step = int(time_step)
    channel_step = int(channel_step)
    if time_step <= 0 or channel_step <= 0:
        raise ReaderError("downsample steps must be positive")
    return time_step, channel_step


def normalize_slice(value: SliceLike, size: int, *, axis_name: str) -> slice:
    """Normalize a user slice or tuple into a bounded positive-step slice."""

    if value is None:
        result = slice(None)
    elif isinstance(value, slice):
        result = value
    elif isinstance(value, tuple):
        if len(value) == 2:
            result = slice(value[0], value[1], None)
        elif len(value) == 3:
            result = slice(value[0], value[1], value[2])
        else:
            raise ReaderError(f"{axis_name} slice tuple must have 2 or 3 values")
    else:
        raise ReaderError(f"{axis_name} slice must be a slice, tuple, or None")

    start, stop, step = result.indices(size)
    if step <= 0:
        raise ReaderError(f"{axis_name} slice step must be positive")
    return slice(start, stop, step)


def apply_step(value: slice, step_multiplier: int) -> slice:
    """Apply an additional positive downsampling step to a normalized slice."""

    if step_multiplier <= 0:
        raise ReaderError("step_multiplier must be positive")
    step = 1 if value.step is None else int(value.step)
    return slice(value.start, value.stop, step * step_multiplier)


def slice_length(value: slice) -> int:
    """Return the number of selected samples in a normalized slice."""

    return len(range(value.start, value.stop, value.step))


def first_index(value: slice) -> int:
    """Return the first selected index, or zero for an empty slice."""

    return value.start if slice_length(value) else 0
