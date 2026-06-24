import importlib
import sys

import pytest

from das_view.gui import i18n


def test_gui_i18n_default_language_is_chinese():
    assert i18n.get_default_language() == "zh_CN"
    assert "zh_CN" in i18n.get_supported_languages()
    assert "en_US" in i18n.get_supported_languages()
    assert i18n.translate("open_file", "zh_CN") == "打开文件"
    assert i18n.translate("open_file", "en_US") == "Open File"


def test_gui_i18n_key_coverage_and_fallback():
    required = [
        "open_file",
        "waterfall",
        "waveform",
        "spectrum",
        "analysis",
        "display_backend",
        "axis_mode",
        "axis_channel",
        "axis_distance",
        "qc_report",
        "denoise_report",
        "moveout_summary",
        "directional_energy",
    ]
    for key in required:
        assert i18n.translate(key, "zh_CN")
        assert i18n.translate(key, "en_US")
    assert i18n.translate("missing.key", "zh_CN") == "missing.key"


def test_gui_i18n_rejects_unknown_language():
    with pytest.raises(ValueError, match="unsupported GUI language"):
        i18n.set_language("fr_FR")


def test_gui_models_import_does_not_import_pyqt5():
    for name in list(sys.modules):
        if name == "PyQt5" or name.startswith("PyQt5."):
            sys.modules.pop(name, None)
    importlib.import_module("das_view.gui.models")
    assert "PyQt5" not in sys.modules
