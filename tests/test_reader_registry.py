from pathlib import Path

import numpy as np

from das_view.core.data_model import DASData, DASMetadata
from das_view.io.base import BaseDASReader
from das_view.io.registry import ReaderRegistry


class DummyReader(BaseDASReader):
    name = "dummy"
    supported_extensions = (".dummy",)

    def read_metadata(self, path):
        return DASMetadata(n_samples=2, n_channels=2, source_path=path, source_format=self.name)

    def read(self, path):
        return DASData(data=np.zeros((2, 2)), metadata=self.read_metadata(path))


def test_registry_registers_and_selects_reader():
    registry = ReaderRegistry()
    reader = DummyReader()

    registry.register(reader)

    assert registry.get_reader(Path("x.dummy")) is reader
    assert registry.read("x.dummy").data.shape == (2, 2)
