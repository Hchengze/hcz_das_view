import pytest


def test_main_window_key_tooltips_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    assert window.open_action.toolTip()
    assert window.display_backend_combo.toolTip()
    assert window.waterfall_axis_mode_combo.toolTip()
    assert window.analysis_run_button.toolTip()
    assert window.analysis_export_json_button.toolTip()
    assert window.analysis_export_csv_button.toolTip()
    assert window.language_combo.toolTip()
    assert "辅助属性" in window.analysis_type_combo.itemData(
        window.analysis_type_combo.findData("moveout_summary"),
        3,
    )

    window.close()
    app.processEvents()
