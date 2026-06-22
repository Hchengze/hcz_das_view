"""Core data structures and package-wide definitions."""

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import (
    DASViewError,
    DataDimensionError,
    ReaderError,
    UnsupportedFormatError,
)
from das_view.core.metadata_format import (
    format_metadata,
    metadata_summary_lines,
    metadata_to_dict,
)

__all__ = [
    "DASData",
    "DASMetadata",
    "DASViewError",
    "DataDimensionError",
    "ReaderError",
    "UnsupportedFormatError",
    "format_metadata",
    "metadata_summary_lines",
    "metadata_to_dict",
]
