"""Built-in extension metadata for existing HCZ DAS View capabilities."""

from __future__ import annotations

from das_view.plugins.base import (
    AnalysisExtension,
    ExportExtension,
    ExtensionMetadata,
    PlottingExtension,
    ProcessingExtension,
    ReaderExtension,
)
from das_view.plugins.registry import ExtensionRegistry, register_extension


PROVIDER = "hcz-das-view"
VERSION = "0.1.0.dev0"


def _metadata(
    name: str,
    kind: str,
    *,
    description: str,
    module: str,
    tags: tuple[str, ...] = (),
) -> ExtensionMetadata:
    return ExtensionMetadata(
        name=name,
        kind=kind,
        version=VERSION,
        description=description,
        provider=PROVIDER,
        module=module,
        tags=tags,
    )


def list_builtin_extensions() -> list[object]:
    """Return metadata wrappers for stable built-in capabilities.

    This helper does not read DAS files, start GUI code, or run analysis. It
    only describes existing package capabilities for inspection and future
    extension composition.
    """

    return [
        ReaderExtension(
            metadata=_metadata(
                "zd_hdf5",
                "reader",
                description="ZD HDF5 reader",
                module="das_view.io.hdf5_zd",
                tags=("hdf5", "reader"),
            ),
            extensions=(".h5", ".hdf5"),
            can_read="das_view.io.hdf5_zd.ZDHDF5Reader.can_read",
            read_metadata="das_view.io.hdf5_zd.ZDHDF5Reader.read_metadata",
            read="das_view.io.hdf5_zd.ZDHDF5Reader.read",
        ),
        ReaderExtension(
            metadata=_metadata(
                "puniu_dat",
                "reader",
                description="Puniu DAT reader",
                module="das_view.io.puniu_dat",
                tags=("dat", "reader"),
            ),
            extensions=(".dat",),
            can_read="das_view.io.puniu_dat.PuniuDATReader.can_read",
            read_metadata="das_view.io.puniu_dat.PuniuDATReader.read_metadata",
            read="das_view.io.puniu_dat.PuniuDATReader.read",
        ),
        *[
            ProcessingExtension(
                metadata=_metadata(
                    name,
                    "processing",
                    description=description,
                    module=module,
                    tags=("processing",),
                ),
                function=f"{module}.{name}",
            )
            for name, description, module in [
                ("demean", "Remove mean along an axis", "das_view.processing.preprocess"),
                ("detrend_linear", "Remove a linear trend", "das_view.processing.preprocess"),
                ("taper", "Apply an edge taper", "das_view.processing.preprocess"),
                ("normalize", "Normalize amplitudes", "das_view.processing.preprocess"),
                ("standardize", "Standardize amplitudes", "das_view.processing.preprocess"),
                ("clip", "Clip amplitudes", "das_view.processing.preprocess"),
                ("lowpass", "Low-pass filter", "das_view.processing.filters"),
                ("highpass", "High-pass filter", "das_view.processing.filters"),
                ("bandpass", "Band-pass filter", "das_view.processing.filters"),
                ("bandstop", "Band-stop filter", "das_view.processing.filters"),
                ("notch", "Notch filter", "das_view.processing.filters"),
                ("common_mode_removal", "Remove sample-wise common mode", "das_view.processing.denoise"),
                ("despike", "Replace robust outlier spikes", "das_view.processing.denoise"),
                ("running_median_filter", "Centered running median filter", "das_view.processing.denoise"),
                ("channel_balance", "Balance channel amplitudes", "das_view.processing.denoise"),
                ("local_normalize", "Normalize by local amplitude scale", "das_view.processing.denoise"),
                ("time_space_median_filter", "Small time-space median filter", "das_view.processing.denoise"),
                ("robust_clip", "Percentile winsorization", "das_view.processing.denoise"),
                ("denoise_workflow", "Traditional denoise workflow", "das_view.processing.denoise"),
            ]
        ],
        *[
            AnalysisExtension(
                metadata=_metadata(
                    name,
                    "analysis",
                    description=description,
                    module="das_view.analysis.service",
                    tags=("analysis",),
                ),
                function=function,
                input_kind="file_selection",
                output_kind=output_kind,
            )
            for name, description, function, output_kind in [
                (
                    "statistics",
                    "Bounded DAS statistics",
                    "das_view.analysis.service.compute_statistics_for_file",
                    "statistics_summary",
                ),
                (
                    "spectral_attributes",
                    "Bounded spectral attributes",
                    "das_view.analysis.service.compute_spectral_attributes_for_file",
                    "spectral_attributes",
                ),
                (
                    "band_energy",
                    "Frequency-band energy",
                    "das_view.analysis.service.compute_band_energy_for_file",
                    "band_energy",
                ),
                (
                    "amplitude_envelope",
                    "Amplitude envelope",
                    "das_view.analysis.service.compute_envelope_for_file",
                    "envelope",
                ),
                (
                    "sta_lta",
                    "STA/LTA ratio",
                    "das_view.analysis.service.compute_stalta_for_file",
                    "sta_lta",
                ),
                (
                    "event_candidates",
                    "Event candidate detection",
                    "das_view.analysis.service.detect_events_for_file",
                    "event_candidates",
                ),
                (
                    "roi_statistics",
                    "ROI statistics",
                    "das_view.analysis.service.compute_roi_statistics_for_file",
                    "roi_statistics",
                ),
                (
                    "roi_spectral_attributes",
                    "ROI spectral attributes",
                    "das_view.analysis.service.compute_roi_spectral_attributes_for_file",
                    "roi_spectral_attributes",
                ),
                (
                    "fk_transform",
                    "Bounded FK transform",
                    "das_view.analysis.service.compute_fk_for_file",
                    "fk_result",
                ),
                (
                    "fk_velocity_filter",
                    "FK velocity fan smoke filter",
                    "das_view.analysis.service.compute_fk_filter_for_file",
                    "fk_filter_result",
                ),
                (
                    "quality_report",
                    "DAS channel quality report",
                    "das_view.analysis.service.compute_quality_report_for_file",
                    "quality_report",
                ),
                (
                    "bad_channel_detection",
                    "DAS bad-channel detection",
                    "das_view.analysis.qc.detect_bad_channels",
                    "bad_channel_table",
                ),
                (
                    "noise_floor",
                    "Per-channel noise floor estimate",
                    "das_view.analysis.qc.estimate_noise_floor",
                    "noise_floor",
                ),
                (
                    "snr_estimate",
                    "Per-channel SNR estimate",
                    "das_view.analysis.qc.estimate_snr",
                    "snr",
                ),
                (
                    "multiband_energy_map",
                    "Windowed multiband energy map",
                    "das_view.analysis.service.compute_multiband_map_for_file",
                    "multiband_feature_map",
                ),
                (
                    "spectral_attribute_map",
                    "Windowed spectral attribute map",
                    "das_view.analysis.service.compute_spectral_attribute_map_for_file",
                    "spectral_attribute_map",
                ),
                (
                    "local_channel_coherence",
                    "Local channel coherence",
                    "das_view.analysis.service.compute_coherence_for_file",
                    "coherence_map",
                ),
                (
                    "fk_directional_energy",
                    "FK directional energy attribute",
                    "das_view.analysis.service.compute_directional_energy_for_file",
                    "directional_energy",
                ),
                (
                    "directional_energy_ratio",
                    "Positive/negative wavenumber energy ratio",
                    "das_view.analysis.moveout.directional_energy_ratio",
                    "directional_energy_ratio",
                ),
                (
                    "apparent_slope_xcorr",
                    "Cross-correlation apparent slope attribute",
                    "das_view.analysis.service.compute_apparent_moveout_for_file",
                    "apparent_slope",
                ),
                (
                    "apparent_velocity_attribute",
                    "Apparent velocity attribute from moveout slope",
                    "das_view.analysis.moveout.apparent_velocity_from_slope",
                    "apparent_velocity_attribute",
                ),
                (
                    "local_moveout_coherence",
                    "Local moveout coherence attribute",
                    "das_view.analysis.moveout.local_moveout_coherence",
                    "moveout_coherence",
                ),
                (
                    "moveout_summary_report",
                    "Combined moveout summary report",
                    "das_view.analysis.service.compute_moveout_summary_for_file",
                    "moveout_summary",
                ),
            ]
        ],
        *[
            PlottingExtension(
                metadata=_metadata(
                    name,
                    "plotting",
                    description=description,
                    module=module,
                    tags=("plotting",),
                ),
                function=function,
                input_kind=input_kind,
            )
            for name, description, module, function, input_kind in [
                (
                    "waterfall",
                    "Waterfall plot",
                    "das_view.plotting.waterfall",
                    "das_view.plotting.waterfall.plot_waterfall",
                    "DASData",
                ),
                (
                    "waveform",
                    "Waveform plot",
                    "das_view.plotting.waveform",
                    "das_view.plotting.waveform.plot_waveform",
                    "DASData",
                ),
                (
                    "spectrum",
                    "Spectrum plot",
                    "das_view.plotting.spectra",
                    "das_view.plotting.spectra.plot_spectrum",
                    "SpectrumResult",
                ),
                (
                    "spectrogram",
                    "Spectrogram plot",
                    "das_view.plotting.spectra",
                    "das_view.plotting.spectra.plot_spectrogram",
                    "SpectrogramResult",
                ),
                (
                    "psd",
                    "PSD plot",
                    "das_view.plotting.spectra",
                    "das_view.plotting.spectra.plot_psd",
                    "PSDResult",
                ),
                (
                    "fk",
                    "FK plot",
                    "das_view.plotting.fk",
                    "das_view.plotting.fk.plot_fk",
                    "FKResult",
                ),
                (
                    "roi_overlay",
                    "ROI waterfall overlay",
                    "das_view.plotting.roi",
                    "das_view.plotting.roi.plot_rois_on_waterfall",
                    "ROISet",
                ),
                (
                    "channel_quality",
                    "Channel quality plot",
                    "das_view.plotting.qc",
                    "das_view.plotting.qc.plot_channel_quality",
                    "DataQualityReport",
                ),
                (
                    "multiband_energy_map_plot",
                    "Multiband energy map plot",
                    "das_view.plotting.multiband",
                    "das_view.plotting.multiband.plot_multiband_energy_map",
                    "MultibandFeatureMap",
                ),
                (
                    "coherence_map",
                    "Local channel coherence map plot",
                    "das_view.plotting.multiband",
                    "das_view.plotting.multiband.plot_coherence_map",
                    "LocalCoherenceResult",
                ),
                (
                    "before_after_waterfall",
                    "Before/after enhancement waterfall plot",
                    "das_view.plotting.denoise",
                    "das_view.plotting.denoise.plot_before_after_waterfall",
                    "DASData",
                ),
                (
                    "enhancement_metrics",
                    "Enhancement report metrics plot",
                    "das_view.plotting.denoise",
                    "das_view.plotting.denoise.plot_enhancement_metrics",
                    "EnhancementReport",
                ),
                (
                    "directional_energy_plot",
                    "Directional energy attribute plot",
                    "das_view.plotting.moveout",
                    "das_view.plotting.moveout.plot_directional_energy",
                    "DirectionalEnergyResult",
                ),
                (
                    "apparent_velocity_map",
                    "Apparent velocity attribute map",
                    "das_view.plotting.moveout",
                    "das_view.plotting.moveout.plot_apparent_velocity_map",
                    "ApparentSlopeResult",
                ),
                (
                    "moveout_coherence_plot",
                    "Moveout coherence plot",
                    "das_view.plotting.moveout",
                    "das_view.plotting.moveout.plot_moveout_coherence",
                    "MoveoutCoherenceResult",
                ),
            ]
        ],
        ExportExtension(
            metadata=_metadata(
                "json",
                "export",
                description="JSON export helper",
                module="das_view.io.export",
                tags=("export", "json"),
            ),
            function="das_view.io.export.save_json",
            output_format="json",
        ),
        ExportExtension(
            metadata=_metadata(
                "csv",
                "export",
                description="CSV export helper",
                module="das_view.io.export",
                tags=("export", "csv"),
            ),
            function="das_view.io.export.save_csv_rows",
            output_format="csv",
        ),
    ]


def register_builtin_extensions(
    registry: ExtensionRegistry | None = None,
    *,
    replace: bool = True,
) -> list[object]:
    """Register built-in extension metadata in a registry."""

    extensions = list_builtin_extensions()
    for extension in extensions:
        register_extension(extension, registry=registry, replace=replace)
    return extensions
