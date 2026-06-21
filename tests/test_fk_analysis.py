import numpy as np
import pytest

from das_view.analysis.fk import fk_transform
from das_view.core.data_model import DASData, DASMetadata


def make_plane_wave(
    *,
    n_samples=128,
    n_channels=64,
    sample_rate_hz=128.0,
    dx_m=2.0,
    frequency_bin=8,
    wavenumber_bin=5,
):
    frequency_hz = frequency_bin * sample_rate_hz / n_samples
    wavenumber_cpm = wavenumber_bin / (n_channels * dx_m)
    t = np.arange(n_samples, dtype=float) / sample_rate_hz
    x = np.arange(n_channels, dtype=float) * dx_m
    data = np.cos(2.0 * np.pi * (frequency_hz * t[:, None] - wavenumber_cpm * x[None, :]))
    return data, frequency_hz, wavenumber_cpm, sample_rate_hz, dx_m


def test_fk_transform_plane_wave_peak_is_near_target_frequency_and_wavenumber():
    data, frequency_hz, wavenumber_cpm, sample_rate_hz, dx_m = make_plane_wave()

    result = fk_transform(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m)
    peak_frequency_index, peak_wavenumber_index = np.unravel_index(
        np.argmax(result.values),
        result.values.shape,
    )

    frequency_step = sample_rate_hz / data.shape[0]
    wavenumber_step = 1.0 / (data.shape[1] * dx_m)
    assert result.frequencies_hz[peak_frequency_index] == pytest.approx(frequency_hz, abs=frequency_step)
    assert abs(result.wavenumbers_cycles_per_m[peak_wavenumber_index]) == pytest.approx(
        wavenumber_cpm,
        abs=wavenumber_step,
    )


def test_fk_transform_amplitude_and_power_shapes():
    data, _, _, sample_rate_hz, dx_m = make_plane_wave(n_samples=64, n_channels=16)

    amplitude = fk_transform(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        nfft_time=128,
        nfft_space=32,
        output="amplitude",
    )
    power = fk_transform(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        nfft_time=128,
        nfft_space=32,
        output="power",
    )

    assert amplitude.values.shape == (65, 32)
    assert power.values.shape == (65, 32)
    assert amplitude.output == "amplitude"
    assert power.output == "power"
    np.testing.assert_allclose(power.values, np.square(amplitude.values))


def test_fk_transform_reads_dasdata_metadata():
    data, _, _, sample_rate_hz, dx_m = make_plane_wave(n_samples=32, n_channels=8)
    das_data = DASData(
        data=data,
        metadata=DASMetadata(
            n_samples=data.shape[0],
            n_channels=data.shape[1],
            sample_rate_hz=sample_rate_hz,
            dx_m=dx_m,
        ),
    )

    result = fk_transform(das_data)

    assert result.sample_rate_hz == sample_rate_hz
    assert result.dx_m == dx_m


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"sample_rate_hz": 0.0, "dx_m": 1.0}, "sample_rate_hz"),
        ({"sample_rate_hz": 1.0, "dx_m": 0.0}, "dx_m"),
    ],
)
def test_fk_transform_rejects_invalid_sample_rate_or_dx(kwargs, match):
    with pytest.raises(ValueError, match=match):
        fk_transform(np.ones((4, 4)), **kwargs)


def test_fk_transform_rejects_non_2d_input():
    with pytest.raises(ValueError, match="2-D"):
        fk_transform(np.ones(4), sample_rate_hz=1.0, dx_m=1.0)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf])
def test_fk_transform_rejects_nan_or_inf_input(bad_value):
    data = np.ones((4, 4), dtype=float)
    data[0, 0] = bad_value

    with pytest.raises(ValueError, match="finite"):
        fk_transform(data, sample_rate_hz=1.0, dx_m=1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"nfft_time": 0},
        {"nfft_space": 0},
        {"nfft_time": 2},
        {"nfft_space": 2},
    ],
)
def test_fk_transform_rejects_invalid_nfft(kwargs):
    with pytest.raises(ValueError, match="nfft"):
        fk_transform(np.ones((4, 4)), sample_rate_hz=1.0, dx_m=1.0, **kwargs)


@pytest.mark.parametrize("shape", [(1, 4), (4, 1)])
def test_fk_transform_rejects_too_few_samples_or_channels(shape):
    with pytest.raises(ValueError, match="at least 2"):
        fk_transform(np.ones(shape), sample_rate_hz=1.0, dx_m=1.0)


def test_fk_transform_does_not_modify_input():
    data, _, _, sample_rate_hz, dx_m = make_plane_wave(n_samples=32, n_channels=8)
    original = data.copy()

    fk_transform(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m, window_time="hann")

    np.testing.assert_allclose(data, original)
