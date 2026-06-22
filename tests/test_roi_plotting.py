import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from das_view.analysis.events import EventCandidate
from das_view.analysis.roi import TimeChannelROI
from das_view.core.data_model import DASData, DASMetadata
from das_view.plotting.roi import plot_event_candidates_on_waterfall, plot_rois_on_waterfall


def make_das_data():
    data = np.zeros((20, 5), dtype=float)
    return DASData(data=data, metadata=DASMetadata(n_samples=20, n_channels=5, sample_rate_hz=1000.0))


def test_plot_rois_empty_does_not_crash(tmp_path):
    fig, ax = plot_rois_on_waterfall(make_das_data(), [])
    output = tmp_path / "empty.png"
    fig.savefig(output)

    assert output.exists()
    plt.close(fig)


def test_plot_one_roi_can_save_image(tmp_path):
    fig, ax = plot_rois_on_waterfall(make_das_data(), [TimeChannelROI("r1", 2, 8, 1, 3)])
    output = tmp_path / "roi.png"
    fig.savefig(output)

    assert output.exists()
    assert len(ax.patches) == 1
    plt.close(fig)


def test_plot_rois_max_rois_limits_patches():
    fig, ax = plot_rois_on_waterfall(
        make_das_data(),
        [TimeChannelROI("r1", 0, 4, 0, 1), TimeChannelROI("r2", 5, 9, 1, 2)],
        max_rois=1,
    )

    assert len(ax.patches) == 1
    plt.close(fig)


def test_plot_rois_rejects_invalid_objects():
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="TimeChannelROI"):
        plot_rois_on_waterfall(ax, ["bad"])
    plt.close(fig)


def test_plot_event_candidates_overlay():
    candidate = EventCandidate(
        event_id=1,
        start_sample=2,
        end_sample=8,
        duration_samples=6,
        channel_start=1,
        channel_end=1,
        peak_sample=4,
        peak_channel=1,
        peak_value=2.0,
        mean_value=1.0,
        max_value=2.0,
        score=2.0,
    )

    fig, ax = plot_event_candidates_on_waterfall(make_das_data(), [candidate])

    assert len(ax.patches) == 1
    plt.close(fig)
