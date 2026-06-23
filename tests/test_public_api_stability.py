import inspect


def test_core_and_io_public_api_imports():
    from das_view import DASData, DASMetadata
    from das_view.core import ReaderError, UnsupportedFormatError
    from das_view.io import create_preview, read_selection, read_trace

    assert DASData
    assert DASMetadata
    assert issubclass(UnsupportedFormatError, ReaderError)
    assert callable(create_preview)
    assert callable(read_selection)
    assert callable(read_trace)


def test_processing_public_api_imports():
    from das_view.processing import (
        apply_preprocess,
        bandpass,
        bandstop,
        channel_balance,
        clip,
        common_mode_removal,
        demean,
        despike,
        detrend_linear,
        highpass,
        local_normalize,
        lowpass,
        normalize,
        notch,
        robust_clip,
        running_median_filter,
        standardize,
        taper,
        time_space_median_filter,
    )

    for func in [
        demean,
        detrend_linear,
        taper,
        normalize,
        standardize,
        clip,
        lowpass,
        highpass,
        bandpass,
        bandstop,
        notch,
        common_mode_removal,
        despike,
        running_median_filter,
        channel_balance,
        local_normalize,
        time_space_median_filter,
        robust_clip,
        apply_preprocess,
    ]:
        assert callable(func)


def test_analysis_public_api_imports():
    from das_view.analysis import (
        amplitude_envelope,
        band_energy,
        basic_statistics,
        channel_quality_metrics,
        compute_apparent_moveout_for_file,
        compute_coherence_for_file,
        compute_denoised_selection_for_file,
        compute_directional_energy_for_file,
        compute_enhancement_report_for_file,
        compute_multiband_map_for_file,
        compute_moveout_summary_for_file,
        compute_quality_report_for_file,
        compute_roi_statistics_for_file,
        estimate_noise_floor,
        estimate_snr,
        estimate_apparent_slope_xcorr,
        directional_energy_ratio,
        fk_directional_energy,
        local_channel_coherence,
        local_moveout_coherence,
        multiband_energy_map,
        moveout_summary_report,
        compute_spectral_attributes_for_file,
        compute_statistics_for_file,
        detect_events_for_file,
        spectral_attributes,
        sta_lta_ratio,
    )

    for func in [
        basic_statistics,
        channel_quality_metrics,
        band_energy,
        multiband_energy_map,
        spectral_attributes,
        amplitude_envelope,
        sta_lta_ratio,
        estimate_noise_floor,
        estimate_snr,
        local_channel_coherence,
        detect_events_for_file,
        compute_statistics_for_file,
        compute_spectral_attributes_for_file,
        compute_roi_statistics_for_file,
        compute_quality_report_for_file,
        compute_multiband_map_for_file,
        compute_coherence_for_file,
        compute_denoised_selection_for_file,
        compute_apparent_moveout_for_file,
        compute_directional_energy_for_file,
        compute_enhancement_report_for_file,
        compute_moveout_summary_for_file,
        estimate_apparent_slope_xcorr,
        directional_energy_ratio,
        fk_directional_energy,
        local_moveout_coherence,
        moveout_summary_report,
    ]:
        assert callable(func)


def test_plotting_public_api_imports():
    from das_view.plotting import (
        plot_fk,
        plot_channel_quality,
        plot_coherence_map,
        plot_before_after_waterfall,
        plot_apparent_velocity_map,
        plot_directional_energy,
        plot_enhancement_metrics,
        plot_multiband_energy_map,
        plot_moveout_coherence,
        plot_psd,
        plot_rois_on_waterfall,
        plot_spectrum,
        plot_waterfall,
        plot_waveform,
    )

    for func in [
        plot_waterfall,
        plot_waveform,
        plot_spectrum,
        plot_psd,
        plot_fk,
        plot_channel_quality,
        plot_coherence_map,
        plot_before_after_waterfall,
        plot_apparent_velocity_map,
        plot_directional_energy,
        plot_enhancement_metrics,
        plot_multiband_energy_map,
        plot_moveout_coherence,
        plot_rois_on_waterfall,
    ]:
        assert callable(func)


def test_plugins_public_api_imports():
    from das_view.plugins import (
        ExtensionMetadata,
        ExtensionRegistry,
        discover_entry_point_extensions,
        register_builtin_extensions,
    )

    assert ExtensionMetadata
    assert ExtensionRegistry
    assert callable(register_builtin_extensions)
    assert callable(discover_entry_point_extensions)


def test_representative_public_signatures_are_stable():
    from das_view.analysis import compute_statistics_for_file
    from das_view.io import create_preview, read_selection
    from das_view.plugins import ExtensionMetadata

    assert "path" in inspect.signature(create_preview).parameters
    assert "path" in inspect.signature(read_selection).parameters
    assert "path" in inspect.signature(compute_statistics_for_file).parameters
    assert "name" in inspect.signature(ExtensionMetadata).parameters
    assert "kind" in inspect.signature(ExtensionMetadata).parameters
