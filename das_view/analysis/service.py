"""File-level analysis services for CLI and future GUI workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from das_view.analysis.fk import FKResult, fk_transform
from das_view.analysis.fk_filter import FKFilterResult, fk_velocity_filter
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
from das_view.analysis.statistics import StatisticsResult, basic_statistics
from das_view.core.data_model import DASData, DASMetadata
from das_view.io.data_service import SelectionResult, read_selection, read_trace
from das_view.processing.service import PreprocessStep, apply_preprocess

AnalysisKind = Literal["amplitude", "power", "periodogram", "welch", "spectrogram"]
AnalysisResult = SpectrumResult | PSDResult | SpectrogramResult | StatisticsResult
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


@dataclass(frozen=True, slots=True)
class FKServiceResult:
    """Result from a file-level FK analysis service call."""

    result: FKResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class FKFilterServiceResult:
    """Result from a file-level FK velocity-filter service call."""

    result: FKFilterResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]
    filter_parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StatisticsServiceResult:
    """Result from a file-level statistics analysis service call."""

    result: StatisticsResult
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


def compute_fk_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    downsample: int | tuple[int, int] | None = None,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    output: Literal["amplitude", "power"] = "amplitude",
    window_time=None,
    window_space=None,
    preprocessing_steps: Sequence[StepLike] | None = None,
) -> FKServiceResult:
    """Read a bounded 2-D selection and compute a basic FK transform."""

    selection = read_selection(
        path,
        time_slice=time_slice,
        channel_slice=channel_slice,
        downsample=downsample,
    )
    das_data = selection.das_data
    if preprocessing_steps:
        das_data = apply_preprocess(das_data, preprocessing_steps)
    result = fk_transform(
        das_data,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        window_time=window_time,
        window_space=window_space,
        output=output,
    )
    return _fk_service_result(result=result, das_data=das_data, selection=selection)


def compute_fk_filter_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    downsample: int | tuple[int, int] | None = None,
    vmin_mps: float | None = None,
    vmax_mps: float | None = None,
    pass_inside: bool = True,
    include_zero_wavenumber: bool = True,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    window_time=None,
    window_space=None,
    preprocessing_steps: Sequence[StepLike] | None = None,
    return_fk: bool = False,
) -> FKFilterServiceResult:
    """Read a bounded 2-D selection and apply a minimal FK velocity filter."""

    selection = read_selection(
        path,
        time_slice=time_slice,
        channel_slice=channel_slice,
        downsample=downsample,
    )
    das_data = selection.das_data
    if preprocessing_steps:
        das_data = apply_preprocess(das_data, preprocessing_steps)
    result = fk_velocity_filter(
        das_data,
        vmin_mps=vmin_mps,
        vmax_mps=vmax_mps,
        pass_inside=pass_inside,
        include_zero_wavenumber=include_zero_wavenumber,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        window_time=window_time,
        window_space=window_space,
        return_fk=return_fk,
    )
    return _fk_filter_service_result(
        result=result,
        das_data=result.das_data,
        selection=selection,
        filter_parameters={
            "vmin_mps": result.vmin_mps,
            "vmax_mps": result.vmax_mps,
            "pass_inside": result.pass_inside,
            "include_zero_wavenumber": bool(include_zero_wavenumber),
            "nfft_time": result.nfft_time,
            "nfft_space": result.nfft_space,
        },
    )


def compute_statistics_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    axis: int | None = None,
    percentiles=(1, 5, 25, 50, 75, 95, 99),
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "omit",
) -> StatisticsServiceResult:
    """Read a bounded 2-D selection and compute basic DAS statistics."""

    bounded_time = _bounded_slice(time_slice, max_samples=max_samples, axis_name="time")
    bounded_channel = _bounded_slice(channel_slice, max_samples=max_channels, axis_name="channel")
    selection = read_selection(
        path,
        time_slice=bounded_time,
        channel_slice=bounded_channel,
        downsample=downsample,
    )
    das_data = selection.das_data
    if preprocessing_steps:
        das_data = apply_preprocess(das_data, preprocessing_steps)
    result = basic_statistics(
        das_data,
        axis=axis,
        percentiles=percentiles,
        nan_policy=nan_policy,
    )
    return _statistics_service_result(result=result, das_data=das_data, selection=selection)


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


def _fk_service_result(
    *,
    result: FKResult,
    das_data: DASData,
    selection: SelectionResult,
) -> FKServiceResult:
    history = das_data.metadata.extra_attrs.get("preprocessing_history", [])
    if isinstance(history, list):
        normalized_history = tuple(entry for entry in history if isinstance(entry, dict))
    elif isinstance(history, dict):
        normalized_history = (history,)
    else:
        normalized_history = ()
    return FKServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=normalized_history,
    )


def _statistics_service_result(
    *,
    result: StatisticsResult,
    das_data: DASData,
    selection: SelectionResult,
) -> StatisticsServiceResult:
    history = _preprocessing_history(das_data)
    return StatisticsServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _fk_filter_service_result(
    *,
    result: FKFilterResult,
    das_data: DASData,
    selection: SelectionResult,
    filter_parameters: dict[str, Any],
) -> FKFilterServiceResult:
    history = das_data.metadata.extra_attrs.get("preprocessing_history", [])
    if isinstance(history, list):
        normalized_history = tuple(entry for entry in history if isinstance(entry, dict))
    elif isinstance(history, dict):
        normalized_history = (history,)
    else:
        normalized_history = ()
    return FKFilterServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=normalized_history,
        filter_parameters=dict(filter_parameters),
    )


def _preprocessing_history(das_data: DASData) -> tuple[dict[str, Any], ...]:
    history = das_data.metadata.extra_attrs.get("preprocessing_history", [])
    if isinstance(history, list):
        return tuple(entry for entry in history if isinstance(entry, dict))
    if isinstance(history, dict):
        return (history,)
    return ()


def _normalize_max_samples(value: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_samples must be a positive integer") from exc
    if result <= 0:
        raise ValueError("max_samples must be a positive integer")
    return result


def _bounded_slice(value, *, max_samples: int, axis_name: str) -> slice:
    limit = _normalize_max_samples(max_samples)
    if value is None:
        return slice(0, limit)
    return value
