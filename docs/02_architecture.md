# Architecture

## Package layout

    das_view/
    - __init__.py
    - core/
      - data_model.py
      - metadata_format.py
      - exceptions.py
      - config.py
    - io/
      - base.py
      - registry.py
      - preview.py
      - data_service.py
      - export.py
      - hdf5_zd.py
      - puniu_dat.py
    - processing/
      - preprocess.py
      - filters.py
      - service.py
    - analysis/
      - spectrum.py
      - statistics.py
      - spectral_attributes.py
      - events.py
      - roi.py
      - qc.py
      - multiband.py
      - fk.py
      - fk_filter.py
      - service.py
    - plotting/
      - waterfall.py
      - waveform.py
      - spectra.py
      - fk.py
      - roi.py
      - qc.py
      - multiband.py
    - plugins/
      - base.py
      - registry.py
      - builtins.py
    - cli/
      - validate.py
      - preview.py
      - statistics.py
      - spectrum.py
      - events.py
      - extensions.py
    - gui/
      - app.py
      - main_window.py
      - models.py
      - workers.py
    - utils/
      - slicing.py
      - validation.py
      - logging.py

## Layer responsibilities

- core: data model, metadata display formatting, package-wide constants, and exceptions.
- io: data readers, metadata readers, format registry, GUI-independent preview
  workflow, bounded data selection services, and JSON/CSV export helpers.
- processing: GUI-independent preprocessing operations such as demean, linear
  detrend, taper, normalization, standardization, clipping, and later filtering/resampling.
- analysis: GUI-independent DAS analysis. Current support includes basic
  statistics, spectral attributes, envelope/STA-LTA event candidates,
  amplitude spectrum, power spectrum, periodogram PSD, Welch PSD,
  single-channel spectrogram smoke-path helpers, ROI/annotation helpers,
  DAS QC/channel-quality metrics, multiband feature maps, local channel
  coherence, file-level analysis services, FK visualization, and FK-domain
  smoke filtering for DAS 2D wavefield inspection.
- plotting: Matplotlib plotting helpers independent from GUI widgets, including
  waterfall, waveform, spectrum, spectrogram, FK views, ROI overlays, QC plots,
  multiband maps, and coherence maps.
- plugins: lightweight extension metadata, extension wrappers, registry, built-in
  capability metadata, and optional Python entry point discovery. It does not
  replace existing services or trigger plugin scans at package import time.
- cli: installed command-line entry points that call stable service-layer APIs
  and avoid depending on examples/ as package API.
- gui: optional PyQt5 layer that calls preview, formatting, plotting,
  analysis-service, and export-helper APIs.
- utils: validation, slicing, logging, and shared small helpers.
- docs/09_tutorial_user_manual.ipynb: stable user tutorial and operation
  manual. It is not a development log, test report, or commit history.

## Dependency direction

Allowed:

    gui -> plotting -> analysis/processing -> io/core
    io -> core/utils
    processing/analysis -> core/utils
    plotting -> core
    cli -> analysis/processing/io/plotting/core
    cli -> plugins

Not allowed:

    core -> GUI
    io -> GUI
    processing/analysis -> GUI
    plugins -> GUI
    das_view -> old_code

## CLI and GUI entry points

- pyproject.toml defines installed console scripts for bounded validation,
  preview, statistics, spectrum/PSD/spectrogram, and event-candidate workflows.
- pyproject.toml defines GUI scripts for the optional PyQt5 application.
- das_view/cli modules are lightweight wrappers around service-layer APIs. They
  do not inspect HDF5/DAT internal paths, do not import old_code, and do not
  require PyQt5 at import time.
- das_view/gui/app.py provides the GUI entry point and delays PyQt5/MainWindow
  imports until the GUI is actually launched. `--help` can run without starting
  a Qt event loop.
- Release smoke validation can call `python -m das_view.gui.app --help` when a
  Windows gui-scripts executable does not echo help text to the active shell.
- examples/ remain user-facing runnable examples, not installed package API.

## Plugin architecture

- das_view/plugins/base.py defines ExtensionMetadata plus reader, processing,
  analysis, plotting, and export extension wrappers.
- ExtensionMetadata records name, kind, version, description, provider, module,
  tags, and enabled status. It is JSON-friendly through to_dict/from_dict.
