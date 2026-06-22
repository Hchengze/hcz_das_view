import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib

matplotlib.use("Agg")

from das_view.analysis.multiband import multiband_energy_map
from das_view.analysis.qc import data_quality_report, local_channel_coherence
from das_view.plotting import plot_bad_channels, plot_channel_quality, plot_coherence_map, plot_multiband_energy_map


def test_plot_channel_quality_and_bad_channels(tmp_path):
    report = data_quality_report(np.column_stack([np.arange(20, dtype=float), np.zeros(20)]))

    ax = plot_channel_quality(report)
    path = tmp_path / "quality.png"
    ax.figure.savefig(path)
    assert path.exists()

    ax = plot_bad_channels(report)
    path = tmp_path / "bad.png"
    ax.figure.savefig(path)
    assert path.exists()


def test_plot_multiband_energy_map_and_coherence(tmp_path):
    data = np.column_stack([np.sin(np.linspace(0, 4 * np.pi, 64)), np.sin(np.linspace(0, 4 * np.pi, 64))])
    multiband = multiband_energy_map(
        data,
        sample_rate_hz=100.0,
        bands=[(1, 20)],
        window_samples=32,
        step_samples=16,
    )
    coherence = local_channel_coherence(data, window_samples=32, step_samples=16)

    ax = plot_multiband_energy_map(multiband)
    path = tmp_path / "multiband.png"
    ax.figure.savefig(path)
    assert path.exists()

    ax = plot_coherence_map(coherence)
    path = tmp_path / "coherence.png"
    ax.figure.savefig(path)
    assert path.exists()


def test_plot_multiband_rejects_empty_or_bad_band():
    result = multiband_energy_map(
        np.ones((16, 1)),
        sample_rate_hz=20.0,
        bands=[(1, 5)],
        window_samples=8,
        step_samples=8,
    )

    with pytest.raises(ValueError):
        plot_multiband_energy_map(result, band_index=10)
