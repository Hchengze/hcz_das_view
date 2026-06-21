import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
pytest.importorskip("scipy")

from das_view.analysis.spectrum import (
    SpectrumResult,
    amplitude_spectrum,
    single_channel_spectrogram,
)
from das_view.plotting.spectra import plot_spectrogram, plot_spectrum


def sine_data():
    sample_rate_hz = 200.0
    t = np.arange(512, dtype=float) / sample_rate_hz
    return np.column_stack(
        [
            np.sin(2 * np.pi * 10.0 * t),
            np.sin(2 * np.pi * 20.0 * t),
        ]
    )


def test_plot_spectrum_saves_image(tmp_path):
    result = amplitude_spectrum(sine_data(), sample_rate_hz=200.0, channels=[0, 1])

    fig, ax = plot_spectrum(result)
    output = tmp_path / "spectrum.png"
    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert ax.get_xlabel() == "Frequency (Hz)"
    assert len(ax.lines) == 2


def test_plot_spectrogram_saves_image(tmp_path):
    result = single_channel_spectrogram(sine_data(), sample_rate_hz=200.0, channel=0, nperseg=128)

    fig, ax = plot_spectrogram(result)
    output = tmp_path / "spectrogram.png"
    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0
    assert ax.get_ylabel() == "Frequency (Hz)"


def test_plot_spectrum_rejects_empty_result():
    result = SpectrumResult(
        frequencies_hz=np.array([]),
        values=np.array([]),
        kind="amplitude",
        sample_rate_hz=100.0,
        axis=0,
        nfft=0,
    )

    with pytest.raises(ValueError, match="non-empty"):
        plot_spectrum(result)


def test_plot_spectrogram_rejects_bad_shape():
    result = single_channel_spectrogram(sine_data(), sample_rate_hz=200.0, channel=0, nperseg=128)
    bad = type(result)(
        frequencies_hz=result.frequencies_hz,
        times_s=result.times_s,
        values=result.values.T,
        sample_rate_hz=result.sample_rate_hz,
        channel=result.channel,
        nperseg=result.nperseg,
        noverlap=result.noverlap,
        scaling=result.scaling,
    )

    with pytest.raises(ValueError, match="shaped"):
        plot_spectrogram(bad)
