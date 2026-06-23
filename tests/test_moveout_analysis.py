import numpy as np
import pytest

from das_view.analysis.moveout import (
    apparent_velocity_from_slope,
    directional_energy_ratio,
    estimate_apparent_slope_xcorr,
    fk_directional_energy,
    local_moveout_coherence,
    moveout_summary_report,
)
from das_view.core import DASData, DASMetadata


def make_delayed_wave(*, n_samples=96, n_channels=8, sample_rate_hz=96.0, dx_m=2.0, lag_samples=2):
    t = np.arange(n_samples, dtype=float) / sample_rate_hz
    base = np.sin(2 * np.pi * 6.0 * t)
    data = np.column_stack([np.roll(base, channel * lag_samples) for channel in range(n_channels)])
    return data, sample_rate_hz, dx_m, lag_samples


def test_directional_energy_ratio_detects_nonbalanced_traveling_wave():
    data, sample_rate_hz, dx_m, _ = make_delayed_wave()

    result = directional_energy_ratio(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m)

    assert result.positive_wavenumber_energy >= 0
    assert result.negative_wavenumber_energy >= 0
    assert result.zero_wavenumber_energy >= 0
    assert abs(result.directional_ratio) > 0.2
    assert result.dominant_direction in {"positive_k", "negative_k"}
    assert result.total_energy > 0


def test_directional_energy_zero_input_is_stable():
    result = fk_directional_energy(np.zeros((16, 4)), sample_rate_hz=20.0, dx_m=1.0)

    assert result.total_energy == 0.0
    assert result.directional_ratio == 0.0
    assert result.dominant_direction == "balanced"


def test_estimate_apparent_slope_xcorr_known_lag():
    data, sample_rate_hz, dx_m, lag_samples = make_delayed_wave()

    result = estimate_apparent_slope_xcorr(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        channel_lag=1,
        max_lag_samples=4,
    )

    assert result.lag_samples.shape == (data.shape[1] - 1,)
    assert np.median(result.lag_samples) == pytest.approx(lag_samples, abs=1)
    assert np.nanmedian(np.abs(result.correlation_peak)) > 0.8


def test_apparent_velocity_from_slope_handles_zero():
    result = apparent_velocity_from_slope(np.array([0.5, 0.0, -0.25]))

    assert result.apparent_velocity_mps[0] == pytest.approx(2.0)
    assert np.isinf(result.apparent_velocity_mps[1])
    assert result.apparent_velocity_mps[2] == pytest.approx(-4.0)


def test_local_moveout_coherence_windowed_shape():
    data, sample_rate_hz, dx_m, _ = make_delayed_wave(n_samples=64)

    result = local_moveout_coherence(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        window_samples=32,
        step_samples=16,
        max_lag_samples=4,
    )

    assert result.coherence.shape == (3, data.shape[1] - 1)
    assert result.lag_samples.shape == result.coherence.shape


def test_moveout_summary_report_contains_summary():
    data, sample_rate_hz, dx_m, _ = make_delayed_wave()

    result = moveout_summary_report(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m)

    assert "dominant_direction" in result.summary
    assert result.moveout_coherence.coherence.size


def test_invalid_channel_lag_and_missing_metadata_raise():
    data, sample_rate_hz, dx_m, _ = make_delayed_wave()

    with pytest.raises(ValueError, match="channel_lag"):
        estimate_apparent_slope_xcorr(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m, channel_lag=0)
    with pytest.raises(ValueError, match="sample_rate_hz"):
        estimate_apparent_slope_xcorr(data, dx_m=dx_m)
    with pytest.raises(ValueError, match="dx_m"):
        directional_energy_ratio(data, sample_rate_hz=sample_rate_hz)


def test_dasdata_input_and_no_inplace_mutation():
    data, sample_rate_hz, dx_m, _ = make_delayed_wave()
    original = data.copy()
    das_data = DASData(
        data=data,
        metadata=DASMetadata(n_samples=data.shape[0], n_channels=data.shape[1], sample_rate_hz=sample_rate_hz, dx_m=dx_m),
    )

    result = estimate_apparent_slope_xcorr(das_data, max_lag_samples=4)

    assert result.lag_samples.size == data.shape[1] - 1
    np.testing.assert_allclose(data, original)
