"""ROI and event-candidate overlay plotting helpers."""

from __future__ import annotations

from typing import Any

from das_view.analysis.roi import TimeChannelROI, rois_from_event_candidates
from das_view.core.data_model import DASData
from das_view.plotting.waterfall import plot_waterfall


def plot_rois_on_waterfall(
    data_or_ax,
    rois,
    *,
    ax: Any | None = None,
    max_rois: int = 50,
    label: bool = True,
):
    """Overlay ROI rectangles on an existing axis or a DASData waterfall."""

    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if ax is None:
        if isinstance(data_or_ax, DASData):
            fig, ax = plot_waterfall(data_or_ax, show_colorbar=False)
        elif hasattr(data_or_ax, "imshow"):
            ax = data_or_ax
            fig = ax.figure
        else:
            raise ValueError("plot_rois_on_waterfall requires ax or DASData input")
    else:
        fig = ax.figure

    roi_list = list(rois)
    if max_rois is not None:
        if int(max_rois) < 0:
            raise ValueError("max_rois must be nonnegative")
        roi_list = roi_list[: int(max_rois)]

    for roi in roi_list:
        if not isinstance(roi, TimeChannelROI):
            raise ValueError("plot_rois_on_waterfall expects TimeChannelROI objects")
        x0 = roi.channel_start if roi.channel_start is not None else ax.get_xlim()[0]
        x1 = roi.channel_end if roi.channel_end is not None else ax.get_xlim()[1]
        y0 = roi.start_sample
        height = roi.duration_samples
        width = x1 - x0
        if width <= 0 or height <= 0:
            raise ValueError("ROI overlay has nonpositive width or height")
        rect = Rectangle(
            (x0, y0),
            width,
            height,
            fill=False,
            edgecolor="yellow",
            linewidth=1.5,
        )
        ax.add_patch(rect)
        if label:
            ax.text(x0, y0, roi.label, color="yellow", fontsize=8, va="bottom", ha="left")
    return fig, ax


def plot_event_candidates_on_waterfall(
    data_or_ax,
    candidates,
    *,
    ax: Any | None = None,
    max_events: int = 50,
):
    """Convert event candidates to ROIs and overlay them on a waterfall axis."""

    rois = rois_from_event_candidates(candidates, max_rois=max_events)
    return plot_rois_on_waterfall(data_or_ax, rois, ax=ax, max_rois=max_events)
