import numpy as np
import pytest

from das_view.analysis.fk import fk_transform
from das_view.analysis.fk_filter import apply_fk_mask, fk_velocity_filter, velocity_fan_mask
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


def rms(data):
    return float(np.sqrt(np.mean(np.square(data))))


def test_velocity_fan_mask_shape_and_zero_wavenumber_handling():
    frequencies = np.array([0.0, 10.0, 20.0])
    wavenumbers = np.array([-0.1, 0.0, 0.1])

    mask = velocity_fan_mask(frequencies, wavenumbers, vmin_mps=50.0, vmax_mps=300.0)
    excluded_zero = velocity_fan_mask(
        frequencies,
        wavenumbers,
        vmin_mps=50.0,
        vmax_mps=300.0,
        include_zero_wavenumber=False,
    )

    assert mask.shape == (3, 3)
    assert mask.dtype == bool
    assert np.all(mask[:, 1])
    assert not np.any(excluded_zero[:, 1])


def test_velocity_fan_mask_vmin_vmax_and_pass_inside_flag():
    frequencies = np.array([10.0])
    wavenumbers = np.array([0.01, 0.1])

    inside = velocity_fan_mask(frequencies, wavenumbers, vmin_mps=200.0, vmax_mps=1200.0)
    outside = velocity_fan_mask(
        frequencies,
        wavenumbers,
        vmin_mps=200.0,
        vmax_mps=1200.0,
        pass_inside=False,
    )

    assert inside.tolist() == [[True, False]]
    np.testing.assert_array_equal(outside, ~inside)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vmin_mps": 0.0},
        {"vmax_mps": -1.0},
        {"vmin_mps": 100.0, "vmax_mps": 100.0},
        {"vmin_mps": 200.0, "vmax_mps": 100.0},
    ],
)
def test_velocity_fan_mask_rejects_invalid_velocity_limits(kwargs):
    with pytest.raises(ValueError):
        velocity_fan_mask([1.0], [0.1], **kwargs)


def test_apply_fk_mask_returns_original_shape_and_does_not_modify_input():
    data, _, _, sample_rate_hz, dx_m = make_plane_wave(n_samples=64, n_channels=16)
    original = data.copy()
    mask = np.ones((data.shape[0] // 2 + 1, data.shape[1]), dtype=bool)

    result = apply_fk_mask(data, mask, sample_rate_hz=sample_rate_hz, dx_m=dx_m)

    assert result.das_data.data.shape == data.shape
    np.testing.assert_allclose(data, original)
    np.testing.assert_allclose(result.das_data.data, original, atol=1e-12)


def test_apply_fk_mask_rejects_mismatched_mask_shape():
    data, _, _, sample_rate_hz, dx_m = make_plane_wave(n_samples=32, n_channels=8)

    with pytest.raises(ValueError, match="mask shape"):
        apply_fk_mask(data, np.ones((3, 3)), sample_rate_hz=sample_rate_hz, dx_m=dx_m)


def test_fk_velocity_filter_suppresses_synthetic_plane_wave_outside_pass_fan():
    data, frequency_hz, wavenumber_cpm, sample_rate_hz, dx_m = make_plane_wave()
    apparent_velocity = abs(frequency_hz / wavenumber_cpm)

    result = fk_velocity_filter(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        vmin_mps=apparent_velocity * 2.0,
        vmax_mps=apparent_velocity * 4.0,
        pass_inside=True,
        include_zero_wavenumber=False,
        return_fk=True,
    )

    assert result.das_data.data.shape == data.shape
    assert rms(result.das_data.data) < rms(data) * 0.25
    assert result.input_fk is not None
    assert result.filtered_fk is not None


def test_fk_velocity_filter_pass_inside_false_rejects_selected_plane_wave():
    data, frequency_hz, wavenumber_cpm, sample_rate_hz, dx_m = make_plane_wave()
    apparent_velocity = abs(frequency_hz / wavenumber_cpm)

    result = fk_velocity_filter(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        vmin_mps=apparent_velocity * 0.8,
        vmax_mps=apparent_velocity * 1.2,
        pass_inside=False,
        include_zero_wavenumber=False,
    )

    assert rms(result.das_data.data) < rms(data) * 0.25


def test_fk_velocity_filter_reads_dasdata_metadata():
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

    result = fk_velocity_filter(das_data, vmax_mps=1000.0)

    assert result.sample_rate_hz == sample_rate_hz
    assert result.dx_m == dx_m
    assert result.das_data.metadata.extra_attrs["fk_filter"]["vmax_mps"] == 1000.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"sample_rate_hz": 0.0, "dx_m": 1.0}, "sample_rate_hz"),
        ({"sample_rate_hz": 1.0, "dx_m": 0.0}, "dx_m"),
    ],
)
def test_fk_velocity_filter_rejects_invalid_sample_rate_or_dx(kwargs, match):
    with pytest.raises(ValueError, match=match):
        fk_velocity_filter(np.ones((4, 4)), **kwargs)


def test_fk_velocity_filter_rejects_non_2d_input():
    with pytest.raises(ValueError, match="2-D"):
        fk_velocity_filter(np.ones(4), sample_rate_hz=1.0, dx_m=1.0)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf])
def test_fk_velocity_filter_rejects_nan_or_inf_input(bad_value):
    data = np.ones((4, 4), dtype=float)
    data[0, 0] = bad_value

    with pytest.raises(ValueError, match="finite"):
        fk_velocity_filter(data, sample_rate_hz=1.0, dx_m=1.0)


def test_fk_velocity_filter_filtered_fk_peak_is_reduced_for_rejected_wave():
    data, frequency_hz, wavenumber_cpm, sample_rate_hz, dx_m = make_plane_wave()
    apparent_velocity = abs(frequency_hz / wavenumber_cpm)

    before = fk_transform(data, sample_rate_hz=sample_rate_hz, dx_m=dx_m)
    result = fk_velocity_filter(
        data,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        vmin_mps=apparent_velocity * 0.8,
        vmax_mps=apparent_velocity * 1.2,
        pass_inside=False,
        include_zero_wavenumber=False,
        return_fk=True,
    )

    assert result.filtered_fk is not None
    assert np.max(result.filtered_fk.values) < np.max(before.values) * 0.25