- das_view/plugins/registry.py provides ExtensionRegistry plus global helper
  functions for register, unregister, list, get, and clear operations. Isolated
  registries are preferred for tests and one-off inspection.
- das_view/plugins/builtins.py registers metadata for existing stable package
  capabilities. Builtins describe callable import paths and capability tags; they
  do not read data, run analysis, create plots, or start GUI code.
- discover_entry_point_extensions uses importlib.metadata on demand for the
  `das_view.plugins` group. It is not called at import time, does not use the
  network, and records third-party loading failures instead of crashing the
  application.
- The current plugin layer is an extension boundary for future work. It does not
  replace the existing reader registry, IO data service, analysis service,
  plotting helpers, export helpers, or GUI workflows.

## Public API and compatibility

Stable public API:

- Top-level `das_view` exports core data containers and project exceptions.
- `das_view.io` exports reader-independent preview, selection, and trace
  services.
- `das_view.processing` exports documented preprocessing/filter functions and
  the preprocessing service.
- `das_view.analysis` exports documented analysis helpers and file-level
  services.
- `das_view.plotting` exports documented Matplotlib plotting helpers.
- `das_view.plugins` exports lightweight extension metadata, registry,
  builtins, and explicit discovery helpers.
- Installed CLI entry points are user-facing API.

Experimental API:

- Plugin extension wrappers and discovery are lightweight boundaries for future
  packages and may evolve after real third-party validation.
- GUI internals, worker classes, and model implementation details are internal
  unless explicitly documented otherwise.

Internal helpers:

- Underscore-prefixed functions, private parsing helpers, concrete reader
  internals, and module-local implementation details may change without notice.

Compatibility policy:

- Public API is kept stable within the current development line when practical.
- Internal helpers may change without notice.
- Data arrays keep the `(n_samples, n_channels)` convention.
- Event candidates, ROIs, and FK views are data-review aids, not location,
  inversion, or geologic interpretation results.

## Packaging

- pyproject.toml is the source of package metadata, optional dependencies, and
  entry points.
- Optional dependency groups separate GUI, development, and packaging needs.
- packaging/ contains Windows packaging notes, a PowerShell build helper, and
  a PyInstaller spec without local absolute paths.
- build/, dist/, wheel/source archives, exe files, and *.egg-info directories
  are ignored local artifacts and must not be committed.
- Release validation may create ignored local artifacts such as
  `.tmp_release_venv/` for clean editable-install smoke checks. These
  environments are not package inputs and should not be committed.

## Reader design

Readers implement BaseDASReader and return DASData.

Reader responsibilities:

- Identify whether a path can be read.
- Read metadata without loading large data arrays.
- Read data into (n_samples, n_channels).
- Support slicing and simple downsampling where practical.
- Record source format and source path.
- Preserve source-specific information in extra_attrs.

## Metadata display and preview service

- das_view/core/metadata_format.py converts DASMetadata into stable dictionaries,
  summary lines, and text blocks for CLI and GUI display.
- das_view/io/preview.py owns the lightweight preview workflow:
  path -> reader selection -> metadata read -> bounded slice/downsample read -> PreviewResult.
- PreviewResult includes full-file metadata, preview DASData, reader name, normalized
  slices, downsampling steps, and warnings.
- max_samples and max_channels are used to compute simple integer downsampling before
  data is read, so large files are not loaded blindly for preview.

## Data service

- das_view/io/data_service.py provides GUI/CLI reusable bounded data access helpers.
- read_selection selects a reader, validates time/channel slices in internal coordinates,
  and delegates actual IO to the reader with optional downsampling.
- read_trace reads one or a small set of channels for waveform views. Single-channel
  requests are passed to the reader as a narrow channel slice; non-contiguous multi-channel
  requests read the smallest enclosing channel window and then keep the requested columns.
- SelectionResult records the selected reader, normalized slices, downsampling, and
  requested channels. Callers should use this service instead of duplicating reader logic.

## Export helpers

- das_view/io/export.py provides to_jsonable, save_json, save_csv_rows,
  event_candidates_to_rows, rois_to_rows, annotations_to_rows, and
  analysis_summary_to_rows.
- Export helpers are GUI-independent and convert dataclasses, numpy scalars,
  numpy arrays, slices, and Path objects to JSON/CSV-friendly values.
