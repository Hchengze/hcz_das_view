import ast

import pytest

from das_view.core.data_model import DASMetadata
from das_view.gui.models import (
    GUI_DEFAULT_MAX_SELECTION_BYTES,
    estimate_gui_selection_memory,
    format_gui_file_summary,
    format_gui_selection_warning,
    gui_large_file_warning,
    gui_safe_selection_presets,
    gui_selection_estimate,
)
from das_view.utils.memory import estimate_array_nbytes, estimate_selection_nbytes


def test_estimate_gui_selection_memory_defaults_to_full_selection():
    metadata = DASMetadata(n_samples=100, n_channels=20, sample_rate_hz=50.0)

    estimated = estimate_gui_selection_memory(metadata)

    assert estimated == estimate_array_nbytes(100, 20)


def test_estimate_gui_selection_memory_supports_slices_steps_and_downsample():
    metadata = DASMetadata(n_samples=1000, n_channels=100, dx_m=2.0)

    estimated = estimate_gui_selection_memory(
        metadata,
        time_start=100,
        time_stop=500,
        time_step=2,
        channel_start=10,
        channel_stop=60,
        channel_step=5,
        downsample=(2, 1),
    )

    assert estimated == estimate_selection_nbytes(
        n_samples=1000,
        n_channels=100,
        time_slice=slice(100, 500, 2),
        channel_slice=slice(10, 60, 5),
        downsample=(2, 1),
    )


def test_gui_file_summary_handles_missing_sample_rate_and_dx():
    metadata = DASMetadata(n_samples=128, n_channels=8)

    lines = format_gui_file_summary(metadata, reader_name="synthetic")

    text = "\n".join(lines)
    assert "Reader: synthetic" in text
    assert "sample_rate_hz: unknown" in text
    assert "duration_seconds: unknown" in text
    assert "dx_m: unknown" in text
    assert "estimated full array size:" in text


def test_format_gui_selection_warning_reports_large_selection():
    message = format_gui_selection_warning(
        300 * 1024 * 1024,
        max_bytes=GUI_DEFAULT_MAX_SELECTION_BYTES,
        operation_name="Analysis",
    )

    assert "Analysis selection is large" in message
    assert "bounded time/channel selection" in message


def test_gui_selection_estimate_marks_over_limit():
    metadata = DASMetadata(n_samples=1000, n_channels=1000)

    estimate = gui_selection_estimate(
        metadata,
        max_bytes=1024,
        operation_name="FK",
    )

    assert not estimate.within_limit
    assert estimate.estimated_bytes > 1024
    assert "FK selection is large" in estimate.message


def test_gui_large_file_warning_and_safe_presets():
    metadata = DASMetadata(n_samples=100_000, n_channels=1_000)

    assert gui_large_file_warning(metadata) is not None
    presets = gui_safe_selection_presets()
    assert presets["small_preview"] == (2000, 256)
    assert presets["analysis"] == (4096, 512)
    assert presets["fk"] == (2048, 256)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"time_start": 10, "time_stop": 1},
        {"channel_start": -1, "channel_stop": 5},
        {"time_step": 0},
        {"downsample": (1, 0)},
    ],
)
def test_estimate_gui_selection_memory_rejects_invalid_selection(kwargs):
    metadata = DASMetadata(n_samples=100, n_channels=10)

    with pytest.raises(ValueError):
        estimate_gui_selection_memory(metadata, **kwargs)


def test_gui_models_do_not_import_pyqt5():
    import das_view.gui.models as models

    source = models.__loader__.get_source(models.__name__)  # type: ignore[union-attr]
    assert source is not None
    tree = ast.parse(source)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
    assert all(not name.startswith("PyQt5") for name in imported_modules)
