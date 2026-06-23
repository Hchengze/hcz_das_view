# Project handoff summary

This document is the handoff point for starting a new Codex conversation on
hcz_das_view after Phase R1 project target realignment. It records the current
project identity, supported capabilities, constraints, and recommended next
phases.

## 1. Project identity

- Project name: hcz_das_view, with the Python package named das_view.
- Project role: HCZ DAS View is a DAS Viewer / DAS Analysis package.
- It focuses on DAS file reading, metadata display, time-channel
  visualization, waveform analysis, spectrum/spectrogram/FK visualization,
  preprocessing, filtering, feature extraction, GUI interaction, testing,
  documentation, packaging, and long-term maintainability.
- It is not a dedicated surface-wave inversion, MASW, F-J, or
  dispersion-picking package.
- 本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J
  或频散拾取软件。
- Development model: the new das_view/ package is being rebuilt after auditing
  legacy material under old_code/.
- New runtime code must not depend on, import, or call old_code.
- Latest project state: current HEAD after Phase 7C traditional DAS denoising
  and enhancement.
- Current phase: Phase 7C, Level 4 traditional signal-enhancement helpers:
  common-mode removal, despike, running median filtering, channel balancing,
  local normalization, time-space median filtering, robust clipping,
  hcz-das-denoise, and enhancement reports.
- Current expected test result after Phase 7C: 481 passed. The count increased
  from the Phase 7B baseline of 458 because Phase 7C added denoise processing,
  service, CLI, plotting, plugin metadata, entrypoint, public API, and tutorial
  coverage tests.

## 2. Repository and environment

- GitHub repository: https://github.com/Hchengze/hcz_das_view
- Local project path:

      <local-checkout>\HCZ_das_view

- Python environment:

      <python-from-your-environment>

- Common test command:

      python -B -m pytest -p no:cacheprovider

- Development install:

      pip install -e .[dev]

- Optional GUI install:

      pip install -e .[gui]

## 3. Non-negotiable project rules

1. New code must not import old_code.
2. Do not modify old_code/.
3. Do not commit real DAS data.
4. Do not commit generated images, caches, validation outputs, or temporary
   output directories.
5. Internal DAS arrays use one convention:

       data.shape == (n_samples, n_channels)

6. axis=0 means the time/sample axis by default.
7. GUI code must call services; it must not read HDF5/DAT internal paths or
   implement reader details directly.
8. core, io, processing, analysis, plotting, and plugins must not depend on
   PyQt5.
9. PyQt5 should only appear in das_view/gui/ or GUI startup entry points.
10. Every development round must update docs/05_development_log.md.
11. Keep markdown docs at eight files. docs/09_tutorial_user_manual.ipynb is
    the allowed additional Jupyter tutorial/user-manual file.
12. If a development round adds mature, stable user-facing functionality,
    update docs/09_tutorial_user_manual.ipynb in the same round. The notebook
    must explain method principles, key formulas, CLI examples, GUI workflow,
    and interpretation boundaries, and must not include development process,
    test runs, commit history, or real/private data paths.
13. FK visualization and FK-domain smoke filtering may remain as DAS 2D
    wavefield inspection capabilities, but should not be treated as a mainline
    path toward specialized inversion or picking workflows.

## 4. Current package architecture

- das_view/core/: core data structures, metadata formatting, and package
  exceptions.
- das_view/io/: file readers, reader registry, preview generation, and data
  selection services.
- das_view/processing/: pure preprocessing functions, scipy-based filters,
  traditional denoising/enhancement helpers, and DASData-level processing
  service.
- das_view/analysis/: spectrum, spectrogram, PSD/Welch, spectral attributes,
  envelope/STA-LTA event candidates, ROI/annotation helpers, DAS QC/channel
  quality, multiband feature maps, local channel coherence, FK visualization,
  FK-domain smoke filtering, basic statistics, and file-level analysis services.
- das_view/io/export.py: JSON/CSV export helpers for event candidates, ROIs,
  annotations, and ROI analysis summaries.
