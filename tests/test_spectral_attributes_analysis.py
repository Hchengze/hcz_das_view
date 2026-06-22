import numpy as np
import pytest

from das_view.analysis.spectral_attributes import band_energy, spectral_attributes
from das_view.core.data_model import DASData, DASMetadata


def sine_data(*, sample_rate_hz=1000.0, n_samples=1000):
    t = np.arange(n_samples, dtype=float) / sample_rate_hz
    return np.column_stack(
        [
            np.sin(2 * np.pi * 10.0 * t),
            np.sin(2 * np.pi * 40.0 * t),
        ]
    )


def test_spectral_attributes_detects_single_frequency():
    sample_rate_hz = 1000.0
    data = sine_data(sample_rate_hz=sample_rate_hz)[:, :1]

    result = spectral_attributes(data, sample_rate_hz=sample_rate_hz)

    assert result.dominant_frequency_hz == pytest.approx(10.0)
    assert result.peak_amplitude_or_power > 0.0


def test_band_energy_is_larger_in_target_band():
    data = sine_data()

    result = band_energy(data, sample_rate_hz=1000.0, bands=[(8.0, 12.0), (35.0, 45.0)])

    assert result.band_energy.shape == (2, 2)
    assert result.band_energy[0, 0] > result.band_energy[1, 0] * 100
    assert result.band_energy[1, 1] > result.band_energy[0, 1] * 100


def test_band_energy_ratio_is_reasonable():
    data = sine_data()

    result = band_energy(data, sample_rate_hz=1000.0, bands=[(8.0, 12.0), (35.0, 45.0)])

    assert np.all(result.band_energy_ratio >= 0.0)
    assert np.all(result.band_energy_ratio <= 1.0 + 1e-12)
    np.testing.assert_allclose(np.sum(result.band_energy_ratio, axis=0), np.ones(2), atol=1e-12)


def test_spectral_centroid_and_bandwidth_are_reasonable():
    data = sine_data()[:, :1]

    result = spectral_attributes(data, sample_rate_hz=1000.0)

    assert result.spectral_centroid_hz == pytest.approx(10.0)
    assert result.spectral_bandwidth_hz >= 0.0


def test_spectral_rolloff_is_in_frequency_range():
    data = sine_data()[:, :1]

    result = spectral_attributes(data, sample_rate_hz=1000.0, rolloff=0.95)

    assert result.low_frequency_hz <= result.spectral_rolloff_hz <= result.high_frequency_hz


def test_frequency_range_limits_analysis():
    data = sine_data()

    result = spectral_attributes(
        data,
        sample_rate_hz=1000.0,
        frequency_range=(30.0, 50.0),
        average_channels=True,
    )

    assert result.low_frequency_hz == 30.0
    assert result.high_frequency_hz == 50.0
    assert result.dominant_frequency_hz == pytest.approx(40.0)


def test_average_channels_returns_band_vectors_and_scalar_attributes():
    data = sine_data()

    bands = band_energy(data, sample_rate_hz=1000.0, bands=[(8.0, 12.0), (35.0, 45.0)], average_channels=True)
    attrs = spectral_attributes(data, sample_rate_hz=1000.0, average_channels=True)

    assert bands.band_energy.shape == (2,)
    assert isinstance(attrs.dominant_frequency_hz, float)


def test_average_channels_false_output_shapes():
    data = sine_data()

    bands = band_energy(data, sample_rate_hz=1000.0, bands=[(8.0, 12.0), (35.0, 45.0)])
    attrs = spectral_attributes(data, sample_rate_hz=1000.0)

    assert bands.band_energy.shape == (2, 2)
    assert attrs.dominant_frequency_hz.shape == (2,)


def test_dasdata_input_uses_metadata_sample_rate():
    data = sine_data()
    das_data = DASData(
        data=data,
        metadata=DASMetadata(n_samples=data.shape[0], n_channels=data.shape[1], sample_rate_hz=1000.0),
    )

    result = spectral_attributes(das_data, average_channels=True)

    assert result.sample_rate_hz == 1000.0
    assert result.dominant_frequency_hz == pytest.approx(10.0)


def test_invalid_sample_rate_is_rejected():
    with pytest.raises(ValueError, match="sample_rate_hz"):
        band_energy(np.ones(16), sample_rate_hz=0.0, bands=[(1.0, 2.0)])


@pytest.mark.parametrize(
    "bands",
    [
        [(-1.0, 2.0)],
        [(2.0, 2.0)],
        [(3.0, 2.0)],
    ],
)
def test_invalid_band_limits_are_rejected(bands):
    with pytest.raises(ValueError, match="band"):
        band_energy(np.ones(100), sample_rate_hz=100.0, bands=bands)


def test_band_above_nyquist_is_rejected():
    with pytest.raises(ValueError, match="Nyquist"):
        band_energy(np.ones(100), sample_rate_hz=100.0, bands=[(10.0, 60.0)])


def test_band_without_frequency_bin_is_rejected():
    with pytest.raises(ValueError, match="frequency bins"):
        band_energy(np.ones(100), sample_rate_hz=100.0, bands=[(0.1, 0.2)])


@pytest.mark.parametrize("rolloff", [0.0, -0.1, 1.1])
def test_invalid_rolloff_is_rejected(rolloff):
    with pytest.raises(ValueError, match="rolloff"):
        spectral_attributes(np.ones(100), sample_rate_hz=100.0, rolloff=rolloff)


def test_nan_inf_raise_policy_rejects_input():
    with pytest.raises(ValueError, match="NaN or Inf"):
        spectral_attributes(np.array([1.0, np.nan]), sample_rate_hz=100.0)
    with pytest.raises(ValueError, match="NaN or Inf"):
        band_energy(np.array([1.0, np.inf]), sample_rate_hz=100.0, bands=[(1.0, 2.0)])


def test_input_is_not_modified():
    data = sine_data()
    original = data.copy()

    spectral_attributes(data, sample_rate_hz=1000.0)
    band_energy(data, sample_rate_hz=1000.0, bands=[(8.0, 12.0)])

    np.testing.assert_array_equal(data, original)
