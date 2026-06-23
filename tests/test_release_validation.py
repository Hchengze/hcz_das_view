import importlib
import json
import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(".")
PYPROJECT = ROOT / "pyproject.toml"
NOTEBOOK = ROOT / "docs" / "09_tutorial_user_manual.ipynb"


def _pyproject():
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_release_metadata_and_entrypoints_are_declared():
    project = _pyproject()["project"]

    assert project["name"] == "hcz-das-view"
    assert project["version"]
    assert project["readme"] == "README.md"
    assert project["requires-python"].startswith(">=")
    assert {"numpy", "scipy"}.issubset(set(project["dependencies"]))
    assert {"gui", "dev", "packaging"}.issubset(project["optional-dependencies"])

    assert set(project["scripts"]) >= {
        "hcz-das-validate",
        "hcz-das-preview",
        "hcz-das-stats",
        "hcz-das-spectrum",
        "hcz-das-events",
        "hcz-das-extensions",
        "hcz-das-qc",
        "hcz-das-denoise",
        "hcz-das-moveout",
        "hcz-das-gpu",
    }
    assert project["gui-scripts"]["hcz-das-view"] == "das_view.gui.app:main"


def test_package_import_does_not_pull_in_pyqt5():
    sys.modules.pop("PyQt5", None)

    importlib.import_module("das_view")

    assert "PyQt5" not in sys.modules


@pytest.mark.parametrize(
    "module_name",
    [
        "das_view.cli.validate",
        "das_view.cli.preview",
        "das_view.cli.statistics",
        "das_view.cli.spectrum",
        "das_view.cli.events",
        "das_view.cli.extensions",
        "das_view.cli.qc",
        "das_view.cli.denoise",
        "das_view.cli.moveout",
        "das_view.cli.gpu",
    ],
)
def test_cli_modules_have_help_smoke(module_name, capsys):
    module = importlib.import_module(module_name)

    assert callable(module.main)
    assert callable(module.build_parser)
    with pytest.raises(SystemExit) as excinfo:
        module.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_gui_help_does_not_start_qt_event_loop(capsys):
    app = importlib.import_module("das_view.gui.app")

    assert app.main(["hcz-das-view", "--help"]) == 0
    output = capsys.readouterr().out
    assert "usage:" in output
    assert "hcz-das-view" in output


def test_packaging_files_are_relative_and_data_free():
    paths = [
        Path("packaging/README_windows_packaging.md"),
        Path("packaging/build_windows.ps1"),
        Path("packaging/hcz_das_view.spec"),
    ]

    for path in paths:
        assert path.exists()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    forbidden = [
        "E:\\",
        "HczDocument",
        "validation_outputs\\",
        "outputs\\",
        "*.h5",
        "*.hdf5",
        "*.dat",
    ]
    for needle in forbidden:
        assert needle not in combined
    assert "build/" in combined
    assert "dist/" in combined


def test_gitignore_covers_release_artifacts():
    text = Path(".gitignore").read_text(encoding="utf-8")

    for pattern in [
        "build/",
        "dist/",
        "*.egg-info/",
        "*.exe",
        "*.whl",
        "*.tar.gz",
        ".tmp_release_venv/",
        "release_validation_outputs/",
    ]:
        assert pattern in text


def test_tutorial_notebook_release_sections_are_user_facing():
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    text = "\n".join(
        "".join(cell.get("source", []))
        for cell in payload["cells"]
    )

    for keyword in [
        "Installation",
        "editable install",
        "Command-line entry points",
        "GUI launch",
        "examples/",
        "Windows packaging",
        "PyInstaller",
        "Release usage notes",
    ]:
        assert keyword in text

    forbidden = [
        "E:\\HczDocument",
        "development log",
        "commit",
        "test session starts",
        " passed in ",
        " failed in ",
    ]
    for needle in forbidden:
        assert needle.lower() not in text.lower()