- das_view/plotting/: Matplotlib plotting helpers independent of PyQt5,
  including QC, multiband/coherence map plots, and denoise before/after/report
  plots.
- das_view/plugins/: lightweight extension metadata, extension wrappers,
  registry helpers, built-in capability metadata, and optional on-demand entry
  point discovery.
- das_view/cli/: installed command-line wrappers for validation, preview,
  statistics, spectrum/PSD/spectrogram, event-candidate workflows, extension
  inspection, QC/multiband/coherence workflows, and traditional denoise
  workflows.
- das_view/gui/: optional PyQt5 application, main window, models, and worker
  scaffolding.
- das_view/utils/: shared utilities, including slicing helpers.
- examples/: small CLI and GUI entry points for supported workflows.
- packaging/: Windows packaging notes, a PyInstaller spec, and a PowerShell
  build helper. Generated build/dist artifacts are not committed.
- tests/: synthetic-data tests for readers, services, processing, analysis,
  plotting, examples, and GUI smoke behavior.
- docs/: compact project documentation and phase history.
- docs/09_tutorial_user_manual.ipynb: stable user tutorial and operation
  manual; not a development log, test report, or commit history.

## 5. Public API inventory

Stable public API:

- `das_view`: `DASData`, `DASMetadata`, and package exceptions such as
  `DASViewError`, `ReaderError`, and `UnsupportedFormatError`.
- `das_view.io`: reader-independent preview, selection, trace, and export
  helpers, including `create_preview`, `read_selection`, `read_trace`,
  `save_json`, and `save_csv_rows`.
- `das_view.processing`: documented preprocessing and filter functions plus
  `apply_preprocess`, traditional denoise/enhancement helpers, and
  `apply_denoise_workflow`.
- `das_view.analysis`: documented numerical helpers and bounded file-level
  services for statistics, spectral attributes, events, ROI summaries, QC,
  multiband feature maps, local coherence, denoise/enhancement reports,
  spectrum/PSD/spectrogram, and FK smoke workflows.
- `das_view.plotting`: documented Matplotlib helpers for waterfall, waveform,
  spectrum, PSD, spectrogram, FK, ROI overlays, QC plots, multiband maps, and
  coherence maps.
- `das_view.plugins`: lightweight extension metadata, registry helpers,
  built-in metadata registration, and explicit entry point discovery.
- Installed CLI commands such as `hcz-das-validate`, `hcz-das-stats`,
  `hcz-das-events`, `hcz-das-extensions`, `hcz-das-qc`,
  `hcz-das-denoise`, and `hcz-das-view`.

Experimental API:

- Plugin extension wrapper details and third-party entry point conventions are
  expected to remain lightweight until validated with real external packages.
- GUI internals, worker classes, parser helpers, and widget implementation
  details are not guaranteed as stable package API.

Internal helpers:

- Underscore-prefixed functions, concrete reader internals, module-local parser
  details, and implementation-specific result-formatting helpers may change
  without notice.

Compatibility policy:

- Public API is kept stable within the current development line when practical.
- CLI entry points are user-facing and should remain backward compatible where
  reasonable.
- Internal helpers may change without notice.
- The data shape convention is always `(n_samples, n_channels)`.
- Event candidates, ROIs, and FK views are analysis and review aids, not
  source-location, earthquake-location, inversion, or geologic interpretation
  results.

Key modules:

- Core:
  - data_model.py: DASData / DASMetadata and dimension validation.
  - metadata_format.py: user-facing metadata formatting.
  - exceptions.py: explicit project exceptions.
- IO:
  - hdf5_zd.py: ZD HDF5 reader.
  - puniu_dat.py: Puniu DAT reader.
  - registry.py: reader registration and auto-detection.
  - preview.py: bounded preview service.
  - data_service.py: read_selection and read_trace.
- Processing:
  - preprocess.py: demean, detrend, taper, normalize, standardize, clipping.
  - filters.py: lowpass, highpass, bandpass, bandstop, notch.
  - denoise.py: common-mode removal, despike, running median filter,
    channel balancing, local normalization, time-space median filter, robust
    clipping, and denoise workflow reports.
  - service.py: ordered preprocessing/filter steps on DASData with history.
