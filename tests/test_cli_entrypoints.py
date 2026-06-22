import importlib

import pytest


CLI_MODULES = [
    "das_view.cli.validate",
    "das_view.cli.preview",
    "das_view.cli.statistics",
    "das_view.cli.spectrum",
    "das_view.cli.events",
    "das_view.cli.extensions",
    "das_view.cli.qc",
]


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_cli_modules_import_and_expose_main(module_name):
    module = importlib.import_module(module_name)

    assert callable(module.main)
    assert callable(module.build_parser)


@pytest.mark.parametrize("module_name", CLI_MODULES)
def test_cli_main_help_exits_cleanly(module_name, capsys):
    module = importlib.import_module(module_name)

    with pytest.raises(SystemExit) as excinfo:
        module.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "usage:" in output


def test_gui_app_imports_and_help_does_not_require_qt_event_loop(capsys):
    module = importlib.import_module("das_view.gui.app")

    assert callable(module.main)
    assert module.main(["hcz-das-view", "--help"]) == 0
    output = capsys.readouterr().out
    assert "usage:" in output
    assert "hcz-das-view" in output


def test_gui_main_window_smoke_skips_cleanly_without_pyqt5():
    pytest.importorskip("PyQt5")

    from das_view.gui.app import main

    assert callable(main)
