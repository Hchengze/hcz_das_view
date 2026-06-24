import numpy as np
import pytest

from das_view.gui.models import (
    AnalysisRequest,
    format_bad_channel_rows,
    format_denoise_report_rows,
    format_directional_energy_rows,
    format_moveout_summary_rows,
    format_multiband_rows,
    format_qc_rows,
    parse_analysis_request,
    parse_denoise_request,
    parse_moveout_request,
    parse_multiband_request,
    parse_qc_request,
)
from das_view.gui.workers import AnalysisWorker
from tests.test_hdf5_zd_reader import create_zd_h5

pytest.importorskip("h5py")


def _make_zd_file(tmp_path):
    path = tmp_path / "gui_advanced.h5"
    t = np.arange(256, dtype=np.float32) / 1000.0
    data = np.column_stack(
        [
            np.sin(2 * np.pi * 20.0 * t),
            np.sin(2 * np.pi * 40.0 * t),
            np.zeros_like(t),
            np.sin(2 * np.pi * 10.0 * t) + 0.1 * np.arange(t.size, dtype=np.float32),
        ]
    ).astype(np.float32)
    create_zd_h5(path, data)
    return path


def test_advanced_analysis_workers_run_on_synthetic_zd_hdf5(tmp_path):
    path = _make_zd_file(tmp_path)

    qc_result = AnalysisWorker(path, request=parse_qc_request(max_samples=128)).run()
    denoise_result = AnalysisWorker(path, request=parse_denoise_request(max_samples=128)).run()
    moveout_result = AnalysisWorker(
        path,
        request=parse_moveout_request(max_samples=128, window_samples=64, step_samples=32),
    ).run()

    assert qc_result.reader_name == "zd_hdf5"
    assert format_qc_rows(qc_result)
    assert denoise_result.reader_name == "zd_hdf5"
    assert format_denoise_report_rows(denoise_result)
    assert moveout_result.reader_name == "zd_hdf5"
    assert format_moveout_summary_rows(moveout_result)


def test_multiband_and_directional_workers_run_on_synthetic_zd_hdf5(tmp_path):
    path = _make_zd_file(tmp_path)

    multiband_result = AnalysisWorker(
        path,
        request=parse_multiband_request(
            max_samples=128,
            bands_text="5-30,30-80",
            window_samples=64,
            step_samples=32,
        ),
    ).run()
    directional_result = AnalysisWorker(
        path,
        request=parse_analysis_request(analysis_type="Directional energy", max_samples=128),
    ).run()

    assert format_multiband_rows(multiband_result)
    assert format_directional_energy_rows(directional_result)


def test_bad_channel_worker_uses_quality_report_rows(tmp_path):
    path = _make_zd_file(tmp_path)
    request = parse_analysis_request(analysis_type="Bad channels", max_samples=128)

    result = AnalysisWorker(path, request=request).run()

    assert result.result.bad_channel_indices
    rows = format_bad_channel_rows(result)
    assert rows
    assert {"channel", "reason", "quality_score"}.issubset(rows[0])


def test_main_window_contains_advanced_analysis_types_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    values = [
        window.analysis_type_combo.itemData(index)
        for index in range(window.analysis_type_combo.count())
    ]

    assert "质量控制报告" in [
        window.analysis_type_combo.itemText(index)
        for index in range(window.analysis_type_combo.count())
    ]
    assert "qc_report" in values
    assert "multiband_summary" in values
    assert "directional_energy" in values
    window.language_combo.setCurrentIndex(window.language_combo.findData("en_US"))
    labels = [
        window.analysis_type_combo.itemText(index)
        for index in range(window.analysis_type_combo.count())
    ]
    assert "QC report" in labels
    assert "Denoise report" in labels
    assert "Moveout summary" in labels
    assert not window.analysis_export_json_button.isEnabled()
    assert not window.analysis_export_csv_button.isEnabled()
    window.close()
    app.processEvents()


def test_main_window_advanced_parameter_state_and_clear_when_pyqt5_is_available():
    pytest.importorskip("PyQt5")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)

    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()

    window.analysis_type_combo.setCurrentIndex(window.analysis_type_combo.findData("multiband_summary"))
    window._update_analysis_parameter_state()
    assert window.analysis_bands_input.isEnabled()
    assert window.analysis_window_samples_input.isEnabled()
    assert window.analysis_step_samples_input.isEnabled()

    window.analysis_type_combo.setCurrentIndex(window.analysis_type_combo.findData("denoise_report"))
    window._update_analysis_parameter_state()
    assert window.analysis_denoise_workflow_input.isEnabled()

    window.analysis_type_combo.setCurrentIndex(window.analysis_type_combo.findData("moveout_summary"))
    window._update_analysis_parameter_state()
    assert window.analysis_channel_lag_input.isEnabled()

    window._latest_analysis_result = object()
    window._latest_analysis_request = AnalysisRequest("qc_report")
    window._latest_analysis_rows = [{"channel": 0}]
    window._update_analysis_export_state()
    assert window.analysis_export_json_button.isEnabled()
    assert window.analysis_export_csv_button.isEnabled()
    window.clear_analysis_results()
    assert not window.analysis_export_json_button.isEnabled()
    assert not window.analysis_export_csv_button.isEnabled()
    window.close()
    app.processEvents()
