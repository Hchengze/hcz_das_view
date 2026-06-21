"""Small GUI-facing state helpers that do not import PyQt5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PreviewLimits:
    """Validated preview size limits from GUI controls or CLI options."""

    max_samples: int = 2000
    max_channels: int = 500


@dataclass(frozen=True, slots=True)
class PreviewDisplayInfo:
    """Display-ready summary for a preview result."""

    path: str
    reader_name: str
    preview_shape: tuple[int, int]
    downsample: tuple[int, int]

    @classmethod
    def from_preview_result(cls, result: Any) -> "PreviewDisplayInfo":
        source_path = result.metadata.source_path
        path = "N/A" if source_path is None else str(Path(source_path))
        return cls(
            path=path,
            reader_name=result.reader_name,
            preview_shape=tuple(int(v) for v in result.preview.data.shape),
            downsample=tuple(int(v) for v in result.downsample),
        )

    def as_lines(self) -> list[str]:
        return [
            f"Path: {self.path}",
            f"Reader: {self.reader_name}",
            f"Preview shape: {self.preview_shape[0]} samples x {self.preview_shape[1]} channels",
            f"Downsample: time_step={self.downsample[0]}, channel_step={self.downsample[1]}",
        ]

    def loaded_status(self) -> str:
        """Return a compact status bar summary."""

        return (
            f"Loaded: {self.reader_name} | "
            f"preview={self.preview_shape} | downsample={self.downsample}"
        )


@dataclass(frozen=True, slots=True)
class TaskControlState:
    """PyQt-free description of control availability during GUI tasks."""

    open_enabled: bool
    preview_controls_enabled: bool
    waveform_controls_enabled: bool
    cancel_enabled: bool
    progress_visible: bool
    progress_minimum: int
    progress_maximum: int


def task_control_state(is_running: bool) -> TaskControlState:
    """Return the control state for idle or running background tasks."""

    if is_running:
        return TaskControlState(
            open_enabled=False,
            preview_controls_enabled=False,
            waveform_controls_enabled=False,
            cancel_enabled=True,
            progress_visible=True,
            progress_minimum=0,
            progress_maximum=0,
        )
    return TaskControlState(
        open_enabled=True,
        preview_controls_enabled=True,
        waveform_controls_enabled=True,
        cancel_enabled=False,
        progress_visible=False,
        progress_minimum=0,
        progress_maximum=100,
    )


def format_task_status(task_name: str, state: str, message: str | None = None) -> str:
    """Return a compact status message for GUI background tasks."""

    normalized_task = str(task_name).strip().lower()
    labels = {
        "preview": "preview",
        "waveform": "waveform",
    }
    label = labels.get(normalized_task, normalized_task or "task")
    normalized_state = str(state).strip().lower()

    if normalized_state in {"loading", "running", "started"}:
        base = f"Loading {label}"
    elif normalized_state == "loaded":
        base = f"Loaded {label}"
    elif normalized_state == "cancelled":
        base = "Cancelled"
    elif normalized_state == "error":
        base = "Error"
    else:
        base = normalized_state.capitalize() if normalized_state else "Task"

    if message:
        return f"{base}: {message}"
    return base


def should_apply_task_result(
    *,
    task_id: int,
    active_task_id: int | None,
    was_cancelled: bool,
) -> bool:
    """Return whether a worker result still belongs to the active GUI task."""

    return active_task_id == task_id and not was_cancelled


def parse_preview_limits(max_samples: Any, max_channels: Any) -> PreviewLimits:
    """Validate preview limits before passing them to create_preview."""

    try:
        parsed_samples = int(max_samples)
        parsed_channels = int(max_channels)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_samples and max_channels must be integers") from exc
    if parsed_samples <= 0:
        raise ValueError("max_samples must be positive")
    if parsed_channels <= 0:
        raise ValueError("max_channels must be positive")
    return PreviewLimits(max_samples=parsed_samples, max_channels=parsed_channels)


def parse_channel_indices(text: str) -> tuple[int, ...]:
    """Parse comma-separated zero-based channel indices for waveform display.

    Duplicate channel indices are preserved intentionally so the GUI and tests
    reflect the user's requested order exactly.
    """

    if text is None:
        raise ValueError("channel input must not be empty")
    parts = [part.strip() for part in str(text).split(",")]
    if not parts or any(part == "" for part in parts):
        raise ValueError("channel input must contain one or more comma-separated integers")

    channels: list[int] = []
    for part in parts:
        try:
            value = int(part)
        except ValueError as exc:
            raise ValueError(f"channel index must be an integer: {part!r}") from exc
        if value < 0:
            raise ValueError("channel indices must be non-negative")
        channels.append(value)
    return tuple(channels)


def format_error_message(error: BaseException) -> str:
    """Return a concise error message suitable for status bars/dialogs."""

    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
