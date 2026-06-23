import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib

matplotlib.use("Agg")

from das_view.analysis.moveout import (
    directional_energy_ratio,
    estimate_apparent_slope_xcorr,
    local_moveout_coherence,
)
from das_view.plotting import plot_apparent_velocity_map, plot_directional_energy, plot_moveout_coherence


def make_wave():
    t = np.arange(64, dtype=float) / 64.0
    base = np.sin(2 * np.pi * 4 * t)
    return np.column_stack([np.roll(base, channel) for channel in range(4)])


def test_plot_directional_energy(tmp_path):
    result = directional_energy_ratio(make_wave(), sample_rate_hz=64.0, dx_m=1.0)

    ax = plot_directional_energy(result)
    path = tmp_path / "direction.png"
    ax.figure.savefig(path)

    assert path.exists()


def test_plot_apparent_velocity_and_coherence(tmp_path):
    data = make_wave()
    slope = estimate_apparent_slope_xcorr(data, sample_rate_hz=64.0, dx_m=1.0, max_lag_samples=4)
    coherence = local_moveout_coherence(data, sample_rate_hz=64.0, dx_m=1.0, max_lag_samples=4)

    ax = plot_apparent_velocity_map(slope)
    velocity_path = tmp_path / "velocity.png"
    ax.figure.savefig(velocity_path)
    assert velocity_path.exists()

    ax = plot_moveout_coherence(coherence)
    coherence_path = tmp_path / "coherence.png"
    ax.figure.savefig(coherence_path)
    assert coherence_path.exists()


def test_plot_moveout_rejects_wrong_type():
    with pytest.raises(TypeError):
        plot_directional_energy(object())
