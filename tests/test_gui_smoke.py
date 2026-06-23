import pytest

from das_view.gui.models import (
    AnalysisRequest,
    PreviewDisplayInfo,
    candidates_to_table_rows,
    format_gui_file_summary,
    format_error_message,
    format_analysis_summary,
    format_fk_status,
    format_spectrum_status,
    format_task_status,
    parse_analysis_request,
    parse_analysis_selection,
    parse_band_ranges,
    parse_channel_indices,
    parse_frequency_range,
    parse_fk_request,
    parse_optional_nonnegative_int,
    parse_optional_positive_int,
    parse_percentiles,
    parse_preview_limits,
    parse_roi_text,
    parse_spectrum_request,
    roi_statistics_to_table_rows,
    should_apply_task_result,
    spectrum_analysis_label,
    task_control_state,
)
from das_view.analysis.events import EventCandidate
from das_view.analysis.roi import TimeChannelROI
from das_view.core.data_model import DASMetadata
from das_view.gui.workers import AnalysisWorker, FKWorker, PreviewWorker, SpectrumWorker, WaveformWorker


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
    assert info.loaded_status() == "Loaded: synthetic | preview=(10, 4) | downsample=(2, 3)"
    assert format_error_message(ValueError("bad file")) == "ValueError: bad file"


def test_gui_file_summary_includes_memory_and_safe_selection():
    metadata = DASMetadata(n_samples=4096, n_channels=512, sample_rate_hz=100.0, dx_m=2.0)

    lines = format_gui_file_summary(metadata, reader_name="synthetic")

    text = "\n".join(lines)
    assert "estimated full array size" in text
    assert "recommended preview selection" in text
    assert "recommended analysis selection" in text


def test_gui_task_status_helpers_are_pyqt_free():
    assert format_task_status("preview", "loading") == "Loading preview"
    assert format_task_status("waveform", "loaded") == "Loaded waveform"
    assert format_task_status("preview", "cancelled") == "Cancelled"
    assert format_task_status("waveform", "error", "bad channel") == "Error: bad channel"


def test_gui_task_result_helper_rejects_cancelled_or_stale_results():
    assert should_apply_task_result(task_id=3, active_task_id=3, was_cancelled=False)
    assert not should_apply_task_result(task_id=3, active_task_id=3, was_cancelled=True)
    assert not should_apply_task_result(task_id=2, active_task_id=3, was_cancelled=False)
    assert not should_apply_task_result(task_id=3, active_task_id=None, was_cancelled=False)


def test_gui_task_control_state_helper():
    running = task_control_state(True)
    idle = task_control_state(False)

    assert not running.open_enabled
    assert not running.preview_controls_enabled
    assert not running.waveform_controls_enabled
    assert not running.spectrum_controls_enabled
    assert not running.fk_controls_enabled
    assert not running.analysis_controls_enabled
    assert running.cancel_enabled
    assert running.progress_visible
    assert running.progress_minimum == running.progress_maximum == 0

    assert idle.open_enabled
    assert idle.preview_controls_enabled
    assert idle.waveform_controls_enabled
    assert idle.spectrum_controls_enabled
    assert idle.fk_controls_enabled
    assert idle.analysis_controls_enabled
    assert not idle.cancel_enabled
    assert not idle.progress_visible
    assert idle.progress_minimum == 0
    assert idle.progress_maximum == 100


def test_parse_preview_limits_accepts_positive_integer_values():
    limits = parse_preview_limits("2000", 500)

    assert limits.max_samples == 2000
    assert limits.max_channels == 500


@pytest.mark.parametrize(
    ("max_samples", "max_channels", "message"),
    [
        ("abc", 500, "must be integers"),
        (0, 500, "max_samples must be positive"),
        (2000, -1, "max_channels must be positive"),
    ],
)
def test_parse_preview_limits_rejects_invalid_values(max_samples, max_channels, message):
    with pytest.raises(ValueError, match=message):
        parse_preview_limits(max_samples, max_channels)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10", (10,)),
        ("10,20,30", (10, 20, 30)),
        ("10, 20, 30", (10, 20, 30)),
        ("2,2", (2, 2)),
    ],
)
def test_parse_channel_indices_accepts_supported_forms(text, expected):
    assert parse_channel_indices(text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "one or more"),
        ("1,,2", "one or more"),
        ("abc", "integer"),
        ("1, bad", "integer"),
        ("-1", "non-negative"),
    ],
)
def test_parse_channel_indices_rejects_invalid_input(text, message):
    with pytest.raises(ValueError, match=message):
        parse_channel_indices(text)


