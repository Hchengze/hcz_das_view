"""Small GUI-facing state helpers that do not import PyQt5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from das_view.analysis.qc import channel_quality_rows
from das_view.analysis.roi import TimeChannelROI, rois_from_event_candidates
from das_view.io.export import analysis_summary_to_rows, event_candidates_to_rows, rois_to_rows
from das_view.utils.memory import estimate_array_nbytes, estimate_selection_nbytes, format_nbytes

SpectrumAnalysisType = Literal[
    "amplitude",
    "power",
    "psd_periodogram",
    "psd_welch",
    "spectrogram",
]
GUI_DEFAULT_MAX_SELECTION_BYTES = 256 * 1024 * 1024
GUI_LARGE_FILE_BYTES = 512 * 1024 * 1024


GUI_SAFE_SELECTION_PRESETS: dict[str, tuple[int, int]] = {
    "small_preview": (2000, 256),
    "medium_preview": (4096, 512),
    "analysis": (4096, 512),
    "fk": (2048, 256),
}
FKMode = Literal["transform", "velocity_filter"]
FKOutputMode = Literal["amplitude", "power"]
AnalysisType = Literal[
    "statistics",
    "band_energy",
    "spectral_attributes",
    "events_stalta",
    "events_envelope",
    "roi_statistics",
    "qc_report",
    "bad_channels",
    "multiband_summary",
    "denoise_report",
    "moveout_summary",
    "directional_energy",
]
WaterfallAxisMode = Literal["channel", "distance"]


@dataclass(frozen=True, slots=True)
class WaterfallAxisInfo:
    """Display-ready x-axis decision for GUI waterfall views."""

    requested_mode: WaterfallAxisMode
    mode: WaterfallAxisMode
    x_min: float
    x_max: float
    label_en: str
    label_zh: str
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class PreviewLimits:
    """Validated preview size limits from GUI controls or CLI options."""

    max_samples: int = 2000
    max_channels: int = 500


@dataclass(frozen=True, slots=True)
class PreviewDisplayInfo:
    """Display-ready summary for a preview result."""

    path: str
    reader_name: str
    preview_shape: tuple[int, int]
    downsample: tuple[int, int]

    @classmethod
    def from_preview_result(cls, result: Any) -> "PreviewDisplayInfo":
        source_path = result.metadata.source_path
        path = "N/A" if source_path is None else str(Path(source_path))
        return cls(
            path=path,
            reader_name=result.reader_name,
            preview_shape=tuple(int(v) for v in result.preview.data.shape),
            downsample=tuple(int(v) for v in result.downsample),
        )

    def as_lines(self) -> list[str]:
        return [
            f"Path: {self.path}",
            f"Reader: {self.reader_name}",
            f"Preview shape: {self.preview_shape[0]} samples x {self.preview_shape[1]} channels",
            f"Downsample: time_step={self.downsample[0]}, channel_step={self.downsample[1]}",
        ]

    def loaded_status(self) -> str:
        """Return a compact status bar summary."""

        return (
            f"Loaded: {self.reader_name} | "
            f"preview={self.preview_shape} | downsample={self.downsample}"
        )


@dataclass(frozen=True, slots=True)
class TaskControlState:
    """PyQt-free description of control availability during GUI tasks."""

    open_enabled: bool
    preview_controls_enabled: bool
    waveform_controls_enabled: bool
    spectrum_controls_enabled: bool
    fk_controls_enabled: bool
    analysis_controls_enabled: bool
    cancel_enabled: bool
    progress_visible: bool
    progress_minimum: int
    progress_maximum: int


@dataclass(frozen=True, slots=True)
class GUISelectionEstimate:
    """Display-ready estimate for a planned GUI read or analysis selection."""

    estimated_bytes: int
    formatted_size: str
    max_bytes: int | None
    within_limit: bool
    message: str


@dataclass(frozen=True, slots=True)
class SpectrumAnalysisRequest:
    """Validated GUI request for a single-channel spectrum analysis task."""

    analysis_type: SpectrumAnalysisType
    channel: int = 0
    max_samples: int = 4096
    nfft: int | None = None
    nperseg: int = 256
    noverlap: int | None = None
    db: bool = False

    @property
    def label(self) -> str:
        return spectrum_analysis_label(self.analysis_type)


@dataclass(frozen=True, slots=True)
class FKAnalysisRequest:
    """Validated GUI request for a bounded FK task."""

    mode: FKMode
    output: FKOutputMode = "amplitude"
    time_slice: slice | None = None
    channel_slice: slice | None = None
    downsample: tuple[int, int] = (1, 1)
    vmin_mps: float | None = None
    vmax_mps: float | None = None
    pass_inside: bool = True
    db: bool = False
    max_samples: int = 4096
    max_channels: int = 512

    @property
    def label(self) -> str:
        return fk_mode_label(self.mode)

    def bounded_time_slice(self) -> slice:
        return _bounded_slice(self.time_slice, self.max_samples)

    def bounded_channel_slice(self) -> slice:
        return _bounded_slice(self.channel_slice, self.max_channels)


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Validated GUI request for a bounded analysis-panel task."""

    analysis_type: AnalysisType
    time_slice: slice | None = None
    channel_slice: slice | None = None
    downsample: tuple[int, int] = (1, 1)
    max_samples: int = 4096
    max_channels: int = 512
    axis: int | None = None
    percentiles: tuple[float, ...] = (1, 5, 25, 50, 75, 95, 99)
    nan_policy: Literal["omit", "raise"] = "omit"
    bands: tuple[tuple[float, float], ...] = ((1.0, 5.0),)
    frequency_range: tuple[float, float] | None = None
    rolloff: float = 0.95
    average_channels: bool = False
    sta_samples: int = 25
    lta_samples: int = 250
    trigger_on: float = 3.0
    trigger_off: float | None = None
    threshold: float = 1.0
    smooth_samples: int | None = None
    min_duration_samples: int = 1
    merge_gap_samples: int = 0
    max_events: int | None = None
    rois: tuple[TimeChannelROI, ...] = ()
    use_event_rois: bool = False
    padding_samples: int = 0
    padding_channels: int = 0
    max_rois: int | None = None
    window_samples: int = 256
    step_samples: int = 128
    channel_lag: int = 1
    denoise_steps: tuple[tuple[str, dict[str, Any]], ...] = (
        ("common_mode_removal", {"method": "median"}),
    )

    @property
    def label(self) -> str:
        return analysis_type_label(self.analysis_type)

    def bounded_time_slice(self) -> slice:
        return _bounded_slice(self.time_slice, self.max_samples)

    def bounded_channel_slice(self) -> slice:
        return _bounded_slice(self.channel_slice, self.max_channels)


def task_control_state(is_running: bool) -> TaskControlState:
    """Return the control state for idle or running background tasks."""

    if is_running:
        return TaskControlState(
            open_enabled=False,
            preview_controls_enabled=False,
            waveform_controls_enabled=False,
            spectrum_controls_enabled=False,
            fk_controls_enabled=False,
            analysis_controls_enabled=False,
            cancel_enabled=True,
            progress_visible=True,
            progress_minimum=0,
            progress_maximum=0,
        )
    return TaskControlState(
        open_enabled=True,
        preview_controls_enabled=True,
        waveform_controls_enabled=True,
        spectrum_controls_enabled=True,
        fk_controls_enabled=True,
        analysis_controls_enabled=True,
        cancel_enabled=False,
        progress_visible=False,
        progress_minimum=0,
        progress_maximum=100,
    )


