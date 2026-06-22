import numpy as np
import pytest

from das_view.analysis.qc import (
    channel_quality_metrics,
    data_quality_report,
    detect_bad_channels,
    estimate_noise_floor,
    estimate_snr,
    local_channel_coherence,
)
from das_view.core.data_model import DASData, DASMetadata


def test_channel_quality_metrics_per_channel_shape_and_no_mutation():
    data = np.arange(40, dtype=float).reshape(10, 4)
    original = data.copy()

    result = channel_quality_metrics(data)

    assert result.rms.shape == (4,)
    assert result.quality_score.shape == (4,)
    np.testing.assert_allclose(data, original)


def test_zero_channel_is_dead_or_low_energy():
    data = np.column_stack([np.arange(10, dtype=float), np.zeros(10), np.arange(10, dtype=float)])

    result = channel_quality_metrics(data)

    assert result.dead_channel[1]
    assert result.low_energy_channel[1]


def test_spike_clipping_nan_inf_metrics():
    data = np.ones((20, 3), dtype=float)
    data[5, 0] = 100.0
    data[2, 1] = np.nan
    data[3, 2] = np.inf

    result = channel_quality_metrics(data, clipping_threshold=10.0)

    assert result.spike_count[0] >= 1
    assert result.clipping_fraction[0] > 0
    assert result.nan_fraction[1] == pytest.approx(1 / 20)
    assert result.inf_fraction[2] == pytest.approx(1 / 20)


def test_noise_floor_mad_and_snr_windows():
    noise = np.ones((10, 2))
    signal = np.ones((10, 2)) * 10.0
    data = np.vstack([noise, signal])

    floor = estimate_noise_floor(data, method="mad")
    snr = estimate_snr(data, signal_window=slice(10, 20), noise_window=slice(0, 10))

    assert floor.shape == (2,)
    assert np.all(snr > 5)


def test_detect_bad_channels_and_report():
    data = np.column_stack([np.arange(20, dtype=float), np.zeros(20), np.arange(20, dtype=float) * 100])

    bad = detect_bad_channels(data)
    report = data_quality_report(data)

    assert 1 in bad
    assert report.global_summary["bad_channel_count"] >= 1


def test_dasdata_input():
    metadata = DASMetadata(n_samples=8, n_channels=2)
    das_data = DASData(np.ones((8, 2)), metadata)

    result = channel_quality_metrics(das_data)

    assert result.n_samples == 8
    assert result.n_channels == 2


def test_local_channel_coherence_identical_high_random_lower_and_windowed():
    rng = np.random.default_rng(123)
    base = np.sin(np.linspace(0, 4 * np.pi, 64))
    coherent = np.column_stack([base, base, base])
    random = rng.normal(size=(64, 3))

    high = local_channel_coherence(coherent)
    low = local_channel_coherence(random)
    windowed = local_channel_coherence(coherent, window_samples=16, step_samples=8)

    assert np.nanmean(high.coherence) > 0.99
    assert np.nanmean(low.coherence) < 0.8
    assert windowed.coherence.shape[0] == 7


def test_local_channel_coherence_invalid_lag_and_nan_policy():
    data = np.ones((10, 2))
    data[0, 0] = np.nan

    with pytest.raises(ValueError):
        local_channel_coherence(data, channel_lag=0)
    with pytest.raises(ValueError):
        local_channel_coherence(data, nan_policy="raise")