def test_spectrum_optional_integer_parsers():
    assert parse_optional_positive_int("", name="nfft") is None
    assert parse_optional_positive_int("512", name="nfft") == 512
    assert parse_optional_nonnegative_int("", name="noverlap") is None
    assert parse_optional_nonnegative_int("0", name="noverlap") == 0

    with pytest.raises(ValueError, match="nfft must be a positive integer"):
        parse_optional_positive_int("abc", name="nfft")
    with pytest.raises(ValueError, match="nfft must be a positive integer"):
        parse_optional_positive_int("0", name="nfft")
    with pytest.raises(ValueError, match="noverlap must be a non-negative integer"):
        parse_optional_nonnegative_int("-1", name="noverlap")


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Amplitude spectrum", "amplitude"),
        ("Power spectrum", "power"),
        ("PSD periodogram", "psd_periodogram"),
        ("PSD Welch", "psd_welch"),
        ("Spectrogram", "spectrogram"),
    ],
)
def test_parse_spectrum_request_maps_gui_labels(label, expected):
    request = parse_spectrum_request(
        analysis_type=label,
        channel_text="2",
        nfft_text="1024",
        nperseg_text="128",
        noverlap_text="64",
        db=True,
    )

    assert request.analysis_type == expected
    assert request.channel == 2
    assert request.nfft == 1024
    assert request.nperseg == 128
    assert request.noverlap == 64
    assert request.db is True


def test_parse_spectrum_request_defaults_and_validation():
    request = parse_spectrum_request(
        analysis_type="amplitude",
        channel_text="0",
        nfft_text="",
        nperseg_text="",
        noverlap_text="",
        db=False,
    )

    assert request.nfft is None
    assert request.nperseg == 256
    assert request.noverlap is None
    assert request.db is False

    with pytest.raises(ValueError, match="exactly one channel"):
        parse_spectrum_request(analysis_type="amplitude", channel_text="0,1")
    with pytest.raises(ValueError, match="noverlap must be less than nperseg"):
        parse_spectrum_request(
            analysis_type="spectrogram",
            channel_text="0",
            nperseg_text="128",
            noverlap_text="128",
        )


def test_format_spectrum_status_is_pyqt_free():
    request = parse_spectrum_request(
        analysis_type="PSD Welch",
        channel_text="3",
        nfft_text="512",
        nperseg_text="128",
        noverlap_text="64",
        db=True,
    )

    class AnalysisResult:
        frequencies_hz = [0.0, 1.0, 2.0]
        sample_rate_hz = 100.0

    class ServiceResult:
        reader_name = "synthetic"
        result = AnalysisResult()

    lines = format_spectrum_status(ServiceResult(), request)

    assert spectrum_analysis_label(request.analysis_type) == "PSD Welch"
    assert "Reader: synthetic" in lines
    assert "Analysis: PSD Welch" in lines
    assert "Channel: 3" in lines
    assert "Frequency bins: 3" in lines
    assert "PSD display: dB" in lines


def test_parse_fk_request_defaults_and_bounded_slices():
    request = parse_fk_request(
        mode="FK transform",
        output="Amplitude",
        time_start_text="",
        time_stop_text="",
        time_step=1,
        channel_start_text="",
        channel_stop_text="",
        channel_step=1,
        vmin_text="",
        vmax_text="",
        db=True,
    )

    assert request.mode == "transform"
    assert request.output == "amplitude"
    assert request.time_slice is None
    assert request.channel_slice is None
    assert request.downsample == (1, 1)
    assert request.vmin_mps is None
    assert request.vmax_mps is None
    assert request.db is True
    assert request.bounded_time_slice() == slice(0, 4096)
    assert request.bounded_channel_slice() == slice(0, 512)


