import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib

matplotlib.use("Agg")

from das_view.processing.denoise import apply_denoise_workflow
from das_view.plotting import plot_before_after_waterfall, plot_enhancement_metrics


def test_plot_before_after_waterfall_and_metrics(tmp_path):
    data = np.column_stack([np.arange(16, dtype=float), np.arange(16, dtype=float) + 1])
    result = apply_denoise_workflow(data, [("common_mode_removal", {"method": "median"})])

    axes = plot_before_after_waterfall(data, result.data)
    path = tmp_path / "before_after.png"
    axes[0].figure.savefig(path)
    assert path.exists()

    ax = plot_enhancement_metrics(result.report)
    metrics_path = tmp_path / "metrics.png"
    ax.figure.savefig(metrics_path)
    assert metrics_path.exists()


def test_plot_before_after_accepts_single_channel(tmp_path):
    data = np.arange(16, dtype=float)

    axes = plot_before_after_waterfall(data, data)
    path = tmp_path / "single.png"
    axes[0].figure.savefig(path)

    assert path.exists()


def test_plot_before_after_rejects_empty():
    with pytest.raises(ValueError):
        plot_before_after_waterfall(np.array([]), np.array([]))
