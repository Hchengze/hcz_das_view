"""Small GUI-facing state helpers that do not import PyQt5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from das_view.analysis.roi import TimeChannelROI, rois_from_event_candidates
from das_view.io.export import analysis_summary_to_rows, event_candidates_to_rows, rois_to_rows

SpectrumAnalysisType = Literal[
    "amplitude",
    "power",
    "psd_periodogram",
    "psd_welch",
    "spectrogram",
]
FKMode = Literal["transform", "velocity_filter"]
FKOutputMode = Literal["amplitude", "power"]
AnalysisType = Literal[
    "statistics",
    "band_energy",
    "spectral_attributes",
    "events_stalta",
    "events_envelope",
    "roi_statistics",
]


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
        bands=parse_band_ranges(bands_text) if parsed_type == "band_energy" else ((1.0, 5.0),),
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
    )


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


def _parse_analysis_axis(value: str | None) -> int | None:
    normalized = "global" if value is None else str(value).strip().lower()
    if normalized in {"global", "none", ""}:
        return None
    if normalized in {"time", "channel summary", "axis 0", "0"}:
        return 0
    if normalized in {"channel", "time summary", "axis 1", "1"}:
        return 1
    raise ValueError(f"unsupported statistics axis: {value!r}")


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


def format_error_message(error: BaseException) -> str:
    """Return a concise error message suitable for status bars/dialogs."""

    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return f"{error.__class__.__name__}: {message}"