def test_parse_fk_request_maps_filter_and_velocity_parameters():
    request = parse_fk_request(
        mode="FK velocity filter",
        output="Power",
        time_start_text="10",
        time_stop_text="100",
        time_step=2,
        channel_start_text="3",
        channel_stop_text="40",
        channel_step=4,
        vmin_text="300",
        vmax_text="3000",
        pass_inside=False,
    )

    assert request.mode == "velocity_filter"
    assert request.output == "power"
    assert request.time_slice == slice(10, 100)
    assert request.channel_slice == slice(3, 40)
    assert request.downsample == (2, 4)
    assert request.vmin_mps == 300.0
    assert request.vmax_mps == 3000.0
    assert request.pass_inside is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"time_step": 0}, "time_step must be a positive integer"),
        ({"channel_step": 0}, "channel_step must be a positive integer"),
        ({"vmin_text": "bad"}, "vmin_mps must be a number"),
        ({"vmin_text": "-1"}, "vmin_mps must be positive"),
        ({"mode": "FK velocity filter"}, "requires at least one"),
        ({"vmin_text": "3000", "vmax_text": "300"}, "vmin_mps must be smaller"),
        ({"mode": "unsupported mode"}, "unsupported FK mode"),
        ({"output": "phase"}, "unsupported FK output mode"),
    ],
)
def test_parse_fk_request_rejects_invalid_values(kwargs, message):
    params = {
        "mode": "FK transform",
        "output": "Amplitude",
        "time_start_text": "",
        "time_stop_text": "",
        "time_step": 1,
        "channel_start_text": "",
        "channel_stop_text": "",
        "channel_step": 1,
        "vmin_text": "",
        "vmax_text": "",
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        parse_fk_request(**params)


def test_parse_analysis_selection_and_common_ranges():
    time_slice, channel_slice, downsample, max_samples, max_channels = parse_analysis_selection(
        time_start_text="10",
        time_stop_text="100",
        time_step=2,
        channel_start_text="3",
        channel_stop_text="40",
        channel_step=4,
        max_samples="4096",
        max_channels="512",
    )

    assert time_slice == slice(10, 100)
    assert channel_slice == slice(3, 40)
    assert downsample == (2, 4)
    assert max_samples == 4096
    assert max_channels == 512

    assert parse_percentiles("1, 50, 99") == (1.0, 50.0, 99.0)
    assert parse_band_ranges("1-5,5-20") == ((1.0, 5.0), (5.0, 20.0))
    assert parse_frequency_range("1-80") == (1.0, 80.0)
    assert parse_frequency_range("") is None


def test_parse_analysis_request_maps_supported_types():
    statistics = parse_analysis_request(
        analysis_type="Statistics",
        axis="channel",
        percentiles_text="5,50,95",
    )
    band = parse_analysis_request(
        analysis_type="Band energy",
        bands_text="1-5,5-20",
        average_channels=True,
    )
    attrs = parse_analysis_request(
        analysis_type="Spectral attributes",
        frequency_range_text="1,80",
        rolloff_text="0.9",
    )
    stalta = parse_analysis_request(
        analysis_type="Event candidates - STA/LTA",
        sta_samples=10,
        lta_samples=100,
        trigger_on_text="3.0",
        trigger_off_text="1.5",
    )
    envelope = parse_analysis_request(
        analysis_type="Event candidates - Envelope threshold",
        threshold_text="0.8",
        smooth_samples_text="5",
    )
    roi = parse_analysis_request(
        analysis_type="ROI statistics",
        roi_text="0,100,0,4",
        use_event_rois=False,
        max_rois_text="3",
    )

    assert statistics.analysis_type == "statistics"
    assert statistics.axis == 1
    assert statistics.percentiles == (5.0, 50.0, 95.0)
    assert band.analysis_type == "band_energy"
    assert band.average_channels
    assert attrs.frequency_range == (1.0, 80.0)
    assert attrs.rolloff == 0.9
    assert stalta.analysis_type == "events_stalta"
    assert stalta.sta_samples == 10
    assert stalta.lta_samples == 100
    assert stalta.trigger_off == 1.5
    assert envelope.analysis_type == "events_envelope"
    assert envelope.threshold == 0.8
    assert envelope.smooth_samples == 5
    assert roi.analysis_type == "roi_statistics"
    assert roi.rois[0].start_sample == 0
    assert roi.rois[0].channel_end == 4
    assert roi.max_rois == 3


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"time_start_text": "10", "time_stop_text": "1"}, "time_start must be smaller"),
        ({"analysis_type": "unknown"}, "unsupported analysis type"),
        ({"percentiles_text": "101"}, "percentiles must be between"),
        ({"analysis_type": "Band energy", "bands_text": "5-1"}, "0 <= low < high"),
        ({"analysis_type": "Spectral attributes", "frequency_range_text": "80-1"}, "0 <= low < high"),
        (
            {"analysis_type": "Event candidates - STA/LTA", "sta_samples": 100, "lta_samples": 10},
            "lta_samples must be greater",
        ),
        (
            {
                "analysis_type": "Event candidates - STA/LTA",
                "trigger_on_text": "2",
                "trigger_off_text": "3",
            },
            "trigger_off must be less",
        ),
        ({"analysis_type": "ROI statistics", "roi_text": "0,10,1"}, "ROI rows"),
    ],
)
def test_parse_analysis_request_rejects_invalid_values(kwargs, message):
    params = {"analysis_type": "Statistics"}
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        parse_analysis_request(**params)