def format_task_status(task_name: str, state: str, message: str | None = None) -> str:
    """Return a compact status message for GUI background tasks."""

    normalized_task = str(task_name).strip().lower()
    labels = {
        "preview": "preview",
        "waveform": "waveform",
        "spectrum": "spectrum",
        "fk": "FK",
        "analysis": "analysis",
    }
    label = labels.get(normalized_task, normalized_task or "task")
    normalized_state = str(state).strip().lower()

    if normalized_state in {"loading", "running", "started"}:
        base = f"Loading {label}"
    elif normalized_state == "loaded":
        base = f"Loaded {label}"
    elif normalized_state == "cancelled":
        base = "Cancelled"
    elif normalized_state == "error":
        base = "Error"
    else:
        base = normalized_state.capitalize() if normalized_state else "Task"

    if message:
        return f"{base}: {message}"
    return base


def should_apply_task_result(
    *,
    task_id: int,
    active_task_id: int | None,
    was_cancelled: bool,
) -> bool:
    """Return whether a worker result still belongs to the active GUI task."""

    return active_task_id == task_id and not was_cancelled


def estimate_gui_selection_memory(
    metadata: Any,
    *,
    time_start: int | None = None,
    time_stop: int | None = None,
    time_step: int | None = None,
    channel_start: int | None = None,
    channel_stop: int | None = None,
    channel_step: int | None = None,
    downsample: int | tuple[int, int] | None = None,
    dtype: str | np.dtype[Any] = "float64",
) -> int:
    """Estimate GUI selection memory from metadata without reading data."""

    n_samples = _metadata_dimension(metadata, "n_samples")
    n_channels = _metadata_dimension(metadata, "n_channels")
    normalized_time_step = 1 if time_step is None else _positive_int(time_step, name="time_step")
    normalized_channel_step = (
        1 if channel_step is None else _positive_int(channel_step, name="channel_step")
    )
    if downsample is None:
        normalized_downsample = (1, 1)
    elif isinstance(downsample, int):
        step = _positive_int(downsample, name="downsample")
        normalized_downsample = (step, step)
    else:
        if len(downsample) != 2:
            raise ValueError("downsample must be an int or a (time_step, channel_step) tuple")
        normalized_downsample = (
            _positive_int(downsample[0], name="downsample time_step"),
            _positive_int(downsample[1], name="downsample channel_step"),
        )
    return estimate_selection_nbytes(
        n_samples=n_samples,
        n_channels=n_channels,
        time_slice=_selection_slice(
            time_start,
            time_stop,
            normalized_time_step,
            axis_name="time",
        ),
        channel_slice=_selection_slice(
            channel_start,
            channel_stop,
            normalized_channel_step,
            axis_name="channel",
        ),
        downsample=normalized_downsample,
        dtype=dtype,
    )


def format_gui_selection_warning(
    estimated_bytes: int,
    *,
    max_bytes: int | None = None,
    operation_name: str | None = None,
) -> str:
    """Return a user-facing GUI message for a planned selection."""

    operation = str(operation_name or "Selection").strip() or "Selection"
    estimated = int(estimated_bytes)
    if estimated < 0:
        raise ValueError("estimated_bytes must be non-negative")
    if max_bytes is None:
        return f"{operation} estimated memory: {format_nbytes(estimated)}."
    limit = int(max_bytes)
    if limit < 0:
        raise ValueError("max_bytes must be non-negative")
    if estimated <= limit:
        return (
            f"{operation} estimated memory: {format_nbytes(estimated)} "
            f"(limit {format_nbytes(limit)})."
        )
    return (
        f"{operation} selection is large: estimated {format_nbytes(estimated)} "
        f"exceeds the {format_nbytes(limit)} limit. Use bounded time/channel "
        "selection before running heavy analysis."
    )


def gui_selection_estimate(
    metadata: Any,
    *,
    max_bytes: int | None = GUI_DEFAULT_MAX_SELECTION_BYTES,
    operation_name: str | None = None,
    **selection: Any,
) -> GUISelectionEstimate:
    """Build a display-ready estimate for GUI run-before checks."""

    estimated = estimate_gui_selection_memory(metadata, **selection)
    within_limit = True if max_bytes is None else estimated <= int(max_bytes)
    return GUISelectionEstimate(
        estimated_bytes=estimated,
        formatted_size=format_nbytes(estimated),
        max_bytes=max_bytes,
        within_limit=within_limit,
        message=format_gui_selection_warning(
            estimated,
            max_bytes=max_bytes,
            operation_name=operation_name,
        ),
    )


def gui_large_file_warning(
    metadata: Any,
    *,
    max_bytes: int = GUI_LARGE_FILE_BYTES,
    dtype: str | np.dtype[Any] = "float64",
) -> str | None:
    """Return a large-file hint based on metadata-only full-array size."""

    n_samples = _metadata_dimension(metadata, "n_samples")
    n_channels = _metadata_dimension(metadata, "n_channels")
    estimated = estimate_array_nbytes(n_samples, n_channels, dtype=dtype)
    if estimated <= int(max_bytes):
        return None
    return (
        "This file is large. Use bounded time/channel selection before running "
        "heavy analysis."
    )


def format_gui_file_summary(
    metadata: Any,
    *,
    reader_name: str | None = None,
    max_preview_samples: int = 2000,
    max_preview_channels: int = 500,
    dtype: str | np.dtype[Any] = "float64",
) -> list[str]:
    """Return GUI file-summary lines with large-file and safe-selection hints."""

    n_samples = _metadata_dimension(metadata, "n_samples")
    n_channels = _metadata_dimension(metadata, "n_channels")
    full_bytes = estimate_array_nbytes(n_samples, n_channels, dtype=dtype)
    sample_rate_hz = getattr(metadata, "sample_rate_hz", None)
    dt_s = getattr(metadata, "dt_s", None)
    dx_m = getattr(metadata, "dx_m", None)
    duration = None
    if sample_rate_hz:
        duration = n_samples / float(sample_rate_hz)
    elif dt_s:
        duration = n_samples * float(dt_s)

    presets = gui_safe_selection_presets()
    lines = [
        f"Reader: {reader_name or 'unknown'}",
        f"n_samples: {n_samples}",
        f"n_channels: {n_channels}",
        f"sample_rate_hz: {_unknown_if_none(sample_rate_hz)}",
        f"duration_seconds: {_unknown_if_none(duration)}",
        f"dt_s: {_unknown_if_none(dt_s)}",
        f"dx_m: {_unknown_if_none(dx_m)}",
        f"estimated full array size: {format_nbytes(full_bytes)}",
        (
            "recommended preview selection: "
            f"up to {int(max_preview_samples)} samples x {int(max_preview_channels)} channels"
        ),
        (
            "recommended analysis selection: "
            f"up to {presets['analysis'][0]} samples x {presets['analysis'][1]} channels"
        ),
        (
            "FK safe default: "
            f"up to {presets['fk'][0]} samples x {presets['fk'][1]} channels"
        ),
    ]
    warning = gui_large_file_warning(metadata, dtype=dtype)
    if warning:
        lines.append(f"large-file warning: {warning}")
    return lines


def gui_safe_selection_presets() -> dict[str, tuple[int, int]]:
    """Return stable safe-selection presets for GUI labels and tests."""

    return dict(GUI_SAFE_SELECTION_PRESETS)


