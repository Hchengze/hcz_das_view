"""File-level analysis services for CLI and future GUI workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from das_view.analysis.events import (
    EnvelopeResult,
    EventDetectionResult,
    STALTARatioResult,
    amplitude_envelope,
    detect_stalta_events,
    detect_threshold_events,
    sta_lta_ratio,
)
from das_view.analysis.fk import FKResult, fk_transform
from das_view.analysis.fk_filter import FKFilterResult, fk_velocity_filter
from das_view.analysis.roi import ROIAnalysisResult, ROISet, TimeChannelROI
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
from das_view.analysis.spectral_attributes import (
    BandEnergyResult,
    SpectralAttributesResult,
    band_energy,
    spectral_attributes,
)
from das_view.analysis.statistics import StatisticsResult, basic_statistics
from das_view.core.data_model import DASData, DASMetadata
from das_view.io.data_service import SelectionResult, read_selection, read_trace
from das_view.processing.service import PreprocessStep, apply_preprocess

AnalysisKind = Literal["amplitude", "power", "periodogram", "welch", "spectrogram"]
AnalysisResult = (
    SpectrumResult
    | PSDResult
    | SpectrogramResult
    | StatisticsResult
    | BandEnergyResult
    | SpectralAttributesResult
    | EnvelopeResult
    | STALTARatioResult
    | EventDetectionResult
    | ROIAnalysisResult
)
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


@dataclass(frozen=True, slots=True)
class BandEnergyServiceResult:
    """Result from a file-level band-energy analysis service call."""

    result: BandEnergyResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class SpectralAttributesServiceResult:
    """Result from a file-level spectral-attributes analysis service call."""

    result: SpectralAttributesResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class EnvelopeServiceResult:
    """Result from a file-level envelope analysis service call."""

    result: EnvelopeResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class STALTAServiceResult:
    """Result from a file-level STA/LTA analysis service call."""

    result: STALTARatioResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class EventDetectionServiceResult:
    """Result from a file-level event-candidate detection service call."""

    result: EventDetectionResult
    das_data: DASData
    reader_name: str
    metadata: DASMetadata
    selection: SelectionResult
    preprocessing_history: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ROIAnalysisServiceResult:
    """Result from file-level analysis over one or more ROIs."""

    results: tuple[ROIAnalysisResult, ...]
    reader_name: str | None
    preprocessing_history: tuple[dict[str, Any], ...]
    analysis_kind: str


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


def compute_band_energy_for_file(
    path: str | Path,
    *,
    bands,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    nfft: int | None = None,
    average_channels: bool = False,
    scaling: Literal["power", "density"] = "power",
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> BandEnergyServiceResult:
    """Read a bounded 2-D selection and compute frequency-band energy."""

    das_data, selection = _read_selection_and_maybe_preprocess(
        path,
        channel_slice=channel_slice,
        time_slice=time_slice,
        max_samples=max_samples,
        max_channels=max_channels,
        downsample=downsample,
        preprocessing_steps=preprocessing_steps,
    )
    result = band_energy(
        das_data,
        bands=bands,
        axis=0,
        nfft=nfft,
        average_channels=average_channels,
        scaling=scaling,
        nan_policy=nan_policy,
    )
    return _band_energy_service_result(result=result, das_data=das_data, selection=selection)


def compute_spectral_attributes_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    nfft: int | None = None,
    frequency_range=None,
    rolloff: float = 0.95,
    average_channels: bool = False,
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> SpectralAttributesServiceResult:
    """Read a bounded 2-D selection and compute spectral attributes."""

    das_data, selection = _read_selection_and_maybe_preprocess(
        path,
        channel_slice=channel_slice,
        time_slice=time_slice,
        max_samples=max_samples,
        max_channels=max_channels,
        downsample=downsample,
        preprocessing_steps=preprocessing_steps,
    )
    result = spectral_attributes(
        das_data,
        axis=0,
        nfft=nfft,
        frequency_range=frequency_range,
        rolloff=rolloff,
        average_channels=average_channels,
        nan_policy=nan_policy,
    )
    return _spectral_attributes_service_result(result=result, das_data=das_data, selection=selection)


def compute_envelope_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    method: Literal["hilbert"] = "hilbert",
    smooth_samples: int | None = None,
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> EnvelopeServiceResult:
    """Read a bounded 2-D selection and compute amplitude envelope."""

    das_data, selection = _read_selection_and_maybe_preprocess(
        path,
        channel_slice=channel_slice,
        time_slice=time_slice,
        max_samples=max_samples,
        max_channels=max_channels,
        downsample=downsample,
        preprocessing_steps=preprocessing_steps,
        require_sample_rate=False,
    )
    result = amplitude_envelope(
        das_data,
        axis=0,
        method=method,
        smooth_samples=smooth_samples,
        nan_policy=nan_policy,
    )
    return _envelope_service_result(result=result, das_data=das_data, selection=selection)


def compute_stalta_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    sta_samples: int,
    lta_samples: int,
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> STALTAServiceResult:
    """Read a bounded 2-D selection and compute STA/LTA ratio."""

    das_data, selection = _read_selection_and_maybe_preprocess(
        path,
        channel_slice=channel_slice,
        time_slice=time_slice,
        max_samples=max_samples,
        max_channels=max_channels,
        downsample=downsample,
        preprocessing_steps=preprocessing_steps,
        require_sample_rate=False,
    )
    result = sta_lta_ratio(
        das_data,
        axis=0,
        sta_samples=sta_samples,
        lta_samples=lta_samples,
        nan_policy=nan_policy,
    )
    return _stalta_service_result(result=result, das_data=das_data, selection=selection)


def detect_events_for_file(
    path: str | Path,
    *,
    channel_slice=None,
    time_slice=None,
    max_samples: int = 4096,
    max_channels: int = 512,
    downsample: int | tuple[int, int] | None = None,
    method: Literal["stalta", "envelope"] = "stalta",
    threshold: float | None = None,
    sta_samples: int | None = None,
    lta_samples: int | None = None,
    trigger_on: float | None = None,
    trigger_off: float | None = None,
    smooth_samples: int | None = None,
    min_duration_samples: int = 1,
    merge_gap_samples: int = 0,
    max_events: int | None = None,
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> EventDetectionServiceResult:
    """Read a bounded 2-D selection and detect event candidates."""

    das_data, selection = _read_selection_and_maybe_preprocess(
        path,
        channel_slice=channel_slice,
        time_slice=time_slice,
        max_samples=max_samples,
        max_channels=max_channels,
        downsample=downsample,
        preprocessing_steps=preprocessing_steps,
        require_sample_rate=False,
    )
    if method == "stalta":
        if sta_samples is None or lta_samples is None or trigger_on is None:
            raise ValueError("stalta detection requires sta_samples, lta_samples, and trigger_on")
        result = detect_stalta_events(
            das_data,
            sta_samples=sta_samples,
            lta_samples=lta_samples,
            trigger_on=trigger_on,
            trigger_off=trigger_off,
            axis=0,
            min_duration_samples=min_duration_samples,
            merge_gap_samples=merge_gap_samples,
            max_events=max_events,
            nan_policy=nan_policy,
        )
    elif method == "envelope":
        if threshold is None:
            raise ValueError("envelope detection requires threshold")
        envelope = amplitude_envelope(
            das_data,
            axis=0,
            smooth_samples=smooth_samples,
            nan_policy=nan_policy,
        )
        threshold_result = detect_threshold_events(
            envelope,
            threshold=threshold,
            axis=0,
            min_duration_samples=min_duration_samples,
            merge_gap_samples=merge_gap_samples,
            max_events=max_events,
        )
        result = EventDetectionResult(
            feature=threshold_result.feature,
            candidates=threshold_result.candidates,
            axis=threshold_result.axis,
            input_shape=threshold_result.input_shape,
            method="envelope",
            parameters={
                **threshold_result.parameters,
                "feature": "amplitude_envelope",
                "smooth_samples": smooth_samples,
                "nan_policy": nan_policy,
            },
        )
    else:
        raise ValueError("method must be 'stalta' or 'envelope'")
    return _event_detection_service_result(result=result, das_data=das_data, selection=selection)


def compute_roi_statistics_for_file(
    path: str | Path,
    rois,
    *,
    max_channels: int = 512,
    preprocessing_steps: Sequence[StepLike] | None = None,
    percentiles=(1, 5, 25, 50, 75, 95, 99),
    nan_policy: Literal["omit", "raise"] = "omit",
) -> ROIAnalysisServiceResult:
    """Compute basic statistics for each bounded ROI."""

    roi_values = _normalize_rois(rois)
    results: list[ROIAnalysisResult] = []
    for roi in roi_values:
        das_data, selection = _read_roi_and_maybe_preprocess(
            path,
            roi,
            max_channels=max_channels,
            preprocessing_steps=preprocessing_steps,
            require_sample_rate=False,
        )
        result = basic_statistics(
            das_data,
            axis=None,
            percentiles=percentiles,
            nan_policy=nan_policy,
        )
        results.append(
            ROIAnalysisResult(
                roi=roi,
                result=result,
                reader_name=selection.reader_name,
                metadata=das_data.metadata,
                selection=selection,
                preprocessing_history=_preprocessing_history(das_data),
            )
        )
    return _roi_analysis_service_result(results=results, analysis_kind="statistics")


def compute_roi_spectral_attributes_for_file(
    path: str | Path,
    rois,
    *,
    bands=None,
    max_channels: int = 512,
    nfft: int | None = None,
    frequency_range=None,
    rolloff: float = 0.95,
    preprocessing_steps: Sequence[StepLike] | None = None,
    nan_policy: Literal["omit", "raise"] = "raise",
) -> ROIAnalysisServiceResult:
    """Compute band energy or spectral attributes for each bounded ROI."""

    roi_values = _normalize_rois(rois)
    results: list[ROIAnalysisResult] = []
    for roi in roi_values:
        das_data, selection = _read_roi_and_maybe_preprocess(
            path,
            roi,
            max_channels=max_channels,
            preprocessing_steps=preprocessing_steps,
            require_sample_rate=True,
        )
        if bands is not None:
            result = band_energy(
                das_data,
                bands=bands,
                axis=0,
                nfft=nfft,
                average_channels=True,
                nan_policy=nan_policy,
            )
            kind = "band_energy"
        else:
            result = spectral_attributes(
                das_data,
                axis=0,
                nfft=nfft,
                frequency_range=frequency_range,
                rolloff=rolloff,
                average_channels=True,
                nan_policy=nan_policy,
            )
            kind = "spectral_attributes"
        results.append(
            ROIAnalysisResult(
                roi=roi,
                result=result,
                reader_name=selection.reader_name,
                metadata=das_data.metadata,
                selection=selection,
                preprocessing_history=_preprocessing_history(das_data),
            )
        )
    return _roi_analysis_service_result(results=results, analysis_kind=kind if roi_values else "spectral_attributes")


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


def _read_selection_and_maybe_preprocess(
    path: str | Path,
    *,
    channel_slice,
    time_slice,
    max_samples: int,
    max_channels: int,
    downsample: int | tuple[int, int] | None,
    preprocessing_steps: Sequence[StepLike] | None,
    require_sample_rate: bool = True,
) -> tuple[DASData, SelectionResult]:
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
    if require_sample_rate and das_data.metadata.sample_rate_hz is None:
        raise ValueError("sample_rate_hz is required for spectral attribute analysis but was not found")
    return das_data, selection


def _read_roi_and_maybe_preprocess(
    path: str | Path,
    roi: TimeChannelROI,
    *,
    max_channels: int,
    preprocessing_steps: Sequence[StepLike] | None,
    require_sample_rate: bool,
) -> tuple[DASData, SelectionResult]:
    time_slice = slice(roi.start_sample, roi.end_sample)
    if roi.channel_start is None or roi.channel_end is None:
        channel_slice = slice(0, _normalize_max_samples(max_channels))
    else:
        channel_slice = slice(roi.channel_start, roi.channel_end)
    selection = read_selection(path, time_slice=time_slice, channel_slice=channel_slice)
    das_data = selection.das_data
    if preprocessing_steps:
        das_data = apply_preprocess(das_data, preprocessing_steps)
    if require_sample_rate and das_data.metadata.sample_rate_hz is None:
        raise ValueError("sample_rate_hz is required for ROI spectral analysis but was not found")
    return das_data, selection


def _normalize_rois(rois) -> tuple[TimeChannelROI, ...]:
    if isinstance(rois, ROISet):
        values = tuple(rois)
    else:
        values = tuple(rois)
    for roi in values:
        if not isinstance(roi, TimeChannelROI):
            raise TypeError("ROI analysis expects TimeChannelROI objects")
    return values


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


def _band_energy_service_result(
    *,
    result: BandEnergyResult,
    das_data: DASData,
    selection: SelectionResult,
) -> BandEnergyServiceResult:
    history = _preprocessing_history(das_data)
    return BandEnergyServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _spectral_attributes_service_result(
    *,
    result: SpectralAttributesResult,
    das_data: DASData,
    selection: SelectionResult,
) -> SpectralAttributesServiceResult:
    history = _preprocessing_history(das_data)
    return SpectralAttributesServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _envelope_service_result(
    *,
    result: EnvelopeResult,
    das_data: DASData,
    selection: SelectionResult,
) -> EnvelopeServiceResult:
    history = _preprocessing_history(das_data)
    return EnvelopeServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _stalta_service_result(
    *,
    result: STALTARatioResult,
    das_data: DASData,
    selection: SelectionResult,
) -> STALTAServiceResult:
    history = _preprocessing_history(das_data)
    return STALTAServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _event_detection_service_result(
    *,
    result: EventDetectionResult,
    das_data: DASData,
    selection: SelectionResult,
) -> EventDetectionServiceResult:
    history = _preprocessing_history(das_data)
    return EventDetectionServiceResult(
        result=result,
        das_data=das_data,
        reader_name=selection.reader_name,
        metadata=das_data.metadata,
        selection=selection,
        preprocessing_history=history,
    )


def _roi_analysis_service_result(
    *,
    results: list[ROIAnalysisResult],
    analysis_kind: str,
) -> ROIAnalysisServiceResult:
    reader_name = results[0].reader_name if results else None
    history = results[0].preprocessing_history if results else ()
    return ROIAnalysisServiceResult(
        results=tuple(results),
        reader_name=reader_name,
        preprocessing_history=history,
        analysis_kind=analysis_kind,
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
