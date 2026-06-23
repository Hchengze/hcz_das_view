"""Matplotlib helpers for moveout and directional-energy attributes."""

from __future__ import annotations

import numpy as np

from das_view.analysis.moveout import ApparentSlopeResult, DirectionalEnergyResult, MoveoutCoherenceResult


def plot_directional_energy(result, *, ax=None):
    """Plot positive/negative/zero wavenumber energy summary."""

    import matplotlib.pyplot as plt

    if not isinstance(result, DirectionalEnergyResult):
        raise TypeError("plot_directional_energy expects DirectionalEnergyResult")
    if ax is None:
        _, ax = plt.subplots()
    labels = ["positive k", "negative k", "zero k"]
    values = [
        result.positive_wavenumber_energy,
        result.negative_wavenumber_energy,
        result.zero_wavenumber_energy,
    ]
    ax.bar(labels, values, color=["tab:blue", "tab:orange", "tab:gray"])
    ax.set_ylabel("FK energy")
    ax.set_title("Directional energy attribute")
    return ax


def plot_apparent_velocity_map(result, *, ax=None):
    """Plot apparent velocity attributes by window/channel pair."""

    import matplotlib.pyplot as plt

    if not isinstance(result, ApparentSlopeResult):
        raise TypeError("plot_apparent_velocity_map expects ApparentSlopeResult")
    if ax is None:
        _, ax = plt.subplots()
    values = _as_image(result.apparent_velocity_mps)
    if values.size == 0:
        values = np.zeros((1, 1), dtype=float)
    finite = values[np.isfinite(values)]
    vmax = float(np.percentile(np.abs(finite), 95)) if finite.size else None
    image = ax.imshow(
        values,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
        cmap="coolwarm",
        vmin=-vmax if vmax else None,
        vmax=vmax,
    )
    ax.set_xlabel("Channel pair")
    ax.set_ylabel("Window")
    ax.set_title("Apparent velocity attribute")
    ax.figure.colorbar(image, ax=ax, label="m/s")
    return ax


def plot_moveout_coherence(result, *, ax=None):
    """Plot local moveout coherence values."""

    import matplotlib.pyplot as plt

    if not isinstance(result, MoveoutCoherenceResult):
        raise TypeError("plot_moveout_coherence expects MoveoutCoherenceResult")
    if ax is None:
        _, ax = plt.subplots()
    values = _as_image(result.coherence)
    if values.size == 0:
        values = np.zeros((1, 1), dtype=float)
    image = ax.imshow(values, aspect="auto", origin="upper", interpolation="nearest", cmap="viridis", vmin=0, vmax=1)
    ax.set_xlabel("Channel pair")
    ax.set_ylabel("Window")
    ax.set_title("Moveout coherence")
    ax.figure.colorbar(image, ax=ax, label="Correlation peak")
    return ax


def _as_image(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(1, -1)
    if array.ndim == 2:
        return array
    raise ValueError("moveout plotting expects scalar, 1-D, or 2-D values")
