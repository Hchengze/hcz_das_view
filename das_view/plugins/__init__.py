"""Lightweight extension metadata and registry helpers."""

from das_view.plugins.base import (
    AnalysisExtension,
    ExportExtension,
    ExtensionMetadata,
    PlottingExtension,
    ProcessingExtension,
    ReaderExtension,
    VALID_EXTENSION_KINDS,
)
from das_view.plugins.builtins import list_builtin_extensions, register_builtin_extensions
from das_view.plugins.registry import (
    ExtensionDiscoveryResult,
    ExtensionRegistry,
    clear_extensions,
    discover_entry_point_extensions,
    get_extension,
    get_global_registry,
    list_extensions,
    register_extension,
    unregister_extension,
)

__all__ = [
    "AnalysisExtension",
    "ExportExtension",
    "ExtensionDiscoveryResult",
    "ExtensionMetadata",
    "ExtensionRegistry",
    "PlottingExtension",
    "ProcessingExtension",
    "ReaderExtension",
    "VALID_EXTENSION_KINDS",
    "clear_extensions",
    "discover_entry_point_extensions",
    "get_extension",
    "get_global_registry",
    "list_builtin_extensions",
    "list_extensions",
    "register_builtin_extensions",
    "register_extension",
    "unregister_extension",
]
