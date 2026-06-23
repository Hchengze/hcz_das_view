import ast
from types import SimpleNamespace

import numpy as np
import pytest

from das_view.analysis.qc import data_quality_report
from das_view.gui.models import (
    format_bad_channel_rows,
    format_denoise_report_rows,
    format_denoise_report_summary,
    format_directional_energy_rows,
    format_directional_energy_summary,
    format_moveout_summary,
    format_moveout_summary_rows,
    format_multiband_rows,
    format_multiband_summary,
    format_qc_rows,
    format_qc_summary,
    parse_analysis_request,
    parse_denoise_request,
    parse_denoise_workflow,
    parse_moveout_request,
    parse_multiband_request,
    parse_qc_request,
)
from das_view.processing.denoise import apply_denoise_workflow


def test_advanced_analysis_request_parsers():
    qc = parse_qc_request(time_start_text="0", time_stop_text="100")
    bad = parse_analysis_request(analysis_type="Bad channels")
    multiband = parse_multiband_request(
        bands_text="1-5,5-20",
        window_samples=64,
        step_samples=32,
    )
    denoise = parse_denoise_request(
        denoise_workflow="common_mode_removal:method=median;channel_balance:target=rms"
    )
    moveout = parse_moveout_request(window_samples=128, step_samples=64, channel_lag=2)
    directional = parse_analysis_request(analysis_type="Directional energy")

    assert qc.analysis_type == "qc_report"
    assert bad.analysis_type == "bad_channels"
    assert multiband.analysis_type == "multiband_summary"
    assert multiband.bands == ((1.0, 5.0), (5.0, 20.0))
    assert multiband.window_samples == 64
    assert multiband.step_samples == 32
    assert denoise.analysis_type == "denoise_report"
    assert denoise.denoise_steps[1] == ("channel_balance", {"target": "rms"})
    assert moveout.analysis_type == "moveout_summary"
    assert moveout.channel_lag == 2
    assert directional.analysis_type == "directional_energy"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"bands_text": "10-1"}, "0 <= low < high"),
        ({"window_samples": 32, "step_samples": 64}, "step_samples"),
    ],
)
def test_multiband_request_rejects_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        parse_multiband_request(**kwargs)


def test_denoise_workflow_parser_rejects_invalid_values():
    assert parse_denoise_workflow("") == (("common_mode_removal", {"method": "median"}),)
    with pytest.raises(ValueError, match="unsupported denoise step"):
        parse_denoise_request(denoise_workflow="neural_magic")
    with pytest.raises(ValueError, match="key=value"):
        parse_denoise_request(denoise_workflow="common_mode_removal:method")


def test_qc_summary_and_rows_are_display_ready():
    data = np.ones((32, 4), dtype=float)
    data[:, 1] = 0.0
    data[3, 2] = 1_000.0
    report = data_quality_report(data)
    service_result = SimpleNamespace(result=report)

    lines = format_qc_summary(service_result)
    rows = format_qc_rows(service_result)
    bad_rows = format_bad_channel_rows(service_result)

    assert any("n_channels: 4" in line for line in lines)
    assert any("data-quality review aids" in line for line in lines)
    assert rows and {"channel", "rms", "quality_score", "flags"}.issubset(rows[0])
    assert all("reason" in row for row in bad_rows)


def test_multiband_summary_and_rows_are_display_ready():
    result = SimpleNamespace(
        values=np.array([[[1.0, 3.0], [2.0, 2.0]], [[4.0, 4.0], [1.0, 9.0]]]),
        feature_names=("1-5 Hz", "5-20 Hz"),
        window_samples=64,
        step_samples=32,
        metadata={"bands": ((1.0, 5.0), (5.0, 20.0))},
    )
    service_result = SimpleNamespace(result=result)

    lines = format_multiband_summary(service_result)
    rows = format_multiband_rows(service_result)

    assert "window_samples: 64" in lines
    assert "n_bands: 2" in lines
    assert rows[0]["band"] == "1-5 Hz"
    assert {"mean_energy", "max_energy", "mean_ratio"}.issubset(rows[0])


def test_denoise_report_summary_and_rows_are_display_ready():
    data = np.arange(64, dtype=float).reshape(16, 4)
    result = apply_denoise_workflow(
        data,
        [("common_mode_removal", {"method": "median"})],
        return_report=True,
    )
    service_result = SimpleNamespace(result=result.report)

    lines = format_denoise_report_summary(service_result)
    rows = format_denoise_report_rows(service_result)

    assert "steps: 1" in lines
    assert any("signal-review aids" in line for line in lines)
    assert rows[0]["method"] == "common_mode_removal"
    assert "after_energy" in rows[0]


def test_moveout_and_directional_energy_formatters_are_display_ready():
    directional = SimpleNamespace(
        positive_wavenumber_energy=10.0,
        negative_wavenumber_energy=4.0,
        zero_wavenumber_energy=1.0,
        directional_ratio=0.6,
        dominant_direction="positive_k",
        velocity_band_energy={"slow": 2.0},
    )
    moveout_report = SimpleNamespace(
        directional_energy=directional,
        summary={
            "directional_ratio": 0.6,
            "dominant_direction": "positive_k",
            "median_apparent_velocity_mps": 1200.0,
            "mean_abs_correlation_peak": 0.8,
            "n_windows": 3,
            "n_channel_pairs": 4,
        },
    )

    moveout_result = SimpleNamespace(result=moveout_report)
    directional_result = SimpleNamespace(result=directional)

    moveout_lines = format_moveout_summary(moveout_result)
    moveout_rows = format_moveout_summary_rows(moveout_result)
    directional_lines = format_directional_energy_summary(directional_result)
    directional_rows = format_directional_energy_rows(directional_result)

    assert any("auxiliary attribute" in line for line in moveout_lines)
    assert any("not localization or inversion" in line for line in moveout_lines)
    assert moveout_rows[0]["dominant_direction"] == "positive_k"
    assert any("FK-domain review attribute" in line for line in directional_lines)
    assert directional_rows[-1]["component"] == "velocity_band:slow"


def test_gui_models_remain_pyqt_free_for_advanced_analysis():
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