- Output directories are created explicitly by the export helpers; generated
  JSON/CSV output files remain user artifacts and must not be committed.

## Plotting services

- plot_waterfall draws variable-density DAS previews from DASData.
- plot_waveform draws one or more channel traces from DASData with optional normalization
  and offsets. It is pure Matplotlib and does not depend on PyQt5.
- plot_spectrum and plot_spectrogram draw results from the analysis layer. They
  do not compute spectra and do not depend on PyQt5.
- plot_fk draws FKResult amplitude or power matrices from the analysis layer.
  It does not compute FK values and does not depend on PyQt5.
- plot_fk_mask can display a simple FK mask matrix for smoke-path validation.
  It does not compute or apply the filter.
- plot_rois_on_waterfall and plot_event_candidates_on_waterfall overlay
  half-open time/channel ROI boxes on Matplotlib axes or DASData waterfall
  plots. They do not perform ROI analysis and do not depend on PyQt5.
- plot_channel_quality, plot_bad_channels, plot_multiband_energy_map, and
  plot_coherence_map visualize DAS QC and feature-map outputs with Matplotlib.
  They do not compute QC or spectral features and do not depend on PyQt5.
- Plotting helpers assume the internal data convention (n_samples, n_channels).

## Analysis services

- das_view/analysis/statistics.py provides FiniteSummary and StatisticsResult
  containers plus finite_summary, basic_statistics, and window_statistics.
  These functions accept numpy arrays or DASData, never modify inputs in place,
  and support global, time-wise, channel-wise, and local window summaries.
  Statistics include count, finite/NaN/Inf counts, mean, standard deviation,
  min, max, median, percentiles, RMS, absolute mean, peak-to-peak, and energy.
- das_view/analysis/spectral_attributes.py provides BandEnergyResult and
  SpectralAttributesResult containers plus band_energy and
  spectral_attributes. These functions accept numpy arrays or DASData, use the
  DAS axis convention by default, and compute frequency-band energy, band
  power, band energy ratio, dominant frequency, peak power, spectral centroid,
  spectral bandwidth, spectral rolloff, and total energy.
- das_view/analysis/events.py provides EnvelopeResult, STALTARatioResult,
  EventCandidate, and EventDetectionResult containers plus amplitude_envelope,
  energy_envelope, sta_lta_ratio, detect_threshold_events, and
  detect_stalta_events. These functions accept numpy arrays or DASData, keep
  the DAS axis convention, and return event candidates only. They do not perform
  earthquake location, source location, inversion, or final interpretation.
- das_view/analysis/roi.py provides TimeChannelROI, Annotation, ROISet,
  ROIAnalysisResult, and rois_from_event_candidates. ROI sample and channel
  ranges are half-open intervals. These objects are data review and export aids,
  not location or interpretation results.
- das_view/analysis/qc.py provides ChannelQualityResult, DataQualityReport,
  LocalCoherenceResult, channel_quality_metrics, bad-channel detection,
  noise-floor estimates, SNR estimates, local_channel_coherence, and QC row
  helpers. These functions are data-quality and spatial-continuity aids only.
- das_view/analysis/multiband.py provides MultibandFeatureMap,
  multiband_energy_map, and spectral_attribute_map for windowed
  time-channel-band feature extraction. These maps are interpretable feature
  summaries, not classification, location, inversion, MASW, F-J, or dispersion
  picking.
- das_view/analysis/spectrum.py provides SpectrumResult, PSDResult, and
  SpectrogramResult containers plus amplitude_spectrum, power_spectrum,
  periodogram_psd, welch_psd, and single_channel_spectrogram.
- das_view/analysis/service.py provides file-level helpers such as
  compute_spectrum_for_file, compute_psd_for_file, and
  compute_spectrogram_for_file. They read bounded traces through the data
  service, optionally apply preprocessing/filter steps, and return the analysis
  result with reader metadata and preprocessing history.
- das_view/analysis/service.py also provides compute_statistics_for_file. It
  reads bounded 2-D selections through das_view/io/data_service.py::read_selection,
  optionally applies das_view/processing/service.py::apply_preprocess, then
  calls basic_statistics. It does not inspect HDF5/DAT internal paths and does
  not depend on GUI code.
