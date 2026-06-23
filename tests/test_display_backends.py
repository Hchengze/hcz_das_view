import importlib
import sys

import pytest

from das_view.gui.display_backends import (
    format_display_backend_report,
    get_available_display_backends,
    is_pyqtgraph_available,
    is_vispy_available,
    select_display_backend,
)


def test_matplotlib_display_backend_is_always_available():
    info = select_display_backend("matplotlib")

    assert info.name == "matplotlib"
    assert info.available
    assert not info.experimental


def test_optional_display_backend_checks_do_not_crash():
    assert isinstance(is_pyqtgraph_available(), bool)
    assert isinstance(is_vispy_available(), bool)
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

    importlib.import_module("das_view")

    assert "pyqtgraph" not in sys.modules
    assert "vispy" not in sys.modules
