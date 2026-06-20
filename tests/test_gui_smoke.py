import pytest

from das_view.gui.models import (
    PreviewDisplayInfo,
    format_error_message,
    parse_channel_indices,
    parse_preview_limits,
)


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
    window.close()
    app.processEvents()
