import sys

from das_view.plugins.builtins import list_builtin_extensions, register_builtin_extensions
from das_view.plugins.registry import ExtensionRegistry


def _names_by_kind(registry, kind):
    return {extension.metadata.name for extension in registry.list(kind=kind)}


def test_register_builtin_extensions_contains_expected_capabilities():
    registry = ExtensionRegistry()

    register_builtin_extensions(registry=registry)

    assert {"zd_hdf5", "puniu_dat"}.issubset(_names_by_kind(registry, "reader"))
    assert {"common_mode_removal", "despike", "denoise_workflow"}.issubset(
        _names_by_kind(registry, "processing")
    )
    assert {"statistics", "event_candidates"}.issubset(_names_by_kind(registry, "analysis"))
    assert {"quality_report", "multiband_energy_map", "local_channel_coherence"}.issubset(
        _names_by_kind(registry, "analysis")
    )
    assert {"fk_directional_energy", "apparent_slope_xcorr", "moveout_summary_report"}.issubset(
        _names_by_kind(registry, "analysis")
    )
    assert {"channel_quality", "multiband_energy_map_plot", "coherence_map"}.issubset(
        _names_by_kind(registry, "plotting")
    )
    assert {"before_after_waterfall", "enhancement_metrics"}.issubset(_names_by_kind(registry, "plotting"))
    assert {"directional_energy_plot", "apparent_velocity_map", "moveout_coherence_plot"}.issubset(
        _names_by_kind(registry, "plotting")
    )
    assert {"json", "csv"}.issubset(_names_by_kind(registry, "export"))


def test_builtin_extensions_cover_processing_plotting_and_metadata_shape():
    extensions = list_builtin_extensions()
    kinds = {extension.metadata.kind for extension in extensions}

    assert {"reader", "processing", "analysis", "plotting", "export"}.issubset(kinds)
    assert all(extension.metadata.provider == "hcz-das-view" for extension in extensions)
    assert all(extension.metadata.enabled for extension in extensions)


def test_builtin_extensions_do_not_import_pyqt5_or_read_data():
    sys.modules.pop("PyQt5", None)

    extensions = list_builtin_extensions()

    assert extensions
    assert "PyQt5" not in sys.modules
