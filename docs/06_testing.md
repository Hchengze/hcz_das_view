# Testing

## Test goals

The project should test core logic independently from the GUI.

Current coverage:

- DASMetadata initialization.
- DASData dimension convention.
- Dimension mismatch errors.
- Reader registry registration and lookup.
- ZD HDF5 metadata read, full read, time slicing, channel slicing, downsampling, orientation transpose, missing path errors, and ambiguous orientation errors.
- ZD HDF5 edge cases for numpy scalar attrs, bytes attrs, missing RawData,
  Count/NumberOfLoci mismatches, Count-as-total-values metadata, ambiguous
  orientation, and empty selections.
- Puniu DAT header parsing, full read, slicing, downsampling, start_time conversion, and length mismatch errors.
- Puniu DAT edge cases for incomplete headers, invalid seek, unaligned payloads,
  validated seek fallback when payload follows the fixed header, invalid
  timestamps, and empty/out-of-range selections.
- plot_waterfall smoke test with non-interactive Matplotlib backend and image save.
- Metadata formatting to dict, text summary, missing-value display, and duration calculation.
- Reader preview API for synthetic ZD HDF5 and Puniu DAT, including automatic downsampling, unsupported formats, and metadata error wrapping.
- plot_waterfall edge cases for constant matrices and empty data.
- GUI smoke coverage: PyQt-free GUI model helpers, and MainWindow creation when PyQt5 and Matplotlib Qt support are available.
- GUI preview limit parsing, status summary formatting, task status formatting,
  stale/cancelled result rejection, control-state helpers, and error formatting.
- Phase 2D GUI responsiveness tests cover callable worker parameter storage,
  Qt worker construction/cancellation flags when PyQt5 is available, progress
  bar and Cancel button presence, initial disabled Cancel state, task control
  switching, and soft-cancel status updates without opening real file dialogs or
  requiring real DAS data.
- Phase 3E GUI spectrum tests cover PyQt-free spectrum parameter parsing,
  analysis type to service-request mapping, PSD dB flag preservation for
  plotting, spectrum status formatting, SpectrumWorker parameter storage,
  QtSpectrumWorker construction/cancellation flags when PyQt5 is available, and
  Spectrum tab widget/control smoke checks without real DAS data.
- Phase 4C GUI FK tests cover PyQt-free FK parameter parsing, FK mode/output
  mapping, bounded time/channel slice construction, vmin/vmax validation, dB
  display flag preservation, FK status formatting, FKWorker parameter storage,
  QtFKWorker construction/cancellation flags when PyQt5 is available, and FK tab
  widget/control smoke checks without real DAS data.
- Data service coverage for synthetic ZD HDF5 and Puniu DAT selections, trace reads,
  slicing, downsampling, invalid channels, empty selections, and unsupported formats.
- Phase 2B extends data service trace coverage to contiguous multi-channel reads,
  non-contiguous reads, non-increasing channel order, duplicate channels, negative
  channels, empty channel selections, non-integer channel sequences, and metadata
  spacing behavior for non-contiguous selections.
- plot_waveform coverage for single-channel, multi-channel, image save with Agg,
  invalid channels, and constant/zero data.
- GUI waveform smoke coverage checks that the Waveform tab and controls can be
  constructed when PyQt5 is available.
- Channel parser tests are PyQt-free and cover single channel input, comma-separated
  input, spaces, duplicate preservation, empty input, non-integer input, and negative
  input.
- Local validation script tests cover path-list parsing, UTF-8 BOM stripping,
  missing path-list friendly exit behavior, path-safe preview summaries, and
  direct plot_waveform.py script import behavior.
- Basic preprocessing function tests cover demean, linear detrend, taper,
  maxabs/minmax normalization, standardization, clipping, invalid parameters,
  NaN/Inf behavior, and no in-place modification.
- Preprocessing service tests cover DASData copying, metadata preservation,
  preprocessing_history records, multi-step ordering, unknown steps, and invalid
  parameters.
- Preprocessing example tests cover CLI step construction without requiring real
  DAS input files.
- Filter function tests cover lowpass, highpass, bandpass, bandstop, notch,
  shape preservation, no in-place modification, axis=0/axis=1, causal and
  zero-phase paths, invalid frequency/order/quality/axis parameters, NaN/Inf
  rejection, and too-short data errors.