- das_view/analysis/service.py also provides compute_band_energy_for_file and
  compute_spectral_attributes_for_file. They read bounded 2-D selections
  through read_selection, optionally apply apply_preprocess, then call
  band_energy or spectral_attributes. They do not inspect HDF5/DAT internal
  paths and do not depend on GUI code.
- das_view/analysis/service.py also provides compute_envelope_for_file,
  compute_stalta_for_file, and detect_events_for_file. They read bounded 2-D
  selections through read_selection, optionally apply apply_preprocess, then
  call the events analysis helpers. They do not inspect HDF5/DAT internal paths
  and do not depend on GUI code.
- das_view/analysis/service.py also provides compute_roi_statistics_for_file
  and compute_roi_spectral_attributes_for_file. They read each ROI through
  read_selection, optionally call apply_preprocess, then call existing
  statistics or spectral attribute helpers. They do not inspect HDF5/DAT
  internal paths and do not depend on GUI code.
- das_view/analysis/service.py also provides compute_quality_report_for_file,
  compute_multiband_map_for_file, compute_spectral_attribute_map_for_file, and
  compute_coherence_for_file. They read bounded 2-D selections through
  read_selection, optionally apply apply_preprocess, then call the QC,
  multiband, or local-coherence helpers. They do not inspect HDF5/DAT internal
  paths and do not depend on GUI code.
- das_view/gui/main_window.py provides a minimal Analysis tab that exposes
  bounded statistics, band energy, spectral attributes, event candidates, and
  ROI statistics. The tab builds validated requests through
  das_view/gui/models.py and runs them through das_view/gui/workers.py.
- Analysis workers call only das_view/analysis/service.py functions. They do
  not read HDF5/DAT internal paths and do not update Qt widgets directly.
- Analysis result summaries, QTableWidget rows, Matplotlib canvas updates, and
  JSON/CSV save dialogs remain in the Qt main thread. Export buttons call
  das_view/io/export.py helpers instead of implementing serialization in GUI
  code.
- The default axis=0 follows the DAS convention and treats each column as an
  independent channel through time.
- Spectrum helpers accept numpy arrays or DASData. DASData input can provide
  sample_rate_hz from metadata.
- The current spectrogram path is intentionally single-channel and smoke-test
  oriented. CLI/GUI integration should call analysis service and plotting
  helpers instead of implementing FFT/STFT/PSD logic in examples or
  das_view/gui/.
- das_view/analysis/fk.py provides FKResult and fk_transform. The default input
  convention is (n_samples, n_channels), axis=0 is time, and axis=1 is the
  channel/space axis. It uses a one-sided real FFT along time and a full FFT
  along space, returning values shaped as (n_frequencies, n_wavenumbers).
- das_view/analysis/service.py also provides compute_fk_for_file. It reads
  bounded 2-D selections through das_view/io/data_service.py::read_selection,
  optionally applies das_view/processing/service.py::apply_preprocess, then
  calls fk_transform. It does not inspect HDF5/DAT internal paths.
- das_view/analysis/fk_filter.py provides FKFilterResult, velocity_fan_mask,
  apply_fk_mask, and fk_velocity_filter. The mask is shaped as
  (n_frequencies, n_wavenumbers), uses apparent velocity approximated as
  abs(f / k), handles k=0 explicitly, applies the mask to the complex FK
  spectrum, and inverts back to the original time-channel shape.
- Phase 4D makes FK velocity-filter limits explicit: at least one of vmin_mps
  or vmax_mps is required, one-sided limits are allowed, and pass_inside=True
  means pass the selected velocity range while pass_inside=False rejects it.
  The k=0 column is handled by include_zero_wavenumber instead of dividing by
  zero; f=0 remains a finite row in the apparent-velocity mask.
- das_view/analysis/service.py also provides compute_fk_filter_for_file. It
  reads bounded 2-D selections through read_selection, optionally applies
  apply_preprocess, then calls fk_velocity_filter. The service returns filtered
  DASData, reader/metadata/selection information, preprocessing history, and
  filter parameters. It does not inspect HDF5/DAT internal paths.
- Phase 4B/4D FK filtering is a smoke path only. It is intended to validate
  coordinates, shape, mask behavior, and inverse-transform plumbing for DAS 2D
  wavefield inspection. It is not a specialized inversion or picking workflow.

## Processing services

- das_view/processing/preprocess.py provides pure numpy array functions. The
  default axis=0 follows the DAS convention and processes each channel along
  time.