def parse_preview_limits(max_samples: Any, max_channels: Any) -> PreviewLimits:
    """Validate preview limits before passing them to create_preview."""

    try:
        parsed_samples = int(max_samples)
        parsed_channels = int(max_channels)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_samples and max_channels must be integers") from exc
    if parsed_samples <= 0:
        raise ValueError("max_samples must be positive")
    if parsed_channels <= 0:
        raise ValueError("max_channels must be positive")
    return PreviewLimits(max_samples=parsed_samples, max_channels=parsed_channels)


def normalize_waterfall_axis_mode(value: str | None) -> WaterfallAxisMode:
    """Normalize GUI waterfall x-axis mode labels or stable keys."""

    normalized = "channel" if value is None else str(value).strip().lower()
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    if normalized in {"channel", "channels", "channel index", "通道", "通道号"}:
        return "channel"
    if normalized in {"distance", "distance m", "distance (m)", "距离", "距离 (m)"}:
        return "distance"
    raise ValueError(f"unsupported waterfall axis mode: {value!r}")


def waterfall_axis_info(metadata: Any, mode: str | None) -> WaterfallAxisInfo:
    """Return x-axis extent and labels for a waterfall display.

    Channel mode is always available and is the GUI default. Distance mode
    requires metadata.dx_m; if it is missing, the result falls back to channel
    mode with a user-readable warning.
    """

    requested = normalize_waterfall_axis_mode(mode)
    n_channels = _metadata_dimension(metadata, "n_channels")
    start_channel = getattr(metadata, "start_channel", None)
    channel_start = 0 if start_channel is None else int(start_channel)
    if requested == "distance":
        dx_m = getattr(metadata, "dx_m", None)
        if dx_m is not None:
            return WaterfallAxisInfo(
                requested_mode=requested,
                mode="distance",
                x_min=0.0,
                x_max=float(dx_m) * max(n_channels - 1, 0),
                label_en="Distance (m)",
                label_zh="距离 (m)",
            )
        return WaterfallAxisInfo(
            requested_mode=requested,
            mode="channel",
            x_min=float(channel_start),
            x_max=float(channel_start + max(n_channels - 1, 0)),
            label_en="Channel",
            label_zh="通道",
            warning="Distance axis requires dx_m metadata; falling back to channel axis.",
        )
    return WaterfallAxisInfo(
        requested_mode=requested,
        mode="channel",
        x_min=float(channel_start),
        x_max=float(channel_start + max(n_channels - 1, 0)),
        label_en="Channel",
        label_zh="通道",
    )


def parse_channel_indices(text: str) -> tuple[int, ...]:
    """Parse comma-separated zero-based channel indices for waveform display.

    Duplicate channel indices are preserved intentionally so the GUI and tests
    reflect the user's requested order exactly.
    """

    if text is None:
        raise ValueError("channel input must not be empty")
    parts = [part.strip() for part in str(text).split(",")]
    if not parts or any(part == "" for part in parts):
        raise ValueError("channel input must contain one or more comma-separated integers")

    channels: list[int] = []
    for part in parts:
        try:
            value = int(part)
        except ValueError as exc:
            raise ValueError(f"channel index must be an integer: {part!r}") from exc
        if value < 0:
            raise ValueError("channel indices must be non-negative")
        channels.append(value)
    return tuple(channels)


