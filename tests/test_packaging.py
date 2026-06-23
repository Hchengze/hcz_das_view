import importlib
import sys
import tomllib
from pathlib import Path


PYPROJECT = Path("pyproject.toml")


def load_pyproject():
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_pyproject_has_build_system_and_project_metadata():
    payload = load_pyproject()

    assert "build-system" in payload
    project = payload["project"]
    assert project["name"] == "hcz-das-view"
    assert project["version"]
    assert project["description"]
    assert project["requires-python"]
    assert project["dependencies"]


def test_pyproject_has_optional_dependencies_and_entrypoints():
    project = load_pyproject()["project"]

    optional = project["optional-dependencies"]
    assert "gui" in optional
    assert "dev" in optional
    assert "packaging" in optional
    assert "PyQt5" in optional["gui"]
    assert "build" in optional["packaging"]
    assert "pyinstaller" in {value.lower() for value in optional["packaging"]}

    scripts = project["scripts"]
    assert scripts["hcz-das-validate"] == "das_view.cli.validate:main"
    assert scripts["hcz-das-preview"] == "das_view.cli.preview:main"
    assert scripts["hcz-das-stats"] == "das_view.cli.statistics:main"
    assert scripts["hcz-das-spectrum"] == "das_view.cli.spectrum:main"
    assert scripts["hcz-das-events"] == "das_view.cli.events:main"
    assert scripts["hcz-das-extensions"] == "das_view.cli.extensions:main"
    assert scripts["hcz-das-qc"] == "das_view.cli.qc:main"
    assert scripts["hcz-das-denoise"] == "das_view.cli.denoise:main"

    assert project["entry-points"]["das_view.plugins"][
        "hcz_das_view_builtins"
    ] == "das_view.plugins.builtins:list_builtin_extensions"

    gui_scripts = project["gui-scripts"]
    assert gui_scripts["hcz-das-view"] == "das_view.gui.app:main"


def test_package_import_does_not_import_pyqt5_when_not_already_loaded():
    already_loaded = "PyQt5" in sys.modules

    importlib.import_module("das_view")

    if not already_loaded:
        assert "PyQt5" not in sys.modules


def test_packaging_files_exist_and_do_not_use_local_absolute_paths():
    readme = Path("packaging/README_windows_packaging.md")
    script = Path("packaging/build_windows.ps1")
    spec = Path("packaging/hcz_das_view.spec")

    assert readme.exists()
    assert script.exists()
    assert spec.exists()
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (readme, script, spec)
    )
    assert "E:\\HczDocument" not in combined
    assert "local_validation_paths.txt" in combined