- Analysis:
  - statistics.py: FiniteSummary, StatisticsResult, finite_summary,
    basic_statistics, and window_statistics.
  - spectral_attributes.py: BandEnergyResult, SpectralAttributesResult,
    band_energy, and spectral_attributes.
  - events.py: EnvelopeResult, STALTARatioResult, EventCandidate,
    EventDetectionResult, amplitude_envelope, energy_envelope, sta_lta_ratio,
    detect_threshold_events, and detect_stalta_events.
  - roi.py: TimeChannelROI, Annotation, ROISet, ROIAnalysisResult, and
    rois_from_event_candidates.
  - spectrum.py: amplitude spectrum, power spectrum, spectrogram, periodogram
    PSD, and Welch PSD.
  - service.py: file-level spectrum/PSD/spectrogram workflows for CLI and GUI
    reuse, bounded statistics/spectral/event services, plus bounded
    FK/FK-filter services.
  - fk.py: FKResult and bounded FK transform.
  - fk_filter.py: FKFilterResult, simple velocity fan mask, FK-domain mask
    application, and inverse FK smoke path.
- Plotting:
  - waterfall.py: waterfall preview plotting.
  - waveform.py: waveform trace plotting.
  - spectra.py: spectrum, spectrogram, and PSD plotting.
  - fk.py: FK plotting and FK mask plotting.
- CLI:
  - validate.py: installed validation smoke workflow.
  - preview.py: installed metadata/preview workflow.
  - statistics.py: installed bounded statistics workflow.
  - spectrum.py: installed spectrum/PSD/spectrogram workflow.
  - events.py: installed event-candidate workflow.
- GUI:
  - main_window.py: minimal GUI with metadata, waterfall, waveform, spectrum,
    and FK tabs.
  - app.py: GUI application entry point.
  - models.py: GUI-independent parsing and small models.
  - workers.py: no-Qt callable service wrappers plus QThread QObject workers.

## 6. Completed phase history

- Phase 0: established layout, core data model, old-code rules, and baseline
  tests.
- Phase 1A-1D: added ZD HDF5 workflow, metadata formatting, bounded preview,
  waterfall plotting, minimal GUI, and validation entry points.
- Phase 2A-2D: added reader-independent selection services, waveform plotting,
  Puniu DAT validation tooling, reader edge-case checks, and QThread-backed GUI
  preview/waveform loading with soft cancellation.
- Phase 2E: validated representative local Puniu DAT and ZD HDF5 samples,
  hardened reader/tooling compatibility issues, and confirmed bounded analysis
  smoke paths without committing input data or generated outputs.
- Phase 3A-3E: added preprocessing, filters, amplitude/power spectrum,
  periodogram PSD, Welch PSD, single-channel spectrogram smoke paths,
  file-level spectrum services, and a minimal GUI Spectrum tab.
- Phase 4A-4D: added FK visualization, FK plotting, FK-domain velocity fan
  smoke filtering, GUI FK service panel, and safer FK velocity-limit defaults.
- Phase R1: realigned project target toward DAS Viewer / DAS Analysis, removed
  specialized inversion/picking workflows from the current main roadmap, and
  redirected next work toward DAS analysis capabilities.
- Phase 5A: added basic DAS statistics analysis, file-level statistics service,
  bounded CLI example, tests, and documentation.
- Phase 5B: added band energy and spectral attribute analysis, file-level
  services, bounded CLI example, tests, and documentation.
- Phase 5C: added envelope, energy envelope, STA/LTA, threshold event
  candidates, file-level event services, bounded CLI JSON/CSV example,
  tutorial/user-manual notebook, tests, and documentation.
- Phase 5D: added ROI and annotation helpers, event-candidate to ROI
  conversion, ROI statistics and spectral summaries, JSON/CSV export helpers,
  ROI overlay plotting, bounded ROI export CLI example, tests, and tutorial
  notebook updates.
