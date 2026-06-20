import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

from das_view.core.data_model import DASData, DASMetadata
from das_view.plotting.waveform import plot_waveform


def make_das_data(data):
    return DASData(
        data=np.asarray(data, dtype=np.float32),
        metadata=DASMetadata(
            n_samples=np.asarray(data).shape[0],
            n_channels=np.asarray(data).shape[1],
            sample_rate_hz=100.0,
            dx_m=0.5,
            start_channel=10,
            source_format="synthetic",
        ),
    )


def test_plot_waveform_single_channel_saves_image(tmp_path):
    das_data = make_das_data(np.linspace(-1.0, 1.0, 20).reshape(10, 2))

    fig, ax = plot_waveform(das_data, channels=1)
    output = tmp_path / "trace.png"
    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert ax.get_xlabel() == "Time (s)"
    assert "channel 11" in ax.get_title()


def test_plot_waveform_multiple_channels_with_offsets(tmp_path):
    data = np.arange(40, dtype=np.float32).reshape(10, 4)
    das_data = make_das_data(data)

    fig, ax = plot_waveform(das_data, channels=[0, 2, 3])
    output = tmp_path / "traces.png"
    fig.savefig(output)

    assert output.exists()
    assert len(ax.lines) == 3
    assert ax.get_legend() is not None


def test_plot_waveform_rejects_invalid_channel():
    das_data = make_das_data(np.zeros((5, 2), dtype=np.float32))

    with pytest.raises(ValueError, match="out of range"):
        plot_waveform(das_data, channels=2)


def test_plot_waveform_handles_constant_and_zero_data(tmp_path):
    constant = make_das_data(np.zeros((8, 3), dtype=np.float32))

    fig, ax = plot_waveform(constant, channels=[0, 1, 2])
    output = tmp_path / "constant.png"
    fig.savefig(output)

    assert output.exists()
    assert len(ax.lines) == 3


def test_plot_waveform_can_use_sample_index_without_dt():
    data = np.ones((4, 1), dtype=np.float32)
    das_data = DASData(data=data, metadata=DASMetadata(n_samples=4, n_channels=1))

    _, ax = plot_waveform(das_data)

    assert ax.get_xlabel() == "Sample index"
