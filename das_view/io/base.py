"""Base interfaces for DAS readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from das_view.core.data_model import DASData, DASMetadata


class BaseDASReader(ABC):
    """Abstract base class for DAS data readers."""

    name: str = "base"
    supported_extensions: tuple[str, ...] = ()

    def can_read(self, path: str | Path) -> bool:
        suffix = Path(path).suffix.lower()
        return suffix in self.supported_extensions

    @abstractmethod
    def read_metadata(self, path: str | Path) -> DASMetadata:
        """Read metadata without necessarily loading the full data matrix."""

    @abstractmethod
    def read(self, path: str | Path) -> DASData:
        """Read data and metadata using the internal shape convention."""