- Phase 5E: added a minimal GUI Analysis tab that connects bounded statistics,
  band energy, spectral attributes, event candidates, ROI statistics, and
  JSON/CSV export to existing service-layer APIs through QThread workers.
- Phase 6A: hardened packaging metadata, added installed CLI/GUI entry points,
  added Windows PyInstaller packaging notes/spec/script, added packaging and
  entrypoint tests, and documented the release checklist.
- Phase 6C: polished release validation for pyproject metadata, ignored clean
  venv editable install smoke, installed CLI help smoke, GUI help smoke,
  example help smoke, packaging artifact policy, release validation tests, and
  tutorial/user manual release-operation notes.
- Phase 6B: added a lightweight plugin / extension architecture with
  ExtensionMetadata, reader/processing/analysis/plotting/export extension
  wrappers, an isolated/global extension registry, built-in extension metadata,
  on-demand Python entry point discovery, and the hcz-das-extensions inspection
  CLI.
- Phase 7A: stabilized the public API inventory, exported core exceptions,
  added import-boundary and public API stability tests, documented compatibility
  policy, cleaned handoff/roadmap consistency, and updated the tutorial
  notebook with public API, data-shape, usage-boundary, and troubleshooting
  guidance.
- Phase 7B: added DAS QC/channel-quality metrics, bad-channel flags,
  noise-floor and SNR estimates, multiband energy maps, spectral-attribute
  maps, local channel coherence, bounded service functions, hcz-das-qc,
  Matplotlib QC/map plots, plugin metadata, tests, and tutorial updates. Level
  4 traditional denoising and Level 5 wavefield/apparent-moveout work remain
  roadmap-only.
- Phase 7C: added Level 4 traditional denoising/enhancement helpers,
  apply_denoise_workflow reports, bounded denoise service functions,
  hcz-das-denoise, Matplotlib before/after and enhancement-metric plots,
  plugin metadata, tests, and tutorial updates. Level 5 wavefield/apparent
  moveout remains deferred.

## 7. Current supported capabilities

### Readers

- ZD HDF5 reader.
- Puniu DAT reader.
- Reader registry and auto-detection.
- Metadata-only reads.
- Bounded reads.
- Time/channel slice and downsample handling.
- Local validation scripts for real or quasi-real samples without committing
  data.

### Data services

- Preview service via create_preview.
- General bounded selection via read_selection.
- Trace/channel selection via read_trace.

### Installed entry points

- hcz-das-validate.
- hcz-das-preview.
- hcz-das-stats.
- hcz-das-spectrum.
- hcz-das-events.
- hcz-das-extensions.
- hcz-das-qc.
- hcz-das-denoise.
- hcz-das-view.
- das-view-gui remains as a compatibility GUI script.

### Plotting

- Waterfall preview plots.
- Waveform trace plots.
- Spectrum plots.
- Spectrogram plots.
- PSD plots, including optional dB display.
- FK amplitude/power plots.
- FK mask plots for smoke-path validation.
- Channel quality and bad-channel plots.
- Multiband energy map plots.
- Local coherence map plots.
- Denoise before/after waterfall plots.
- Enhancement report metric plots.

### GUI

- Open supported files.
- Display formatted metadata.
- Show bounded waterfall preview tab.
- Show waveform tab.
- Show Spectrum tab for single-channel amplitude spectrum, power spectrum,
  PSD periodogram, PSD Welch, and spectrogram tasks.
- Show FK tab for bounded FK transform and FK velocity filter service tasks.
- Show Analysis tab for bounded statistics, band energy, spectral attributes,
  STA/LTA event candidates, envelope-threshold event candidates, ROI
  statistics, result tables, and JSON/CSV export.
- Configure max_samples and max_channels.
- Parse single or comma-separated channel input.
- Preview, waveform, spectrum, and FK tasks run in QThread-backed background
  workers with busy progress feedback and soft cancellation.

### Processing

