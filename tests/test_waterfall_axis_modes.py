import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg", force=True)

from das_view.core.data_model import DASData, DASMetadata
from das_view.gui.models import normalize_waterfall_axis_mode, waterfall_axis_info
from das_view.plotting.waterfall import plot_waterfall


def test_waterfall_axis_mode_labels_and_distance_fallback():
    metadata = DASMetadata(n_samples=10, n_channels=4, dx_m=2.5, start_channel=10)

    channel = waterfall_axis_info(metadata, "channel")
    distance = waterfall_axis_info(metadata, "distance")

    assert channel.mode == "channel"
    assert channel.label_en == "Channel"
    assert channel.x_min == 10.0
    assert channel.x_max == 13.0
    assert distance.mode == "distance"
    assert distance.label_en == "Distance (m)"
    assert distance.x_min == 0.0
    assert distance.x_max == 7.5

    missing_dx = waterfall_axis_info(DASMetadata(n_samples=10, n_channels=4), "distance")
    assert missing_dx.mode == "channel"
    assert "falling back" in missing_dx.warning


def test_normalize_waterfall_axis_mode_rejects_unknown():
    assert normalize_waterfall_axis_mode("通道") == "channel"
    assert normalize_waterfall_axis_mode("距离") == "distance"
    with pytest.raises(ValueError, match="unsupported waterfall axis mode"):
        normalize_waterfall_axis_mode("bad")


def test_matplotlib_waterfall_axis_mode_labels():
    data = np.ones((8, 3), dtype=float)
    das_data = DASData(
        data=data,
        metadata=DASMetadata(n_samples=8, n_channels=3, dx_m=1.5, dt_s=0.01),
    )

    _, channel_ax = plot_waterfall(das_data, axis_mode="channel")
    _, distance_ax = plot_waterfall(das_data, axis_mode="distance")

    assert channel_ax.get_xlabel() == "Channel"
    assert distance_ax.get_xlabel() == "Distance (m)"
