import pytest

from das_view.analysis.events import EventCandidate
from das_view.analysis.roi import Annotation, ROISet, TimeChannelROI, rois_from_event_candidates


def make_candidate(event_id=1, start=10, end=20, channel=3, score=4.5):
    return EventCandidate(
        event_id=event_id,
        start_sample=start,
        end_sample=end,
        duration_samples=end - start,
        channel_start=channel,
        channel_end=channel,
        peak_sample=start + 2,
        peak_channel=channel,
        peak_value=score,
        mean_value=score / 2,
        max_value=score,
        score=score,
    )


def test_time_channel_roi_validation_duration_and_channels():
    roi = TimeChannelROI("r1", 2, 10, 1, 4, label="event", score=0.8)

    assert roi.duration_samples == 8
    assert roi.n_channels == 3
    assert roi.label == "event"
    with pytest.raises(ValueError, match="start_sample < end_sample"):
        TimeChannelROI("bad", 5, 5)
    with pytest.raises(ValueError, match="channel_start < channel_end"):
        TimeChannelROI("bad", 0, 5, 4, 4)


def test_time_channel_roi_to_dict_from_dict_and_time_only_roi():
    roi = TimeChannelROI("time", 0, 12, label="time_only", metadata={"kind": "window"})

    payload = roi.to_dict()
    restored = TimeChannelROI.from_dict(payload)

    assert restored == roi
    assert restored.n_channels is None
    assert payload["duration_samples"] == 12


def test_annotation_validation_and_roundtrip():
    annotation = Annotation("a1", "r1", "candidate", confidence=0.5, description="review")

    restored = Annotation.from_dict(annotation.to_dict())

    assert restored == annotation
    with pytest.raises(ValueError, match="confidence"):
        Annotation("a2", "r1", "bad", confidence=1.5)
    with pytest.raises(ValueError, match="label"):
        Annotation("a3", "r1", "")


def test_roiset_add_remove_filter_sort_and_limit():
    rois = ROISet()
    rois.add(TimeChannelROI("r1", 0, 10, 0, 2, label="a", score=1.0))
    rois.add(TimeChannelROI("r2", 10, 20, 0, 2, label="b", score=3.0))

    assert len(rois) == 2
    assert len(rois.filter_by_label("a")) == 1
    assert rois.sorted_by_score()[0].roi_id == "r2"
    assert len(rois.limited(1)) == 1
    removed = rois.remove("r1")
    assert removed.roi_id == "r1"
    with pytest.raises(KeyError):
        rois.remove("missing")


def test_rois_from_event_candidates_padding_and_max_rois():
    candidates = [make_candidate(1, 10, 20, 3, 4.5), make_candidate(2, 30, 35, 1, 2.0)]

    rois = rois_from_event_candidates(candidates, padding_samples=5, padding_channels=2, max_rois=1)

    assert len(rois) == 1
    roi = rois[0]
    assert roi.start_sample == 5
    assert roi.end_sample == 25
    assert roi.channel_start == 1
    assert roi.channel_end == 6
    assert roi.score == 4.5


def test_rois_from_event_candidates_handles_missing_channel_info():
    candidate = make_candidate(channel=None)
    candidate = EventCandidate(
        event_id=1,
        start_sample=2,
        end_sample=5,
        duration_samples=3,
        channel_start=None,
        channel_end=None,
        peak_sample=3,
        peak_channel=None,
        peak_value=1.0,
        mean_value=0.5,
        max_value=1.0,
        score=1.0,
    )

    rois = rois_from_event_candidates([candidate], padding_samples=10)

    assert rois[0].start_sample == 0
    assert rois[0].channel_start is None
    assert rois[0].channel_end is None


def test_roiset_from_list_and_invalid_add():
    rois = ROISet.from_list([TimeChannelROI("r1", 0, 4).to_dict()])

    assert rois.to_dict()["count"] == 1
    with pytest.raises(TypeError):
        rois.add("not a roi")
