import numpy as np
import pytest

pytest.importorskip("scipy")

from das_view.analysis.spectrum import (
    PSDResult,
    amplitude_spectrum,
    periodogram_psd,
    power_spectrum,
    single_channel_spectrogram,
    welch_psd,
)
from das_view.core.data_model import DASData, DASMetadata


def sine_wave(*, frequency_hz=12.0, sample_rate_hz=200.0, n_samples=1000):
    t = np.arange(n_samples, dtype=float) / sample_rate_hz
    return np.sin(2 * np.pi * frequency_hz * t)


def peak_frequency(result):
    values = np.asarray(result.values)
    if values.ndim == 2:
        values = values[:, 0] if result.axis == 0 else values[0, :]
    return result.frequencies_hz[int(np.argmax(values))]


def make_das(data, *, sample_rate_hz=200.0):
    array = np.asarray(data, dtype=float)
    return DASData(
        data=array,
        metadata=DASMetadata(
            n_samples=array.shape[0],
            n_channels=array.shape[1],
            sample_rate_hz=sample_rate_hz,
            source_format="synthetic",
        ),
    )


def test_amplitude_spectrum_single_frequency_peak():
    trace = sine_wave(frequency_hz=12.0, sample_rate_hz=200.0, n_samples=1000)

    result = amplitude_spectrum(trace, sample_rate_hz=200.0)

    assert peak_frequency(result) == pytest.approx(12.0, abs=0.25)
    assert result.amplitude.max() == pytest.approx(1.0, rel=0.05)


def test_power_spectrum_single_frequency_peak():
    trace = sine_wave(frequency_hz=25.0, sample_rate_hz=500.0, n_samples=1000)

    result = power_spectrum(trace, sample_rate_hz=500.0)

    assert peak_frequency(result) == pytest.approx(25.0, abs=0.5)
    assert result.power.max() > 0.1


def test_frequency_axis_length_and_nfft_resolution():
    trace = sine_wave(n_samples=100)

    default = amplitude_spectrum(trace, sample_rate_hz=200.0)
    padded = amplitude_spectrum(trace, sample_rate_hz=200.0, nfft=400)

    assert default.frequencies_hz.shape == (51,)
    assert padded.frequencies_hz.shape == (201,)
    assert padded.frequencies_hz[1] - padded.frequencies_hz[0] < (
        default.frequencies_hz[1] - default.frequencies_hz[0]
    )


def test_spectrum_does_not_modify_input():
    data = np.column_stack([sine_wave(), sine_wave(frequency_hz=20.0)])
    original = data.copy()

    amplitude_spectrum(data, sample_rate_hz=200.0, channels=1)

    np.testing.assert_array_equal(data, original)


def test_spectrum_rejects_invalid_sample_rate_nfft_and_nonfinite():
    trace = sine_wave()

    with pytest.raises(ValueError, match="sample_rate_hz"):
        amplitude_spectrum(trace, sample_rate_hz=0)
    with pytest.raises(ValueError, match="nfft"):
        amplitude_spectrum(trace, sample_rate_hz=200.0, nfft=10)
    trace_with_nan = trace.copy()
    trace_with_nan[0] = np.nan
    with pytest.raises(ValueError, match="NaN/Inf"):
        amplitude_spectrum(trace_with_nan, sample_rate_hz=200.0)


def test_axis_0_and_axis_1_for_das_data():
    data = np.column_stack([sine_wave(frequency_hz=10.0), sine_wave(frequency_hz=30.0)])

    axis0 = amplitude_spectrum(data, sample_rate_hz=200.0, axis=0, channels=[0, 1])
    axis1 = amplitude_spectrum(data.T, sample_rate_hz=200.0, axis=1, channels=[0, 1])

    assert axis0.values.shape == (501, 2)
    assert axis1.values.shape == (2, 501)
    assert peak_frequency(axis0) == pytest.approx(10.0, abs=0.25)


def test_average_channel_spectrum():
    data = np.column_stack([sine_wave(frequency_hz=10.0), sine_wave(frequency_hz=10.0)])

    result = amplitude_spectrum(data, sample_rate_hz=200.0, average_channels=True)

    assert result.values.ndim == 1
    assert result.average_channels is True


def test_dasdata_input_reads_sample_rate_from_metadata():
    das_data = make_das(np.column_stack([sine_wave(frequency_hz=15.0)]), sample_rate_hz=200.0)

    result = amplitude_spectrum(das_data, channels=0)

    assert result.sample_rate_hz == 200.0
    assert peak_frequency(result) == pytest.approx(15.0, abs=0.25)


