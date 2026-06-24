import importlib
import sys

from das_view.gui.display_backends import (
    format_vispy_report,
    get_vispy_info,
    is_pyopengl_available,
    is_vispy_available,
    select_display_backend,
    validate_vispy_backend,
)


def test_vispy_availability_checks_do_not_crash():
    assert isinstance(is_vispy_available(), bool)
    assert isinstance(is_pyopengl_available(), bool)


def test_validate_vispy_backend_import_only_status():
    result = validate_vispy_backend()

    assert result["backend"] == "vispy"
    assert result["context_tested"] is False
    assert result["status"] in {
        "unavailable",
        "pyopengl_unavailable",
        "importable",
    }


def test_validate_vispy_backend_context_probe_is_safe():
    result = validate_vispy_backend(test_context=True)

    assert result["backend"] == "vispy"
    assert result["status"] in {
        "unavailable",
        "pyopengl_unavailable",
        "importable",
        "context_unavailable",
        "context_available",
    }
    if result["status"] in {"context_unavailable", "context_available"}:
        assert result["context_tested"] is True
        assert isinstance(result["context_available"], bool)


def test_get_vispy_info_contains_versions_and_hint():
    info = get_vispy_info()

    assert "vispy_version" in info
    assert "pyopengl_version" in info
    assert "installation_hint" in info


def test_format_vispy_report_is_user_readable():
    report = format_vispy_report()

    assert "VisPy / OpenGL capability" in report
    assert "vispy available" in report
    assert "PyOpenGL available" in report
    assert "default display backend: matplotlib" in report


def test_import_das_view_does_not_import_vispy_or_pyopengl():
    sys.modules.pop("das_view", None)
    sys.modules.pop("vispy", None)
    sys.modules.pop("OpenGL", None)

    importlib.import_module("das_view")

    assert "vispy" not in sys.modules
    assert "OpenGL" not in sys.modules


def test_matplotlib_and_pyqtgraph_backend_paths_remain_independent():
    matplotlib_info = select_display_backend("matplotlib")

    assert matplotlib_info.name == "matplotlib"
    assert matplotlib_info.available
