import numpy as np
import pytest

from das_view.acceleration import is_cupy_available
from das_view.analysis.fk import fk_transform
from das_view.analysis.multiband import multiband_energy_map
from das_view.analysis.qc import channel_quality_metrics
from das_view.analysis.statistics import basic_statistics


def _sample_data():
    t = np.linspace(0.0, 1.0, 64, endpoint=False)
    return np.column_stack(
        [
            np.sin(2 * np.pi * 5 * t),
            np.cos(2 * np.pi * 10 * t),
            np.sin(2 * np.pi * 15 * t),
        ]
    )


def test_optional_backend_cpu_and_auto_match_for_statistics():
    data = _sample_data()

    cpu = basic_statistics(data, axis=0, backend="cpu")
    auto = basic_statistics(data, axis=0, backend="auto")

    np.testing.assert_allclose(auto.mean, cpu.mean)
    np.testing.assert_allclose(auto.energy, cpu.energy)


def test_optional_backend_cpu_and_auto_match_for_multiband():
    data = _sample_data()

    cpu = multiband_energy_map(
        data,
        sample_rate_hz=64.0,
        bands=((1.0, 8.0), (8.0, 20.0)),
        window_samples=32,
        step_samples=16,
        backend="cpu",
    )
    auto = multiband_energy_map(
        data,
        sample_rate_hz=64.0,
        bands=((1.0, 8.0), (8.0, 20.0)),
        window_samples=32,
        step_samples=16,
        backend="auto",
    )

    np.testing.assert_allclose(auto.values, cpu.values)


def test_optional_backend_cpu_and_auto_match_for_fk():
    data = _sample_data()

    cpu = fk_transform(data, sample_rate_hz=64.0, dx_m=1.0, backend="cpu")
    auto = fk_transform(data, sample_rate_hz=64.0, dx_m=1.0, backend="auto")

    np.testing.assert_allclose(auto.values, cpu.values)


def test_optional_backend_cpu_and_auto_match_for_qc():
    data = _sample_data()

    cpu = channel_quality_metrics(data, backend="cpu")
    auto = channel_quality_metrics(data, backend="auto")

    np.testing.assert_allclose(auto.rms, cpu.rms)
    np.testing.assert_allclose(auto.energy, cpu.energy)


def test_gpu_backend_errors_cleanly_without_cupy():
    if is_cupy_available():
        pytest.skip("CuPy is available in this environment")

    with pytest.raises(ImportError, match="CuPy"):
        basic_statistics(_sample_data(), backend="gpu")


@pytest.mark.skipif(not is_cupy_available(), reason="CuPy is optional and not required for CI")
def test_gpu_backend_matches_cpu_when_cupy_is_available():
    data = _sample_data()

    cpu_stats = basic_statistics(data, axis=0, backend="cpu")
    gpu_stats = basic_statistics(data, axis=0, backend="gpu")
    np.testing.assert_allclose(gpu_stats.mean, cpu_stats.mean, rtol=1e-6, atol=1e-8)
    np.testing.assert_allclose(gpu_stats.energy, cpu_stats.energy, rtol=1e-6, atol=1e-8)

    cpu_fk = fk_transform(data, sample_rate_hz=64.0, dx_m=1.0, backend="cpu")
    gpu_fk = fk_transform(data, sample_rate_hz=64.0, dx_m=1.0, backend="gpu")
    np.testing.assert_allclose(gpu_fk.values, cpu_fk.values, rtol=1e-6, atol=1e-8)