def test_parse_roi_text_and_analysis_table_rows():
    rois = parse_roi_text("0,100,0,4\n200,300")

    assert len(rois) == 2
    assert rois[0].roi_id == "manual_001"
    assert rois[0].n_channels == 4
    assert rois[1].channel_start is None

    candidate = EventCandidate(
        event_id=1,
        start_sample=10,
        end_sample=20,
        duration_samples=10,
        channel_start=2,
        channel_end=2,
        peak_sample=15,
        peak_channel=2,
        peak_value=5.0,
        mean_value=3.0,
        max_value=5.0,
        score=5.0,
    )
    rows = candidates_to_table_rows([candidate])
    assert rows[0]["event_id"] == 1
    assert rows[0]["score"] == 5.0
    assert roi_statistics_to_table_rows([]) == []


def test_format_analysis_summary_is_pyqt_free_for_statistics_and_events():
    request = parse_analysis_request(analysis_type="Statistics")

    class Stats:
        axis = None
        input_shape = (10, 4)
        count = 40
        finite_count = 40
        nan_count = 0
        posinf_count = 0
        neginf_count = 0
        mean = 1.0
        std = 0.5
        rms = 1.1
        energy = 12.0
        min = 0.0
        max = 2.0
        percentiles = {50.0: 1.0}

    class Selection:
        time_slice = slice(0, 10, 1)
        channel_slice = slice(0, 4, 1)
        downsample = (1, 1)

    class ServiceResult:
        reader_name = "synthetic"
        result = Stats()
        selection = Selection()
        preprocessing_history = ()

    lines = format_analysis_summary(ServiceResult(), request)
    assert "Reader: synthetic" in lines
    assert "Analysis: Statistics" in lines
    assert "mean: 1" in lines

    event_request = parse_analysis_request(analysis_type="Event candidates - Envelope threshold")

    class EventResult:
        method = "envelope"
        feature = type("Feature", (), {"shape": (10, 4)})()
        candidates = ()

    class EventServiceResult:
        reader_name = "synthetic"
        result = EventResult()
        selection = Selection()
        preprocessing_history = ()

    event_lines = format_analysis_summary(EventServiceResult(), event_request)
    assert "Event candidates: 0" in event_lines
    assert any("not location" in line for line in event_lines)