- Filter service tests cover lowpass, bandpass, mixed demean -> bandpass ->
  normalize workflows, preprocessing_history records, and unknown-step
  regression.
- Filter example tests cover CLI filter-step construction without requiring real
  DAS input files.
- Spectrum analysis tests cover amplitude/power peak detection, periodogram PSD,
  Welch PSD, frequency-axis lengths, nfft resolution changes, axis=0/axis=1,
  channel selection, channel averaging, DASData sample-rate metadata, invalid
  PSD parameters, and NaN/Inf rejection.
- Spectrogram tests cover single-channel scipy.signal spectrogram smoke paths,
  output dimension consistency, invalid channel/nperseg/noverlap errors, and
  Matplotlib Agg image saving.
- Spectrum plotting tests cover plot_spectrum, plot_psd, dB PSD display,
  plot_spectrogram, and clear errors for empty or malformed result containers.
- Spectrum service tests cover compute_spectrum_for_file, compute_psd_for_file,
  and compute_spectrogram_for_file on synthetic ZD HDF5 data, including optional
  bandpass preprocessing history.
- Spectrum example tests cover CLI processing-step construction, analysis mode
  selection, conflict handling, and PSD argument parsing without requiring real
  DAS input files.
- Statistics analysis tests cover global statistics, RMS, energy, absolute
  mean, peak-to-peak, percentiles, axis=0/channel-wise outputs, axis=1/time-wise
  outputs, DASData metadata summaries, finite/NaN/Inf counts, omit/raise
  non-finite policies, all-nonfinite stability, non-numeric rejection, window
  statistics, and no in-place mutation.
- Statistics service tests cover compute_statistics_for_file on synthetic ZD
  HDF5 data, bounded time/channel selections, preprocessing history, axis=None,
  axis=0, axis=1, reader name, metadata, and selection reporting.
- Statistics example tests cover parser behavior, bounded default slices,
  explicit slices, axis parsing, JSON output to pytest tmp_path, and global CSV
  output to pytest tmp_path without requiring real DAS data.
- Spectral attributes analysis tests cover dominant frequency on synthetic
  single-frequency data, band-energy separation, band-energy ratios, spectral
  centroid, non-negative spectral bandwidth, spectral rolloff bounds,
  frequency_range behavior, average_channels=True, per-channel output shapes,
  DASData sample-rate metadata, invalid sample rates, invalid band limits,
  Nyquist checks, empty-bin bands, invalid rolloff values, NaN/Inf rejection,
  and no in-place mutation.
- Spectral attributes service tests cover compute_band_energy_for_file and
  compute_spectral_attributes_for_file on synthetic ZD HDF5 data, bounded
  time/channel selections, preprocessing history, average_channels=True,
  reader name, metadata, and selection reporting.
- Spectral attributes example tests cover band pair parsing, attributes mode,
  bounded default slices, JSON output, and CSV output to pytest tmp_path without
  requiring real DAS data.
- Event analysis tests cover amplitude envelope shape, synthetic sinusoid
  envelope behavior, energy envelope non-negativity, sliding-window energy
  shape, STA/LTA shape and invalid window errors, threshold event detection,
  min-duration filtering, merge-gap behavior, max-events limiting, DASData
  input, NaN/Inf rejection, and no in-place mutation.
- Event service tests cover compute_envelope_for_file, compute_stalta_for_file,
  and detect_events_for_file on synthetic ZD HDF5 data, bounded time/channel
  selections, preprocessing history, reader name, metadata, and selection
  reporting.
- Event detection example tests cover STA/LTA argument parsing, envelope
  argument parsing, bounded default slices, JSON output, and CSV candidate-table
  output to pytest tmp_path without requiring real DAS data.
- Tutorial notebook tests verify that docs/09_tutorial_user_manual.ipynb exists,
  is valid JSON, declares nbformat, contains key DAS Viewer / DAS Analysis
  formulas and concepts, avoids local absolute paths, and avoids development
  log, commit, or pytest content.
