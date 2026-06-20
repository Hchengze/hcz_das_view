"""Preview worker helpers for the optional PyQt5 GUI layer."""

from __future__ import annotations

from pathlib import Path

from das_view.io.preview import PreviewResult, create_preview


class PreviewWorker:
    """Thin callable wrapper around create_preview.

    The class intentionally contains no reader logic. It exists so the GUI can
    later move the same callable into QThread without changing file IO code.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_samples: int = 2000,
        max_channels: int = 500,
    ) -> None:
        self.path = Path(path)
        self.max_samples = int(max_samples)
        self.max_channels = int(max_channels)

    def run(self) -> PreviewResult:
        return create_preview(
            self.path,
            max_samples=self.max_samples,
            max_channels=self.max_channels,
        )
