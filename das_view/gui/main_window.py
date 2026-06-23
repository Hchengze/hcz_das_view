"""Minimal PyQt5 main window for DAS preview."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from das_view.core.metadata_format import format_metadata
from das_view.gui.display_backends import is_pyqtgraph_available
from das_view.gui.models import (
    AnalysisRequest,
    GUI_DEFAULT_MAX_SELECTION_BYTES,
    PreviewDisplayInfo,
    candidates_to_table_rows,
    format_analysis_summary,
    format_bad_channel_rows,
    format_denoise_report_rows,
    format_directional_energy_rows,
    format_error_message,
    format_fk_status,
    format_gui_file_summary,
    format_moveout_summary_rows,
    format_multiband_rows,
    format_qc_rows,
    format_spectrum_status,
    format_task_status,
    gui_selection_estimate,
    gui_safe_selection_presets,
    parse_channel_indices,
    parse_analysis_request,
    parse_fk_request,
    parse_preview_limits,
    parse_spectrum_request,
    roi_statistics_to_table_rows,
    should_apply_task_result,
    task_control_state,
)
from das_view.gui.pyqtgraph_canvas import create_pyqtgraph_waterfall_widget
from das_view.gui.workers import (
    QtAnalysisWorker,
    QtFKWorker,
    QtPreviewWorker,
    QtSpectrumWorker,
    QtWaveformWorker,
)
from das_view.io.export import save_csv_rows, save_json
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


def _channels_to_slice(channels: tuple[int, ...]) -> slice:
    """Return a conservative contiguous slice covering requested channels."""

    if not channels:
        return slice(0, 0)
    return slice(min(channels), max(channels) + 1)


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
        self._current_metadata: Any | None = None
        self._current_reader_name: str | None = None
        self._gui_max_selection_bytes = GUI_DEFAULT_MAX_SELECTION_BYTES
        self._display_backend = "matplotlib"
        self._pyqtgraph_available = is_pyqtgraph_available()
        self._pyqtgraph_waterfall_view: Any | None = None
        self._latest_preview_data: Any | None = None
        self._latest_analysis_result: Any | None = None
        self._latest_analysis_request: AnalysisRequest | None = None
        self._latest_analysis_rows: list[dict[str, Any]] = []
        self._latest_event_candidates: tuple[Any, ...] = ()
        self.setWindowTitle("DAS View")
        self.resize(1100, 750)

        self.file_info = QtWidgets.QPlainTextEdit()
        self.file_info.setReadOnly(True)
        self.file_info.setMaximumHeight(150)
        presets = gui_safe_selection_presets()
        self.file_info.setPlainText(
            "No file loaded.\n"
            f"Safe preview: {presets['small_preview'][0]} samples x "
            f"{presets['small_preview'][1]} channels.\n"
            f"Analysis safe default: {presets['analysis'][0]} samples x "
            f"{presets['analysis'][1]} channels."
        )

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

        self.display_backend_combo = QtWidgets.QComboBox()
        self.display_backend_combo.addItem("Matplotlib", "matplotlib")
        pyqtgraph_label = (
            "PyQtGraph experimental"
            if self._pyqtgraph_available
            else "PyQtGraph experimental (install display extra)"
        )
        self.display_backend_combo.addItem(pyqtgraph_label, "pyqtgraph")
        self.display_backend_combo.setCurrentIndex(0)
        self.display_backend_combo.setToolTip("Waterfall display backend; Matplotlib remains the default")
        self.display_backend_combo.currentIndexChanged.connect(self._handle_display_backend_changed)
        self.waterfall_stack = QtWidgets.QStackedWidget()
        self.waterfall_matplotlib_panel = QtWidgets.QWidget()
        waterfall_mpl_layout = QtWidgets.QVBoxLayout(self.waterfall_matplotlib_panel)
        waterfall_mpl_layout.setContentsMargins(0, 0, 0, 0)
        waterfall_mpl_layout.addWidget(self.toolbar)
        waterfall_mpl_layout.addWidget(self.canvas)
        self.waterfall_stack.addWidget(self.waterfall_matplotlib_panel)

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
        self.waveform_info.setPlainText(
            "Load a file, then plot one or more channels. Large files should use a time step."
        )

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
        self.spectrum_info.setPlainText(
            "Load a file, then run a bounded single-channel spectrum analysis."
        )

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
        self.fk_info.setPlainText(
            f"Load a file, then run a bounded FK task. Safe default: "
            f"{presets['fk'][0]} samples x {presets['fk'][1]} channels."
        )

        self.analysis_time_start_input = QtWidgets.QLineEdit("")
        self.analysis_time_start_input.setToolTip("Optional zero-based start sample")
        self.analysis_time_stop_input = QtWidgets.QLineEdit("")
        self.analysis_time_stop_input.setToolTip("Optional stop sample")
        self.analysis_time_step_input = QtWidgets.QSpinBox()
        self.analysis_time_step_input.setRange(1, 10_000_000)
        self.analysis_time_step_input.setValue(1)
        self.analysis_channel_start_input = QtWidgets.QLineEdit("")
        self.analysis_channel_start_input.setToolTip("Optional zero-based start channel")
        self.analysis_channel_stop_input = QtWidgets.QLineEdit("")
        self.analysis_channel_stop_input.setToolTip("Optional stop channel")
        self.analysis_channel_step_input = QtWidgets.QSpinBox()
        self.analysis_channel_step_input.setRange(1, 1_000_000)
        self.analysis_channel_step_input.setValue(1)
        self.analysis_type_combo = QtWidgets.QComboBox()
        self.analysis_type_combo.addItem("Statistics", "statistics")
        self.analysis_type_combo.addItem("Band energy", "band_energy")
        self.analysis_type_combo.addItem("Spectral attributes", "spectral_attributes")
        self.analysis_type_combo.addItem("Event candidates - STA/LTA", "events_stalta")
        self.analysis_type_combo.addItem("Event candidates - Envelope threshold", "events_envelope")
        self.analysis_type_combo.addItem("ROI statistics", "roi_statistics")
        self.analysis_type_combo.addItem("QC report", "qc_report")
        self.analysis_type_combo.addItem("Bad channels", "bad_channels")
        self.analysis_type_combo.addItem("Multiband map summary", "multiband_summary")
        self.analysis_type_combo.addItem("Denoise report", "denoise_report")
        self.analysis_type_combo.addItem("Moveout summary", "moveout_summary")
        self.analysis_type_combo.addItem("Directional energy", "directional_energy")
        self.analysis_type_combo.currentIndexChanged.connect(self._update_analysis_parameter_state)
        self.analysis_axis_combo = QtWidgets.QComboBox()
        self.analysis_axis_combo.addItems(["global", "time", "channel"])
        self.analysis_percentiles_input = QtWidgets.QLineEdit("1,5,25,50,75,95,99")
        self.analysis_nan_policy_combo = QtWidgets.QComboBox()
        self.analysis_nan_policy_combo.addItems(["omit", "raise"])
        self.analysis_bands_input = QtWidgets.QLineEdit("1-5,5-20,20-80")
        self.analysis_frequency_range_input = QtWidgets.QLineEdit("")
        self.analysis_frequency_range_input.setToolTip("Optional frequency range, e.g. 1-80")
        self.analysis_rolloff_input = QtWidgets.QLineEdit("0.95")
        self.analysis_average_channels_checkbox = QtWidgets.QCheckBox("Average channels")
        self.analysis_sta_input = QtWidgets.QSpinBox()
        self.analysis_sta_input.setRange(1, 10_000_000)
        self.analysis_sta_input.setValue(25)
        self.analysis_lta_input = QtWidgets.QSpinBox()
        self.analysis_lta_input.setRange(2, 10_000_000)
        self.analysis_lta_input.setValue(250)
        self.analysis_trigger_on_input = QtWidgets.QLineEdit("3.0")
        self.analysis_trigger_off_input = QtWidgets.QLineEdit("")
        self.analysis_threshold_input = QtWidgets.QLineEdit("1.0")
        self.analysis_smooth_samples_input = QtWidgets.QLineEdit("")
        self.analysis_min_duration_input = QtWidgets.QSpinBox()
        self.analysis_min_duration_input.setRange(1, 10_000_000)
        self.analysis_min_duration_input.setValue(1)
        self.analysis_merge_gap_input = QtWidgets.QSpinBox()
        self.analysis_merge_gap_input.setRange(0, 10_000_000)
        self.analysis_merge_gap_input.setValue(0)
        self.analysis_max_events_input = QtWidgets.QLineEdit("")
        self.analysis_roi_text = QtWidgets.QPlainTextEdit()
        self.analysis_roi_text.setMaximumHeight(80)
        self.analysis_roi_text.setPlaceholderText("start,end,ch_start,ch_end")
        self.analysis_use_event_rois_checkbox = QtWidgets.QCheckBox("Use latest event candidates as ROIs")
        self.analysis_padding_samples_input = QtWidgets.QSpinBox()
        self.analysis_padding_samples_input.setRange(0, 10_000_000)
        self.analysis_padding_samples_input.setValue(0)
        self.analysis_padding_channels_input = QtWidgets.QSpinBox()
        self.analysis_padding_channels_input.setRange(0, 1_000_000)
        self.analysis_padding_channels_input.setValue(0)
        self.analysis_max_rois_input = QtWidgets.QLineEdit("")
        self.analysis_window_samples_input = QtWidgets.QSpinBox()
        self.analysis_window_samples_input.setRange(1, 10_000_000)
        self.analysis_window_samples_input.setValue(256)
        self.analysis_window_samples_input.setToolTip("Window length for multiband or moveout summaries")
        self.analysis_step_samples_input = QtWidgets.QSpinBox()
        self.analysis_step_samples_input.setRange(1, 10_000_000)
        self.analysis_step_samples_input.setValue(128)
        self.analysis_step_samples_input.setToolTip("Window step for multiband or moveout summaries")
        self.analysis_channel_lag_input = QtWidgets.QSpinBox()
        self.analysis_channel_lag_input.setRange(1, 1_000_000)
        self.analysis_channel_lag_input.setValue(1)
        self.analysis_channel_lag_input.setToolTip("Channel lag for moveout summary")
        self.analysis_denoise_workflow_input = QtWidgets.QLineEdit(
            "common_mode_removal:method=median"
        )
        self.analysis_denoise_workflow_input.setToolTip(
            "Semicolon-separated denoise steps, e.g. common_mode_removal:method=median"
        )
        self.analysis_run_button = QtWidgets.QPushButton("Run analysis")
        self.analysis_run_button.clicked.connect(self.run_analysis)
        self.analysis_export_json_button = QtWidgets.QPushButton("Export JSON")
        self.analysis_export_json_button.clicked.connect(self.export_analysis_json)
        self.analysis_export_csv_button = QtWidgets.QPushButton("Export CSV")
        self.analysis_export_csv_button.clicked.connect(self.export_analysis_csv)
        self.analysis_clear_button = QtWidgets.QPushButton("Clear results")
        self.analysis_clear_button.clicked.connect(self.clear_analysis_results)
        self.analysis_info = QtWidgets.QPlainTextEdit()
        self.analysis_info.setReadOnly(True)
        self.analysis_info.setMaximumHeight(180)
        self.analysis_info.setPlainText(
            f"Load a file, then run a bounded analysis task. Safe default: "
            f"{presets['analysis'][0]} samples x {presets['analysis'][1]} channels."
        )
        self.analysis_table = QtWidgets.QTableWidget()
        self.analysis_table.setAlternatingRowColors(True)
        self.analysis_table.setSortingEnabled(False)

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
        waterfall_controls = QtWidgets.QFormLayout()
        waterfall_controls.addRow("Display backend", self.display_backend_combo)
        waterfall_layout.addLayout(waterfall_controls)
        waterfall_layout.addWidget(self.waterfall_stack)

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

        analysis_panel = QtWidgets.QWidget()
        analysis_layout = QtWidgets.QVBoxLayout(analysis_panel)
        analysis_controls = QtWidgets.QFormLayout()
        analysis_controls.addRow("Time start", self.analysis_time_start_input)
        analysis_controls.addRow("Time stop", self.analysis_time_stop_input)
        analysis_controls.addRow("Time step", self.analysis_time_step_input)
        analysis_controls.addRow("Channel start", self.analysis_channel_start_input)
        analysis_controls.addRow("Channel stop", self.analysis_channel_stop_input)
        analysis_controls.addRow("Channel step", self.analysis_channel_step_input)
        analysis_controls.addRow("Analysis type", self.analysis_type_combo)
        analysis_controls.addRow("Statistics axis", self.analysis_axis_combo)
        analysis_controls.addRow("Percentiles", self.analysis_percentiles_input)
        analysis_controls.addRow("NaN policy", self.analysis_nan_policy_combo)
        analysis_controls.addRow("Bands Hz", self.analysis_bands_input)
        analysis_controls.addRow("Frequency range Hz", self.analysis_frequency_range_input)
        analysis_controls.addRow("Rolloff", self.analysis_rolloff_input)
        analysis_controls.addRow("", self.analysis_average_channels_checkbox)
        analysis_controls.addRow("STA samples", self.analysis_sta_input)
        analysis_controls.addRow("LTA samples", self.analysis_lta_input)
        analysis_controls.addRow("Trigger on", self.analysis_trigger_on_input)
        analysis_controls.addRow("Trigger off", self.analysis_trigger_off_input)
        analysis_controls.addRow("Envelope threshold", self.analysis_threshold_input)
        analysis_controls.addRow("Smooth samples", self.analysis_smooth_samples_input)
        analysis_controls.addRow("Min duration", self.analysis_min_duration_input)
        analysis_controls.addRow("Merge gap", self.analysis_merge_gap_input)
        analysis_controls.addRow("Max events", self.analysis_max_events_input)
        analysis_controls.addRow("Manual ROI", self.analysis_roi_text)
        analysis_controls.addRow("", self.analysis_use_event_rois_checkbox)
        analysis_controls.addRow("ROI pad samples", self.analysis_padding_samples_input)
        analysis_controls.addRow("ROI pad channels", self.analysis_padding_channels_input)
        analysis_controls.addRow("Max ROIs", self.analysis_max_rois_input)
        analysis_controls.addRow("Window samples", self.analysis_window_samples_input)
        analysis_controls.addRow("Step samples", self.analysis_step_samples_input)
        analysis_controls.addRow("Channel lag", self.analysis_channel_lag_input)
        analysis_controls.addRow("Denoise workflow", self.analysis_denoise_workflow_input)
        analysis_layout.addLayout(analysis_controls)
        analysis_buttons = QtWidgets.QHBoxLayout()
        analysis_buttons.addWidget(self.analysis_run_button)
        analysis_buttons.addWidget(self.analysis_export_json_button)
        analysis_buttons.addWidget(self.analysis_export_csv_button)
        analysis_buttons.addWidget(self.analysis_clear_button)
        analysis_layout.addLayout(analysis_buttons)
        analysis_layout.addWidget(self.analysis_info)
        analysis_layout.addWidget(self.analysis_table)

        self.plot_tabs = QtWidgets.QTabWidget()
        self.plot_tabs.addTab(waterfall_panel, "Waterfall")
        self.plot_tabs.addTab(waveform_panel, "Waveform")
        self.plot_tabs.addTab(spectrum_panel, "Spectrum")
        self.plot_tabs.addTab(fk_panel, "FK")
        self.plot_tabs.addTab(analysis_panel, "Analysis")

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
        self._update_analysis_parameter_state()
        self._apply_task_control_state(is_running=False)
        self._update_analysis_export_state()
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
        self._current_metadata = None
        self._current_reader_name = None
        self._latest_preview_data = None
        self.file_info.setPlainText(f"Path: {path}\nLoading preview...")
        self.metadata_text.setPlainText("Loading preview...")
        self.waveform_info.setPlainText(
            "Load a file, then plot one or more channels. Large files should use a time step."
        )
        self.spectrum_info.setPlainText(
            "Load a file, then run a bounded single-channel spectrum analysis."
        )
        presets = gui_safe_selection_presets()
        self.fk_info.setPlainText(
            f"Load a file, then run a bounded FK task. Safe default: "
            f"{presets['fk'][0]} samples x {presets['fk'][1]} channels."
        )
        self.clear_analysis_results()
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
            self.analysis_info.setPlainText(f"Analysis unavailable.\n\n{message}")
            self._current_metadata = None
            self._current_reader_name = None
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

    def run_analysis(self) -> None:
        """Run a bounded analysis-panel task in the background."""

        if self._active_task_id is not None:
            self.statusBar().showMessage("A background task is already running")
            return
        if self.current_path is None:
            message = "Open a supported DAS file before running analysis."
            self.analysis_info.setPlainText(message)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.warning(self, "DAS View analysis", message)
            return

        try:
            request = parse_analysis_request(
                analysis_type=self.analysis_type_combo.currentData()
                or self.analysis_type_combo.currentText(),
                time_start_text=self.analysis_time_start_input.text(),
                time_stop_text=self.analysis_time_stop_input.text(),
                time_step=self.analysis_time_step_input.value(),
                channel_start_text=self.analysis_channel_start_input.text(),
                channel_stop_text=self.analysis_channel_stop_input.text(),
                channel_step=self.analysis_channel_step_input.value(),
                max_samples=self.max_samples_input.value(),
                max_channels=self.max_channels_input.value(),
                axis=self.analysis_axis_combo.currentText(),
                percentiles_text=self.analysis_percentiles_input.text(),
                nan_policy=self.analysis_nan_policy_combo.currentText(),
                bands_text=self.analysis_bands_input.text(),
                frequency_range_text=self.analysis_frequency_range_input.text(),
                rolloff_text=self.analysis_rolloff_input.text(),
                average_channels=self.analysis_average_channels_checkbox.isChecked(),
                sta_samples=self.analysis_sta_input.value(),
                lta_samples=self.analysis_lta_input.value(),
                trigger_on_text=self.analysis_trigger_on_input.text(),
                trigger_off_text=self.analysis_trigger_off_input.text(),
                threshold_text=self.analysis_threshold_input.text(),
                smooth_samples_text=self.analysis_smooth_samples_input.text(),
                min_duration_samples=self.analysis_min_duration_input.value(),
                merge_gap_samples=self.analysis_merge_gap_input.value(),
                max_events_text=self.analysis_max_events_input.text(),
                roi_text=self.analysis_roi_text.toPlainText(),
                use_event_rois=self.analysis_use_event_rois_checkbox.isChecked(),
                padding_samples=self.analysis_padding_samples_input.value(),
                padding_channels=self.analysis_padding_channels_input.value(),
                max_rois_text=self.analysis_max_rois_input.text(),
                window_samples=self.analysis_window_samples_input.value(),
                step_samples=self.analysis_step_samples_input.value(),
                channel_lag=self.analysis_channel_lag_input.value(),
                denoise_workflow=self.analysis_denoise_workflow_input.text(),
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.analysis_info.setPlainText(f"Failed to run analysis.\n\n{message}")
            self._clear_analysis_table()
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View analysis error", message)
            return
        heavy_types = {"multiband_summary", "moveout_summary", "directional_energy"}
        memory_limit = (
            max(1, self._gui_max_selection_bytes // 2)
            if request.analysis_type in heavy_types
            else self._gui_max_selection_bytes
        )
        operation_name = "Advanced analysis" if request.analysis_type in heavy_types else "Analysis"
        if not self._check_selection_memory(
            operation_name,
            time_slice=request.bounded_time_slice(),
            channel_slice=request.bounded_channel_slice(),
            downsample=request.downsample,
            info_widget=self.analysis_info,
            max_bytes=memory_limit,
        ):
            return

        self._latest_analysis_result = None
        self._latest_analysis_request = None
        self._latest_analysis_rows = []
        self._update_analysis_export_state()
        self.analysis_info.setPlainText(f"Loading analysis...\n\nAnalysis: {request.label}")
        self._clear_analysis_table()
        self.statusBar().showMessage(format_task_status("analysis", "loading"))
        worker = QtAnalysisWorker(
            self.current_path,
            request=request,
            event_candidates=self._latest_event_candidates,
        )
        self._start_background_task(
            "analysis",
            worker,
            on_finished=lambda result, task_id: self._handle_analysis_finished(
                result,
                task_id=task_id,
                request=request,
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
        if not self._check_selection_memory(
            "Waveform",
            channel_slice=_channels_to_slice(channels),
            downsample=(time_step, 1),
            info_widget=self.waveform_info,
        ):
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
        if not self._check_selection_memory(
            "Spectrum",
            time_slice=slice(0, request.max_samples),
            channel_slice=slice(request.channel, request.channel + 1),
            info_widget=self.spectrum_info,
        ):
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
        if not self._check_selection_memory(
            "FK",
            time_slice=request.bounded_time_slice(),
            channel_slice=request.bounded_channel_slice(),
            downsample=request.downsample,
            info_widget=self.fk_info,
        ):
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

    def export_analysis_json(self) -> None:
        """Export the latest analysis result using shared JSON helpers."""

        if self._latest_analysis_result is None or self._latest_analysis_request is None:
            message = "No analysis result to export. Run a bounded analysis first."
            self.statusBar().showMessage(message)
            _qt_widgets().QMessageBox.information(self, "DAS View analysis export", message)
            return
        path, _ = _qt_widgets().QFileDialog.getSaveFileName(
            self,
            "Export analysis JSON",
            "analysis_result.json",
            "JSON files (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            save_json(self._analysis_export_payload(), path)
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View analysis export error", message)
            return
        self.statusBar().showMessage(f"Exported analysis JSON: {path}")

    def export_analysis_csv(self) -> None:
        """Export the latest analysis table rows using shared CSV helpers."""

        if not self._latest_analysis_rows:
            message = "No analysis table rows to export. Run an analysis that produces rows first."
            self.statusBar().showMessage(message)
            _qt_widgets().QMessageBox.information(self, "DAS View analysis export", message)
            return
        path, _ = _qt_widgets().QFileDialog.getSaveFileName(
            self,
            "Export analysis CSV",
            "analysis_rows.csv",
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return
        try:
            save_csv_rows(self._latest_analysis_rows, path)
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, "DAS View analysis export error", message)
            return
        self.statusBar().showMessage(f"Exported analysis CSV: {path}")

    def clear_analysis_results(self) -> None:
        """Clear Analysis-tab summary, rows, and cached export state."""

        self._latest_analysis_result = None
        self._latest_analysis_request = None
        self._latest_analysis_rows = []
        self._latest_event_candidates = ()
        presets = gui_safe_selection_presets()
        self.analysis_info.setPlainText(
            f"Load a file, then run a bounded analysis task. Safe default: "
            f"{presets['analysis'][0]} samples x {presets['analysis'][1]} channels."
        )
        self._clear_analysis_table()
        self._update_analysis_export_state()

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
        elif task == "analysis":
            self.analysis_info.setPlainText(
                "Cancelling analysis task...\n\n"
                "Soft cancellation cannot interrupt a reader or analysis call already in progress, "
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
        lines.extend(
            format_gui_file_summary(
                result.metadata,
                reader_name=result.reader_name,
                max_preview_samples=self.max_samples_input.value(),
                max_preview_channels=self.max_channels_input.value(),
            )
        )
        lines.extend(f"Warning: {warning}" for warning in result.warnings)
        self.file_info.setPlainText("\n".join(lines))
        metadata_lines = [format_metadata(result.metadata), "", "GUI large-file summary:"]
        metadata_lines.extend(
            format_gui_file_summary(
                result.metadata,
                reader_name=result.reader_name,
                max_preview_samples=self.max_samples_input.value(),
                max_preview_channels=self.max_channels_input.value(),
            )
        )
        self.metadata_text.setPlainText("\n".join(metadata_lines))
        self._draw_preview(result.preview)
        self._latest_preview_data = result.preview
        self.current_path = path
        self._current_metadata = result.metadata
        self._current_reader_name = result.reader_name
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

    def _handle_analysis_finished(self, result: Any, *, task_id: int, request: AnalysisRequest) -> None:
        if not should_apply_task_result(
            task_id=task_id,
            active_task_id=self._active_task_id,
            was_cancelled=self._task_cancel_requested,
        ):
            return
        rows = self._analysis_rows_for_result(result, request)
        self._latest_analysis_result = result
        self._latest_analysis_request = request
        self._latest_analysis_rows = rows
        if request.analysis_type in {"events_stalta", "events_envelope"}:
            self._latest_event_candidates = tuple(result.result.candidates)
        self.analysis_info.setPlainText("\n".join(format_analysis_summary(result, request)))
        self._populate_analysis_table(rows)
        self._update_analysis_export_state()
        self.statusBar().showMessage(
            f"Loaded analysis: {request.label} | rows={len(rows)}"
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
            self._current_metadata = None
            self._current_reader_name = None
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
        elif task_kind == "fk":
            self.fk_info.setPlainText(f"Failed to run FK task.\n\n{message}")
            self._clear_fk_figure()
            title = "DAS View FK error"
        else:
            self.analysis_info.setPlainText(f"Failed to run analysis.\n\n{message}")
            self._clear_analysis_table()
            self._latest_analysis_result = None
            self._latest_analysis_request = None
            self._latest_analysis_rows = []
            self._update_analysis_export_state()
            title = "DAS View analysis error"
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
        elif task_kind == "analysis":
            self.analysis_info.setPlainText("Analysis task cancelled.")
            self._clear_analysis_table()
            self._latest_analysis_result = None
            self._latest_analysis_request = None
            self._latest_analysis_rows = []
            self._update_analysis_export_state()

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
        self.display_backend_combo.setEnabled(state.preview_controls_enabled)
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
        self._set_analysis_controls_enabled(state.analysis_controls_enabled)
        self.cancel_button.setEnabled(state.cancel_enabled)
        self.progress_bar.setVisible(state.progress_visible)
        self.progress_bar.setRange(state.progress_minimum, state.progress_maximum)
        if not state.progress_visible:
            self.progress_bar.setValue(0)

    def _clear_waterfall_figure(self) -> None:
        if self._pyqtgraph_waterfall_view is not None:
            self._pyqtgraph_waterfall_view.clear()
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

    def _clear_analysis_table(self) -> None:
        self.analysis_table.clear()
        self.analysis_table.setRowCount(0)
        self.analysis_table.setColumnCount(0)

    def _draw_preview(self, preview_data) -> None:
        if self._display_backend == "pyqtgraph":
            try:
                view = self._ensure_pyqtgraph_waterfall_view()
                displayed = view.set_waterfall_image(preview_data)
            except Exception as exc:  # noqa: BLE001 - GUI boundary reports optional backend errors.
                message = format_error_message(exc)
                self.statusBar().showMessage(f"PyQtGraph unavailable, using Matplotlib: {message}")
                self._set_display_backend("matplotlib")
            else:
                self.waterfall_stack.setCurrentWidget(view.widget)
                self.statusBar().showMessage(
                    f"PyQtGraph waterfall display: shown shape={displayed.shape}"
                )
                return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        plot_waterfall(preview_data, ax=ax)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.waterfall_stack.setCurrentWidget(self.waterfall_matplotlib_panel)

    def _handle_display_backend_changed(self) -> None:
        backend = self.display_backend_combo.currentData() or "matplotlib"
        if backend == self._display_backend:
            return
        if backend == "pyqtgraph" and not self._pyqtgraph_available:
            message = 'PyQtGraph display backend is unavailable. Install with: pip install -e ".[display]"'
            self.statusBar().showMessage(message)
            _qt_widgets().QMessageBox.information(self, "DAS View display backend", message)
            self._set_display_backend("matplotlib")
            return
        self._set_display_backend(str(backend))
        if self._latest_preview_data is not None:
            self._draw_preview(self._latest_preview_data)

    def _set_display_backend(self, backend: str) -> None:
        self._display_backend = backend
        index = self.display_backend_combo.findData(backend)
        if index >= 0 and self.display_backend_combo.currentIndex() != index:
            self.display_backend_combo.blockSignals(True)
            self.display_backend_combo.setCurrentIndex(index)
            self.display_backend_combo.blockSignals(False)
        if backend == "matplotlib":
            self.waterfall_stack.setCurrentWidget(self.waterfall_matplotlib_panel)

    def _ensure_pyqtgraph_waterfall_view(self):
        if self._pyqtgraph_waterfall_view is None:
            self._pyqtgraph_waterfall_view = create_pyqtgraph_waterfall_widget(parent=self)
            self.waterfall_stack.addWidget(self._pyqtgraph_waterfall_view.widget)
        return self._pyqtgraph_waterfall_view

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

    def _update_analysis_parameter_state(self) -> None:
        if not hasattr(self, "analysis_type_combo"):
            return
        analysis_type = self.analysis_type_combo.currentData() or "statistics"
        is_statistics = analysis_type == "statistics"
        is_band = analysis_type == "band_energy"
        is_spectral = analysis_type == "spectral_attributes"
        is_stalta = analysis_type == "events_stalta"
        is_envelope = analysis_type == "events_envelope"
        is_events = is_stalta or is_envelope
        is_roi = analysis_type == "roi_statistics"
        is_multiband = analysis_type == "multiband_summary"
        is_denoise = analysis_type == "denoise_report"
        is_moveout = analysis_type == "moveout_summary"

        self.analysis_axis_combo.setEnabled(is_statistics)
        self.analysis_percentiles_input.setEnabled(is_statistics or is_roi)
        self.analysis_nan_policy_combo.setEnabled(True)
        self.analysis_bands_input.setEnabled(is_band or is_multiband)
        self.analysis_frequency_range_input.setEnabled(is_spectral)
        self.analysis_rolloff_input.setEnabled(is_spectral)
        self.analysis_average_channels_checkbox.setEnabled(is_band or is_spectral)
        self.analysis_sta_input.setEnabled(is_stalta)
        self.analysis_lta_input.setEnabled(is_stalta)
        self.analysis_trigger_on_input.setEnabled(is_stalta)
        self.analysis_trigger_off_input.setEnabled(is_stalta)
        self.analysis_threshold_input.setEnabled(is_envelope)
        self.analysis_smooth_samples_input.setEnabled(is_envelope)
        self.analysis_min_duration_input.setEnabled(is_events)
        self.analysis_merge_gap_input.setEnabled(is_events)
        self.analysis_max_events_input.setEnabled(is_events)
        self.analysis_roi_text.setEnabled(is_roi)
        self.analysis_use_event_rois_checkbox.setEnabled(is_roi)
        self.analysis_padding_samples_input.setEnabled(is_roi)
        self.analysis_padding_channels_input.setEnabled(is_roi)
        self.analysis_max_rois_input.setEnabled(is_roi)
        self.analysis_window_samples_input.setEnabled(is_multiband or is_moveout)
        self.analysis_step_samples_input.setEnabled(is_multiband or is_moveout)
        self.analysis_channel_lag_input.setEnabled(is_moveout)
        self.analysis_denoise_workflow_input.setEnabled(is_denoise)

    def _set_analysis_controls_enabled(self, enabled: bool) -> None:
        widgets = [
            self.analysis_time_start_input,
            self.analysis_time_stop_input,
            self.analysis_time_step_input,
            self.analysis_channel_start_input,
            self.analysis_channel_stop_input,
            self.analysis_channel_step_input,
            self.analysis_type_combo,
            self.analysis_run_button,
            self.analysis_clear_button,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)
        if enabled:
            self._update_analysis_parameter_state()
            self._update_analysis_export_state()
        else:
            self.analysis_export_json_button.setEnabled(False)
            self.analysis_export_csv_button.setEnabled(False)
            for widget in [
                self.analysis_axis_combo,
                self.analysis_percentiles_input,
                self.analysis_nan_policy_combo,
                self.analysis_bands_input,
                self.analysis_frequency_range_input,
                self.analysis_rolloff_input,
                self.analysis_average_channels_checkbox,
                self.analysis_sta_input,
                self.analysis_lta_input,
                self.analysis_trigger_on_input,
                self.analysis_trigger_off_input,
                self.analysis_threshold_input,
                self.analysis_smooth_samples_input,
                self.analysis_min_duration_input,
                self.analysis_merge_gap_input,
                self.analysis_max_events_input,
                self.analysis_roi_text,
                self.analysis_use_event_rois_checkbox,
                self.analysis_padding_samples_input,
                self.analysis_padding_channels_input,
                self.analysis_max_rois_input,
                self.analysis_window_samples_input,
                self.analysis_step_samples_input,
                self.analysis_channel_lag_input,
                self.analysis_denoise_workflow_input,
            ]:
                widget.setEnabled(False)

    def _update_analysis_export_state(self) -> None:
        if not hasattr(self, "analysis_export_json_button"):
            return
        idle = self._active_task_id is None
        has_result = self._latest_analysis_result is not None and self._latest_analysis_request is not None
        self.analysis_export_json_button.setEnabled(idle and has_result)
        self.analysis_export_csv_button.setEnabled(idle and bool(self._latest_analysis_rows))

    def _check_selection_memory(
        self,
        operation_name: str,
        *,
        time_slice: slice | None = None,
        channel_slice: slice | None = None,
        downsample: int | tuple[int, int] | None = None,
        info_widget: Any | None = None,
        max_bytes: int | None = None,
    ) -> bool:
        if self._current_metadata is None:
            return True
        try:
            estimate = gui_selection_estimate(
                self._current_metadata,
                time_start=None if time_slice is None else time_slice.start,
                time_stop=None if time_slice is None else time_slice.stop,
                time_step=None if time_slice is None else time_slice.step,
                channel_start=None if channel_slice is None else channel_slice.start,
                channel_stop=None if channel_slice is None else channel_slice.stop,
                channel_step=None if channel_slice is None else channel_slice.step,
                downsample=downsample,
                max_bytes=self._gui_max_selection_bytes if max_bytes is None else max_bytes,
                operation_name=operation_name,
            )
        except Exception as exc:  # noqa: BLE001 - GUI boundary should catch and display all errors.
            message = format_error_message(exc)
            if info_widget is not None:
                info_widget.setPlainText(f"Selection check failed.\n\n{message}")
            self.statusBar().showMessage(f"Error: {message}")
            _qt_widgets().QMessageBox.critical(self, f"DAS View {operation_name} error", message)
            return False
        if estimate.within_limit:
            self.statusBar().showMessage(estimate.message)
            return True
        if info_widget is not None:
            info_widget.setPlainText(estimate.message)
        self.statusBar().showMessage(estimate.message)
        _qt_widgets().QMessageBox.warning(
            self,
            f"DAS View {operation_name} selection",
            estimate.message,
        )
        return False

    def _analysis_rows_for_result(self, result: Any, request: AnalysisRequest) -> list[dict[str, Any]]:
        if request.analysis_type in {"events_stalta", "events_envelope"}:
            return candidates_to_table_rows(result.result.candidates)
        if request.analysis_type == "roi_statistics":
            return roi_statistics_to_table_rows(result.results)
        if request.analysis_type == "qc_report":
            return format_qc_rows(result)
        if request.analysis_type == "bad_channels":
            return format_bad_channel_rows(result)
        if request.analysis_type == "multiband_summary":
            return format_multiband_rows(result)
        if request.analysis_type == "denoise_report":
            return format_denoise_report_rows(result)
        if request.analysis_type == "moveout_summary":
            return format_moveout_summary_rows(result)
        if request.analysis_type == "directional_energy":
            return format_directional_energy_rows(result)
        if request.analysis_type == "band_energy":
            band_result = result.result
            rows = []
            for index, band in enumerate(band_result.bands):
                rows.append(
                    {
                        "band": f"{band[0]:g}-{band[1]:g}",
                        "band_energy": self._table_value(band_result.band_energy[index]),
                        "band_energy_ratio": self._table_value(band_result.band_energy_ratio[index]),
                        "average_channels": band_result.average_channels,
                    }
                )
            return rows
        if request.analysis_type == "spectral_attributes":
            attr = result.result
            return [
                {
                    "dominant_frequency_hz": self._table_value(attr.dominant_frequency_hz),
                    "spectral_centroid_hz": self._table_value(attr.spectral_centroid_hz),
                    "spectral_bandwidth_hz": self._table_value(attr.spectral_bandwidth_hz),
                    "spectral_rolloff_hz": self._table_value(attr.spectral_rolloff_hz),
                    "total_energy": self._table_value(attr.total_energy),
                }
            ]
        if request.analysis_type == "statistics":
            stats = result.result
            return [
                {
                    "count": self._table_value(stats.count),
                    "finite_count": self._table_value(stats.finite_count),
                    "nan_count": self._table_value(stats.nan_count),
                    "mean": self._table_value(stats.mean),
                    "std": self._table_value(stats.std),
                    "rms": self._table_value(stats.rms),
                    "energy": self._table_value(stats.energy),
                    "min": self._table_value(stats.min),
                    "max": self._table_value(stats.max),
                }
            ]
        return []

    def _populate_analysis_table(self, rows: list[dict[str, Any]]) -> None:
        self._clear_analysis_table()
        if not rows:
            return
        columns: list[str] = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
        self.analysis_table.setColumnCount(len(columns))
        self.analysis_table.setRowCount(len(rows))
        self.analysis_table.setHorizontalHeaderLabels(columns)
        for row_index, row in enumerate(rows):
            for column_index, column in enumerate(columns):
                item = _qt_widgets().QTableWidgetItem(str(row.get(column, "")))
                self.analysis_table.setItem(row_index, column_index, item)
        self.analysis_table.resizeColumnsToContents()

    def _analysis_export_payload(self) -> dict[str, Any]:
        request = self._latest_analysis_request
        result = self._latest_analysis_result
        return {
            "analysis_type": None if request is None else request.analysis_type,
            "summary": [] if request is None or result is None else format_analysis_summary(result, request),
            "rows": self._latest_analysis_rows,
        }

    def _table_value(self, value: Any) -> Any:
        try:
            import numpy as np

            array = np.asarray(value)
            if array.ndim == 0:
                scalar = array.item()
                if isinstance(scalar, float):
                    return float(scalar)
                return scalar
            return array.tolist()
        except Exception:  # noqa: BLE001 - best-effort display conversion.
            return value
