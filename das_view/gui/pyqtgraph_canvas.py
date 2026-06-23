"""Optional PyQtGraph waterfall display helper for the GUI."""

from __future__ import annotations

from typing import Any

import numpy as np

from das_view.core.data_model import DASData
from das_view.plotting.downsample import downsample_for_display


class PyQtGraphWaterfallView:
    """Small wrapper around a PyQtGraph ImageView.

    PyQtGraph is imported lazily when the widget is constructed.
    """

    def __init__(self, *, parent: Any | None = None) -> None:
        try:
            import pyqtgraph as pg
        except ImportError as exc:
            raise ImportError(
                'PyQtGraph display backend is unavailable. Install with: pip install -e ".[display]"'
            ) from exc

        self._pg = pg
        self.widget = pg.ImageView(parent=parent)
        self.widget.ui.roiBtn.hide()
        self.widget.ui.menuBtn.hide()
        self._last_shape: tuple[int, ...] | None = None

    @property
    def last_shape(self) -> tuple[int, ...] | None:
        return self._last_shape

    def set_waterfall_image(
        self,
        data: Any,
        *,
        auto_downsample: bool = True,
        levels: tuple[float, float] | None = None,
        max_samples: int = 2048,
        max_channels: int = 1024,
    ) -> np.ndarray:
        """Set image data and return the displayed array."""

        displayed = prepare_waterfall_image(
            data,
            auto_downsample=auto_downsample,
            max_samples=max_samples,
            max_channels=max_channels,
        )
        self.widget.setImage(displayed.T, autoLevels=levels is None, levels=levels)
        self._last_shape = tuple(int(v) for v in displayed.shape)
        return displayed

    def clear(self) -> None:
        self.widget.clear()
        self._last_shape = None


def create_pyqtgraph_waterfall_widget(*, parent: Any | None = None) -> PyQtGraphWaterfallView:
    """Create a lazy-import PyQtGraph waterfall view."""

    return PyQtGraphWaterfallView(parent=parent)


def set_waterfall_image(
    widget: PyQtGraphWaterfallView,
    data: Any,
    *,
    auto_downsample: bool = True,
    levels: tuple[float, float] | None = None,
    max_samples: int = 2048,
    max_channels: int = 1024,
) -> np.ndarray:
    """Set image data on a PyQtGraphWaterfallView."""

    return widget.set_waterfall_image(
        data,
        auto_downsample=auto_downsample,
        levels=levels,
        max_samples=max_samples,
        max_channels=max_channels,
    )


def prepare_waterfall_image(
    data: Any,
    *,
    auto_downsample: bool = True,
    max_samples: int = 2048,
    max_channels: int = 1024,
) -> np.ndarray:
    """Return a finite 2-D array suitable for PyQtGraph ImageView."""

    array = np.asarray(data.data if isinstance(data, DASData) else data)
    if array.ndim != 2:
        raise ValueError("waterfall display expects a 2-D array shaped as (n_samples, n_channels)")
    if array.size == 0 or array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError("waterfall display cannot show empty data")
    if auto_downsample:
        array = downsample_for_display(
            array,
            max_samples=max_samples,
            max_channels=max_channels,
        ).data
    return np.asarray(array, dtype=float)
