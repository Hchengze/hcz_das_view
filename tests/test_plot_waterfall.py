import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from das_view.core.data_model import DASData, DASMetadata
from das_view.plotting.waterfall import plot_waterfall


def test_plot_waterfall_saves_image_without_pyqt(tmp_path):
    metadata = DASMetadata(
        n_samples=10,
        n_channels=4,
        sample_rate_hz=100.0,
        dx_m=0.5,
        source_format="synthetic",
    )
    das_data = DASData(
        data=np.linspace(-1.0, 1.0, 40, dtype=np.float32).reshape(10, 4),
        metadata=metadata,
    )

    fig, ax = plot_waterfall(das_data)
    output = tmp_path / "waterfall.png"
    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert ax.get_xlabel() == "Distance (m)"
