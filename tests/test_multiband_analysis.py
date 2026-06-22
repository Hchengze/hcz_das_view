import numpy as np
import pytest

from das_view.analysis.multiband import multiband_energy_map, spectral_attribute_map
from das_view.core.data_model import DASData, DASMetadata


def _sine(freq, *, sample_rate=100.0, n=128):
    t = np.arange(n) / sample_rate
    return np.sin(2 * np.pi * freq * t)


def test_multiband_single_frequency_prefers_matching_band():
    data = np.column_stack([_sine(5), _sine(30)])

    result = multiband_energy_map(
        data,
        sample_rate_hz=100.0,
        bands=[(1, 10), (20, 40)],
        window_samples=64,
        step_samples=64,
    )

    assert result.values.shape == (2, 2, 2)
    assert result.values[0, 0, 0] > result.values[0, 0, 1]
    assert result.values[0, 1, 1] > result.values[0, 1, 0]


def test_multiband_invalid_band_window_and_no_mutation():
    data = np.ones((16, 2))
    original = data.copy()

    with pytest.raises(ValueError):
        multiband_energy_map(data, sample_rate_hz=20.0, bands=[(10, 1)], window_samples=8, step_samples=4)
    with pytest.raises(ValueError):
        multiband_energy_map(data, sample_rate_hz=20.0, bands=[(1, 2)], window_samples=0, step_samples=4)
    np.testing.assert_allclose(data, original)


def test_spectral_attribute_map_outputs_expected_keys():
    data = np.column_stack([_sine(5), _sine(10)])

    result = spectral_attribute_map(
        data,
        sample_rate_hz=100.0,
        window_samples=64,
        step_samples=32,
        attributes=("dominant_frequency", "centroid", "bandwidth", "rolloff"),
    )

    assert set(result) == {"dominant_frequency", "centroid", "bandwidth", "rolloff"}
    assert result["dominant_frequency"].values.shape == (3, 2)


def test_dasdata_uses_metadata_sample_rate():
    metadata = DASMetadata(n_samples=64, n_channels=1, sample_rate_hz=100.0)
    das_data = DASData(_sine(8, n=64).reshape(64, 1), metadata)

    result = multiband_energy_map(das_data, bands=[(1, 12)], window_samples=32, step_samples=16)

    assert result.sample_rate_hz == 100.0
    assert result.values.shape == (3, 1, 1)
