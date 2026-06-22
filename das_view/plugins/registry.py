"""Extension registry and optional entry point discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any

from das_view.plugins.base import ExtensionMetadata, VALID_EXTENSION_KINDS


ExtensionObject = Any


def _metadata_for(extension: ExtensionObject) -> ExtensionMetadata:
    if isinstance(extension, ExtensionMetadata):
        return extension
    metadata = getattr(extension, "metadata", None)
    if isinstance(metadata, ExtensionMetadata):
        return metadata
    raise TypeError("extension must be ExtensionMetadata or expose ExtensionMetadata as .metadata")


@dataclass(slots=True)
class ExtensionDiscoveryResult:
    """Summary from optional Python entry point discovery."""

    registered: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[Any]]:
        return {
            "registered": list(self.registered),
            "failed": [dict(item) for item in self.failed],
        }


class ExtensionRegistry:
    """In-memory extension registry."""

    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionObject] = {}

    def register(self, extension: ExtensionObject, *, replace: bool = False) -> ExtensionObject:
        metadata = _metadata_for(extension)
        key = metadata.key
        if key in self._extensions and not replace:
            raise ValueError(f"Extension {key!r} is already registered")
        self._extensions[key] = extension
        return extension

    def unregister(self, name: str) -> ExtensionObject:
        key = str(name).strip()
        try:
            return self._extensions.pop(key)
        except KeyError as exc:
            raise KeyError(f"Extension {key!r} is not registered") from exc

    def get(self, name: str) -> ExtensionObject:
        key = str(name).strip()
        try:
            return self._extensions[key]
        except KeyError as exc:
            raise KeyError(f"Extension {key!r} is not registered") from exc

    def list(
        self,
        *,
        kind: str | None = None,
        enabled: bool | None = None,
    ) -> list[ExtensionObject]:
        if kind is not None and kind not in VALID_EXTENSION_KINDS:
            allowed = ", ".join(VALID_EXTENSION_KINDS)
            raise ValueError(f"Invalid extension kind {kind!r}; expected one of: {allowed}")
        items = list(self._extensions.values())
        if kind is not None:
            items = [item for item in items if _metadata_for(item).kind == kind]
        if enabled is not None:
            items = [item for item in items if _metadata_for(item).enabled is bool(enabled)]
        return sorted(items, key=lambda item: (_metadata_for(item).kind, _metadata_for(item).name))

    def clear(self) -> None:
        self._extensions.clear()

    def __len__(self) -> int:
        return len(self._extensions)


_GLOBAL_REGISTRY = ExtensionRegistry()


def get_global_registry() -> ExtensionRegistry:
    return _GLOBAL_REGISTRY


def register_extension(
    extension: ExtensionObject,
    *,
    registry: ExtensionRegistry | None = None,
    replace: bool = False,
) -> ExtensionObject:
    target = get_global_registry() if registry is None else registry
    return target.register(extension, replace=replace)


def unregister_extension(name: str, *, registry: ExtensionRegistry | None = None) -> ExtensionObject:
    target = get_global_registry() if registry is None else registry
    return target.unregister(name)


def list_extensions(
    *,
    registry: ExtensionRegistry | None = None,
    kind: str | None = None,
    enabled: bool | None = None,
) -> list[ExtensionObject]:
    target = get_global_registry() if registry is None else registry
    return target.list(kind=kind, enabled=enabled)


def get_extension(name: str, *, registry: ExtensionRegistry | None = None) -> ExtensionObject:
    target = get_global_registry() if registry is None else registry
    return target.get(name)


def clear_extensions(*, registry: ExtensionRegistry | None = None) -> None:
    target = get_global_registry() if registry is None else registry
    target.clear()


def _iter_entry_points(group: str):
    entry_points = importlib_metadata.entry_points()
    if hasattr(entry_points, "select"):
        return entry_points.select(group=group)
    return entry_points.get(group, ())


def _coerce_loaded_extensions(loaded: Any) -> list[ExtensionObject]:
    if loaded is None:
        return []
    if isinstance(loaded, (ExtensionMetadata,)) or hasattr(loaded, "metadata"):
        return [loaded]
    if callable(loaded):
        loaded = loaded()
    if isinstance(loaded, (ExtensionMetadata,)) or hasattr(loaded, "metadata"):
        return [loaded]
    return list(loaded)


def discover_entry_point_extensions(
    group: str = "das_view.plugins",
    *,
    registry: ExtensionRegistry | None = None,
    replace: bool = False,
) -> ExtensionDiscoveryResult:
    """Load optional extension entry points on demand.

    Discovery is never run at import time. Failures are collected in the result
    so a broken third-party plugin does not prevent the application from
    starting.
    """

    target = get_global_registry() if registry is None else registry
    result = ExtensionDiscoveryResult()
    for entry_point in _iter_entry_points(group):
        entry_name = getattr(entry_point, "name", "<unknown>")
        try:
            loaded = entry_point.load()
            for extension in _coerce_loaded_extensions(loaded):
                target.register(extension, replace=replace)
                result.registered.append(_metadata_for(extension).name)
        except Exception as exc:  # pragma: no cover - exercised by tests via fake entry point
            result.failed.append({"entry_point": str(entry_name), "error": str(exc)})
    return result