def test_format_fk_status_is_pyqt_free_for_transform_and_filter():
    transform_request = parse_fk_request(mode="FK transform", output="Power", db=True)

    class Selection:
        time_slice = slice(0, 20)
        channel_slice = slice(0, 8)
        downsample = (1, 1)

    class FKResult:
        sample_rate_hz = 100.0
        dx_m = 2.0
        frequencies_hz = [0.0, 1.0]
        wavenumbers_cycles_per_m = [-0.25, 0.0, 0.25]
        output = "power"

    class FKServiceResult:
        reader_name = "synthetic"
        result = FKResult()
        selection = Selection()

    lines = format_fk_status(FKServiceResult(), transform_request)

    assert "Reader: synthetic" in lines
    assert "Mode: FK transform" in lines
    assert "Frequency bins: 2" in lines
    assert "Wavenumber bins: 3" in lines
    assert "Display: dB" in lines

    filter_request = parse_fk_request(
        mode="FK velocity filter",
        output="Amplitude",
        vmin_text="300",
        vmax_text="3000",
    )

    class Array:
        shape = (20, 8)

    class DASData:
        data = Array()

    class Mask:
        shape = (11, 8)

    class FilterResult:
        vmin_mps = 300.0
        vmax_mps = 3000.0
        pass_inside = True
        das_data = DASData()
        mask = Mask()

    class FilterServiceResult:
        reader_name = "synthetic"
        result = FilterResult()
        selection = Selection()
        preprocessing_history = ()

    filter_lines = format_fk_status(FilterServiceResult(), filter_request)

    assert "Mode: FK velocity filter" in filter_lines
    assert "vmin_mps: 300.0" in filter_lines
    assert "Fan mode: pass velocity range" in filter_lines
    assert "Filtered shape: (20, 8)" in filter_lines


def test_callable_workers_store_service_parameters():
    preview = PreviewWorker("sample.h5", max_samples=10, max_channels=5)
    waveform = WaveformWorker("sample.h5", channels=(1, 3), time_step=4)
    spectrum_request = parse_spectrum_request(
        analysis_type="Power spectrum",
        channel_text="2",
        nfft_text="1024",
    )
    spectrum = SpectrumWorker("sample.h5", request=spectrum_request)
    fk_request = parse_fk_request(mode="FK velocity filter", output="Amplitude", vmin_text="300")
    fk = FKWorker("sample.h5", request=fk_request)
    analysis_request = parse_analysis_request(analysis_type="Statistics")
    analysis = AnalysisWorker("sample.h5", request=analysis_request)

    assert preview.path.name == "sample.h5"
    assert preview.max_samples == 10
    assert preview.max_channels == 5
    assert waveform.path.name == "sample.h5"
    assert waveform.channels == (1, 3)
    assert waveform.time_step == 4
    assert spectrum.path.name == "sample.h5"
    assert spectrum.request.analysis_type == "power"
    assert spectrum.request.channel == 2
    assert fk.path.name == "sample.h5"
    assert fk.request.mode == "velocity_filter"
    assert analysis.path.name == "sample.h5"
    assert analysis.request.analysis_type == "statistics"


