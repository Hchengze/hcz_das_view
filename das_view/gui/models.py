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


def format_error_message(error: BaseException) -> str:
    """Return a concise error message suitable for status bars/dialogs."""

    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
