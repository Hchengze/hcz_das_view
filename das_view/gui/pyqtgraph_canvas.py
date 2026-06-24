"""Optional PyQtGraph waterfall display helper for the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from das_view.core.data_model import DASData
from das_view.gui.models import waterfall_axis_info
from das_view.plotting.downsample import downsample_for_display


@dataclass(frozen=True, slots=True)
class PyQtGraphWaterfallImage:
    """Prepared image data and coordinates for PyQtGraph ImageView."""

    data: np.ndarray
    image: np.ndarray
    rect: tuple[float, float, float, float]
    x_label_en: str
    x_label_zh: str
    y_label_en: str
    y_label_zh: str
    axis_mode: str
    warning: str | None = None


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
        axis_mode: str = "channel",
        language: str = "en_US",
        auto_downsample: bool = True,
        levels: tuple[float, float] | None = None,
        max_samples: int = 2048,
        max_channels: int = 1024,
    ) -> PyQtGraphWaterfallImage:
        """Set image data and return the prepared display description."""

        prepared = prepare_waterfall_image_for_pyqtgraph(
            data,
            axis_mode=axis_mode,
            auto_downsample=auto_downsample,
            max_samples=max_samples,
            max_channels=max_channels,
        )
        try:
            import pyqtgraph as pg

            rect = pg.QtCore.QRectF(*prepared.rect)
        except Exception:  # noqa: BLE001 - PyQtGraph is already loaded; fallback is harmless.
            rect = None
        self.widget.setImage(prepared.image, autoLevels=levels is None, levels=levels)
        if rect is not None:
            self.widget.imageItem.setRect(rect)
        view = self.widget.getView()
        view.setAspectLocked(False)
        view.autoRange()
        self._last_shape = tuple(int(v) for v in prepared.data.shape)
        return prepared

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
    axis_mode: str = "channel",
    language: str = "en_US",
    auto_downsample: bool = True,
    levels: tuple[float, float] | None = None,
    max_samples: int = 2048,
    max_channels: int = 1024,
) -> PyQtGraphWaterfallImage:
    """Set image data on a PyQtGraphWaterfallView."""

    return widget.set_waterfall_image(
        data,
        axis_mode=axis_mode,
        language=language,
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

    return prepare_waterfall_image_for_pyqtgraph(
        data,
        axis_mode="channel",
        auto_downsample=auto_downsample,
        max_samples=max_samples,
        max_channels=max_channels,
    ).data


def prepare_waterfall_image_for_pyqtgraph(
    data: Any,
    *,
    axis_mode: str = "channel",
    auto_downsample: bool = True,
    max_samples: int = 2048,
    max_channels: int = 1024,
) -> PyQtGraphWaterfallImage:
    """Prepare a DAS waterfall image for PyQtGraph without importing PyQtGraph.

    The internal DAS convention remains ``(n_samples, n_channels)``. PyQtGraph
    ImageView interprets image shape as ``(x, y)``, so the returned ``image`` is
    transposed to ``(n_channels, n_samples)`` while ``data`` preserves the DAS
    orientation for tests and status messages.
    """

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
    displayed = np.asarray(array, dtype=float)
    metadata = getattr(data, "metadata", None)
    if metadata is None:
        metadata = _ArrayMetadata(displayed.shape)
    axis = waterfall_axis_info(metadata, axis_mode)
    x0, x1 = axis.x_min, axis.x_max
    width = _positive_span(x0, x1)
    if getattr(metadata, "dt_s", None) is not None:
        y0 = 0.0
        y1 = float(metadata.dt_s) * max(displayed.shape[0] - 1, 0)
        y_label_en = "Time (s)"
        y_label_zh = "时间 (s)"
    else:
        y0 = 0.0
        y1 = float(max(displayed.shape[0] - 1, 0))
        y_label_en = "Sample index"
        y_label_zh = "采样点"
    height = _positive_span(y0, y1)
    return PyQtGraphWaterfallImage(
        data=displayed,
        image=displayed.T,
        rect=(min(x0, x1), min(y0, y1), width, height),
        x_label_en=axis.label_en,
        x_label_zh=axis.label_zh,
        y_label_en=y_label_en,
        y_label_zh=y_label_zh,
        axis_mode=axis.mode,
        warning=axis.warning,
    )


class _ArrayMetadata:
    def __init__(self, shape: tuple[int, int]) -> None:
        self.n_samples = int(shape[0])
        self.n_channels = int(shape[1])
        self.dx_m = None
        self.dt_s = None
        self.start_channel = None


def _positive_span(start: float, stop: float) -> float:
    span = abs(float(stop) - float(start))
    return span if span > 0 else 1.0