- ROI analysis tests cover TimeChannelROI validation, duration_samples,
  n_channels, to_dict/from_dict, Annotation confidence validation, ROISet
  add/remove/filter/sort/limit, event-candidate to ROI conversion, padding,
  max_rois, and invalid ROI errors.
- ROI service tests cover compute_roi_statistics_for_file and
  compute_roi_spectral_attributes_for_file on synthetic ZD HDF5 data, bounded
  ROI time/channel selections, preprocessing history, multiple ROIs, reader
  name, metadata, selection reporting, and band-energy ROI summaries.
- Export tests cover dataclass/numpy/Path to_jsonable conversion, JSON output,
  CSV output, event candidate rows, ROI rows, and annotation rows using pytest
  tmp_path only.
- ROI plotting tests cover empty ROI overlays, single ROI image saving with
  Matplotlib Agg, max_rois limiting, invalid ROI errors, and event-candidate
  overlay conversion.
- ROI export example tests cover manual ROI parsing, detect-events argument
  parsing, bounded default slices, JSON output, CSV output, and no-real-data
  synthetic file workflows.
- Phase 5E GUI analysis tests cover PyQt-free analysis selection parsing,
  percentile, band-range, frequency-range, ROI text parsing, analysis type
  mapping, invalid parameter errors, analysis summary formatting, event
  candidate rows, ROI summary rows, AnalysisWorker parameter storage,
  QtAnalysisWorker construction/cancellation flags when PyQt5 is available,
  Analysis tab widget/control smoke checks, task-control state switching, and
  analysis-result clearing without real DAS data.
- Phase 6A packaging tests cover pyproject.toml build-system and project
  metadata, optional dependency groups, console/gui script declarations,
  das_view.cli module imports, CLI `--help` smoke behavior, GUI app help
  behavior without starting the Qt event loop, package import without PyQt5,
  and Windows packaging files without local absolute paths.
- Phase 6C release validation tests cover release metadata, package import
  without PyQt5, CLI module help smoke, GUI help without a Qt event loop,
  Windows packaging README/spec/script artifact policy, .gitignore release
  artifact coverage, and tutorial notebook installation/CLI/GUI/packaging
  sections.
- Phase 6B plugin tests cover ExtensionMetadata validation and round trips,
  extension wrapper construction, isolated and global registries, kind/enabled
  filtering, duplicate and replace behavior, entry point discovery success and
  failure summaries, built-in extension metadata, and the
  hcz-das-extensions CLI.
- Phase 7A API/import-boundary tests cover package and subpackage imports
  without PyQt5, top-level import without plugin entry point discovery, package
  import without real data reads, CLI module imports without GUI startup, GUI
  app help without a Qt event loop, and stable public API import/callability
  checks for core, IO, processing, analysis, plotting, and plugins.
- FK analysis tests cover synthetic plane-wave peak frequency/wavenumber
  detection, amplitude/power shapes, DASData metadata sample-rate/dx handling,
  invalid sample_rate_hz/dx/nfft/dimensionality/NaN/Inf/too-short inputs, and
  no in-place modification.
- FK plotting tests cover Matplotlib Agg image saving, dB plotting with zero
  values, and clear errors for invalid or malformed FKResult objects.
- FK service tests cover compute_fk_for_file on synthetic ZD HDF5 selections
  and optional bandpass preprocessing history.
- FK example tests cover bounded time/channel slice construction and bandpass
  processing-step construction without requiring real DAS input files.
- FK filter analysis tests cover velocity_fan_mask shape and k=0 handling,
  vmin/vmax validation, pass_inside True/False behavior, apply_fk_mask inverse
  shape restoration, mask shape validation, no in-place mutation, DASData
  metadata sample-rate/dx handling, invalid input rejection, and synthetic
  plane-wave suppression smoke paths.
- Phase 4D extends FK filter tests for safer defaults: missing vmin/vmax is an
  error, one-sided vmin-only and vmax-only ranges are supported, k=0/f=0 cases
  do not divide by zero, and mask dtype/shape stay stable.
- FK filter plotting/service/example tests cover plot_fk_mask Agg image saving,
  compute_fk_filter_for_file on synthetic ZD HDF5 selections with optional
  bandpass preprocessing history, and examples/fk_filter_file.py bounded slice,
  FK output path, velocity-limit argument validation, reject mapping, and
  processing-step helpers without requiring real data.

