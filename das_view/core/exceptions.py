"""Project-specific exceptions."""


class DASViewError(Exception):
    """Base exception for das_view."""


class DataDimensionError(DASViewError, ValueError):
    """Raised when data does not follow the internal dimension convention."""


class ReaderError(DASViewError):
    """Raised when a DAS reader cannot read a source safely."""


class UnsupportedFormatError(ReaderError):
    """Raised when no reader supports a source."""
