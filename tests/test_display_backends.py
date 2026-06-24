import importlib
import sys

import pytest

from das_view.gui.display_backends import (
    format_display_backend_report,
    format_vispy_report,
    get_available_display_backends,
    get_vispy_info,
    is_pyqtgraph_available,
    is_pyopengl_available,
    is_vispy_available,
    select_display_backend,
    validate_vispy_backend,
)


def test_matplotlib_display_backend_is_always_available():
    info = select_display_backend("matplotlib")

    assert info.name == "matplotlib"
    assert info.available
    assert not info.experimental


def test_optional_display_backend_checks_do_not_crash():
    assert isinstance(is_pyqtgraph_available(), bool)
    assert isinstance(is_vispy_available(), bool)
    assert isinstance(is_pyopengl_available(), bool)
    infos = get_available_display_backends()
    assert {info.name for info in infos} == {"matplotlib", "pyqtgraph", "vispy"}


def test_select_pyqtgraph_backend_reports_readable_status():
    if is_pyqtgraph_available():
        info = select_display_backend("pyqtgraph")
        assert info.name == "pyqtgraph"
        assert info.available
        assert info.experimental
    else:
        with pytest.raises(ImportError, match="pyqtgraph"):
            select_display_backend("pyqtgraph")


def test_select_display_backend_rejects_unknown_name():
    with pytest.raises(ValueError, match="unsupported display backend"):
        select_display_backend("not-a-backend")


def test_format_display_backend_report_mentions_default_and_optional_backends():
    report = format_display_backend_report()

    assert "matplotlib" in report
    assert "pyqtgraph" in report
    assert "vispy" in report
    assert "Default backend: matplotlib" in report


def test_import_das_view_does_not_import_optional_display_packages():
    sys.modules.pop("das_view", None)
    sys.modules.pop("pyqtgraph", None)
    sys.modules.pop("vispy", None)
    sys.modules.pop("OpenGL", None)

    importlib.import_module("das_view")

    assert "pyqtgraph" not in sys.modules
    assert "vispy" not in sys.modules
    assert "OpenGL" not in sys.modules


def test_vispy_info_and_validation_return_dicts():
    info = get_vispy_info()
    validation = validate_vispy_backend()

    assert isinstance(info, dict)
    assert isinstance(validation, dict)
    assert info["backend"] == "vispy"
    assert validation["backend"] == "vispy"
    assert "status" in validation
    assert validation["context_tested"] is False


def test_vispy_report_mentions_default_and_deferred_integration():
    report = format_vispy_report()

    assert "VisPy / OpenGL capability" in report
    assert "default display backend: matplotlib" in report
    assert "deep VisPy/OpenGL GUI integration: deferred" in report


def test_vispy_context_probe_returns_clean_status():
    validation = validate_vispy_backend(test_context=True)

    assert isinstance(validation, dict)
    assert validation["status"] in {
        "unavailable",
        "pyopengl_unavailable",
        "importable",
        "context_unavailable",
        "context_available",
    }
    if validation["status"] in {"context_unavailable", "context_available"}:
        assert validation["context_tested"] is True