- das_view/processing/filters.py provides scipy.signal based lowpass, highpass,
  bandpass, bandstop, and notch filters. The default axis=0 filters each
  channel independently along time.
- das_view/processing/service.py applies named preprocessing steps to DASData,
  returns a new DASData, preserves metadata, and appends preprocessing_history
  in metadata.extra_attrs.
- The service accepts simple step definitions such as ("demean", {"axis": 0})
  and is the intended integration point for future GUI or CLI workflows.
- Phase 3A/3B processing examples are preview-level and in-memory only. They do
  not export processed full-size DAS files and do not implement STFT/FK/PSD.
- Filtering is part of the processing layer and depends on scipy. Future GUI
  filter controls should call apply_preprocess instead of implementing filter
  design or scipy.signal calls in das_view/gui/.

## GUI design direction

The GUI should call preview, data-service, processing, analysis, and plotting services. It should not know details like /Acquisition/Raw[0]/RawData except through reader-facing abstractions.

GUI rules:

- PyQt5 imports live only in das_view/gui/ or GUI entry points.
- MainWindow calls PreviewWorker / QtPreviewWorker, which wrap create_preview.
- MainWindow exposes max_samples and max_channels controls; these values are
  validated in GUI model helpers and then passed to PreviewWorker/create_preview.
- Metadata text comes from format_metadata.
- The image panel uses plot_waterfall with an embedded Matplotlib Qt canvas.
- Phase 2B adds a Waveform tab. It parses zero-based channel indices in GUI
  model helpers, then calls read_trace through WaveformWorker / QtWaveformWorker
  and plot_waveform in the main GUI thread. The GUI does not implement channel
  slicing, downsampling algorithms, or concrete reader paths.
- Non-contiguous, reordered, or duplicate channel waveform selections are
  represented in metadata extra_attrs. dx_m is cleared for non-contiguous
  selections so downstream displays do not pretend the selected traces are
  evenly spaced.
- Phase 2D moves preview and waveform data loading into QThread-backed QObject
  workers. The workers call only service-layer functions: preview loading calls
  create_preview, and waveform loading calls read_trace.
- Matplotlib Qt canvas drawing remains in the main thread. Background workers
  return data/service results; MainWindow applies the latest non-cancelled result
  and then calls plot_waterfall or plot_waveform.
- The GUI supports a single active background task at a time. Open/preview and
  waveform controls are disabled while a task is running, a Cancel button requests
  soft cancellation, and a busy progress bar shows that work is ongoing.
- Phase 2D cancellation is cooperative. It cannot forcibly interrupt synchronous
  reader IO already in progress, but cancelled or stale task results are not
  applied to the GUI.
- Phase 3E adds a minimal Spectrum tab. It parses a single channel plus nfft,
  nperseg, noverlap, analysis type, and PSD dB display options in GUI model
  helpers, then starts a QThread-backed spectrum worker.
- Spectrum workers call only das_view.analysis.service helpers:
  compute_spectrum_for_file, compute_psd_for_file, and
  compute_spectrogram_for_file. They do not inspect HDF5/DAT internal paths and
  do not implement FFT, PSD, or spectrogram algorithms in the GUI layer.
- Spectrum plotting remains in the main GUI thread. MainWindow receives the
  latest non-cancelled service result and calls plot_spectrum, plot_psd, or
  plot_spectrogram on the embedded Matplotlib Qt canvas.
- Phase 4C adds a minimal FK tab. It parses bounded time/channel selection,
  output mode, display dB, and velocity fan parameters in PyQt-free GUI model
  helpers, then starts a QThread-backed FK worker.
- FK GUI workers call only das_view.analysis.service helpers:
  compute_fk_for_file for FK transform mode and compute_fk_filter_for_file for
  velocity-filter mode. They do not inspect HDF5/DAT internal paths and do not
  implement FK algorithms in the GUI layer.
- FK plotting remains in the main GUI thread. MainWindow receives the latest
  non-cancelled service result and calls plot_fk for transform results, or
  plot_waterfall plus plot_fk_mask for the minimal velocity-filter display.
- FK tab cancellation reuses the Phase 2D soft-cancel behavior. It cannot
  interrupt synchronous reader/FK service calls already in progress, but stale
  or cancelled results are not applied.
