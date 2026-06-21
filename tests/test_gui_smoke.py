import pytest

from das_view.gui.models import (
    PreviewDisplayInfo,
    format_error_message,
    format_task_status,
    parse_channel_indices,
    parse_preview_limits,
    should_apply_task_result,
    task_control_state,
)
from das_view.gui.workers import PreviewWorker, WaveformWorker


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
    assert running.cancel_enabled
    assert running.progress_visible
    assert running.progress_minimum == running.progress_maximum == 0

    assert idle.open_enabled
    assert idle.preview_controls_enabled
    assert idle.waveform_controls_enabled
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


def test_callable_workers_store_service_parameters():
    preview = PreviewWorker("sample.h5", max_samples=10, max_channels=5)
    waveform = WaveformWorker("sample.h5", channels=(1, 3), time_step=4)

    assert preview.path.name == "sample.h5"
    assert preview.max_samples == 10
    assert preview.max_channels == 5
    assert waveform.path.name == "sample.h5"
    assert waveform.channels == (1, 3)
    assert waveform.time_step == 4


def test_qt_workers_can_be_constructed_and_cancelled_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")

    from das_view.gui.workers import QtPreviewWorker, QtWaveformWorker

    preview = QtPreviewWorker("sample.h5", max_samples=10, max_channels=5)
    waveform = QtWaveformWorker("sample.h5", channels=(1, 3), time_step=4)

    assert not preview.is_cancelled()
    assert not waveform.is_cancelled()
    preview.cancel()
    waveform.cancel()
    assert preview.is_cancelled()
    assert waveform.is_cancelled()


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
    assert window.plot_tabs.count() == 2
    assert window.waveform_channel_input.text() == "0"
    assert window.waveform_time_step_input.value() == 1
    assert window.progress_bar is not None
    assert window.cancel_button is not None
    assert window.progress_bar.isHidden()
    assert not window.cancel_button.isEnabled()
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
    assert window.cancel_button.isEnabled()
    assert not window.progress_bar.isHidden()

    window._apply_task_control_state(is_running=False)
    assert window.open_action.isEnabled()
    assert window.max_samples_input.isEnabled()
    assert window.max_channels_input.isEnabled()
    assert window.waveform_button.isEnabled()
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
