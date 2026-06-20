"""Minimal PyQt5 main window for DAS preview."""

from __future__ import annotations

from pathlib import Path

from das_view.core.metadata_format import format_metadata
from das_view.gui.models import (
    PreviewDisplayInfo,
    format_error_message,
    parse_preview_limits,
)
from das_view.gui.workers import PreviewWorker
from das_view.plotting.waterfall import plot_waterfall


def _qt_widgets():
    try:
        from PyQt5 import QtWidgets
    except ImportError as exc:
        raise ImportError("PyQt5 is required to use das_view.gui") from exc
    return QtWidgets


def _create_matplotlib_widgets(parent):
    try:
        from matplotlib.backends.backend_qt5agg import (
            FigureCanvasQTAgg,
            NavigationToolbar2QT,
        )
        from matplotlib.figure import Figure
    except ImportError as exc:
        raise ImportError("matplotlib with Qt5 backend is required to use das_view.gui") from exc

    figure = Figure(figsize=(7, 5))
    canvas = FigureCanvasQTAgg(figure)
    toolbar = NavigationToolbar2QT(canvas, parent)
    return figure, canvas, toolbar


class MainWindow(_qt_widgets().QMainWindow):
    """Small GUI that opens a file and displays metadata plus waterfall preview."""

    def __init__(self, *, max_samples: int = 2000, max_channels: int = 500) -> None:
        QtWidgets = _qt_widgets()
        super().__init__()
        self.max_samples = int(max_samples)
        self.max_channels = int(max_channels)
        self.setWindowTitle("DAS View")
        self.resize(1100, 750)

        self.file_info = QtWidgets.QPlainTextEdit()
        self.file_info.setReadOnly(True)
        self.file_info.setMaximumHeight(150)
        self.file_info.setPlainText("No file loaded.")

        self.max_samples_input = QtWidgets.QSpinBox()
        self.max_samples_input.setRange(1, 10_000_000)
        self.max_samples_input.setValue(self.max_samples)
        self.max_samples_input.setToolTip("Maximum time samples to read for preview")

        self.max_channels_input = QtWidgets.QSpinBox()
        self.max_channels_input.setRange(1, 1_000_000)
        self.max_channels_input.setValue(self.max_channels)
        self.max_channels_input.setToolTip("Maximum channels to read for preview")

        self.metadata_text = QtWidgets.QPlainTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setPlainText("Open a supported DAS file to view metadata.")

        self.figure, self.canvas, self.toolbar = _create_matplotlib_widgets(self)

        splitter = QtWidgets.QSplitter()
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("File information"))
        left_layout.addWidget(self.file_info)
        limits_layout = QtWidgets.QFormLayout()
        limits_layout.addRow("Max samples", self.max_samples_input)
        limits_layout.addRow("Max channels", self.max_channels_input)
        left_layout.addLayout(limits_layout)
        left_layout.addWidget(QtWidgets.QLabel("Metadata"))
        left_layout.addWidget(self.metadata_text)

        plot_panel = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout(plot_panel)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        splitter.addWidget(left_panel)
        splitter.addWidget(plot_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        self._build_menu()
        self.statusBar().showMessage("Ready")

    def open_file_dialog(self) -> None:
        QtWidgets = _qt_widgets()
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open DAS file",
            "",
            "DAS files (*.h5 *.hdf5 *.dat);;All files (*)",
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str | Path) -> None:
        """Load a file preview through the preview service."""

        self.statusBar().showMessage("Loading")
        self.file_info.setPlainText(f"Path: {path}\nLoading preview...")
        self.metadata_text.setPlainText("")
        self._clear_figure()
        try:
            limits = parse_preview_limits(
                self.max_samples_input.value(),
                self.max_channels_input.value(),
            )
            result = PreviewWorker(
                path,
                max_samples=limits.max_samples,
                max_channels=limits.max_channels,
            ).run()
            display = PreviewDisplayInfo.from_preview_result(result)
            lines = display.as_lines()
            lines.extend(f"Warning: {warning}" for warning in result.warnings)
            self.file_info.setPlainText("\n".join(lines))
            self.metadata_text.setPlainText(format_metadata(result.metadata))
            self._draw_preview(result.preview)
            self.statusBar().showMessage(display.loaded_status())
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.file_info.setPlainText(f"Path: {path}\nError: {message}")
            self.metadata_text.setPlainText(f"Failed to load preview.\n\n{message}")
            self._clear_figure()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View error", message)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        open_action = file_menu.addAction("&Open File")
        open_action.triggered.connect(self.open_file_dialog)
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

    def _clear_figure(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("No preview loaded")
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw_idle()

    def _draw_preview(self, preview_data) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        plot_waterfall(preview_data, ax=ax)
        self.figure.tight_layout()
        self.canvas.draw_idle()
