import pytest

from das_view.gui.models import PreviewDisplayInfo, format_error_message


def test_gui_display_info_and_error_formatting_are_pyqt_free():
    class Result:
        reader_name = "synthetic"
        downsample = (2, 3)

        class metadata:
            source_path = "sample.h5"

        class preview:
            class data:
                shape = (10, 4)

    info = PreviewDisplayInfo.from_preview_result(Result())

    assert info.preview_shape == (10, 4)
    assert "synthetic" in "\n".join(info.as_lines())
    assert format_error_message(ValueError("bad file")) == "ValueError: bad file"


def test_main_window_can_be_created_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    assert window.windowTitle() == "DAS View"
    assert window.statusBar().currentMessage() == "Ready"
    window.close()
    app.processEvents()