def test_spectrum_rejects_invalid_axis_and_channel():
    data = np.column_stack([sine_wave(), sine_wave()])

    with pytest.raises(ValueError, match="axis"):
        amplitude_spectrum(data, sample_rate_hz=200.0, axis=2)
    with pytest.raises(ValueError, match="out of range"):
        amplitude_spectrum(data, sample_rate_hz=200.0, channels=2)


def test_single_channel_spectrogram_shapes():
    data = np.column_stack([sine_wave(frequency_hz=10.0), sine_wave(frequency_hz=20.0)])

    result = single_channel_spectrogram(
        data,
        sample_rate_hz=200.0,
        channel=1,
        nperseg=128,
        noverlap=64,
    )

    assert result.channel == 1
    assert result.values.shape == (result.frequencies_hz.size, result.times_s.size)
    assert result.frequencies_hz.size > 0
    assert result.times_s.size > 0


def test_single_channel_spectrogram_rejects_invalid_params():
    data = np.column_stack([sine_wave(), sine_wave()])

    with pytest.raises(ValueError, match="out of range"):
        single_channel_spectrogram(data, sample_rate_hz=200.0, channel=2)
    with pytest.raises(ValueError, match="nperseg"):
        single_channel_spectrogram(data, sample_rate_hz=200.0, nperseg=0)
    with pytest.raises(ValueError, match="noverlap"):
        single_channel_spectrogram(data, sample_rate_hz=200.0, nperseg=128, noverlap=128)


def test_periodogram_psd_single_frequency_peak():
    trace = sine_wave(frequency_hz=18.0, sample_rate_hz=300.0, n_samples=900)

    result = periodogram_psd(trace, sample_rate_hz=300.0, window="boxcar")

    assert isinstance(result, PSDResult)
    assert result.method == "periodogram"
    assert peak_frequency(result) == pytest.approx(18.0, abs=0.4)
    assert result.values.shape == result.frequencies_hz.shape


def test_welch_psd_single_frequency_peak():
    trace = sine_wave(frequency_hz=30.0, sample_rate_hz=300.0, n_samples=1024)

    result = welch_psd(trace, sample_rate_hz=300.0, nperseg=256, noverlap=128)

    assert result.method == "welch"
    assert peak_frequency(result) == pytest.approx(30.0, abs=1.5)
    assert result.values.shape == result.frequencies_hz.shape


def test_psd_channel_selection_and_average():
    data = np.column_stack(
        [
            sine_wave(frequency_hz=10.0),
            sine_wave(frequency_hz=20.0),
            sine_wave(frequency_hz=20.0),
        ]
    )

    selected = welch_psd(data, sample_rate_hz=200.0, channels=[1, 2], nperseg=200)
    averaged = welch_psd(
        data,
        sample_rate_hz=200.0,
        channels=[1, 2],
        average_channels=True,
        nperseg=200,
    )

    assert selected.channels == (1, 2)
    assert selected.values.shape == (101, 2)
    assert averaged.values.ndim == 1
    assert averaged.average_channels is True
    assert peak_frequency(averaged) == pytest.approx(20.0, abs=1.0)


def test_psd_dasdata_input_reads_sample_rate_from_metadata():
    das_data = make_das(np.column_stack([sine_wave(frequency_hz=15.0)]), sample_rate_hz=200.0)

    result = periodogram_psd(das_data, channels=0)

    assert result.sample_rate_hz == 200.0
    assert peak_frequency(result) == pytest.approx(15.0, abs=0.25)


def test_psd_rejects_invalid_parameters_and_nonfinite():
    trace = sine_wave(n_samples=512)

    with pytest.raises(ValueError, match="sample_rate_hz"):
        periodogram_psd(trace, sample_rate_hz=0)
    with pytest.raises(ValueError, match="nperseg"):
        welch_psd(trace, sample_rate_hz=200.0, nperseg=0)
    with pytest.raises(ValueError, match="less than or equal"):
        welch_psd(trace, sample_rate_hz=200.0, nperseg=1024)
    with pytest.raises(ValueError, match="noverlap"):
        welch_psd(trace, sample_rate_hz=200.0, nperseg=128, noverlap=128)
    with pytest.raises(ValueError, match="nfft"):
        welch_psd(trace, sample_rate_hz=200.0, nperseg=128, nfft=64)
    trace_with_inf = trace.copy()
    trace_with_inf[0] = np.inf
    with pytest.raises(ValueError, match="NaN/Inf"):
        periodogram_psd(trace_with_inf, sample_rate_hz=200.0)