- demean.
- detrend_linear.
- taper.
- normalize.
- standardize.
- clip.
- lowpass.
- highpass.
- bandpass.
- bandstop.
- notch.
- apply_preprocess with preprocessing/filter history in metadata.extra_attrs.
- common_mode_removal.
- despike.
- running_median_filter.
- channel_balance.
- local_normalize.
- time_space_median_filter.
- robust_clip.
- apply_denoise_workflow with enhancement history and before/after metrics.

### Analysis

- amplitude_spectrum.
- power_spectrum.
- single_channel_spectrogram.
- periodogram_psd.
- welch_psd.
- fk_transform.
- velocity_fan_mask.
- apply_fk_mask.
- fk_velocity_filter.
- compute_spectrum_for_file.
- compute_psd_for_file.
- compute_spectrogram_for_file.
- compute_fk_for_file.
- compute_fk_filter_for_file.
- finite_summary.
- basic_statistics.
- window_statistics.
- compute_statistics_for_file.
- band_energy.
- spectral_attributes.
- compute_band_energy_for_file.
- compute_spectral_attributes_for_file.
- amplitude_envelope.
- energy_envelope.
- sta_lta_ratio.
- detect_threshold_events.
- detect_stalta_events.
- compute_envelope_for_file.
- compute_stalta_for_file.
- detect_events_for_file.
- TimeChannelROI.
- Annotation.
- ROISet.
- rois_from_event_candidates.
- compute_roi_statistics_for_file.
- compute_roi_spectral_attributes_for_file.
- channel_quality_metrics.
- data_quality_report.
- channel_quality_rows.
- detect_bad_channels.
- estimate_noise_floor.
- estimate_snr.
- multiband_energy_map.
- spectral_attribute_map.
- local_channel_coherence.
- compute_quality_report_for_file.
- compute_multiband_map_for_file.
- compute_spectral_attribute_map_for_file.
- compute_coherence_for_file.
- compute_denoised_selection_for_file.
- compute_enhancement_report_for_file.

### Plugins and extensions

- ExtensionMetadata.
- ReaderExtension.
- ProcessingExtension.
- AnalysisExtension.
- PlottingExtension.
- ExportExtension.
- ExtensionRegistry.
- register_builtin_extensions.
- list_builtin_extensions.
- discover_entry_point_extensions.
- hcz-das-extensions for user-facing inspection of built-in extension
  metadata.

## 8. Current examples

- examples/read_and_plot_zd_h5.py: read a ZD HDF5 file and save a waterfall
  smoke plot.
- examples/preview_file.py: create a bounded preview from any registered
  reader.
- examples/validate_file.py: validate one HDF5/DAT file, print metadata and
  preview information, and optionally save preview/waveform images.
- examples/validate_local_samples.py: batch-validate paths listed in ignored
  local_validation_paths.txt.
- examples/plot_waveform.py: plot one or more bounded waveform traces.
- examples/preprocess_file.py: apply preview-level preprocessing and save a
  processed waterfall image.
- examples/filter_file.py: apply preview-level filtering and save a filtered
  waterfall image.
- examples/spectrum_file.py: compute bounded amplitude, power, PSD/Welch, or
  spectrogram plots, optionally after a filter step.
- examples/statistics_file.py: compute bounded global, time-wise, or
  channel-wise DAS statistics and optionally save JSON/global CSV output.
- examples/spectral_attributes_file.py: compute bounded band energy or
  spectral attributes and optionally save JSON/CSV output.
- examples/event_detection_file.py: compute bounded envelope or STA/LTA event
  candidates and optionally save JSON/CSV candidate tables.
- examples/roi_export_file.py: create manual ROIs, convert event candidates to
  ROIs, export events/ROIs as JSON/CSV, and export ROI statistics summaries.
- examples/qc_file.py: run bounded DAS QC reports, bad-channel CSV export,
  multiband feature maps, and local coherence summaries.
- examples/denoise_file.py: run bounded traditional denoising/enhancement
  workflows and optional JSON enhancement reports.
- examples/fk_file.py: compute bounded FK amplitude or power plots, optionally
  after a filter step.
- examples/fk_filter_file.py: apply a minimal bounded FK velocity fan filter
  and save a filtered waterfall, optionally saving the filtered FK image.
