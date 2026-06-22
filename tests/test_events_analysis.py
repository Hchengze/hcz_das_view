import numpy as np
import pytest

pytest.importorskip("scipy")

from das_view.analysis.events import (
    amplitude_envelope,
    detect_stalta_events,
    detect_threshold_events,
    energy_envelope,
    sta_lta_ratio,
)
from das_view.core.data_model import DASData, DASMetadata


def make_das_data(data):
    return DASData(
        data=np.asarray(data, dtype=np.float32),
        metadata=DASMetadata(
            n_samples=np.asarray(data).shape[0],
            n_channels=np.asarray(data).shape[1],
            sample_rate_hz=1000.0,
            source_format="synthetic",
        ),
    )


def test_amplitude_envelope_shape():
    data = np.ones((20, 3), dtype=float)

    result = amplitude_envelope(data)

    assert result.values.shape == data.shape
    assert result.axis == 0


def test_synthetic_sinusoid_envelope_is_near_one():
    t = np.arange(1000, dtype=float) / 1000.0
    data = np.sin(2 * np.pi * 20.0 * t).reshape(-1, 1)

    result = amplitude_envelope(data)

    np.testing.assert_allclose(result.values[100:-100, 0], 1.0, atol=0.05)


def test_energy_envelope_is_nonnegative_and_sliding_shape():
    data = np.linspace(-1.0, 1.0, 30).reshape(10, 3)

    point = energy_envelope(data)
    sliding = energy_envelope(data, window_samples=5)

    assert point.values.shape == data.shape
    assert sliding.values.shape == data.shape
    assert np.all(point.values >= 0.0)
    assert np.all(sliding.values >= 0.0)


def test_stalta_ratio_shape_and_invalid_windows():
    data = np.ones((40, 2), dtype=float)

    result = sta_lta_ratio(data, sta_samples=3, lta_samples=9)

    assert result.ratio.shape == data.shape
    with pytest.raises(ValueError, match="positive"):
        sta_lta_ratio(data, sta_samples=0, lta_samples=9)
    with pytest.raises(ValueError, match="greater"):
        sta_lta_ratio(data, sta_samples=9, lta_samples=3)


def test_threshold_event_detection_finds_synthetic_event():
    feature = np.zeros((20, 2), dtype=float)
    feature[5:10, 1] = 3.0

    result = detect_threshold_events(feature, threshold=2.0)

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.start_sample == 5
    assert candidate.end_sample == 10
    assert candidate.duration_samples == 5
    assert candidate.channel_start == 1


def test_threshold_min_duration_samples_filters_short_events():
    feature = np.zeros(20, dtype=float)
    feature[5:7] = 2.0
    feature[10:15] = 2.0

    result = detect_threshold_events(feature, threshold=1.0, min_duration_samples=3)

    assert len(result.candidates) == 1
    assert result.candidates[0].start_sample == 10


def test_threshold_merge_gap_samples_merges_nearby_events():
    feature = np.zeros(20, dtype=float)
    feature[2:5] = 2.0
    feature[7:10] = 3.0

    result = detect_threshold_events(feature, threshold=1.0, merge_gap_samples=2)

    assert len(result.candidates) == 1
    assert result.candidates[0].start_sample == 2
    assert result.candidates[0].end_sample == 10


def test_threshold_max_events_keeps_highest_scores():
    feature = np.zeros((20, 1), dtype=float)
    feature[2:5, 0] = 2.0
    feature[10:15, 0] = 5.0

    result = detect_threshold_events(feature, threshold=1.0, max_events=1)

    assert len(result.candidates) == 1
    assert result.candidates[0].peak_value == pytest.approx(5.0)


def test_events_accept_dasdata_input():
    data = make_das_data(np.ones((12, 2), dtype=float))

    envelope = amplitude_envelope(data)
    ratio = sta_lta_ratio(data, sta_samples=2, lta_samples=5)

    assert envelope.source_metadata["n_samples"] == 12
    assert ratio.source_metadata["n_channels"] == 2


def test_nan_inf_raise_and_input_not_modified():
    data = np.ones((20, 2), dtype=float)
    original = data.copy()

    amplitude_envelope(data)
    energy_envelope(data, window_samples=3)
    sta_lta_ratio(data, sta_samples=2, lta_samples=5)

    np.testing.assert_array_equal(data, original)
    bad = data.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or Inf"):
        amplitude_envelope(bad, nan_policy="raise")


def test_detect_stalta_events_returns_candidates():
    data = np.zeros((100, 1), dtype=float)
    data[45:55, 0] = 10.0

    result = detect_stalta_events(
        data,
        sta_samples=3,
        lta_samples=20,
        trigger_on=1.5,
        trigger_off=1.0,
        min_duration_samples=2,
    )

    assert result.method == "stalta"
    assert result.feature.shape == data.shape
    assert result.candidates