def parse_optional_positive_int(text: Any, *, name: str) -> int | None:
    """Parse an optional positive integer from a GUI text field."""

    if text is None or str(text).strip() == "":
        return None
    try:
        value = int(str(text).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def parse_optional_nonnegative_int(text: Any, *, name: str) -> int | None:
    """Parse an optional non-negative integer from a GUI text field."""

    if text is None or str(text).strip() == "":
        return None
    try:
        value = int(str(text).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def parse_optional_float(text: Any, *, name: str) -> float | None:
    """Parse an optional finite float from a GUI text field."""

    if text is None or str(text).strip() == "":
        return None
    try:
        value = float(str(text).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not value == value or value in {float("inf"), float("-inf")}:
        raise ValueError(f"{name} must be finite")
    return value


def parse_optional_int(text: Any, *, name: str) -> int | None:
    """Parse an optional integer from a GUI text field."""

    if text is None or str(text).strip() == "":
        return None
    try:
        return int(str(text).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def parse_fk_request(
    *,
    mode: str,
    output: str,
    time_start_text: Any = "",
    time_stop_text: Any = "",
    time_step: Any = 1,
    channel_start_text: Any = "",
    channel_stop_text: Any = "",
    channel_step: Any = 1,
    vmin_text: Any = "",
    vmax_text: Any = "",
    pass_inside: bool = True,
    db: bool = False,
    max_samples: Any = 4096,
    max_channels: Any = 512,
) -> FKAnalysisRequest:
    """Validate FK tab controls before starting a background task."""

    parsed_mode = normalize_fk_mode(mode)
    parsed_output = normalize_fk_output_mode(output)
    time_start = parse_optional_int(time_start_text, name="time_start")
    time_stop = parse_optional_int(time_stop_text, name="time_stop")
    channel_start = parse_optional_int(channel_start_text, name="channel_start")
    channel_stop = parse_optional_int(channel_stop_text, name="channel_stop")
    parsed_time_step = _positive_int(time_step, name="time_step")
    parsed_channel_step = _positive_int(channel_step, name="channel_step")
    vmin = parse_optional_float(vmin_text, name="vmin_mps")
    vmax = parse_optional_float(vmax_text, name="vmax_mps")
    if vmin is not None and vmin <= 0:
        raise ValueError("vmin_mps must be positive")
    if vmax is not None and vmax <= 0:
        raise ValueError("vmax_mps must be positive")
    if parsed_mode == "velocity_filter" and vmin is None and vmax is None:
        raise ValueError("FK velocity filter requires at least one of vmin_mps or vmax_mps")
    if vmin is not None and vmax is not None and vmin >= vmax:
        raise ValueError("vmin_mps must be smaller than vmax_mps")

    parsed_max_samples = _positive_int(max_samples, name="max_samples")
    parsed_max_channels = _positive_int(max_channels, name="max_channels")

    return FKAnalysisRequest(
        mode=parsed_mode,
        output=parsed_output,
        time_slice=_optional_slice(time_start, time_stop, name="time"),
        channel_slice=_optional_slice(channel_start, channel_stop, name="channel"),
        downsample=(parsed_time_step, parsed_channel_step),
        vmin_mps=vmin,
        vmax_mps=vmax,
        pass_inside=bool(pass_inside),
        db=bool(db),
        max_samples=parsed_max_samples,
        max_channels=parsed_max_channels,
    )


def parse_analysis_selection(
    *,
    time_start_text: Any = "",
    time_stop_text: Any = "",
    time_step: Any = 1,
    channel_start_text: Any = "",
    channel_stop_text: Any = "",
    channel_step: Any = 1,
    max_samples: Any = 4096,
    max_channels: Any = 512,
) -> tuple[slice | None, slice | None, tuple[int, int], int, int]:
    """Parse common Analysis-tab time/channel selection controls."""

    time_start = parse_optional_int(time_start_text, name="time_start")
    time_stop = parse_optional_int(time_stop_text, name="time_stop")
    channel_start = parse_optional_int(channel_start_text, name="channel_start")
    channel_stop = parse_optional_int(channel_stop_text, name="channel_stop")
    parsed_time_step = _positive_int(time_step, name="time_step")
    parsed_channel_step = _positive_int(channel_step, name="channel_step")
    parsed_max_samples = _positive_int(max_samples, name="max_samples")
    parsed_max_channels = _positive_int(max_channels, name="max_channels")
    return (
        _optional_slice(time_start, time_stop, name="time"),
        _optional_slice(channel_start, channel_stop, name="channel"),
        (parsed_time_step, parsed_channel_step),
        parsed_max_samples,
        parsed_max_channels,
    )


def parse_percentiles(text: Any) -> tuple[float, ...]:
    """Parse comma-separated percentile values."""

    if text is None or str(text).strip() == "":
        return (1.0, 5.0, 25.0, 50.0, 75.0, 95.0, 99.0)
    values: list[float] = []
    for part in str(text).split(","):
        token = part.strip()
        if not token:
            raise ValueError("percentiles must be comma-separated numbers")
        value = _finite_float(token, name="percentile")
        if value < 0.0 or value > 100.0:
            raise ValueError("percentiles must be between 0 and 100")
        values.append(value)
    return tuple(values)


def parse_band_ranges(text: Any) -> tuple[tuple[float, float], ...]:
    """Parse bands such as ``1-5, 5-20`` into (low, high) pairs."""

    if text is None or str(text).strip() == "":
        raise ValueError("bands must contain at least one range")
    bands: list[tuple[float, float]] = []
    for part in str(text).split(","):
        token = part.strip()
        if not token or "-" not in token:
            raise ValueError("bands must use ranges like 1-5,5-20")
        low_text, high_text = token.split("-", 1)
        low = _finite_float(low_text.strip(), name="band low")
        high = _finite_float(high_text.strip(), name="band high")
        if low < 0.0 or low >= high:
            raise ValueError("each band must satisfy 0 <= low < high")
        bands.append((low, high))
    return tuple(bands)


def parse_frequency_range(text: Any) -> tuple[float, float] | None:
    """Parse an optional frequency range such as ``1-80`` or ``1,80``."""

    if text is None or str(text).strip() == "":
        return None
    token = str(text).strip()
    delimiter = "," if "," in token else "-"
    if delimiter not in token:
        raise ValueError("frequency_range must use low-high or low,high")
    low_text, high_text = token.split(delimiter, 1)
    low = _finite_float(low_text.strip(), name="frequency low")
    high = _finite_float(high_text.strip(), name="frequency high")
    if low < 0.0 or low >= high:
        raise ValueError("frequency_range must satisfy 0 <= low < high")
    return (low, high)


def parse_roi_text(text: Any) -> tuple[TimeChannelROI, ...]:
    """Parse one or more manual ROI rows.

    Accepted row format is ``start,end,ch_start,ch_end``.  Channel values may be
    omitted as ``start,end`` for time-only ROIs.
    """

    if text is None or str(text).strip() == "":
        return ()
    rois: list[TimeChannelROI] = []
    rows = str(text).replace(";", "\n").splitlines()
    for index, row in enumerate(rows, start=1):
        token = row.strip()
        if not token:
            continue
        parts = [part.strip() for part in token.split(",")]
        if len(parts) not in (2, 4):
            raise ValueError("ROI rows must be start,end or start,end,ch_start,ch_end")
        start = _nonnegative_int(parts[0], name="roi start")
        end = _nonnegative_int(parts[1], name="roi end")
        if len(parts) == 2:
            channel_start = None
            channel_end = None
        else:
            channel_start = _nonnegative_int(parts[2], name="roi channel_start")
            channel_end = _nonnegative_int(parts[3], name="roi channel_end")
        rois.append(
            TimeChannelROI(
                roi_id=f"manual_{index:03d}",
                start_sample=start,
                end_sample=end,
                channel_start=channel_start,
                channel_end=channel_end,
                label="manual",
            )
        )
    return tuple(rois)


def parse_analysis_request(
    *,
    analysis_type: str,
    time_start_text: Any = "",
    time_stop_text: Any = "",
    time_step: Any = 1,
    channel_start_text: Any = "",
    channel_stop_text: Any = "",
    channel_step: Any = 1,
    max_samples: Any = 4096,
    max_channels: Any = 512,
    axis: str | None = "global",
    percentiles_text: Any = "1,5,25,50,75,95,99",
    nan_policy: str = "omit",
    bands_text: Any = "1-5,5-20,20-80",
    frequency_range_text: Any = "",
    rolloff_text: Any = "0.95",
    average_channels: bool = False,
    sta_samples: Any = 25,
    lta_samples: Any = 250,
    trigger_on_text: Any = "3.0",
    trigger_off_text: Any = "",
    threshold_text: Any = "1.0",
    smooth_samples_text: Any = "",
    min_duration_samples: Any = 1,
    merge_gap_samples: Any = 0,
    max_events_text: Any = "",
    roi_text: Any = "",
    use_event_rois: bool = False,
    padding_samples: Any = 0,
    padding_channels: Any = 0,
    max_rois_text: Any = "",
    window_samples: Any = 256,
    step_samples: Any = 128,
    channel_lag: Any = 1,
    denoise_workflow: str = "common_mode_removal:method=median",
) -> AnalysisRequest:
    """Validate Analysis-tab controls before starting a background task."""

    parsed_type = normalize_analysis_type(analysis_type)
    time_slice, channel_slice, downsample, parsed_max_samples, parsed_max_channels = (
        parse_analysis_selection(
            time_start_text=time_start_text,
            time_stop_text=time_stop_text,
            time_step=time_step,
            channel_start_text=channel_start_text,
            channel_stop_text=channel_stop_text,
            channel_step=channel_step,
            max_samples=max_samples,
            max_channels=max_channels,
        )
    )
    parsed_nan_policy = str(nan_policy).strip().lower()
    if parsed_nan_policy not in {"omit", "raise"}:
        raise ValueError("nan_policy must be omit or raise")
    parsed_percentiles = (
        parse_percentiles(percentiles_text)
        if parsed_type in {"statistics", "roi_statistics"}
        else (1.0, 5.0, 25.0, 50.0, 75.0, 95.0, 99.0)
    )
    rolloff = _finite_float(rolloff_text, name="rolloff") if parsed_type == "spectral_attributes" else 0.95
    if rolloff <= 0.0 or rolloff > 1.0:
        raise ValueError("rolloff must be in the interval (0, 1]")
    parsed_max_events = (
        parse_optional_positive_int(max_events_text, name="max_events")
        if parsed_type in {"events_stalta", "events_envelope"}
        else None
    )
    parsed_max_rois = (
        parse_optional_positive_int(max_rois_text, name="max_rois")
        if parsed_type == "roi_statistics"
        else None
    )
    if parsed_type == "events_stalta":
        sta_value = _positive_int(sta_samples, name="sta_samples")
        lta_value = _positive_int(lta_samples, name="lta_samples")
        if lta_value <= sta_value:
            raise ValueError("lta_samples must be greater than sta_samples")
        trigger_on = _finite_float(trigger_on_text, name="trigger_on")
        trigger_off = parse_optional_float(trigger_off_text, name="trigger_off")
        if trigger_off is not None and trigger_off > trigger_on:
            raise ValueError("trigger_off must be less than or equal to trigger_on")
    else:
        sta_value = 25
        lta_value = 250
        trigger_on = 3.0
        trigger_off = None
    threshold = (
        _finite_float(threshold_text, name="threshold")
        if parsed_type == "events_envelope"
        else 1.0
    )
    smooth_samples = (
        parse_optional_positive_int(smooth_samples_text, name="smooth_samples")
        if parsed_type == "events_envelope"
        else None
    )
    rois = parse_roi_text(roi_text) if parsed_type == "roi_statistics" else ()
    parsed_window_samples = (
        _positive_int(window_samples, name="window_samples")
        if parsed_type in {"multiband_summary", "moveout_summary"}
        else 256
    )
    parsed_step_samples = (
        _positive_int(step_samples, name="step_samples")
        if parsed_type in {"multiband_summary", "moveout_summary"}
        else 128
    )
    if parsed_type in {"multiband_summary", "moveout_summary"} and parsed_step_samples > parsed_window_samples:
        raise ValueError("step_samples must be less than or equal to window_samples")
    parsed_channel_lag = (
        _positive_int(channel_lag, name="channel_lag")
        if parsed_type == "moveout_summary"
        else 1
    )
    parsed_denoise_steps = (
        parse_denoise_workflow(denoise_workflow)
        if parsed_type == "denoise_report"
        else (("common_mode_removal", {"method": "median"}),)
    )

    return AnalysisRequest(
        analysis_type=parsed_type,
        time_slice=time_slice,
        channel_slice=channel_slice,
        downsample=downsample,
        max_samples=parsed_max_samples,
        max_channels=parsed_max_channels,
        axis=_parse_analysis_axis(axis),
        percentiles=parsed_percentiles,
        nan_policy=parsed_nan_policy,  # type: ignore[arg-type]
        bands=parse_band_ranges(bands_text)
        if parsed_type in {"band_energy", "multiband_summary"}
        else ((1.0, 5.0),),
        frequency_range=parse_frequency_range(frequency_range_text)
        if parsed_type == "spectral_attributes"
        else None,
        rolloff=rolloff,
        average_channels=bool(average_channels),
        sta_samples=sta_value,
        lta_samples=lta_value,
        trigger_on=trigger_on,
        trigger_off=trigger_off,
        threshold=threshold,
        smooth_samples=smooth_samples,
        min_duration_samples=_positive_int(min_duration_samples, name="min_duration_samples"),
        merge_gap_samples=_nonnegative_int(merge_gap_samples, name="merge_gap_samples"),
        max_events=parsed_max_events,
        rois=rois,
        use_event_rois=bool(use_event_rois) if parsed_type == "roi_statistics" else False,
        padding_samples=_nonnegative_int(padding_samples, name="padding_samples")
        if parsed_type == "roi_statistics"
        else 0,
        padding_channels=_nonnegative_int(padding_channels, name="padding_channels")
        if parsed_type == "roi_statistics"
        else 0,
        max_rois=parsed_max_rois,
        window_samples=parsed_window_samples,
        step_samples=parsed_step_samples,
        channel_lag=parsed_channel_lag,
        denoise_steps=parsed_denoise_steps,
    )


def parse_qc_request(**kwargs: Any) -> AnalysisRequest:
    """Build a QC report request from GUI-style keyword arguments."""

    return parse_analysis_request(analysis_type="QC report", **kwargs)


def parse_multiband_request(**kwargs: Any) -> AnalysisRequest:
    """Build a multiband summary request from GUI-style keyword arguments."""

    return parse_analysis_request(analysis_type="Multiband map summary", **kwargs)


def parse_denoise_request(**kwargs: Any) -> AnalysisRequest:
    """Build a denoise report request from GUI-style keyword arguments."""

    return parse_analysis_request(analysis_type="Denoise report", **kwargs)


def parse_moveout_request(**kwargs: Any) -> AnalysisRequest:
    """Build a moveout summary request from GUI-style keyword arguments."""

    return parse_analysis_request(analysis_type="Moveout summary", **kwargs)


def parse_denoise_workflow(text: Any) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Parse a compact GUI denoise workflow string.

    Accepted examples:
    ``common_mode_removal:method=median`` or
    ``common_mode_removal:method=median;channel_balance:target=rms``.
    """

    raw = "common_mode_removal:method=median" if text is None or str(text).strip() == "" else str(text)
    steps: list[tuple[str, dict[str, Any]]] = []
    allowed = {
        "common_mode_removal",
        "despike",
        "running_median_filter",
        "channel_balance",
        "local_normalize",
        "time_space_median_filter",
        "robust_clip",
    }
    for item in raw.split(";"):
        entry = item.strip()
        if not entry:
            continue
        if ":" in entry:
            name, params_text = entry.split(":", 1)
        else:
            name, params_text = entry, ""
        normalized_name = name.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized_name not in allowed:
            raise ValueError(f"unsupported denoise step: {name.strip()!r}")
        params: dict[str, Any] = {}
        if params_text.strip():
            for pair in params_text.split(","):
                if "=" not in pair:
                    raise ValueError("denoise workflow parameters must use key=value pairs")
                key, value = pair.split("=", 1)
                key = key.strip()
                if not key:
                    raise ValueError("denoise workflow parameter names must not be empty")
                params[key] = _parse_denoise_value(value.strip())
        steps.append((normalized_name, params))
    if not steps:
        raise ValueError("denoise workflow must contain at least one step")
    return tuple(steps)


def normalize_analysis_type(value: str) -> AnalysisType:
    """Normalize an Analysis-tab label or stable key."""

    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    mapping: dict[str, AnalysisType] = {
        "statistics": "statistics",
        "band energy": "band_energy",
        "spectral attributes": "spectral_attributes",
        "event candidates sta/lta": "events_stalta",
        "event candidates stalta": "events_stalta",
        "events stalta": "events_stalta",
        "events sta lta": "events_stalta",
        "event candidates envelope threshold": "events_envelope",
        "events envelope": "events_envelope",
        "roi statistics": "roi_statistics",
        "qc report": "qc_report",
        "bad channels": "bad_channels",
        "bad channel detection": "bad_channels",
        "multiband map summary": "multiband_summary",
        "multiband summary": "multiband_summary",
        "denoise report": "denoise_report",
        "enhancement report": "denoise_report",
        "moveout summary": "moveout_summary",
        "directional energy": "directional_energy",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported analysis type: {value!r}") from exc


def analysis_type_label(value: str) -> str:
    labels = {
        "statistics": "Statistics",
        "band_energy": "Band energy",
        "spectral_attributes": "Spectral attributes",
        "events_stalta": "Event candidates - STA/LTA",
        "events_envelope": "Event candidates - Envelope threshold",
        "roi_statistics": "ROI statistics",
        "qc_report": "QC report",
        "bad_channels": "Bad channels",
        "multiband_summary": "Multiband map summary",
        "denoise_report": "Denoise report",
        "moveout_summary": "Moveout summary",
        "directional_energy": "Directional energy",
    }
    return labels.get(str(value), str(value))


def format_analysis_summary(service_result: Any, request: AnalysisRequest) -> list[str]:
    """Return concise display lines for an Analysis-tab service result."""

    lines = [
        f"Reader: {getattr(service_result, 'reader_name', None) or 'N/A'}",
        f"Analysis: {request.label}",
    ]
    selection = getattr(service_result, "selection", None)
    if selection is not None:
        lines.append(
            f"Selection: time={_format_slice(getattr(selection, 'time_slice', None))}, "
            f"channel={_format_slice(getattr(selection, 'channel_slice', None))}"
        )
        lines.append(f"Downsample: {getattr(selection, 'downsample', request.downsample)}")
    if request.analysis_type == "statistics":
        result = service_result.result
        lines.extend(
            [
                f"Axis: {result.axis}",
                f"Input shape: {result.input_shape}",
                f"count: {_compact_value(result.count)}",
                f"finite_count: {_compact_value(result.finite_count)}",
                f"nan_count: {_compact_value(result.nan_count)}",
                f"inf_count: {_compact_value(_inf_count(result))}",
                f"mean: {_compact_value(result.mean)}",
                f"std: {_compact_value(result.std)}",
                f"rms: {_compact_value(result.rms)}",
                f"energy: {_compact_value(result.energy)}",
                f"min: {_compact_value(result.min)}",
                f"max: {_compact_value(result.max)}",
            ]
        )
        for percentile, value in result.percentiles.items():
            lines.append(f"p{percentile:g}: {_compact_value(value)}")
    elif request.analysis_type == "band_energy":
        result = service_result.result
        lines.extend(
            [
                f"Bands: {result.bands}",
                f"average_channels: {result.average_channels}",
                f"band_energy: {_compact_value(result.band_energy)}",
                f"band_energy_ratio: {_compact_value(result.band_energy_ratio)}",
                f"total_energy: {_compact_value(result.total_energy)}",
            ]
        )
    elif request.analysis_type == "spectral_attributes":
        result = service_result.result
        lines.extend(
            [
                f"dominant_frequency_hz: {_compact_value(result.dominant_frequency_hz)}",
                f"spectral_centroid_hz: {_compact_value(result.spectral_centroid_hz)}",
                f"spectral_bandwidth_hz: {_compact_value(result.spectral_bandwidth_hz)}",
                f"spectral_rolloff_hz: {_compact_value(result.spectral_rolloff_hz)}",
                f"total_energy: {_compact_value(result.total_energy)}",
            ]
        )
    elif request.analysis_type in {"events_stalta", "events_envelope"}:
        result = service_result.result
        lines.extend(
            [
                f"Method: {result.method}",
                f"Feature shape: {result.feature.shape}",
                f"Event candidates: {len(result.candidates)}",
                "Event candidates are data-review triggers, not location results.",
            ]
        )
    elif request.analysis_type == "roi_statistics":
        lines.extend(
            [
                f"ROI results: {len(service_result.results)}",
                "ROI statistics are bounded data summaries, not interpretation results.",
            ]
        )
    elif request.analysis_type in {"qc_report", "bad_channels"}:
        lines.extend(format_qc_summary(service_result))
    elif request.analysis_type == "multiband_summary":
        lines.extend(format_multiband_summary(service_result))
    elif request.analysis_type == "denoise_report":
        lines.extend(format_denoise_report_summary(service_result))
    elif request.analysis_type == "moveout_summary":
        lines.extend(format_moveout_summary(service_result))
    elif request.analysis_type == "directional_energy":
        lines.extend(format_directional_energy_summary(service_result))
    history = getattr(service_result, "preprocessing_history", ())
    if history:
        lines.append(f"Preprocessing steps: {len(history)}")
    return lines


def candidates_to_table_rows(candidates) -> list[dict[str, Any]]:
    return event_candidates_to_rows(candidates)


def rois_to_table_rows(rois) -> list[dict[str, Any]]:
    return rois_to_rows(rois)


def roi_statistics_to_table_rows(summary) -> list[dict[str, Any]]:
    return analysis_summary_to_rows(summary)


def format_qc_summary(service_result: Any) -> list[str]:
    report = service_result.result
    metrics = report.channel_metrics
    summary = report.global_summary
    return [
        f"n_channels: {summary.get('n_channels', metrics.n_channels)}",
        f"bad channel count: {len(report.bad_channel_indices)}",
        f"dead channel count: {int(np.sum(metrics.dead_channel))}",
        f"noisy channel count: {int(np.sum(metrics.noisy_channel))}",
        f"low-energy channel count: {int(np.sum(metrics.low_energy_channel))}",
        f"mean quality score: {_compact_value(summary.get('mean_quality_score', np.mean(metrics.quality_score)))}",
        f"nan fraction mean: {_compact_value(np.mean(metrics.nan_fraction))}",
        f"inf fraction mean: {_compact_value(np.mean(metrics.inf_fraction))}",
        f"clipping fraction mean: {_compact_value(np.mean(metrics.clipping_fraction))}",
        f"spike count total: {int(np.sum(metrics.spike_count))}",
        "QC and bad-channel flags are data-quality review aids.",
    ]


def format_bad_channel_rows(report: Any) -> list[dict[str, Any]]:
    data_report = report.result if hasattr(report, "result") else report
    rows = []
    for row in channel_quality_rows(data_report):
        flags = _qc_flags(row)
        if bool(row.get("bad_channel")):
            rows.append(
                {
                    "channel": row["channel"],
                    "reason": "|".join(flags) if flags else "bad_channel",
                    "quality_score": row["quality_score"],
                    "rms": row["rms"],
                    "std": row["std"],
                    "spike_count": row["spike_count"],
                    "clipping_fraction": row["clipping_fraction"],
                }
            )
    return rows


def format_qc_rows(report: Any) -> list[dict[str, Any]]:
    data_report = report.result if hasattr(report, "result") else report
    rows = []
    for row in channel_quality_rows(data_report):
        rows.append(
            {
                "channel": row["channel"],
                "rms": row["rms"],
                "std": row["std"],
                "energy": row["energy"],
                "nan_fraction": row["nan_fraction"],
                "inf_fraction": row["inf_fraction"],
                "zero_fraction": row["zero_fraction"],
                "clipping_fraction": row["clipping_fraction"],
                "spike_count": row["spike_count"],
                "quality_score": row["quality_score"],
                "flags": "|".join(_qc_flags(row)),
            }
        )
    return rows


def format_multiband_summary(service_result: Any) -> list[str]:
    result = service_result.result
    values = np.asarray(result.values, dtype=float)
    return [
        f"bands: {result.metadata.get('bands', result.feature_names)}",
        f"window_samples: {result.window_samples}",
        f"step_samples: {result.step_samples}",
        f"n_windows: {values.shape[0] if values.ndim >= 1 else 0}",
        f"n_channels: {values.shape[1] if values.ndim >= 2 else 0}",
        f"n_bands: {values.shape[2] if values.ndim >= 3 else len(result.feature_names)}",
    ]


def format_multiband_rows(service_result: Any) -> list[dict[str, Any]]:
    result = service_result.result
    values = np.asarray(result.values, dtype=float)
    if values.ndim == 2:
        values = values[:, :, np.newaxis]
    total = np.sum(values, axis=2, keepdims=True)
    ratios = np.divide(values, total, out=np.zeros_like(values), where=total > 0)
    rows = []
    for index, name in enumerate(result.feature_names):
        band_values = values[:, :, index]
        band_ratios = ratios[:, :, index]
        rows.append(
            {
                "band": name,
                "mean_energy": float(np.nanmean(band_values)) if band_values.size else 0.0,
                "max_energy": float(np.nanmax(band_values)) if band_values.size else 0.0,
                "mean_ratio": float(np.nanmean(band_ratios)) if band_ratios.size else 0.0,
            }
        )
    return rows


def format_denoise_report_summary(service_result: Any) -> list[str]:
    report = service_result.result
    before = report.before
    after = report.after
    return [
        f"steps: {len(report.steps)}",
        f"input_shape: {report.input_shape}",
        f"output_shape: {report.output_shape}",
        f"before_rms: {_compact_value(before.get('rms'))}",
        f"after_rms: {_compact_value(after.get('rms'))}",
        f"before_energy: {_compact_value(before.get('energy'))}",
        f"after_energy: {_compact_value(after.get('energy'))}",
        f"finite_count: {_compact_value(after.get('finite_count'))}",
        "Denoise/enhancement reports are signal-review aids.",
    ]


def format_denoise_report_rows(service_result: Any) -> list[dict[str, Any]]:
    rows = []
    for index, step in enumerate(service_result.result.steps, start=1):
        before = step.get("before", {})
        after = step.get("after", {})
        rows.append(
            {
                "step": index,
                "method": step.get("name", ""),
                "before_rms": before.get("rms"),
                "after_rms": after.get("rms"),
                "before_energy": before.get("energy"),
                "after_energy": after.get("energy"),
                "finite_count": after.get("finite_count"),
            }
        )
    return rows


def format_moveout_summary(service_result: Any) -> list[str]:
    report = service_result.result
    directional = report.directional_energy
    summary = report.summary
    return [
        f"positive_k_energy: {_compact_value(directional.positive_wavenumber_energy)}",
        f"negative_k_energy: {_compact_value(directional.negative_wavenumber_energy)}",
        f"zero_k_energy: {_compact_value(directional.zero_wavenumber_energy)}",
        f"directional_ratio: {_compact_value(summary.get('directional_ratio', directional.directional_ratio))}",
        f"dominant_direction: {summary.get('dominant_direction', directional.dominant_direction)}",
        f"mean_apparent_velocity_attribute: {_compact_value(summary.get('median_apparent_velocity_mps'))}",
        f"mean_correlation_peak: {_compact_value(summary.get('mean_abs_correlation_peak'))}",
        "apparent velocity is an auxiliary attribute, not a measured propagation velocity.",
        "directional energy is not localization or inversion.",
    ]


def format_moveout_summary_rows(service_result: Any) -> list[dict[str, Any]]:
    report = service_result.result
    summary = report.summary
    directional = report.directional_energy
    return [
        {
            "positive_k_energy": directional.positive_wavenumber_energy,
            "negative_k_energy": directional.negative_wavenumber_energy,
            "zero_k_energy": directional.zero_wavenumber_energy,
            "directional_ratio": summary.get("directional_ratio", directional.directional_ratio),
            "dominant_direction": summary.get("dominant_direction", directional.dominant_direction),
            "mean_apparent_velocity_attribute": summary.get("median_apparent_velocity_mps"),
            "mean_correlation_peak": summary.get("mean_abs_correlation_peak"),
            "n_windows": summary.get("n_windows"),
            "n_channel_pairs": summary.get("n_channel_pairs"),
        }
    ]


def format_directional_energy_summary(service_result: Any) -> list[str]:
    result = service_result.result
    return [
        f"positive_k_energy: {_compact_value(result.positive_wavenumber_energy)}",
        f"negative_k_energy: {_compact_value(result.negative_wavenumber_energy)}",
        f"zero_k_energy: {_compact_value(result.zero_wavenumber_energy)}",
        f"directional_ratio: {_compact_value(result.directional_ratio)}",
        f"dominant_direction: {result.dominant_direction}",
        "directional energy is an FK-domain review attribute, not localization or inversion.",
    ]


def format_directional_energy_rows(service_result: Any) -> list[dict[str, Any]]:
    result = service_result.result
    rows = [
        {
            "component": "positive_k",
            "energy": result.positive_wavenumber_energy,
            "directional_ratio": result.directional_ratio,
            "dominant_direction": result.dominant_direction,
        },
        {
            "component": "negative_k",
            "energy": result.negative_wavenumber_energy,
            "directional_ratio": result.directional_ratio,
            "dominant_direction": result.dominant_direction,
        },
        {
            "component": "zero_k",
            "energy": result.zero_wavenumber_energy,
            "directional_ratio": result.directional_ratio,
            "dominant_direction": result.dominant_direction,
        },
    ]
    for band, energy in result.velocity_band_energy.items():
        rows.append(
            {
                "component": f"velocity_band:{band}",
                "energy": energy,
                "directional_ratio": result.directional_ratio,
                "dominant_direction": result.dominant_direction,
            }
        )
    return rows


def event_candidates_to_rois(candidates, request: AnalysisRequest) -> tuple[TimeChannelROI, ...]:
    roi_set = rois_from_event_candidates(
        candidates,
        padding_samples=request.padding_samples,
        padding_channels=request.padding_channels,
        max_rois=request.max_rois,
    )
    return tuple(roi_set)


def normalize_fk_mode(value: str) -> FKMode:
    """Normalize a GUI label or stable key to an FK mode."""

    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    mapping: dict[str, FKMode] = {
        "fk transform": "transform",
        "transform": "transform",
        "fk": "transform",
        "fk velocity filter": "velocity_filter",
        "velocity filter": "velocity_filter",
        "filter": "velocity_filter",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported FK mode: {value!r}") from exc


def normalize_fk_output_mode(value: str) -> FKOutputMode:
    """Normalize an FK output mode label or key."""

    normalized = str(value).strip().lower()
    if normalized in {"amplitude", "amp"}:
        return "amplitude"
    if normalized in {"power", "pow"}:
        return "power"
    raise ValueError(f"unsupported FK output mode: {value!r}")


def fk_mode_label(mode: str) -> str:
    """Return a user-facing label for a normalized FK mode."""

    labels = {
        "transform": "FK transform",
        "velocity_filter": "FK velocity filter",
    }
    return labels.get(str(mode), str(mode))


def format_fk_status(result: Any, request: FKAnalysisRequest) -> list[str]:
    """Return display-ready FK tab summary lines for a service result."""

    selection = getattr(result, "selection", None)
    lines = [
        f"Reader: {result.reader_name}",
        f"Mode: {request.label}",
        f"Selection: time={_format_slice(getattr(selection, 'time_slice', None))}, "
        f"channel={_format_slice(getattr(selection, 'channel_slice', None))}",
        f"Downsample: {getattr(selection, 'downsample', request.downsample)}",
    ]
    if request.mode == "transform":
        fk_result = result.result
        lines.extend(
            [
                f"Sample rate: {fk_result.sample_rate_hz} Hz",
                f"dx: {fk_result.dx_m} m",
                f"Frequency bins: {len(fk_result.frequencies_hz)}",
                f"Wavenumber bins: {len(fk_result.wavenumbers_cycles_per_m)}",
                f"Output mode: {fk_result.output}",
                f"Display: {'dB' if request.db else 'linear'}",
            ]
        )
    else:
        filter_result = result.result
        lines.extend(
            [
                f"vmin_mps: {filter_result.vmin_mps if filter_result.vmin_mps is not None else 'none'}",
                f"vmax_mps: {filter_result.vmax_mps if filter_result.vmax_mps is not None else 'none'}",
                f"Fan mode: {'pass velocity range' if filter_result.pass_inside else 'reject velocity range'}",
                f"Filtered shape: {filter_result.das_data.data.shape}",
                f"Mask shape: {filter_result.mask.shape}",
            ]
        )
        history = getattr(result, "preprocessing_history", ())
        if history:
            lines.append(f"Preprocessing steps: {len(history)}")
    return lines


def parse_spectrum_request(
    *,
    analysis_type: str,
    channel_text: str,
    nfft_text: Any = "",
    nperseg_text: Any = "",
    noverlap_text: Any = "",
    db: bool = False,
    max_samples: Any = 4096,
) -> SpectrumAnalysisRequest:
    """Validate Spectrum tab controls before starting a background task."""

    channels = parse_channel_indices(channel_text)
    if len(channels) != 1:
        raise ValueError("spectrum analysis expects exactly one channel index")
    nfft = parse_optional_positive_int(nfft_text, name="nfft")
    nperseg = parse_optional_positive_int(nperseg_text, name="nperseg") or 256
    noverlap = parse_optional_nonnegative_int(noverlap_text, name="noverlap")
    if noverlap is not None and noverlap >= nperseg:
        raise ValueError("noverlap must be less than nperseg")
    try:
        parsed_max_samples = int(max_samples)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_samples must be a positive integer") from exc
    if parsed_max_samples <= 0:
        raise ValueError("max_samples must be a positive integer")

    return SpectrumAnalysisRequest(
        analysis_type=normalize_spectrum_analysis_type(analysis_type),
        channel=channels[0],
        max_samples=parsed_max_samples,
        nfft=nfft,
        nperseg=nperseg,
        noverlap=noverlap,
        db=bool(db),
    )


def normalize_spectrum_analysis_type(value: str) -> SpectrumAnalysisType:
    """Normalize a GUI combo-box label or stable key to an analysis type."""

    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    mapping: dict[str, SpectrumAnalysisType] = {
        "amplitude": "amplitude",
        "amplitude spectrum": "amplitude",
        "power": "power",
        "power spectrum": "power",
        "psd periodogram": "psd_periodogram",
        "periodogram psd": "psd_periodogram",
        "periodogram": "psd_periodogram",
        "psd welch": "psd_welch",
        "welch psd": "psd_welch",
        "welch": "psd_welch",
        "spectrogram": "spectrogram",
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported spectrum analysis type: {value!r}") from exc


def spectrum_analysis_label(analysis_type: str) -> str:
    """Return a user-facing label for a normalized spectrum analysis type."""

    labels = {
        "amplitude": "Amplitude spectrum",
        "power": "Power spectrum",
        "psd_periodogram": "PSD periodogram",
        "psd_welch": "PSD Welch",
        "spectrogram": "Spectrogram",
    }
    return labels.get(str(analysis_type), str(analysis_type))


def format_spectrum_status(result: Any, request: SpectrumAnalysisRequest) -> list[str]:
    """Return display-ready Spectrum tab summary lines for a service result."""

    analysis_result = result.result
    frequencies = getattr(analysis_result, "frequencies_hz", ())
    times = getattr(analysis_result, "times_s", None)
    sample_rate_hz = getattr(analysis_result, "sample_rate_hz", None)
    lines = [
        f"Reader: {result.reader_name}",
        f"Analysis: {request.label}",
        f"Channel: {request.channel}",
        f"Sample rate: {sample_rate_hz} Hz",
        f"Frequency bins: {len(frequencies)}",
    ]
    if times is not None:
        lines.append(f"Time bins: {len(times)}")
    lines.extend(
        [
            f"Max samples: {request.max_samples}",
            f"nfft: {request.nfft if request.nfft is not None else 'auto'}",
            f"nperseg: {request.nperseg}",
            f"noverlap: {request.noverlap if request.noverlap is not None else 'auto'}",
        ]
    )
    if request.analysis_type in {"psd_periodogram", "psd_welch"}:
        lines.append(f"PSD display: {'dB' if request.db else 'linear'}")
    return lines


def _optional_slice(start: int | None, stop: int | None, *, name: str) -> slice | None:
    if start is None and stop is None:
        return None
    if start is not None and start < 0:
        raise ValueError(f"{name}_start must be non-negative")
    if stop is not None and stop < 0:
        raise ValueError(f"{name}_stop must be non-negative")
    if start is not None and stop is not None and start >= stop:
        raise ValueError(f"{name}_start must be smaller than {name}_stop")
    return slice(start, stop)


def _selection_slice(
    start: int | None,
    stop: int | None,
    step: int,
    *,
    axis_name: str,
) -> slice | None:
    if start is None and stop is None and step == 1:
        return None
    if start is not None and int(start) < 0:
        raise ValueError(f"{axis_name}_start must be non-negative")
    if stop is not None and int(stop) < 0:
        raise ValueError(f"{axis_name}_stop must be non-negative")
    if start is not None and stop is not None and int(start) >= int(stop):
        raise ValueError(f"{axis_name}_start must be smaller than {axis_name}_stop")
    return slice(start, stop, step)


def _parse_analysis_axis(value: str | None) -> int | None:
    normalized = "global" if value is None else str(value).strip().lower()
    if normalized in {"global", "none", ""}:
        return None
    if normalized in {"time", "channel summary", "axis 0", "0"}:
        return 0
    if normalized in {"channel", "time summary", "axis 1", "1"}:
        return 1
    raise ValueError(f"unsupported statistics axis: {value!r}")


def _parse_denoise_value(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    if np.isfinite(number) and number.is_integer():
        return int(number)
    return number


def _qc_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if row.get("dead_channel"):
        flags.append("dead")
    if row.get("noisy_channel"):
        flags.append("noisy")
    if row.get("low_energy_channel"):
        flags.append("low_energy")
    if float(row.get("nan_fraction", 0.0)) > 0:
        flags.append("nan")
    if float(row.get("inf_fraction", 0.0)) > 0:
        flags.append("inf")
    if float(row.get("clipping_fraction", 0.0)) > 0:
        flags.append("clipping")
    if int(row.get("spike_count", 0)) > 0:
        flags.append("spikes")
    if row.get("bad_channel") and not flags:
        flags.append("bad")
    return flags


def _bounded_slice(value: slice | None, limit: int) -> slice:
    limit = _positive_int(limit, name="limit")
    if value is None:
        return slice(0, limit)
    start = 0 if value.start is None else int(value.start)
    stop = value.stop
    if stop is None:
        stop = start + limit
    return slice(start, int(stop), value.step)


def _positive_int(value: Any, *, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _nonnegative_int(value: Any, *, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return parsed


def _finite_float(value: Any, *, name: str) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not np.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return float(parsed)


def _compact_value(value: Any, *, max_items: int = 6) -> str:
    array = np.asarray(value)
    if array.ndim == 0:
        scalar = array.item()
        if isinstance(scalar, float):
            return f"{scalar:.6g}"
        return str(scalar)
    flat = array.reshape(-1)
    preview = ", ".join(f"{float(item):.6g}" for item in flat[:max_items])
    suffix = ", ..." if flat.size > max_items else ""
    return f"[{preview}{suffix}] shape={tuple(array.shape)}"


def _inf_count(result: Any) -> Any:
    return np.asarray(result.posinf_count) + np.asarray(result.neginf_count)


def _format_slice(value: Any) -> str:
    if isinstance(value, slice):
        return f"{value.start}:{value.stop}:{value.step}"
    if value is None:
        return "None"
    return str(value)


def _metadata_dimension(metadata: Any, name: str) -> int:
    try:
        value = int(getattr(metadata, name))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"metadata.{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"metadata.{name} must be a positive integer")
    return value


def _unknown_if_none(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def format_error_message(error: BaseException) -> str:
    """Return a concise error message suitable for status bars/dialogs."""

    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
