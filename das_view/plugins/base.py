"""Base extension metadata containers.

The plugin layer is intentionally small: it describes optional extension
capabilities and their callable references, but it does not load data, start
GUI code, or replace the existing reader/service APIs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal


ExtensionKind = Literal["reader", "processing", "analysis", "plotting", "export", "gui"]
VALID_EXTENSION_KINDS: tuple[str, ...] = (
    "reader",
    "processing",
    "analysis",
    "plotting",
    "export",
    "gui",
)
CallableRef = Callable[..., Any] | str


@dataclass(frozen=True, slots=True)
class ExtensionMetadata:
    """User-facing metadata for a DAS View extension."""

    name: str
    kind: ExtensionKind
    version: str | None = None
    description: str | None = None
    provider: str | None = None
    module: str | None = None
    tags: Sequence[str] = field(default_factory=tuple)
    enabled: bool = True

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("ExtensionMetadata.name is required")
        if self.kind not in VALID_EXTENSION_KINDS:
            allowed = ", ".join(VALID_EXTENSION_KINDS)
            raise ValueError(f"Invalid extension kind {self.kind!r}; expected one of: {allowed}")
        tags = tuple(str(tag).strip() for tag in self.tags if str(tag).strip())
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "enabled", bool(self.enabled))

    @property
    def key(self) -> str:
        """Stable registry key."""

        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "version": self.version,
            "description": self.description,
            "provider": self.provider,
            "module": self.module,
            "tags": list(self.tags),
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExtensionMetadata":
        return cls(
            name=payload["name"],
            kind=payload["kind"],
            version=payload.get("version"),
            description=payload.get("description"),
            provider=payload.get("provider"),
            module=payload.get("module"),
            tags=payload.get("tags", ()),
            enabled=payload.get("enabled", True),
        )


def _validate_metadata_kind(metadata: ExtensionMetadata, expected: ExtensionKind) -> None:
    if metadata.kind != expected:
        raise ValueError(
            f"{type(metadata).__name__} kind {metadata.kind!r} does not match {expected!r}"
        )


@dataclass(frozen=True, slots=True)
class ReaderExtension:
    """Reader extension description.

    Callable fields may be direct callables or import-path strings. Keeping
    import-path strings is useful for lazy plugin loading.
    """

    metadata: ExtensionMetadata
    extensions: Sequence[str] = field(default_factory=tuple)
    can_read: CallableRef | None = None
    read_metadata: CallableRef | None = None
    read: CallableRef | None = None

    def __post_init__(self) -> None:
        _validate_metadata_kind(self.metadata, "reader")
        object.__setattr__(self, "extensions", tuple(self.extensions))


@dataclass(frozen=True, slots=True)
class ProcessingExtension:
    """Processing extension description."""

    metadata: ExtensionMetadata
    function: CallableRef | None = None
    parameters_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_metadata_kind(self.metadata, "processing")
        object.__setattr__(self, "parameters_schema", dict(self.parameters_schema))


@dataclass(frozen=True, slots=True)
class AnalysisExtension:
    """Analysis extension description."""

    metadata: ExtensionMetadata
    function: CallableRef | None = None
    input_kind: str | None = None
    output_kind: str | None = None
    parameters_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_metadata_kind(self.metadata, "analysis")
        object.__setattr__(self, "parameters_schema", dict(self.parameters_schema))


@dataclass(frozen=True, slots=True)
class PlottingExtension:
    """Plotting extension description."""

    metadata: ExtensionMetadata
    function: CallableRef | None = None
    input_kind: str | None = None
    parameters_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_metadata_kind(self.metadata, "plotting")
        object.__setattr__(self, "parameters_schema", dict(self.parameters_schema))


@dataclass(frozen=True, slots=True)
class ExportExtension:
    """Export extension description."""

    metadata: ExtensionMetadata
    function: CallableRef | None = None
    output_format: str | None = None
    parameters_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_metadata_kind(self.metadata, "export")
        object.__setattr__(self, "parameters_schema", dict(self.parameters_schema))
