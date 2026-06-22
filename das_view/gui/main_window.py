"""Minimal PyQt5 main window for DAS preview."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from das_view.core.metadata_format import format_metadata
from das_view.gui.models import (
    PreviewDisplayInfo,
    format_error_message,
    format_fk_status,
    format_spectrum_status,
    format_task_status,
    parse_channel_indices,
    parse_fk_request,
    parse_preview_limits,
    parse_spectrum_request,
    should_apply_task_result,
    task_control_state,
)
from das_view.gui.workers import QtFKWorker, QtPreviewWorker, QtSpectrumWorker, QtWaveformWorker
from das_view.plotting.fk import plot_fk, plot_fk_mask
from das_view.plotting.spectra import plot_psd, plot_spectrogram, plot_spectrum
from das_view.plotting.waterfall import plot_waterfall
from das_view.plotting.waveform import plot_waveform


def _qt_widgets():
    try:
        from PyQt5 import QtWidgets
    except ImportError as exc:
        raise ImportError("PyQt5 is required to use das_view.gui") from exc
    return QtWidgets


def _qt_core():
    try:
        from PyQt5 import QtCore
    except ImportError as exc:
        raise ImportError("PyQt5 is required to use das_view.gui") from exc
    return QtCore


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
        self.current_path: Path | None = None
        self._task_thread: Any | None = None
        self._task_worker: Any | None = None
        self._active_task_id: int | None = None
        self._next_task_id = 0
        self._task_cancel_requested = False
        self._task_kind: str | None = None
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
        self.waveform_figure, self.waveform_canvas, self.waveform_toolbar = (
            _create_matplotlib_widgets(self)
        )
        self.spectrum_figure, self.spectrum_canvas, self.spectrum_toolbar = (
            _create_matplotlib_widgets(self)
        )
        self.fk_figure, self.fk_canvas, self.fk_toolbar = _create_matplotlib_widgets(self)

        self.waveform_channel_input = QtWidgets.QLineEdit("0")
        self.waveform_channel_input.setToolTip("Zero-based channel index, e.g. 10 or 10,20,30")
        self.waveform_time_step_input = QtWidgets.QSpinBox()
        self.waveform_time_step_input.setRange(1, 10_000_000)
        self.waveform_time_step_input.setValue(1)
        self.waveform_time_step_input.setToolTip("Time downsampling step for waveform read")
        self.waveform_button = QtWidgets.QPushButton("Plot waveform")
        self.waveform_button.clicked.connect(self.load_waveform)
        self.waveform_info = QtWidgets.QPlainTextEdit()
        self.waveform_info.setReadOnly(True)
        self.waveform_info.setMaximumHeight(120)
        self.waveform_info.setPlainText("Load a file, then plot one or more channels.")

        self.spectrum_channel_input = QtWidgets.QLineEdit("0")
        self.spectrum_channel_input.setToolTip("Zero-based single channel index")
        self.spectrum_type_combo = QtWidgets.QComboBox()
        self.spectrum_type_combo.addItem("Amplitude spectrum", "amplitude")
        self.spectrum_type_combo.addItem("Power spectrum", "power")
        self.spectrum_type_combo.addItem("PSD periodogram", "psd_periodogram")
        self.spectrum_type_combo.addItem("PSD Welch", "psd_welch")
        self.spectrum_type_combo.addItem("Spectrogram", "spectrogram")
        self.spectrum_nfft_input = QtWidgets.QLineEdit("")
        self.spectrum_nfft_input.setToolTip("Optional positive nfft; blank means auto")
        self.spectrum_nperseg_input = QtWidgets.QLineEdit("256")
        self.spectrum_nperseg_input.setToolTip("Optional positive segment length; blank means 256")
        self.spectrum_noverlap_input = QtWidgets.QLineEdit("")
        self.spectrum_noverlap_input.setToolTip("Optional non-negative overlap; blank means auto")
        self.spectrum_db_checkbox = QtWidgets.QCheckBox("PSD in dB")
        self.spectrum_button = QtWidgets.QPushButton("Run spectrum")
        self.spectrum_button.clicked.connect(self.load_spectrum)
        self.spectrum_info = QtWidgets.QPlainTextEdit()
        self.spectrum_info.setReadOnly(True)
        self.spectrum_info.setMaximumHeight(140)
        self.spectrum_info.setPlainText("Load a file, then run a single-channel spectrum analysis.")

        self.fk_time_start_input = QtWidgets.QLineEdit("")
        self.fk_time_start_input.setToolTip("Optional zero-based start sample; blank means 0")
        self.fk_time_stop_input = QtWidgets.QLineEdit("")
        self.fk_time_stop_input.setToolTip("Optional stop sample; blank means start + max samples")
        self.fk_time_step_input = QtWidgets.QSpinBox()
        self.fk_time_step_input.setRange(1, 10_000_000)
        self.fk_time_step_input.setValue(1)
        self.fk_channel_start_input = QtWidgets.QLineEdit("")
        self.fk_channel_start_input.setToolTip("Optional zero-based start channel; blank means 0")
        self.fk_channel_stop_input = QtWidgets.QLineEdit("")
        self.fk_channel_stop_input.setToolTip("Optional stop channel; blank means start + max channels")
        self.fk_channel_step_input = QtWidgets.QSpinBox()
        self.fk_channel_step_input.setRange(1, 1_000_000)
        self.fk_channel_step_input.setValue(1)
        self.fk_mode_combo = QtWidgets.QComboBox()
        self.fk_mode_combo.addItem("FK transform", "transform")
        self.fk_mode_combo.addItem("FK velocity filter", "velocity_filter")
        self.fk_output_combo = QtWidgets.QComboBox()
        self.fk_output_combo.addItem("Amplitude", "amplitude")
        self.fk_output_combo.addItem("Power", "power")
        self.fk_db_checkbox = QtWidgets.QCheckBox("Display in dB")
        self.fk_vmin_input = QtWidgets.QLineEdit("")
        self.fk_vmin_input.setToolTip("Minimum apparent velocity in m/s for velocity-filter mode; optional for transform mode")
        self.fk_vmax_input = QtWidgets.QLineEdit("")
        self.fk_vmax_input.setToolTip("Maximum apparent velocity in m/s for velocity-filter mode; optional for transform mode")
        self.fk_pass_inside_checkbox = QtWidgets.QCheckBox("Pass velocity range (unchecked = reject range)")
        self.fk_pass_inside_checkbox.setChecked(True)
        self.fk_button = QtWidgets.QPushButton("Run FK")
        self.fk_button.clicked.connect(self.load_fk)
        self.fk_info = QtWidgets.QPlainTextEdit()
        self.fk_info.setReadOnly(True)
        self.fk_info.setMaximumHeight(150)
        self.fk_info.setPlainText("Load a file, then run a bounded FK task.")

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_active_task)

        splitter = QtWidgets.QSplitter()
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("File information"))
        left_layout.addWidget(self.file_info)
        limits_layout = QtWidgets.QFormLayout()
        limits_layout.addRow("Max samples", self.max_samples_input)
        limits_layout.addRow("Max channels", self.max_channels_input)
        left_layout.addLayout(limits_layout)
        task_layout = QtWidgets.QHBoxLayout()
        task_layout.addWidget(self.progress_bar)
        task_layout.addWidget(self.cancel_button)
        left_layout.addLayout(task_layout)
        left_layout.addWidget(QtWidgets.QLabel("Metadata"))
        left_layout.addWidget(self.metadata_text)

        waterfall_panel = QtWidgets.QWidget()
        waterfall_layout = QtWidgets.QVBoxLayout(waterfall_panel)
        waterfall_layout.addWidget(self.toolbar)
        waterfall_layout.addWidget(self.canvas)

        waveform_panel = QtWidgets.QWidget()
        waveform_layout = QtWidgets.QVBoxLayout(waveform_panel)
        waveform_controls = QtWidgets.QFormLayout()
        waveform_controls.addRow("Channel index", self.waveform_channel_input)
        waveform_controls.addRow("Time step", self.waveform_time_step_input)
        waveform_layout.addLayout(waveform_controls)
        waveform_layout.addWidget(self.waveform_button)
        waveform_layout.addWidget(self.waveform_info)
        waveform_layout.addWidget(self.waveform_toolbar)
        waveform_layout.addWidget(self.waveform_canvas)

        spectrum_panel = QtWidgets.QWidget()
        spectrum_layout = QtWidgets.QVBoxLayout(spectrum_panel)
        spectrum_controls = QtWidgets.QFormLayout()
        spectrum_controls.addRow("Channel index", self.spectrum_channel_input)
        spectrum_controls.addRow("Analysis type", self.spectrum_type_combo)
        spectrum_controls.addRow("nfft", self.spectrum_nfft_input)
        spectrum_controls.addRow("nperseg", self.spectrum_nperseg_input)
        spectrum_controls.addRow("noverlap", self.spectrum_noverlap_input)
        spectrum_controls.addRow("", self.spectrum_db_checkbox)
        spectrum_layout.addLayout(spectrum_controls)
        spectrum_layout.addWidget(self.spectrum_button)
        spectrum_layout.addWidget(self.spectrum_info)
        spectrum_layout.addWidget(self.spectrum_toolbar)
        spectrum_layout.addWidget(self.spectrum_canvas)

        fk_panel = QtWidgets.QWidget()
        fk_layout = QtWidgets.QVBoxLayout(fk_panel)
        fk_controls = QtWidgets.QFormLayout()
        fk_controls.addRow("Time start", self.fk_time_start_input)
        fk_controls.addRow("Time stop", self.fk_time_stop_input)
        fk_controls.addRow("Time step", self.fk_time_step_input)
        fk_controls.addRow("Channel start", self.fk_channel_start_input)
        fk_controls.addRow("Channel stop", self.fk_channel_stop_input)
        fk_controls.addRow("Channel step", self.fk_channel_step_input)
        fk_controls.addRow("FK mode", self.fk_mode_combo)
        fk_controls.addRow("Output mode", self.fk_output_combo)
        fk_controls.addRow("", self.fk_db_checkbox)
        fk_controls.addRow("vmin m/s", self.fk_vmin_input)
        fk_controls.addRow("vmax m/s", self.fk_vmax_input)
        fk_controls.addRow("", self.fk_pass_inside_checkbox)
        fk_layout.addLayout(fk_controls)
        fk_layout.addWidget(self.fk_button)
        fk_layout.addWidget(self.fk_info)
        fk_layout.addWidget(self.fk_toolbar)
        fk_layout.addWidget(self.fk_canvas)

        self.plot_tabs = QtWidgets.QTabWidget()
        self.plot_tabs.addTab(waterfall_panel, "Waterfall")
        self.plot_tabs.addTab(waveform_panel, "Waveform")
        self.plot_tabs.addTab(spectrum_panel, "Spectrum")
        self.plot_tabs.addTab(fk_panel, "FK")

        splitter.addWidget(left_panel)
        splitter.addWidget(self.plot_tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        self._build_menu()
        self._clear_waterfall_figure()
        self._clear_waveform_figure()
        self._clear_spectrum_figure()
        self._clear_fk_figure()
        self._apply_task_control_state(is_running=False)
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
        """Load a file preview through a background preview worker."""

        if self._active_task_id is not None:
            self.statusBar().showMessage("A background task is already running")
            return
        self.current_path = None
        self.file_info.setPlainText(f"Path: {path}\nLoading preview...")
        self.metadata_text.setPlainText("Loading preview...")
        self.waveform_info.setPlainText("Load a file, then plot one or more channels.")
        self.spectrum_info.setPlainText("Load a file, then run a single-channel spectrum analysis.")
        self.fk_info.setPlainText("Load a file, then run a bounded FK task.")
        self._clear_waterfall_figure()
        self._clear_waveform_figure()
        self._clear_spectrum_figure()
        self._clear_fk_figure()
        try:
            limits = parse_preview_limits(
                self.max_samples_input.value(),
                self.max_channels_input.value(),
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.file_info.setPlainText(f"Path: {path}\nError: {message}")
            self.metadata_text.setPlainText(f"Failed to load preview.\n\n{message}")
            self.waveform_info.setPlainText(f"Waveform unavailable.\n\n{message}")
            self.spectrum_info.setPlainText(f"Spectrum unavailable.\n\n{message}")
            self.fk_info.setPlainText(f"FK unavailable.\n\n{message}")
            self._clear_waterfall_figure()
            self._clear_waveform_figure()
            self._clear_spectrum_figure()
            self._clear_fk_figure()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View error", message)
            return

        worker = QtPreviewWorker(
            path,
            max_samples=limits.max_samples,
            max_channels=limits.max_channels,
        )
        self._start_background_task(
            "preview",
            worker,
            on_finished=lambda result, task_id: self._handle_preview_finished(
                result,
                task_id=task_id,
                path=Path(path),
            ),
        )

    def load_waveform(self) -> None:
        """Read selected channels in the background and draw waveforms."""

        if self._active_task_id is not None:
            self.statusBar().showMessage("A background task is already running")
            return
        if self.current_path is None:
            message = "Open a supported DAS file before plotting waveforms."
            self.waveform_info.setPlainText(message)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.warning(self, "DAS View waveform", message)
            return

        try:
            channels = parse_channel_indices(self.waveform_channel_input.text())
            time_step = int(self.waveform_time_step_input.value())
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.waveform_info.setPlainText(f"Failed to load waveform.\n\n{message}")
            self._clear_waveform_figure()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View waveform error", message)
            return

        self.waveform_info.setPlainText("Loading waveform...")
        self.statusBar().showMessage(format_task_status("waveform", "loading"))
        worker = QtWaveformWorker(
            self.current_path,
            channels=channels,
            time_step=time_step,
        )
        self._start_background_task(
            "waveform",
            worker,
            on_finished=lambda result, task_id: self._handle_waveform_finished(
                result,
                task_id=task_id,
            ),
        )

    def load_spectrum(self) -> None:
        """Compute a single-channel spectrum analysis in the background."""

        if self._active_task_id is not None:
            self.statusBar().showMessage("A background task is already running")
            return
        if self.current_path is None:
            message = "Open a supported DAS file before running spectrum analysis."
            self.spectrum_info.setPlainText(message)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.warning(self, "DAS View spectrum", message)
            return

        try:
            request = parse_spectrum_request(
                analysis_type=self.spectrum_type_combo.currentData()
                or self.spectrum_type_combo.currentText(),
                channel_text=self.spectrum_channel_input.text(),
                nfft_text=self.spectrum_nfft_input.text(),
                nperseg_text=self.spectrum_nperseg_input.text(),
                noverlap_text=self.spectrum_noverlap_input.text(),
                db=self.spectrum_db_checkbox.isChecked(),
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.spectrum_info.setPlainText(f"Failed to run spectrum analysis.\n\n{message}")
            self._clear_spectrum_figure()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View spectrum error", message)
            return

        self.spectrum_info.setPlainText(f"Loading spectrum...\n\nAnalysis: {request.label}")
        self.statusBar().showMessage(format_task_status("spectrum", "loading"))
        worker = QtSpectrumWorker(self.current_path, request=request)
        self._start_background_task(
            "spectrum",
            worker,
            on_finished=lambda result, task_id: self._handle_spectrum_finished(
                result,
                task_id=task_id,
                request=request,
            ),
        )

    def load_fk(self) -> None:
        """Run a bounded FK task in the background and draw the result."""

        if self._active_task_id is not None:
            self.statusBar().showMessage("A background task is already running")
            return
        if self.current_path is None:
            message = "Open a supported DAS file before running FK analysis."
            self.fk_info.setPlainText(message)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.warning(self, "DAS View FK", message)
            return

        try:
            request = parse_fk_request(
                mode=self.fk_mode_combo.currentData() or self.fk_mode_combo.currentText(),
                output=self.fk_output_combo.currentData() or self.fk_output_combo.currentText(),
                time_start_text=self.fk_time_start_input.text(),
                time_stop_text=self.fk_time_stop_input.text(),
                time_step=self.fk_time_step_input.value(),
                channel_start_text=self.fk_channel_start_input.text(),
                channel_stop_text=self.fk_channel_stop_input.text(),
                channel_step=self.fk_channel_step_input.value(),
                vmin_text=self.fk_vmin_input.text(),
                vmax_text=self.fk_vmax_input.text(),
                pass_inside=self.fk_pass_inside_checkbox.isChecked(),
                db=self.fk_db_checkbox.isChecked(),
                max_samples=self.max_samples_input.value(),
                max_channels=self.max_channels_input.value(),
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.fk_info.setPlainText(f"Failed to run FK task.\n\n{message}")
            self._clear_fk_figure()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View FK error", message)
            return

        self.fk_info.setPlainText(f"Loading FK...\n\nMode: {request.label}")
        self.statusBar().showMessage(format_task_status("fk", "loading"))
        worker = QtFKWorker(self.current_path, request=request)
        self._start_background_task(
            "fk",
            worker,
            on_finished=lambda result, task_id: self._handle_fk_finished(
                result,
                task_id=task_id,
                request=request,
            ),
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = file_menu.addAction("&Open File")
        self.open_action.triggered.connect(self.open_file_dialog)
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

    def cancel_active_task(self) -> None:
        """Request soft cancellation for the active background task."""

        if self._task_worker is None or self._active_task_id is None:
            return
        self._task_cancel_requested = True
        if hasattr(self._task_worker, "cancel"):
            self._task_worker.cancel()
        self.cancel_button.setEnabled(False)
        task = self._task_kind or "task"
        self.statusBar().showMessage(format_task_status(task, "cancelled"))
        if task == "preview":
            self.metadata_text.setPlainText(
                "Cancelling preview load...\n\n"
                "Soft cancellation cannot interrupt a reader call already in progress, "
                "but cancelled results will not be applied."
            )
        elif task == "waveform":
            self.waveform_info.setPlainText(
                "Cancelling waveform load...\n\n"
                "Soft cancellation cannot interrupt a reader call already in progress, "
                "but cancelled results will not be applied."
            )
        elif task == "spectrum":
            self.spectrum_info.setPlainText(
                "Cancelling spectrum analysis...\n\n"
                "Soft cancellation cannot interrupt a reader or analysis call already in progress, "
                "but cancelled results will not be applied."
            )
        elif task == "fk":
            self.fk_info.setPlainText(
                "Cancelling FK task...\n\n"
                "Soft cancellation cannot interrupt a reader or FK calculation already in progress, "
                "but cancelled results will not be applied."
            )

    def _start_background_task(self, task_kind: str, worker: Any, *, on_finished: Any) -> None:
        QtCore = _qt_core()
        thread = QtCore.QThread(self)
        self._next_task_id += 1
        task_id = self._next_task_id
        self._active_task_id = task_id
        self._task_cancel_requested = False
        self._task_kind = task_kind
        self._task_thread = thread
        self._task_worker = worker

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.started.connect(
            lambda task_id=task_id, task_kind=task_kind: self._handle_task_started(
                task_kind,
                task_id=task_id,
            )
        )
        worker.progress.connect(
            lambda message, value, task_id=task_id: self._handle_task_progress(
                message,
                value,
                task_id=task_id,
            )
        )
        worker.finished.connect(lambda result, task_id=task_id: on_finished(result, task_id))
        worker.failed.connect(
            lambda message, task_id=task_id, task_kind=task_kind: self._handle_task_failed(
                task_kind,
                message,
                task_id=task_id,
            )
        )
        worker.cancelled.connect(
            lambda task_id=task_id, task_kind=task_kind: self._handle_task_cancelled(
                task_kind,
                task_id=task_id,
            )
        )
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda task_id=task_id: self._cleanup_task(task_id=task_id))
        self._apply_task_control_state(is_running=True)
        self.statusBar().showMessage(format_task_status(task_kind, "loading"))
        thread.start()

    def _handle_task_started(self, task_kind: str, *, task_id: int) -> None:
        if self._active_task_id != task_id:
            return
        self._apply_task_control_state(is_running=True)
        self.statusBar().showMessage(format_task_status(task_kind, "loading"))

    def _handle_task_progress(self, message: str, value: int, *, task_id: int) -> None:
        if self._active_task_id != task_id:
            return
        if self.progress_bar.minimum() != self.progress_bar.maximum():
            self.progress_bar.setValue(max(0, min(100, int(value))))
        self.statusBar().showMessage(message)

    def _handle_preview_finished(self, result: Any, *, task_id: int, path: Path) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        display = PreviewDisplayInfo.from_preview_result(result)
        lines = display.as_lines()
        lines.extend(f"Warning: {warning}" for warning in result.warnings)
        self.file_info.setPlainText("\n".join(lines))
        self.metadata_text.setPlainText(format_metadata(result.metadata))
        self._draw_preview(result.preview)
        self.current_path = path
        self.statusBar().showMessage(display.loaded_status())

    def _handle_waveform_finished(self, result: Any, *, task_id: int) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        self._draw_waveform(result.das_data)
        lines = [
            f"Path: {self.current_path}",
            f"Reader: {result.reader_name}",
            f"Requested channels: {result.requested_channels}",
            f"Waveform shape: {result.das_data.data.shape[0]} samples x "
            f"{result.das_data.data.shape[1]} channels",
            f"Downsample: time_step={result.downsample[0]}, channel_step={result.downsample[1]}",
        ]
        self.waveform_info.setPlainText("\n".join(lines))
        self.statusBar().showMessage(
            f"Loaded waveform: {result.reader_name} | "
            f"channels={result.requested_channels} | "
            f"shape={result.das_data.data.shape} | downsample={result.downsample}"
        )

    def _handle_spectrum_finished(self, result: Any, *, task_id: int, request: Any) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        self._draw_spectrum(result, request)
        self.spectrum_info.setPlainText("\n".join(format_spectrum_status(result, request)))
        frequencies = getattr(result.result, "frequencies_hz", ())
        times = getattr(result.result, "times_s", None)
        extra = f", times={len(times)}" if times is not None else ""
        self.statusBar().showMessage(
            f"Loaded spectrum: {request.label} | channel={request.channel} | "
            f"frequency bins={len(frequencies)}{extra}"
        )

    def _handle_fk_finished(self, result: Any, *, task_id: int, request: Any) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        self._draw_fk(result, request)
        self.fk_info.setPlainText("\n".join(format_fk_status(result, request)))
        if request.mode == "transform":
            self.statusBar().showMessage(
                f"Loaded FK: {request.output} | shape={result.result.values.shape}"
            )
        else:
            self.statusBar().showMessage(
                f"Loaded FK filter: shape={result.result.das_data.data.shape} | "
                f"vmin={request.vmin_mps} | vmax={request.vmax_mps}"
            )

    def _handle_task_failed(self, task_kind: str, message: str, *, task_id: int) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        if task_kind == "preview":
            self.file_info.setPlainText(f"Error: {message}")
            self.metadata_text.setPlainText(f"Failed to load preview.\n\n{message}")
            self.waveform_info.setPlainText(f"Waveform unavailable.\n\n{message}")
            self.spectrum_info.setPlainText(f"Spectrum unavailable.\n\n{message}")
            self.fk_info.setPlainText(f"FK unavailable.\n\n{message}")
            self.current_path = None
            self._clear_waterfall_figure()
            self._clear_waveform_figure()
            self._clear_spectrum_figure()
            self._clear_fk_figure()
            title = "DAS View error"
        elif task_kind == "waveform":
            self.waveform_info.setPlainText(f"Failed to load waveform.\n\n{message}")
            self._clear_waveform_figure()
            title = "DAS View waveform error"
        elif task_kind == "spectrum":
            self.spectrum_info.setPlainText(f"Failed to run spectrum analysis.\n\n{message}")
            self._clear_spectrum_figure()
            title = "DAS View spectrum error"
        else:
            self.fk_info.setPlainText(f"Failed to run FK task.\n\n{message}")
            self._clear_fk_figure()
            title = "DAS View FK error"
        self.statusBar().showMessage(format_task_status(task_kind, "error", message))
        _qt_widgets().QMessageBox.critical(self, title, message)

    def _handle_task_cancelled(self, task_kind: str, *, task_id: int) -> None:
        if self._active_task_id != task_id:
            return
        self._task_cancel_requested = True
        self.statusBar().showMessage(format_task_status(task_kind, "cancelled"))
        if task_kind == "preview":
            self.file_info.setPlainText("Preview load cancelled.")
            self.metadata_text.setPlainText("Preview load cancelled.")
            self._clear_waterfall_figure()
            self._clear_waveform_figure()
            self._clear_spectrum_figure()
        elif task_kind == "waveform":
            self.waveform_info.setPlainText("Waveform load cancelled.")
            self._clear_waveform_figure()
        elif task_kind == "spectrum":
            self.spectrum_info.setPlainText("Spectrum analysis cancelled.")
            self._clear_spectrum_figure()
        elif task_kind == "fk":
            self.fk_info.setPlainText("FK task cancelled.")
            self._clear_fk_figure()

    def _cleanup_task(self, *, task_id: int) -> None:
        if self._active_task_id != task_id:
            return
        self._task_thread = None
        self._task_worker = None
        self._active_task_id = None
        self._task_cancel_requested = False
        self._task_kind = None
        self._apply_task_control_state(is_running=False)

    def _apply_task_control_state(self, *, is_running: bool) -> None:
        state = task_control_state(is_running)
        if hasattr(self, "open_action"):
            self.open_action.setEnabled(state.open_enabled)
        self.max_samples_input.setEnabled(state.preview_controls_enabled)
        self.max_channels_input.setEnabled(state.preview_controls_enabled)
        self.waveform_channel_input.setEnabled(state.waveform_controls_enabled)
        self.waveform_time_step_input.setEnabled(state.waveform_controls_enabled)
        self.waveform_button.setEnabled(state.waveform_controls_enabled)
        self.spectrum_channel_input.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_type_combo.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_nfft_input.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_nperseg_input.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_noverlap_input.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_db_checkbox.setEnabled(state.spectrum_controls_enabled)
        self.spectrum_button.setEnabled(state.spectrum_controls_enabled)
        self.fk_time_start_input.setEnabled(state.fk_controls_enabled)
        self.fk_time_stop_input.setEnabled(state.fk_controls_enabled)
        self.fk_time_step_input.setEnabled(state.fk_controls_enabled)
        self.fk_channel_start_input.setEnabled(state.fk_controls_enabled)
        self.fk_channel_stop_input.setEnabled(state.fk_controls_enabled)
        self.fk_channel_step_input.setEnabled(state.fk_controls_enabled)
        self.fk_mode_combo.setEnabled(state.fk_controls_enabled)
        self.fk_output_combo.setEnabled(state.fk_controls_enabled)
        self.fk_db_checkbox.setEnabled(state.fk_controls_enabled)
        self.fk_vmin_input.setEnabled(state.fk_controls_enabled)
        self.fk_vmax_input.setEnabled(state.fk_controls_enabled)
        self.fk_pass_inside_checkbox.setEnabled(state.fk_controls_enabled)
        self.fk_button.setEnabled(state.fk_controls_enabled)
        self.cancel_button.setEnabled(state.cancel_enabled)
        self.progress_bar.setVisible(state.progress_visible)
        self.progress_bar.setRange(state.progress_minimum, state.progress_maximum)
        if not state.progress_visible:
            self.progress_bar.setValue(0)

    def _clear_waterfall_figure(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("No preview loaded")
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw_idle()

    def _clear_waveform_figure(self) -> None:
        self.waveform_figure.clear()
        ax = self.waveform_figure.add_subplot(111)
        ax.set_title("No waveform loaded")
        ax.set_xticks([])
        ax.set_yticks([])
        self.waveform_canvas.draw_idle()

    def _clear_spectrum_figure(self) -> None:
        self.spectrum_figure.clear()
        ax = self.spectrum_figure.add_subplot(111)
        ax.set_title("No spectrum loaded")
        ax.set_xticks([])
        ax.set_yticks([])
        self.spectrum_canvas.draw_idle()

    def _clear_fk_figure(self) -> None:
        self.fk_figure.clear()
        ax = self.fk_figure.add_subplot(111)
        ax.set_title("No FK result loaded")
        ax.set_xticks([])
        ax.set_yticks([])
        self.fk_canvas.draw_idle()

    def _draw_preview(self, preview_data) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        plot_waterfall(preview_data, ax=ax)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_waveform(self, das_data) -> None:
        self.waveform_figure.clear()
        ax = self.waveform_figure.add_subplot(111)
        plot_waveform(
            das_data,
            channels=list(range(das_data.n_channels)),
            ax=ax,
            title="DAS waveform preview",
        )
        self.waveform_figure.tight_layout()
        self.waveform_canvas.draw_idle()

    def _draw_spectrum(self, service_result, request) -> None:
        self.spectrum_figure.clear()
        ax = self.spectrum_figure.add_subplot(111)
        title = f"{request.label} - channel {request.channel}"
        if request.analysis_type in {"amplitude", "power"}:
            plot_spectrum(service_result.result, ax=ax, title=title)
        elif request.analysis_type in {"psd_periodogram", "psd_welch"}:
            plot_psd(service_result.result, ax=ax, title=title, db=request.db)
        elif request.analysis_type == "spectrogram":
            plot_spectrogram(service_result.result, ax=ax, title=title)
        else:
            raise ValueError(f"unsupported spectrum analysis type: {request.analysis_type!r}")
        self.spectrum_figure.tight_layout()
        self.spectrum_canvas.draw_idle()

    def _draw_fk(self, service_result, request) -> None:
        self.fk_figure.clear()
        if request.mode == "transform":
            ax = self.fk_figure.add_subplot(111)
            title = f"{request.label} - {request.output}"
            plot_fk(service_result.result, ax=ax, title=title, db=request.db)
        elif request.mode == "velocity_filter":
            waterfall_ax = self.fk_figure.add_subplot(121)
            mask_ax = self.fk_figure.add_subplot(122)
            plot_waterfall(
                service_result.result.das_data,
                ax=waterfall_ax,
                title="Filtered waterfall",
                show_colorbar=False,
            )
            plot_fk_mask(
                service_result.result.frequencies_hz,
                service_result.result.wavenumbers_cycles_per_m,
                service_result.result.mask,
                ax=mask_ax,
                title="Velocity fan mask",
                show_colorbar=False,
            )
        else:
            raise ValueError(f"unsupported FK mode: {request.mode!r}")
        self.fk_figure.tight_layout()
        self.fk_canvas.draw_idle()
