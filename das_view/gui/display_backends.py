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


def is_pyopengl_available() -> bool:
    """Return whether PyOpenGL imports cleanly."""

    try:
        import_module("OpenGL")
    except Exception:
        return False
    return True


def get_vispy_info() -> dict[str, object]:
    """Return lazy VisPy/PyOpenGL import information without opening a context."""

    info: dict[str, object] = {
        "backend": "vispy",
        "available": False,
        "vispy_available": False,
        "pyopengl_available": False,
        "vispy_version": None,
        "pyopengl_version": None,
        "status": "unavailable",
        "message": "",
        "context_tested": False,
        "context_available": None,
        "installation_hint": 'Install with: pip install -e ".[opengl]"',
    }

    try:
        vispy = import_module("vispy")
    except Exception as exc:
        info["message"] = f"VisPy import failed: {exc.__class__.__name__}: {exc}"
        return info

    info["vispy_available"] = True
    info["vispy_version"] = _module_version(vispy)

    try:
        opengl = import_module("OpenGL")
    except Exception as exc:
        info["status"] = "pyopengl_unavailable"
        info["message"] = f"PyOpenGL import failed: {exc.__class__.__name__}: {exc}"
        return info

    info["pyopengl_available"] = True
    info["pyopengl_version"] = _module_version(opengl)
    info["available"] = True
    info["status"] = "importable"
    info["message"] = "VisPy and PyOpenGL are importable; OpenGL context not tested."
    return info


def validate_vispy_backend(*, test_context: bool = False) -> dict[str, object]:
    """Validate optional VisPy capability without requiring a headless context.

    The default validation is import-only. Set ``test_context=True`` for a
    minimal canvas context probe; failures are returned as status dictionaries
    rather than raised so CI/headless runs can skip cleanly.
    """

    info = get_vispy_info()
    if not info["available"]:
        return info

    if not test_context:
        return info

    info = dict(info)
    info["context_tested"] = True
    try:
        scene = import_module("vispy.scene")
        canvas = scene.SceneCanvas(show=False, size=(16, 16))
        canvas.close()
    except Exception as exc:
        info["context_available"] = False
        info["status"] = "context_unavailable"
        info["message"] = (
            f"VisPy imports, but a minimal OpenGL context is unavailable: "
            f"{exc.__class__.__name__}: {exc}"
        )
        return info

    info["context_available"] = True
    info["status"] = "context_available"
    info["message"] = "VisPy imports and a minimal SceneCanvas context was created."
    return info


def format_vispy_report(*, test_context: bool = False) -> str:
    """Return a user-readable VisPy/OpenGL capability report."""

    info = validate_vispy_backend(test_context=test_context)
    lines = [
        "VisPy / OpenGL capability:",
        f"- status: {info['status']}",
        f"- vispy available: {info['vispy_available']}",
        f"- vispy version: {info['vispy_version'] or 'unknown'}",
        f"- PyOpenGL available: {info['pyopengl_available']}",
        f"- PyOpenGL version: {info['pyopengl_version'] or 'unknown'}",
        f"- OpenGL context tested: {info['context_tested']}",
        f"- OpenGL context available: {info['context_available']}",
        f"- message: {info['message']}",
        "- default display backend: matplotlib",
        "- deep VisPy/OpenGL GUI integration: deferred",
    ]
    return "\n".join(lines)


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


def _module_version(module: object) -> str | None:
    version = getattr(module, "__version__", None)
    return None if version is None else str(version)


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
    return DisplayBackendInfo(
        name=name,
        available=True,
        version=_module_version(module),
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