def test_qt_workers_can_be_constructed_and_cancelled_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")

    from das_view.gui.workers import (
        QtAnalysisWorker,
        QtFKWorker,
        QtPreviewWorker,
        QtSpectrumWorker,
        QtWaveformWorker,
    )

    preview = QtPreviewWorker("sample.h5", max_samples=10, max_channels=5)
    waveform = QtWaveformWorker("sample.h5", channels=(1, 3), time_step=4)
    spectrum = QtSpectrumWorker(
        "sample.h5",
        request=parse_spectrum_request(analysis_type="Spectrogram", channel_text="0"),
    )
    fk = QtFKWorker("sample.h5", request=parse_fk_request(mode="FK transform", output="Amplitude"))
    analysis = QtAnalysisWorker(
        "sample.h5",
        request=parse_analysis_request(analysis_type="Statistics"),
    )

    assert not preview.is_cancelled()
    assert not waveform.is_cancelled()
    assert not spectrum.is_cancelled()
    assert not fk.is_cancelled()
    assert not analysis.is_cancelled()
    preview.cancel()
    waveform.cancel()
    spectrum.cancel()
    fk.cancel()
    analysis.cancel()
    assert preview.is_cancelled()
    assert waveform.is_cancelled()
    assert spectrum.is_cancelled()
    assert fk.is_cancelled()
    assert analysis.is_cancelled()


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
    assert window.max_samples_input.value() == 2000
    assert window.max_channels_input.value() == 500
    assert window.plot_tabs.count() == 5
    assert window.plot_tabs.tabText(2) == "Spectrum"
    assert window.plot_tabs.tabText(3) == "FK"
    assert window.plot_tabs.tabText(4) == "Analysis"
    assert window.waveform_channel_input.text() == "0"
    assert window.waveform_time_step_input.value() == 1
    assert window.spectrum_channel_input.text() == "0"
    assert window.spectrum_type_combo.currentText() == "Amplitude spectrum"
    assert window.spectrum_nfft_input.text() == ""
    assert window.spectrum_nperseg_input.text() == "256"
    assert window.spectrum_noverlap_input.text() == ""
    assert window.spectrum_button.text() == "Run spectrum"
    assert window.fk_time_start_input.text() == ""
    assert window.fk_time_stop_input.text() == ""
    assert window.fk_time_step_input.value() == 1
    assert window.fk_channel_start_input.text() == ""
    assert window.fk_channel_stop_input.text() == ""
    assert window.fk_channel_step_input.value() == 1
    assert window.fk_mode_combo.currentText() == "FK transform"
    assert window.fk_output_combo.currentText() == "Amplitude"
    assert window.fk_vmin_input.text() == ""
    assert window.fk_vmax_input.text() == ""
    assert window.fk_pass_inside_checkbox.isChecked()
    assert window.fk_button.text() == "Run FK"
    assert window.display_backend_combo.currentData() == "matplotlib"
    assert window.analysis_type_combo.currentText() == "Statistics"
    assert window.analysis_run_button.text() == "Run analysis"
    assert window.analysis_export_json_button.text() == "Export JSON"
    assert window.analysis_export_csv_button.text() == "Export CSV"
    assert not window.analysis_export_json_button.isEnabled()
    assert not window.analysis_export_csv_button.isEnabled()
    assert window.analysis_clear_button.text() == "Clear results"
    assert window.analysis_time_step_input.value() == 1
    assert window.analysis_channel_step_input.value() == 1
    assert window.progress_bar is not None
    assert window.cancel_button is not None
    assert window.progress_bar.isHidden()
    assert not window.cancel_button.isEnabled()
    window.close()
    app.processEvents()


def test_main_window_display_backend_combo_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    assert window.display_backend_combo.currentData() == "matplotlib"
    values = [
        window.display_backend_combo.itemData(index)
        for index in range(window.display_backend_combo.count())
    ]
    assert values == ["matplotlib", "pyqtgraph"]
    assert window._display_backend == "matplotlib"
    assert window.waterfall_stack.currentWidget() is window.waterfall_matplotlib_panel
    window.close()
    app.processEvents()


def test_main_window_task_controls_switch_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    window._apply_task_control_state(is_running=True)
    assert not window.open_action.isEnabled()
    assert not window.max_samples_input.isEnabled()
    assert not window.max_channels_input.isEnabled()
    assert not window.waveform_button.isEnabled()
    assert not window.spectrum_channel_input.isEnabled()
    assert not window.spectrum_type_combo.isEnabled()
    assert not window.spectrum_nfft_input.isEnabled()
    assert not window.spectrum_nperseg_input.isEnabled()
    assert not window.spectrum_noverlap_input.isEnabled()
    assert not window.spectrum_db_checkbox.isEnabled()
    assert not window.spectrum_button.isEnabled()
    assert not window.fk_time_start_input.isEnabled()
    assert not window.fk_time_stop_input.isEnabled()
    assert not window.fk_time_step_input.isEnabled()
    assert not window.fk_channel_start_input.isEnabled()
    assert not window.fk_channel_stop_input.isEnabled()
    assert not window.fk_channel_step_input.isEnabled()
    assert not window.fk_mode_combo.isEnabled()
    assert not window.fk_output_combo.isEnabled()
    assert not window.fk_db_checkbox.isEnabled()
    assert not window.fk_vmin_input.isEnabled()
    assert not window.fk_vmax_input.isEnabled()
    assert not window.fk_pass_inside_checkbox.isEnabled()
    assert not window.fk_button.isEnabled()
    assert not window.analysis_type_combo.isEnabled()
    assert not window.analysis_run_button.isEnabled()
    assert window.cancel_button.isEnabled()
    assert not window.progress_bar.isHidden()

    window._apply_task_control_state(is_running=False)
    assert window.open_action.isEnabled()
    assert window.max_samples_input.isEnabled()
    assert window.max_channels_input.isEnabled()
    assert window.waveform_button.isEnabled()
    assert window.spectrum_channel_input.isEnabled()
    assert window.spectrum_type_combo.isEnabled()
    assert window.spectrum_nfft_input.isEnabled()
    assert window.spectrum_nperseg_input.isEnabled()
    assert window.spectrum_noverlap_input.isEnabled()
    assert window.spectrum_db_checkbox.isEnabled()
    assert window.spectrum_button.isEnabled()
    assert window.fk_time_start_input.isEnabled()
    assert window.fk_time_stop_input.isEnabled()
    assert window.fk_time_step_input.isEnabled()
    assert window.fk_channel_start_input.isEnabled()
    assert window.fk_channel_stop_input.isEnabled()
    assert window.fk_channel_step_input.isEnabled()
    assert window.fk_mode_combo.isEnabled()
    assert window.fk_output_combo.isEnabled()
    assert window.fk_db_checkbox.isEnabled()
    assert window.fk_vmin_input.isEnabled()
    assert window.fk_vmax_input.isEnabled()
    assert window.fk_pass_inside_checkbox.isEnabled()
    assert window.fk_button.isEnabled()
    assert window.analysis_type_combo.isEnabled()
    assert window.analysis_run_button.isEnabled()
    assert not window.cancel_button.isEnabled()
    assert window.progress_bar.isHidden()
    window.close()
    app.processEvents()


