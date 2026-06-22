"""Small GUI-facing state helpers that do not import PyQt5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SpectrumAnalysisType = Literal[
    "amplitude",
    "power",
    "psd_periodogram",
    "psd_welch",
    "spectrogram",
]
FKMode = Literal["transform", "velocity_filter"]
FKOutputMode = Literal["amplitude", "power"]


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


def task_control_state(is_running: bool) -> TaskControlState:
    """Return the control state for idle or running background tasks."""

    if is_running:
        return TaskControlState(
            open_enabled=False,
            preview_controls_enabled=False,
            waveform_controls_enabled=False,
            spectrum_controls_enabled=False,
            fk_controls_enabled=False,
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
