import numpy as np

from das_view.core.data_model import DASData, DASMetadata
from das_view.gui.pyqtgraph_canvas import prepare_waterfall_image_for_pyqtgraph


def test_prepare_waterfall_image_for_pyqtgraph_keeps_visual_shape_and_transposes():
    das_data = DASData(
        data=np.arange(100 * 20, dtype=float).reshape(100, 20),
        metadata=DASMetadata(n_samples=100, n_channels=20, dx_m=2.0, dt_s=0.01),
    )

    prepared = prepare_waterfall_image_for_pyqtgraph(das_data, axis_mode="channel")

    assert prepared.data.shape == (100, 20)
    assert prepared.image.shape == (20, 100)
    assert prepared.rect == (0.0, 0.0, 19.0, 0.99)
    assert prepared.x_label_en == "Channel"
    assert prepared.y_label_en == "Time (s)"


def test_prepare_waterfall_image_for_pyqtgraph_distance_axis_and_fallback():
    with_dx = DASData(
        data=np.zeros((12, 5), dtype=float),
        metadata=DASMetadata(n_samples=12, n_channels=5, dx_m=1.25),
    )
    distance = prepare_waterfall_image_for_pyqtgraph(with_dx, axis_mode="distance")
    assert distance.axis_mode == "distance"
    assert distance.rect[2] == 5.0
    assert distance.x_label_en == "Distance (m)"

    no_dx = DASData(
        data=np.zeros((12, 5), dtype=float),
        metadata=DASMetadata(n_samples=12, n_channels=5),
    )
    fallback = prepare_waterfall_image_for_pyqtgraph(no_dx, axis_mode="distance")
    assert fallback.axis_mode == "channel"
    assert fallback.warning


def test_prepare_waterfall_image_for_pyqtgraph_downsamples_large_data():
    data = np.zeros((5000, 3000), dtype=float)

    prepared = prepare_waterfall_image_for_pyqtgraph(
        data,
        max_samples=100,
        max_channels=80,
    )

    assert prepared.data.shape[0] <= 100
    assert prepared.data.shape[1] <= 80
    assert prepared.image.shape == (prepared.data.shape[1], prepared.data.shape[0])
