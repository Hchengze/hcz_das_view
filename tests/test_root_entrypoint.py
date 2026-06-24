from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys


ROOT_ENTRYPOINT = Path("das_view_main.py")


def test_root_gui_entrypoint_exists_and_is_path_safe():
    assert ROOT_ENTRYPOINT.exists()

    text = ROOT_ENTRYPOINT.read_text(encoding="utf-8")
    assert "das_view.gui.app import main" in text
    assert "E:\\HczDocument" not in text
    assert "BaiduSyncdisk" not in text
    assert "local_validation_paths" not in text


def test_root_gui_entrypoint_import_does_not_start_qt_event_loop():
    sys.modules.pop("PyQt5", None)

    spec = importlib.util.spec_from_file_location("das_view_main_import_smoke", ROOT_ENTRYPOINT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main
    assert "PyQt5" not in sys.modules


def test_root_gui_entrypoint_help_subprocess():
    result = subprocess.run(
        [sys.executable, str(ROOT_ENTRYPOINT), "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "HCZ DAS View GUI" in result.stdout


def test_module_gui_entrypoint_help_subprocess_still_works():
    result = subprocess.run(
        [sys.executable, "-m", "das_view.gui.app", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "HCZ DAS View GUI" in result.stdout