- examples/run_gui.py: launch the optional PyQt5 GUI.
- Installed entry points in das_view/cli provide package-level CLI wrappers
  for validation, preview, statistics, spectrum/PSD/spectrogram, event
  candidates, and QC/multiband/coherence workflows without treating examples/
  as package API.
- hcz-das-extensions lists built-in extension metadata by kind and can emit
  JSON for tooling.
- hcz-das-denoise runs bounded traditional signal-enhancement workflows and can
  export an enhancement report JSON.
- packaging/README_windows_packaging.md documents Windows Conda setup, GUI
  launch, PyInstaller build, artifact policy, and exe validation.
- packaging/build_windows.ps1 runs the local PyInstaller packaging smoke path.
- packaging/hcz_das_view.spec is a relative-path spec for the GUI executable.

## 9. Current tests

Current coverage includes:

- Core data model, metadata formatting, and dimension validation.
- ZD HDF5 and Puniu DAT readers, registry behavior, bounded reads, slicing,
  downsampling, Count-as-total-values HDF5 metadata, Puniu DAT seek fallback,
  and edge cases.
- Preview, selection, and trace data services.
- Waterfall, waveform, spectrum, spectrogram, PSD, FK, and FK mask plotting.
- Preprocessing and filter functions plus DASData service integration.
- Spectrum, PSD/Welch, spectrogram, FK, and FK filter analysis helpers.
- Statistics analysis, service, and example tests for global, axis-wise,
  bounded, NaN/Inf-aware, and JSON/CSV-output workflows.
- Spectral attributes analysis, service, and example tests for band energy,
  band ratios, dominant frequency, centroid, bandwidth, rolloff, bounded
  services, and JSON/CSV-output workflows.
- Event analysis, service, and example tests for amplitude envelope, energy
  envelope, STA/LTA, threshold candidates, bounded services, and JSON/CSV
  candidate-table workflows.
- Tutorial notebook tests for valid ipynb JSON, nbformat, user-manual keywords,
  formulas, and no local path / development-test content.
- ROI, export, plotting, and example tests for ROI validation, annotation
  validation, event-candidate to ROI conversion, ROI services, JSON/CSV export,
  ROI overlays, and bounded CLI outputs.
- CLI example argument construction and no-real-data smoke behavior.
- GUI-independent parser/model helpers and optional PyQt5 smoke tests for
  preview, waveform, spectrum, FK, and Analysis panels.
- Packaging and entrypoint tests for pyproject metadata, optional dependency
  groups, console/gui scripts, das_view.cli imports, CLI help behavior, GUI app
  help behavior, package import without PyQt5, and packaging files without
  local absolute paths.
- Release validation tests for ignored release artifacts, clean-install
  policy, Windows packaging files without local paths or real-data patterns,
  GUI help without a Qt event loop, and tutorial notebook installation/CLI/GUI/
  packaging sections.
- Plugin tests for metadata validation, extension wrapper construction,
  registry register/list/filter/unregister behavior, isolated versus global
  registry behavior, entry point discovery failure summaries, built-in
  extension metadata, and hcz-das-extensions CLI output.
- API stability and import-boundary tests for public imports, PyQt5 dependency
  boundaries, explicit plugin discovery, package import behavior, CLI import
  behavior, and GUI help without a Qt event loop.
- QC and multiband tests for channel quality, bad-channel flags, spike and
  clipping detection, NaN/Inf fractions, noise-floor/SNR estimates, local
  channel coherence, multiband energy maps, spectral attribute maps, service
  bounded reads, hcz-das-qc JSON/CSV output, plotting helpers, plugin metadata,
  and entrypoint declarations.
- Denoise/enhancement tests for common-mode removal, despike, running median
  filtering, channel balancing, local normalization, time-space median
  filtering, robust clipping, workflow history/report metrics, bounded service
  reads, hcz-das-denoise JSON reports, plotting helpers, plugin metadata,
  public API imports, and entrypoint declarations.

Current full test command and expected result:

      python -B -m pytest -p no:cacheprovider

      481 passed