def test_main_window_cancel_requests_soft_cancel_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    class FakeWorker:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    worker = FakeWorker()
    window._task_worker = worker
    window._active_task_id = 1
    window._task_kind = "waveform"
    window.cancel_button.setEnabled(True)

    window.cancel_active_task()

    assert worker.cancelled
    assert window._task_cancel_requested
    assert not window.cancel_button.isEnabled()
    assert "Cancelling waveform" in window.waveform_info.toPlainText()
    window.close()
    app.processEvents()


def test_main_window_cancel_updates_spectrum_info_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    class FakeWorker:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    worker = FakeWorker()
    window._task_worker = worker
    window._active_task_id = 1
    window._task_kind = "spectrum"
    window.cancel_button.setEnabled(True)

    window.cancel_active_task()

    assert worker.cancelled
    assert window._task_cancel_requested
    assert "Cancelling spectrum" in window.spectrum_info.toPlainText()
    window.close()
    app.processEvents()


def test_main_window_cancel_updates_fk_info_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    class FakeWorker:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    worker = FakeWorker()
    window._task_worker = worker
    window._active_task_id = 1
    window._task_kind = "fk"
    window.cancel_button.setEnabled(True)

    window.cancel_active_task()

    assert worker.cancelled
    assert window._task_cancel_requested
    assert "Cancelling FK" in window.fk_info.toPlainText()
    window.close()
    app.processEvents()


def test_main_window_cancel_updates_analysis_info_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    class FakeWorker:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    worker = FakeWorker()
    window._task_worker = worker
    window._active_task_id = 1
    window._task_kind = "analysis"
    window.cancel_button.setEnabled(True)

    window.cancel_active_task()

    assert worker.cancelled
    assert window._task_cancel_requested
    assert "Cancelling analysis" in window.analysis_info.toPlainText()
    window.close()
    app.processEvents()


def test_main_window_analysis_results_clear_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    window._latest_analysis_result = object()
    window._latest_analysis_request = AnalysisRequest("statistics")
    window._latest_analysis_rows = [{"mean": 1.0}]
    window._latest_event_candidates = (object(),)
    window._update_analysis_export_state()
    assert window.analysis_export_json_button.isEnabled()
    assert window.analysis_export_csv_button.isEnabled()
    window.analysis_table.setColumnCount(1)
    window.analysis_table.setRowCount(1)

    window.clear_analysis_results()

    assert window._latest_analysis_result is None
    assert window._latest_analysis_request is None
    assert window._latest_analysis_rows == []
    assert window._latest_event_candidates == ()
    assert window.analysis_table.rowCount() == 0
    assert "Load a file" in window.analysis_info.toPlainText()
    assert not window.analysis_export_json_button.isEnabled()
    assert not window.analysis_export_csv_button.isEnabled()
    window.close()
    app.processEvents()
