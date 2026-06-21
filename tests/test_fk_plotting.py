import numpy as np
import pytest

import matplotlib

matplotlib.use("Agg")

from das_view.analysis.fk import FKResult
from das_view.plotting.fk import plot_fk


def make_result(values=None):
    frequencies = np.linspace(0.0, 10.0, 6)
    wavenumbers = np.linspace(-0.5, 0.5, 5)
    if values is None:
        values = np.ones((frequencies.size, wavenumbers.size))
    return FKResult(
        frequencies_hz=frequencies,
        wavenumbers_cycles_per_m=wavenumbers,
        values=np.asarray(values, dtype=float),
        sample_rate_hz=20.0,
        dx_m=1.0,
        output="amplitude",
        nfft_time=10,
        nfft_space=5,
    )


def test_plot_fk_can_save_image(tmp_path):
    fig, _ = plot_fk(make_result())
    output = tmp_path / "fk.png"

    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_plot_fk_db_handles_zero_values(tmp_path):
    fig, _ = plot_fk(make_result(values=np.zeros((6, 5))), db=True)
    output = tmp_path / "fk_db.png"

    fig.savefig(output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_plot_fk_rejects_invalid_result_type():
    with pytest.raises(ValueError, match="FKResult"):
        plot_fk(object())


def test_plot_fk_rejects_mismatched_shape():
    with pytest.raises(ValueError, match="shaped"):
        plot_fk(make_result(values=np.ones((2, 2))))
