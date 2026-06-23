"""Optional GUI display backend discovery.

This module is GUI-scoped by design. Optional display libraries are imported
only inside explicit detection/selection helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Literal

DisplayBackendName = Literal["matplotlib", "pyqtgraph", "vispy"]


@dataclass(frozen=True, slots=True)
class DisplayBackendInfo:
    """Availability report for one GUI display backend."""

    name: str
    available: bool
    version: str | None = None
    message: str = ""
    experimental: bool = False


def is_pyqtgraph_available() -> bool:
    """Return whether PyQtGraph imports cleanly."""

    try:
        import_module("pyqtgraph")
    except Exception:
        return False
    return True


def is_vispy_available() -> bool:
    """Return whether VisPy imports cleanly without creating an OpenGL context."""

    try:
        import_module("vispy")
    except Exception:
        return False
    return True


def get_available_display_backends() -> tuple[DisplayBackendInfo, ...]:
    """Return availability info for Matplotlib and optional display backends."""

    return (
        DisplayBackendInfo(
            name="matplotlib",
            available=True,
            message="Default stable Matplotlib display backend.",
            experimental=False,
        ),
        _optional_backend_info(
            "pyqtgraph",
            install_hint='Install with: pip install -e ".[display]"',
            experimental=True,
        ),
        _optional_backend_info(
            "vispy",
            install_hint='Install with: pip install -e ".[opengl]"',
            experimental=True,
        ),
    )


def select_display_backend(name: str = "matplotlib") -> DisplayBackendInfo:
    """Select a display backend or raise a readable error when unavailable."""

    normalized = _normalize_backend_name(name)
    for info in get_available_display_backends():
        if info.name == normalized:
            if info.available:
                return info
            raise ImportError(f"display backend {normalized!r} is unavailable: {info.message}")
    raise ValueError(f"unsupported display backend: {name!r}")


def format_display_backend_report() -> str:
    """Return a user-readable backend availability report."""

    lines = ["GUI display backends:"]
    for info in get_available_display_backends():
        status = "available" if info.available else "unavailable"
        suffix = " experimental" if info.experimental else ""
        version = f" version={info.version}" if info.version else ""
        message = f" - {info.message}" if info.message else ""
        lines.append(f"- {info.name}: {status}{suffix}{version}{message}")
    lines.append("Default backend: matplotlib")
    lines.append("VisPy/OpenGL context creation is not tested by default.")
    return "\n".join(lines)


def _optional_backend_info(
    name: DisplayBackendName,
    *,
    install_hint: str,
    experimental: bool,
) -> DisplayBackendInfo:
    try:
        module = import_module(name)
    except Exception as exc:
        return DisplayBackendInfo(
            name=name,
            available=False,
            message=f"{exc.__class__.__name__}: {exc}. {install_hint}",
            experimental=experimental,
        )
    version = getattr(module, "__version__", None)
    return DisplayBackendInfo(
        name=name,
        available=True,
        version=None if version is None else str(version),
        message="Optional backend is importable.",
        experimental=experimental,
    )


def _normalize_backend_name(name: str) -> DisplayBackendName:
    normalized = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    mapping: dict[str, DisplayBackendName] = {
        "matplotlib": "matplotlib",
        "mpl": "matplotlib",
        "pyqtgraph": "pyqtgraph",
        "pyqtgraph_experimental": "pyqtgraph",
        "vispy": "vispy",
        "opengl": "vispy",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported display backend: {name!r}") from exc
