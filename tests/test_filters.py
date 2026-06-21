import numpy as np
import pytest

pytest.importorskip("scipy")

from das_view.processing.filters import bandpass, bandstop, highpass, lowpass, notch


def _signal(freqs, *, sample_rate_hz=500.0, seconds=2.0):
    t = np.arange(int(sample_rate_hz * seconds)) / sample_rate_hz
    data = np.zeros_like(t)
    for freq, amp in freqs:
        data += amp * np.sin(2 * np.pi * freq * t)
    return t, data


def _amplitude(data, freq, *, sample_rate_hz=500.0):
    data = np.asarray(data)
    t = np.arange(data.shape[0]) / sample_rate_hz
    basis_sin = np.sin(2 * np.pi * freq * t)
    basis_cos = np.cos(2 * np.pi * freq * t)
    sin_amp = 2.0 * np.dot(data, basis_sin) / data.shape[0]
    cos_amp = 2.0 * np.dot(data, basis_cos) / data.shape[0]
    return float(np.hypot(sin_amp, cos_amp))


def test_lowpass_suppresses_high_frequency_and_preserves_shape():
    _, trace = _signal([(5.0, 1.0), (80.0, 1.0)])
    data = np.column_stack([trace, trace])
    original = data.copy()

    result = lowpass(data, sample_rate_hz=500.0, cutoff_hz=20.0)

    assert result.shape == data.shape
    np.testing.assert_array_equal(data, original)
    assert _amplitude(result[:, 0], 5.0) > 0.7
    assert _amplitude(result[:, 0], 80.0) < 0.2


def test_highpass_suppresses_low_frequency():
    _, trace = _signal([(5.0, 1.0), (80.0, 1.0)])
    data = trace[:, None]

    result = highpass(data, sample_rate_hz=500.0, cutoff_hz=30.0)

    assert _amplitude(result[:, 0], 80.0) > 0.7
    assert _amplitude(result[:, 0], 5.0) < 0.2


def test_bandpass_keeps_target_band():
    _, trace = _signal([(5.0, 1.0), (40.0, 1.0), (120.0, 1.0)])
    data = trace[:, None]

    result = bandpass(data, sample_rate_hz=500.0, freqmin_hz=20.0, freqmax_hz=60.0)

    assert _amplitude(result[:, 0], 40.0) > 0.6
    assert _amplitude(result[:, 0], 5.0) < 0.2
    assert _amplitude(result[:, 0], 120.0) < 0.2


def test_bandstop_suppresses_target_band():
    _, trace = _signal([(5.0, 1.0), (40.0, 1.0), (120.0, 1.0)])
    data = trace[:, None]

    result = bandstop(data, sample_rate_hz=500.0, freqmin_hz=30.0, freqmax_hz=50.0)

    assert _amplitude(result[:, 0], 5.0) > 0.6
    assert _amplitude(result[:, 0], 120.0) > 0.6
    assert _amplitude(result[:, 0], 40.0) < 0.25


def test_notch_suppresses_target_frequency():
    _, trace = _signal([(10.0, 1.0), (50.0, 1.0)])
    data = trace[:, None]

    result = notch(data, sample_rate_hz=500.0, notch_hz=50.0, quality=20.0)

    assert _amplitude(result[:, 0], 10.0) > 0.6
    assert _amplitude(result[:, 0], 50.0) < 0.35


def test_axis_one_filtering():
    _, trace = _signal([(5.0, 1.0), (80.0, 1.0)])
    data = np.vstack([trace, trace])

    result = lowpass(data, sample_rate_hz=500.0, cutoff_hz=20.0, axis=1)

    assert result.shape == data.shape
    assert _amplitude(result[0], 80.0) < 0.2


def test_causal_filter_path_runs():
    _, trace = _signal([(5.0, 1.0), (80.0, 1.0)])

    result = lowpass(trace[:, None], sample_rate_hz=500.0, cutoff_hz=20.0, zero_phase=False)

    assert result.shape == (trace.shape[0], 1)


def test_cutoff_at_nyquist_raises():
    with pytest.raises(ValueError, match="Nyquist"):
        lowpass(np.ones((100, 2)), sample_rate_hz=100.0, cutoff_hz=50.0)


def test_freqmin_greater_than_freqmax_raises():
    with pytest.raises(ValueError, match="freqmin_hz"):
        bandpass(np.ones((100, 2)), sample_rate_hz=100.0, freqmin_hz=20.0, freqmax_hz=10.0)


def test_sample_rate_order_quality_axis_validation():
    data = np.ones((100, 2))
    with pytest.raises(ValueError, match="sample_rate_hz"):
        lowpass(data, sample_rate_hz=0.0, cutoff_hz=10.0)
    with pytest.raises(ValueError, match="order"):
        highpass(data, sample_rate_hz=100.0, cutoff_hz=10.0, order=0)
    with pytest.raises(ValueError, match="quality"):
        notch(data, sample_rate_hz=100.0, notch_hz=10.0, quality=0.0)
    with pytest.raises(ValueError, match="axis"):
        lowpass(data, sample_rate_hz=100.0, cutoff_hz=10.0, axis=2)


def test_nan_inf_input_raises():
    data = np.ones((100, 2))
    data[0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        lowpass(data, sample_rate_hz=100.0, cutoff_hz=10.0)


def test_too_short_data_raises_clear_error():
    with pytest.raises(ValueError, match="too short"):
        lowpass(np.ones((4, 2)), sample_rate_hz=100.0, cutoff_hz=10.0)
