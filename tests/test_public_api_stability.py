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
        clip,
        demean,
        detrend_linear,
        highpass,
        lowpass,
        normalize,
        notch,
        standardize,
        taper,
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
        apply_preprocess,
    ]:
        assert callable(func)


def test_analysis_public_api_imports():
    from das_view.analysis import (
        amplitude_envelope,
        band_energy,
        basic_statistics,
        compute_roi_statistics_for_file,
        compute_spectral_attributes_for_file,
        compute_statistics_for_file,
        detect_events_for_file,
        spectral_attributes,
        sta_lta_ratio,
    )

    for func in [
        basic_statistics,
        band_energy,
        spectral_attributes,
        amplitude_envelope,
        sta_lta_ratio,
        detect_events_for_file,
        compute_statistics_for_file,
        compute_spectral_attributes_for_file,
        compute_roi_statistics_for_file,
    ]:
        assert callable(func)


def test_plotting_public_api_imports():
    from das_view.plotting import (
        plot_fk,
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