## 10. Old code migration status

- old_code/old_code1/tools/data_tools.py: reader and metadata ideas were
  audited; useful ZD HDF5 concepts were reimplemented through the new reader,
  metadata, and preview interfaces.
- old_code/old_code3/dy_view.py: Puniu DAT header and payload concepts were
  audited; the new Puniu reader reimplements the necessary behavior with clear
  validation and the (n_samples, n_channels) convention.
- old_code/old_code1/tools/analysis_tools.py: preprocessing, filtering,
  spectrum, PSD/Welch, basic FK, and FK filter/fan-mask ideas were audited;
  selected simple numerical logic was reimplemented with explicit numpy/scipy
  interfaces and the (n_samples, n_channels) convention. Historical
  topic-specific sections are not in the current main roadmap.
- old_code/old_code4/hcz_signal_preprocess.py: basic preprocessing and filter
  workflow ideas were audited; clean, dimension-explicit replacements now live
  under das_view/processing/. Old workflow style and unclear parameter coupling
  were not copied.
- old_code/old_code4/hcz_signal_analyse.py: spectrum/spectrogram/PSD ideas were
  audited; the new analysis layer implements bounded, service-friendly
  functions. GUI-coupled plotting and broad analysis workflows were not copied.
- old_code/old_code1/tools/ui_tools.py: old GUI patterns were used only as
  design reference. Large old GUI files were not migrated.

No old_code files are imported by the new runtime package.

## 11. Known limitations and risks

1. ZD HDF5 and Puniu DAT have been validated on a small representative local
   sample set, but broader production coverage is still needed.
2. GUI preview, waveform, spectrum, and FK tasks use QThread workers, but real
   production large-file responsiveness has not been validated.
3. GUI cancellation is soft and cannot forcibly interrupt synchronous reader IO
   or analysis calls already in progress.
4. There is no GUI preprocessing or filter panel.
5. FK visualization and FK-domain filtering are bounded smoke paths for DAS 2D
   wavefield inspection, not polished production denoising workflows.
6. A broader time-frequency workflow is not implemented.
7. Full processing/analysis result export is not implemented.
8. The GUI Analysis tab is intentionally minimal and does not yet provide a
   rich interactive annotation workspace.
9. Automated release CI is not implemented.
10. Windows exe signing is not implemented.
11. Clean-environment install validation across multiple machines is not
    completed.
12. SEGY, SAC, and TDMS are not implemented.
13. The tutorial notebook should be maintained as stable features mature.

## 12. Release checklist

- Check version metadata in pyproject.toml.
- Run the full pytest suite.
- Run local real/quasi-real sample smoke validation without committing data.
- Run installed CLI `--help` smoke.
- Run GUI `--help` smoke and GUI launch smoke.
- Run example script `--help` smoke.
- Build wheel and sdist smoke artifacts when the `build` package is available.
- Run clean venv editable/install smoke.
- Run Windows PyInstaller smoke when preparing an exe.
- Update README and docs/09_tutorial_user_manual.ipynb.
- Confirm no real data, local paths, validation outputs, generated images,
  JSON/CSV outputs, build/dist artifacts, wheels, archives, or exe files are
  staged.
- Create the release tag and GitHub release notes.

## 13. Recommended next phases

### Option A: Phase 6D Release CI planning

Goal:

      Add maintainable release CI planning for tests, packaging smoke, and
      artifact safety checks.

Status:

      Not implemented. This is the recommended next release-hardening step.

### Option B: Phase 7D Wavefield decomposition and apparent moveout planning

Goal:

      Plan Level 5 wavefield decomposition / apparent moveout assistance
      without adding location, inversion, MASW, F-J, or dispersion-picking
      workflows.

Status:

      Not implemented. This is the recommended analysis-roadmap planning option
      after Phase 7C.

### Option C: Phase 2E real sample validation refresh

Goal:

      Re-run local real/quasi-real ZD HDF5 and Puniu DAT validation when new
      sample paths or new format variants are provided.

