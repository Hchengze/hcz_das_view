"""Reader registry for DAS formats."""

from __future__ import annotations

from pathlib import Path

from das_view.core.exceptions import UnsupportedFormatError
from das_view.io.base import BaseDASReader


class ReaderRegistry:
    """Small registry that selects a reader for a path."""

    def __init__(self) -> None:
        self._readers: list[BaseDASReader] = []

    def register(self, reader: BaseDASReader) -> None:
        if not isinstance(reader, BaseDASReader):
            raise TypeError("reader must be an instance of BaseDASReader")
        self._readers.append(reader)

    def readers(self) -> tuple[BaseDASReader, ...]:
        return tuple(self._readers)

    def get_reader(self, path: str | Path) -> BaseDASReader:
        for reader in self._readers:
            if reader.can_read(path):
                return reader
        raise UnsupportedFormatError(f"No registered DAS reader can read: {path}")

    def read(self, path: str | Path):
        return self.get_reader(path).read(path)


def default_registry() -> ReaderRegistry:
    """Create a registry with baseline first-priority readers."""

    from das_view.io.hdf5_zd import ZDHDF5Reader
    from das_view.io.puniu_dat import PuniuDATReader

    registry = ReaderRegistry()
    registry.register(ZDHDF5Reader())
    registry.register(PuniuDATReader())
    return registry
