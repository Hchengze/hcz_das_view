"""File-level spectrum analysis services for CLI and future GUI workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from das_view.analysis.spectrum import (
    PSDResult,
    SpectrogramResult,
    SpectrumResult,
    amplitude_spectrum,
    periodogram_psd,
    power_spectrum,
    single_channel_spectrogram,
    welch_psd,
)
from das_view.core.data_model import DASData, DASMetadata
from das_view.io.data_service import SelectionResult, read_trace
from das_view.processing.service import PreprocessStep, apply_preprocess

AnalysisKind = Literal["amplitude", "power", "periodogram", "welch", "spectrogram"]
AnalysisResult = SpectrumResult | PSDResult | SpectrogramResult
StepLike = PreprocessStep | tuple[str, Mapping[str, Any]] | str


@dataclass(frozen=True, slots=True)
class SpectrumRequest:
    """Common file-level spectrum request parameters."""

    path: str | Path
    channel: int = 0
    max_samples: int = 4096
    preprocessing_steps: tuple[StepLike, ...] = ()


@dataclass(frozen=True, slots=True)
class SpectrumServiceResult:
    """Result from a file-level spectrum analysis service call."""

    result: AnalysisResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


def compute_spectrum_for_file(
    path: str | Path,
    *,
    channel: int = 0,
    max_samples: int = 4096,
    kind: Literal["amplitude", "power"] = "amplitude",
    nfft: int | None = None,
    window: str | Sequence[float] | None = None,
    preprocessing_steps: Sequence[StepLike] | None = None,
) -> SpectrumServiceResult:
    """Read a bounded trace and compute an amplitude or power spectrum."""

    das_data, selection = _read_and_maybe_preprocess(
        path,
        channel=channel,
        max_samples=max_samples,
        preprocessing_steps=preprocessing_steps,
    )
    if kind == "amplitude":
        result = amplitude_spectrum(das_data, channels=0, nfft=nfft, window=window)
    elif kind == "power":
        result = power_spectrum(das_data, channels=0, nfft=nfft, window=window)
    else:
        raise ValueError("kind must be 'amplitude' or 'power'")
    return _service_result(result=result, das_data=das_data, selection=selection)


def compute_psd_for_file(
    path: str | Path,
    *,
    channel: int = 0,
    max_samples: int = 4096,
    method: Literal["periodogram", "welch"] = "welch",
    window: str | Sequence[float] = "hann",
    nfft: int | None = None,
    nperseg: int = 256,
    noverlap: int | None = None,
    scaling: Literal["density", "spectrum"] = "density",
    preprocessing_steps: Sequence[StepLike] | None = None,
) -> SpectrumServiceResult:
    """Read a bounded trace and compute periodogram or Welch PSD."""

    das_data, selection = _read_and_maybe_preprocess(
        path,
        channel=channel,
        max_samples=max_samples,
        preprocessing_steps=preprocessing_steps,
    )
    if method == "periodogram":
        result = periodogram_psd(
            das_data,
            channels=0,
            window=window,
            nfft=nfft,
            scaling=scaling,
        )
    elif method == "welch":
        result = welch_psd(
            das_data,
            channels=0,
            window=window,
            nfft=nfft,
            nperseg=nperseg,
            noverlap=noverlap,
            scaling=scaling,
        )
    else:
        raise ValueError("method must be 'periodogram' or 'welch'")
    return _service_result(result=result, das_data=das_data, selection=selection)


def compute_spectrogram_for_file(
    path: str | Path,
    *,
    channel: int = 0,
    max_samples: int = 4096,
    nperseg: int = 256,
    noverlap: int | None = None,
    window: str | Sequence[float] = "hann",
    scaling: Literal["density", "spectrum"] = "density",
    preprocessing_steps: Sequence[StepLike] | None = None,
) -> SpectrumServiceResult:
    """Read a bounded trace and compute a single-channel spectrogram."""

    das_data, selection = _read_and_maybe_preprocess(
        path,
        channel=channel,
        max_samples=max_samples,
        preprocessing_steps=preprocessing_steps,
    )
    result = single_channel_spectrogram(
        das_data,
        channel=0,
        nperseg=nperseg,
        noverlap=noverlap,
        window=window,
        scaling=scaling,
    )
    return _service_result(result=result, das_data=das_data, selection=selection)


def _read_and_maybe_preprocess(
    path: str | Path,
    *,
    channel: int,
    max_samples: int,
    preprocessing_steps: Sequence[StepLike] | None,
) -> tuple[DASData, SelectionResult]:
    max_samples = _normalize_max_samples(max_samples)
    selection = read_trace(path, channel=channel, time_slice=slice(0, max_samples))
    das_data = selection.das_data
    if preprocessing_steps:
        das_data = apply_preprocess(das_data, preprocessing_steps)
    if das_data.metadata.sample_rate_hz is None:
        raise ValueError("sample_rate_hz is required for spectrum analysis but was not found")
    return das_data, selection


def _service_result(
    *,
    result: AnalysisResult,
    das_data: DASData,
    selection: SelectionResult,
) -> SpectrumServiceResult:
    history = das_data.metadata.extra_attrs.get("preprocessing_history", [])
    if isinstance(history, list):
        normalized_history = tuple(entry for entry in history if isinstance(entry, dict))
    elif isinstance(history, dict):
        normalized_history = (history,)
    else:
        normalized_history = ()
    return SpectrumServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=normalized_history,
    )


def _normalize_max_samples(value: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_samples must be a positive integer") from exc
    if result <= 0:
        raise ValueError("max_samples must be a positive integer")
    return result