Status:

      Phase 2E is complete for the previously provided local sample set.
      Re-enter only when new sample paths are intentionally supplied.

## 14. DAS Analysis capability roadmap

### Five-level DAS Analysis roadmap

1. Level 1: DAS data quality / QC analysis.
   Includes bad/dead/quiet/noisy channel detection, clipping/saturation,
   spikes, NaN/Inf/zero fractions, RMS/STD/energy stability, noise floor, SNR,
   channel quality score, time-window quality score, and QC report JSON/CSV
   export.
2. Level 2: Multiband / multispectral DAS feature map.
   Includes time-window x channel x band energy maps, low/mid/high band maps,
   band ratios, dominant frequency, centroid, bandwidth, rolloff, multiband
   export, and ROI-based multiband summary.
3. Level 3: Cross-channel coherence / local similarity / spatial continuity.
   Includes adjacent-channel correlation, local channel coherence, channel-lag
   coherence, windowed spatial-continuity score, and coherence maps.
4. Level 4: Robust denoising / enhancement using traditional methods.
   Core traditional helpers are implemented in Phase 7C: common-mode removal,
   median filtering, despike, channel balancing, local normalization,
   time-space 2D median filtering, robust clipping, workflow reports, service,
   CLI, plotting, and plugin metadata. Directional FK-domain polish remains
   future work.
5. Level 5: Wavefield decomposition / apparent moveout assisted analysis.
   Deferred. Candidate future helpers include apparent slope/velocity
   attributes, directional energy ratio, directional wavefield energy helpers,
   FK directional energy summary, and event moveout auxiliary attributes.

Levels 1-4 now have core general DAS data-quality, feature-analysis, and
traditional enhancement support. Level 5 remains deferred after Phase 7C. None
of the levels imply surface-wave imaging, MASW, F-J, dispersion picking, source
location, inversion, or geologic interpretation.

### Basic statistics

- time-wise statistics
- channel-wise statistics
- windowed statistics
- RMS
- peak-to-peak
- percentile
- energy
- finite / NaN / Inf summary
- clipping / saturation summary

### Spectral attributes

- band energy
- dominant frequency
- spectral centroid
- spectral bandwidth
- band energy ratio
- spectral peak frequency

### Time-frequency attributes

- spectrogram summary
- band-limited energy image
- time-varying dominant frequency

### Event / anomaly candidates

- envelope
- STA/LTA
- short-window energy
- threshold crossing
- event candidate table
- time-channel bounding box

### Interpretation support

- ROI selection
- annotation
- comparison before/after processing
- summary export
- figure export
- analysis report skeleton

Interpretation support means DAS data review and analysis assistance. It does
not mean geologic inversion or specialized imaging.

## 15. External references for target alignment

- DASCore / DASDAE: reference direction for DAS data management, analysis,
  visualization, processing conversion, and format IO organization.
- Xdas: reference direction for DAS data management, processing, visualization,
  metadata abstraction, and large-data/lazy-processing patterns.
- DASPy: reference direction for DAS processing toolbox organization, including
  preprocessing, filtering, spectral analysis, visualization, denoising,
  wavefield decomposition, and channel analysis.
- ObsPy: reference direction for general seismic time-series processing,
  filtering, visualization, and signal-processing API style.

These are target-alignment references only. No external project code is copied,
and Phase R1 adds no dependency.

## 16. Suggested first prompt for the new Codex chat

Copy this into the next Codex conversation:

    请先不要开发新功能。请先阅读：

    - AGENTS.md
    - README.md
    - docs/08_project_handoff.md
    - docs/05_development_log.md
    - docs/07_roadmap.md

    然后执行：
    git status --short
    git branch -vv
    git log --oneline -8
    python -B -m pytest -p no:cacheprovider

    请先返回当前仓库状态、最新 HEAD、测试结果和下一步建议，不要直接修改代码。

    如果我提供新的真实数据路径，则建议进入：
    Phase 2E: Real sample validation refresh

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J
或频散拾取软件。
    如果继续发布工程化工作，则建议进入：
    Phase 6D: Release CI planning