Future coverage:

- Broader time-frequency workflow tests.
- FK visualization and FK-domain smoke-filter validation with real or
  quasi-real bounded DAS selections.
- Real large-file PSD/Welch performance validation.
- Real large-file FK/FK-filter performance validation.
- Reader edge cases with real small sample files.
- Additional plot types beyond waterfall and waveform.
- GUI load-file behavior with real small files.
- Real large-file GUI responsiveness and cancellation timing.
- Real third-party plugin packages using the das_view.plugins entry point group.

## Command

    python -m pytest

For cache-free runs during agent work:

    python -B -m pytest -p no:cacheprovider

## Optional dependency strategy

- h5py tests use pytest.importorskip("h5py").
- matplotlib plotting tests use pytest.importorskip("matplotlib") and the Agg backend.
- scipy-based filter tests use pytest.importorskip("scipy"). scipy is currently
  a main project dependency because basic filters and spectrogram smoke paths
  are part of the processing/analysis layers.
- Waveform plotting tests also use the Agg backend and write only to pytest tmp_path.
- GUI smoke tests use pytest.importorskip("PyQt5") and pytest.importorskip("matplotlib"). If PyQt5 is not installed, GUI creation and Qt worker tests skip cleanly while core/io/plotting and PyQt-free GUI model tests continue to run.
- GUI waveform tests avoid real file dialogs and real DAS data; they only instantiate
  widgets and test GUI-independent parser/model helpers.
- GUI spectrum tests also avoid real file dialogs and real DAS data. They check
  parser/model helpers and construction/state transitions for the minimal
  Spectrum tab; they do not automate a real asynchronous spectrum computation.
- GUI FK tests also avoid real file dialogs and real DAS data. They check
  parser/model helpers, FK worker construction/cancellation flags, and
  construction/state transitions for the minimal FK tab; they do not automate a
  real asynchronous FK service computation.
- GUI Analysis tab tests also avoid real file dialogs and real DAS data. They
  check parser/model helpers, analysis worker construction/cancellation flags,
  table-row/export mapping, and construction/state transitions for the minimal
  Analysis tab; they do not automate a real asynchronous analysis computation.
- Packaging smoke should include `python -m build` when the `build` package is
  available, plus `pip check`, `pip show hcz-das-view` when installed, and CLI
  `--help` checks for installed entry points. Build artifacts under build/ and
  dist/ are ignored and must not be committed.
- Clean-environment release smoke may use an ignored `.tmp_release_venv/`.
  `pip install -e . --no-deps` validates package metadata and editable
  installation; importing or running analysis code still requires runtime
  dependencies such as numpy and scipy. The temporary venv, build outputs,
  wheels, source archives, exe files, and generated JSON/CSV/image files must
  not be committed.
- Phase 4D GUI FK parser tests verify that transform mode allows empty
  velocity limits, velocity-filter mode requires at least one limit, invalid
  vmin/vmax values fail early, and pass/reject status text is user-facing.
- GUI automation is deferred; GUI-independent state and worker logic should still
  be testable. Phase 2D/3E/4C tests exercise QThread worker construction and soft
  cancellation flags, but do not automate real asynchronous file loading through
  a file dialog.
- Real or quasi-real file validation should use examples/validate_file.py,
  examples/plot_waveform.py, examples/spectrum_file.py,
  examples/statistics_file.py, examples/spectral_attributes_file.py,
  examples/fk_file.py, and examples/fk_filter_file.py with local data paths.
  Do not commit input data, local path lists, generated preview/waveform/FK
  images, JSON/CSV summaries, or validation output directories.
- Batch real/quasi-real validation should use examples/validate_local_samples.py
  with local_validation_paths.txt. The path file and validation output
  directories are ignored by git.
- Phase 2E validated five local real/quasi-real samples selected from two
  user-provided directories: three Puniu DAT samples and two ZD HDF5 samples.
  The validation covered metadata, preview, waveform, spectrum, Welch PSD,
  spectrogram, statistics, spectral attributes, FK transform, and FK-filter
  smoke paths. These local files remain outside automated tests; synthetic tests
  cover the reader/tooling compatibility fixes.
