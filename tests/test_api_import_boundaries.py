import importlib
import sys


def _drop_pyqt5_modules():
    for name in list(sys.modules):
        if name == "PyQt5" or name.startswith("PyQt5."):
            sys.modules.pop(name, None)


def _import_without_pyqt5(module_name):
    _drop_pyqt5_modules()
    module = importlib.import_module(module_name)
    assert "PyQt5" not in sys.modules
    return module


def test_core_package_imports_do_not_import_pyqt5():
    for module_name in [
        "das_view",
        "das_view.io",
        "das_view.processing",
        "das_view.analysis",
        "das_view.plotting",
        "das_view.plugins",
    ]:
        _import_without_pyqt5(module_name)


def test_import_das_view_does_not_trigger_plugin_entry_point_discovery(monkeypatch):
    import importlib.metadata as metadata

    def fail_if_called(*args, **kwargs):
        raise AssertionError("entry point discovery should not run during import das_view")

    monkeypatch.setattr(metadata, "entry_points", fail_if_called)
    sys.modules.pop("das_view", None)

    importlib.import_module("das_view")


def test_import_das_view_does_not_read_data_files(monkeypatch):
    from pathlib import Path

    original_open = Path.open
    attempted_data_paths = []

    def guarded_open(self, *args, **kwargs):
        suffix = self.suffix.lower()
        if suffix in {".h5", ".hdf5", ".dat"}:
            attempted_data_paths.append(str(self))
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    sys.modules.pop("das_view", None)

    importlib.import_module("das_view")

    assert attempted_data_paths == []


def test_public_core_api_imports_from_top_level():
    import das_view

    assert das_view.DASData
    assert das_view.DASMetadata
    assert das_view.DASViewError
    assert das_view.ReaderError
    assert das_view.UnsupportedFormatError


def test_cli_module_imports_do_not_start_gui_event_loop():
    _drop_pyqt5_modules()
    for module_name in [
        "das_view.cli.validate",
        "das_view.cli.preview",
        "das_view.cli.statistics",
        "das_view.cli.spectrum",
        "das_view.cli.events",
        "das_view.cli.extensions",
        "das_view.cli.qc",
    ]:
        module = importlib.import_module(module_name)
        assert callable(module.main)
    assert "PyQt5" not in sys.modules


def test_gui_app_help_does_not_start_qt_event_loop(capsys):
    _drop_pyqt5_modules()
    module = importlib.import_module("das_view.gui.app")

    assert module.main(["hcz-das-view", "--help"]) == 0

    assert "usage:" in capsys.readouterr().out
    assert "PyQt5" not in sys.modules
