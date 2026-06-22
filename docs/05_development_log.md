# Development Log

## 2026-06-20: Development baseline

### Added directories

- das_view/
- das_view/core/
- das_view/io/
- das_view/processing/
- das_view/analysis/
- das_view/plotting/
- das_view/gui/
- das_view/utils/
- docs/
- tests/
- examples/

### Added files

- AGENTS.md
- docs/01_project_baseline.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/04_data_formats.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- Initial package skeleton under das_view/
- Initial tests under tests/

### Design decisions

- Internal data shape is fixed to (n_samples, n_channels).
- Runtime code must not import old_code.
- GUI remains optional and must not be required by core modules.
- First-priority readers are ZD HDF5 and Puniu DAT.
- SEGY, SAC, and TDMS are deferred optional formats.

### Old-code use

| Source | Decision | New location | Test status | Interface/dimension changes |
|---|---|---|---|---|
| old_code/old_code1/tools/data_tools.py | 重构后复写 | das_view/io/hdf5_zd.py | Synthetic HDF5 test added, skipped if h5py unavailable | Reader returns (n_samples, n_channels) and unified metadata |
| old_code/old_code3/dy_view.py::read_puniu_dat_file | 重构后复写 | das_view/io/puniu_dat.py | Synthetic DAT test added | Header parsing isolated from GUI; reader returns unified metadata |
| old_code/old_code1/tools/analysis_tools.py | 暂未复写 | Future processing/ and analysis/ modules | Not yet added | Will require dimension and numerical tests |
| old_code/old_code1/tools/ui_tools.py | 仅参考 | Future das_view/gui/ | Not applicable | No old GUI code copied |
| old_code/old_code4/hcz_signal_analyse.py | 仅参考 | Future analysis/ modules | Not yet added | Not migrated in baseline |

### Not completed

- Full processing/filter/STFT/FK/PSD implementation.
- Functional GUI.
- Generic HDF5/TXT/CSV/NPY/NPZ readers.
- SEGY/SAC/TDMS optional readers.
- Large-file lazy loading strategy.

### Suggested next round

Implement and test the first practical reader workflow: choose either ZD HDF5 or Puniu DAT as the first end-to-end format, then add a small CLI or plotting smoke path that reads metadata and displays/downsamples a small matrix.

## 2026-06-20: Phase 1A reader workflow and non-GUI plotting

### Added files

- das_view/utils/slicing.py
- examples/read_and_plot_zd_h5.py
- tests/test_plot_waterfall.py
- pyproject.toml

### Modified files

- das_view/io/hdf5_zd.py
- das_view/io/puniu_dat.py
- das_view/plotting/waterfall.py
- tests/test_hdf5_zd_reader.py
- tests/test_puniu_dat_reader.py
- AGENTS.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/04_data_formats.md
- docs/06_testing.md
- docs/05_development_log.md

### Design decisions

- ZD HDF5 is the Phase 1A main reader.
- Reader slices are specified in internal coordinates: (time, channel).
- downsample may be an int or (time_step, channel_step).
- ZD HDF5 orientation must be inferred from raw shape plus Count/NumberOfLoci. If ambiguous or unknown, the reader raises ReaderError rather than guessing.
- plot_waterfall is GUI-free and imports Matplotlib only inside the function.
- pyproject.toml was added with minimal dependencies and optional extras.

### Old-code use

| Source | Decision | New location | Test status | Interface/dimension changes |
|---|---|---|---|---|
| old_code/old_code1/tools/data_tools.py | Rewrite after refactor | das_view/io/hdf5_zd.py | Synthetic tests cover metadata, full read, slicing, downsampling, orientation, and missing dataset errors | Reader uses unified DASData/DASMetadata and internal (n_samples, n_channels) convention |
| old_code/old_code3/dy_view.py::read_puniu_dat_file | Rewrite after refactor | das_view/io/puniu_dat.py | Synthetic tests cover header parse, read, slicing, downsampling, and length mismatch | Header parsing is isolated from GUI and reader output follows internal convention |
| old_code/old_code1/tools/ui_tools.py | Reference only | das_view/plotting/waterfall.py | Plot smoke test added | Non-GUI plotting helper only; no old GUI code copied |

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 19 passed.

### Not completed

- Real ZD HDF5 and real Puniu DAT file validation.
- Large-file lazy loading beyond slice/downsample reads.
- Full GUI.
- Preprocessing/filter/STFT/FK/PSD migration.
- Generic HDF5/TXT/CSV/NPY/NPZ readers.

### Suggested next round

Validate ZD HDF5 against a real small sample file, then add metadata formatting and a small CLI/API helper that prints metadata and creates a downsampled preview without requiring users to write Python code.

## 2026-06-20: Phase 1B metadata display and preview workflow

### Added files

- das_view/core/metadata_format.py
- das_view/io/preview.py
- examples/preview_file.py
- tests/test_metadata_format.py
- tests/test_preview_api.py

### Modified files

- das_view/core/__init__.py
- das_view/io/__init__.py
- das_view/plotting/waterfall.py
- tests/test_plot_waterfall.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- Metadata display is implemented in core without importing h5py, Matplotlib, or PyQt5.
- create_preview is the GUI-independent service for future file-open workflows.
- create_preview selects a reader through the registry, reads metadata first, normalizes requested slices, computes integer downsampling from max_samples/max_channels, then asks the reader to read only the preview selection.
- PreviewResult keeps both full-file metadata and preview DASData so GUI widgets can show source metadata while plotting a bounded preview matrix.
- plot_waterfall now rejects empty data, tolerates constant matrices, and generates a metadata-aware default title.

### Old-code use

No old_code files were copied or imported. This round used prior audit conclusions only as architectural context: GUI file opening should be separated from reader and plotting logic, and preview reads should avoid loading full DAS files.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 28 passed.

### Not completed

- Real data validation against user-provided ZD HDF5 or Puniu DAT files.
- Full PyQt5 GUI.
- GUI threading/workers for long file reads.
- Additional data formats and analysis algorithms.

### Suggested next round

Phase 1C: build the smallest PyQt5 GUI that opens a supported file, calls create_preview, displays formatted metadata, and shows the preview waterfall without adding analysis features.

## 2026-06-20: Phase 1C minimal PyQt5 preview GUI

### Added files

- das_view/gui/app.py
- examples/run_gui.py
- tests/test_gui_smoke.py

### Modified files

- das_view/gui/main_window.py
- das_view/gui/models.py
- das_view/gui/workers.py
- pyproject.toml
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- The GUI is optional and PyQt5 imports are limited to das_view/gui/ and GUI entry points.
- MainWindow contains only UI wiring: Open File, metadata display, file/preview information, Matplotlib canvas, toolbar, and status bar.
- PreviewWorker is currently a thin synchronous wrapper around create_preview. It does not implement reader details and can later be moved into QThread.
- MainWindow uses create_preview through PreviewWorker, format_metadata for metadata text, and plot_waterfall for the image.
- Current GUI loading may briefly block on large files; background loading is deferred to Phase 1D or Phase 2A.

### Old-code use

No old GUI files were copied or imported. The old PyQt5 + Matplotlib approach was used only as a design reference; the new GUI calls the Phase 1B preview service instead of reading file internals directly.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 30 passed.

### Not completed

- Real ZD HDF5/Puniu DAT GUI validation.
- Background QThread loading and cancellation.
- Complex parameter panels and analysis workflows.
- Waveform plot and additional plot types.

### Suggested next round

Phase 1D: validate the GUI with real small DAS files, improve error messages and loading robustness, then decide whether to add QThread background preview loading or move into Phase 2A IO/plotting enhancements.

## 2026-06-20: Phase 1D GUI stabilization and usage entry points

### Added files

- README.md
- examples/validate_file.py

### Modified files

- das_view/gui/main_window.py
- das_view/gui/models.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### GUI structure review

- GUI still calls create_preview through PreviewWorker and does not read HDF5/DAT internals directly.
- No PyQt5 imports were added outside das_view/gui/ or GUI entry points.
- PreviewWorker remains a thin synchronous wrapper around create_preview.
- The main remaining architectural limitation is synchronous loading; QThread migration is still deferred.

### Stability changes

- Added max_samples and max_channels controls to the main window.
- Added parse_preview_limits for GUI-safe validation before values reach create_preview.
- Improved file information display, warning display, error text, and loaded status summaries.
- On load failure, metadata and plot area are cleared so stale previews are less likely to mislead users.

### README and validation

- Added README.md with installation, testing, example, GUI, data policy, and development principle notes.
- Added examples/validate_file.py for local real/quasi-real ZD HDF5 or Puniu DAT validation without committing data.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 34 passed.

### Not completed

- Real-data validation results are not yet recorded.
- Background QThread loading and cancellation are not implemented.
- Waveform plot and additional preview views are not implemented.
- Advanced processing and analysis remain deferred.

### Suggested next round

Phase 2A: stabilize IO and preview services further, add a waveform plot path, and start building small reusable data service helpers for GUI and CLI workflows.

## 2026-06-21: Phase 2A waveform plotting and data selection service

### Added files

- das_view/io/data_service.py
- tests/test_data_service.py
- tests/test_waveform_plot.py
- examples/plot_waveform.py

### Modified files

- das_view/plotting/waveform.py
- das_view/io/__init__.py
- das_view/plotting/__init__.py
- README.md
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- read_selection is the GUI/CLI reusable service for bounded file reads. It selects
  a reader through the registry, validates internal time/channel slices, and delegates
  actual IO to the reader.
- read_trace is a waveform-oriented helper. Single-channel and arithmetic channel
  selections are read as narrow reader slices; non-contiguous selections read the
  smallest enclosing channel window and then retain requested columns in memory.
- plot_waveform is pure Matplotlib and accepts DASData only. It supports single or
  multiple internal channel indices, per-trace normalization, offset display, and
  clear channel validation errors.
- GUI waveform integration was intentionally deferred to avoid expanding the Phase 1D
  preview GUI. Future GUI work should call read_trace/read_selection plus plot_waveform.

### Old-code use

No old_code files were copied, imported, or modified. Phase 2A implemented new
service and plotting layers using the existing DASData/DASMetadata convention and
reader APIs established in earlier phases.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 46 passed.

### Not completed

- Real ZD HDF5/Puniu DAT sample validation is still pending.
- GUI waveform integration is not implemented.
- Background QThread loading and cancellation are still deferred.
- STFT/FK/PSD and preprocessing migration remain deferred.

### Suggested next round

Phase 2B: validate ZD HDF5 and Puniu DAT readers against real small samples,
integrate a lightweight GUI waveform preview if the CLI waveform path is stable,
and fix reader edge cases discovered by real data.

## 2026-06-21: Phase 2B GUI waveform integration and channel boundary tests

### Modified files

- das_view/gui/main_window.py
- das_view/gui/models.py
- das_view/io/data_service.py
- tests/test_gui_smoke.py
- tests/test_data_service.py
- README.md
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- Added a minimal Waveform tab to the optional PyQt5 GUI while preserving the
  existing Waterfall preview tab.
- GUI waveform loading calls read_trace and plot_waveform. The GUI does not read
  HDF5/DAT internals and does not implement channel slicing or downsampling logic.
- Channel input parsing is kept in das_view/gui/models.py so it is testable
  without PyQt5. Duplicate channel indices are preserved by design.
- read_trace now wraps non-integer sequence input in ReaderError for clearer
  service-boundary messages.
- Non-contiguous, reordered, and duplicate waveform selections keep requested
  order and clear dx_m to avoid implying regular spatial spacing.

### Old-code use

No old_code files were copied, imported, or modified. Phase 2B only integrated
existing Phase 2A services into the minimal GUI and tightened service tests.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 61 passed.

### Not completed

- Real-data validation using the user-provided local data directories is still
  pending and should not commit any input data or generated images.
- GUI loading is still synchronous; QThread/background loading remains deferred.
- STFT/FK/PSD and preprocessing migration remain deferred.

### Suggested next round

Phase 3A: migrate small preprocessing functions first, such as demean, detrend,
taper, and normalization; or Phase 2C: validate readers with real small samples
and fix edge cases discovered during local validation.

## 2026-06-21: Phase 2C local validation tools and reader edge-case checks

### Added files

- examples/validate_local_samples.py
- tests/test_validation_scripts.py

### Modified files

- .gitignore
- README.md
- das_view/io/hdf5_zd.py
- das_view/io/puniu_dat.py
- das_view/io/preview.py
- examples/validate_file.py
- tests/test_hdf5_zd_reader.py
- tests/test_puniu_dat_reader.py
- docs/04_data_formats.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions and fixes

- local_validation_paths.txt, validation_outputs/, outputs/, DAS data files, and
  generated images are ignored by git.
- validate_file.py now reports metadata, raw_shape/orientation when available,
  preview shape/downsample/warnings, and optional waveform output.
- validate_local_samples.py reads ignored local path lists, skips comments and
  blank lines, and batch-validates files without saving outputs by default.
- ZD HDF5 attribute handling now accepts numpy scalar attributes and decodes
  UTF-8 byte attributes where possible.
- ZD HDF5, Puniu DAT, and preview paths now surface empty selection errors as
  clear ReaderError messages.
- Puniu DAT header parsing now gives clearer errors for invalid/non-finite
  numeric header values.

### Real/quasi-real validation result

- local_validation_paths.txt was not present in the project root during this run.
- The no-path-list validation smoke path was executed successfully and exited
  with a friendly message.
- No real data paths, DAS data files, or generated images were committed.

### Old-code use

No old_code files were copied, imported, or modified. Phase 2C only hardened
the new reader/service layer and local validation tooling.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 72 passed.

### Not completed

- Reader behavior has not yet been verified against real local DAS samples.
- GUI loading remains synchronous; QThread/cancel/progress are deferred.
- Preprocessing and STFT/FK/PSD remain deferred.

### Suggested next round

Phase 3A: migrate small preprocessing functions first, such as demean, detrend,
taper, and normalization; or Phase 2D: add QThread background loading, cancel,
and progress feedback for the GUI.

## 2026-06-21: Phase 3A basic preprocessing functions and service

### Added files

- das_view/processing/service.py
- examples/preprocess_file.py
- tests/test_preprocess.py
- tests/test_preprocessing_service.py
- tests/test_preprocess_example.py

### Modified files

- das_view/processing/preprocess.py
- das_view/processing/__init__.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- Implemented numpy-only preprocessing functions for arrays: demean,
  detrend_linear, taper, normalize, standardize, and clip.
- The default axis=0 follows the project convention data.shape ==
  (n_samples, n_channels), so time-axis operations are per channel by default.
- Functions return new float arrays and do not modify input arrays in place.
- Finite statistics ignore NaN/Inf values; NaN/Inf values are preserved at their
  positions where practical.
- apply_preprocess applies explicit ordered steps to DASData, returns a new
  DASData, preserves metadata, and appends preprocessing_history in
  metadata.extra_attrs.
- examples/preprocess_file.py applies preprocessing only to bounded preview data
  from create_preview and saves a processed waterfall image. It does not export
  processed full-size DAS arrays.

### Old-code migration judgment

| Old source | Function/topic | Judgment | New location | Tests | Interface or dimension changes |
|---|---|---|---|---|---|
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | demeaning | 重构后复写 | das_view/processing/preprocess.py::demean | tests/test_preprocess.py | Adds axis; default axis=0 is per-channel time mean. |
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | detrending/delineaaar_trend | 仅参考 | das_view/processing/preprocess.py::detrend_linear | tests/test_preprocess.py | Rewritten without scipy and with explicit axis semantics. |
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | taper/taper_filter | 重构后复写 | das_view/processing/preprocess.py::taper | tests/test_preprocess.py | Uses ratio instead of taper_point and supports Hann taper along an axis. |
| old_code/old_code4/hcz_signal_preprocess.py | normalization | 重构后复写 | das_view/processing/preprocess.py::normalize | tests/test_preprocess.py | Adds maxabs/minmax modes, axis, eps, and all-zero safety. |
| old_code/old_code4/hcz_signal_preprocess.py | standardization | 重构后复写 | das_view/processing/preprocess.py::standardize | tests/test_preprocess.py | Adds axis and eps; constant finite slices become zero. |
| Reviewed old files | clipping | 新实现 | das_view/processing/preprocess.py::clip | tests/test_preprocess.py | Adds explicit min/max and percentile clipping over finite values. |
| old_code/old_code4/hcz_signal_preprocess.py | data_preprocess workflow | 废弃 | das_view/processing/service.py::apply_preprocess | tests/test_preprocessing_service.py | Old workflow is pass; new service records ordered processing history. |

No old_code files were imported, copied directly, or modified.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 97 passed.

### Not completed

- Bandpass/highpass/lowpass/notch filters are not implemented.
- STFT/FK/PSD remain deferred.
- GUI preprocessing panel is not implemented.
- Full-size preprocessing export is not implemented.

### Suggested next round

Phase 3B: migrate basic filter functions, starting with bandpass, highpass,
lowpass, and notch; or Phase 2D: add QThread background loading, cancel, and
progress feedback for the GUI.

## 2026-06-21: Phase 3B basic filtering functions and service integration

### Added files

- examples/filter_file.py
- tests/test_filters.py
- tests/test_filter_service.py
- tests/test_filter_example.py

### Modified files

- pyproject.toml
- das_view/processing/filters.py
- das_view/processing/service.py
- das_view/processing/__init__.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Dependency decision

- scipy was added as a main dependency because lowpass/highpass/bandpass/
  bandstop/notch are now core processing-layer functions.
- Tests still use pytest.importorskip("scipy") so an unusual environment without
  scipy can skip filter-specific tests cleanly, but normal installs should have
  scipy available.

### Design decisions

- Implemented scipy.signal based lowpass, highpass, bandpass, bandstop, and
  notch filters in das_view/processing/filters.py.
- Butterworth filters use scipy.signal.butter(..., output="sos") plus
  sosfiltfilt for zero_phase=True and sosfilt for zero_phase=False.
- notch uses scipy.signal.iirnotch followed by tf2sos so it shares the same SOS
  application path.
- The default axis=0 follows the DAS convention data.shape ==
  (n_samples, n_channels), so each channel is filtered independently along time.
- Filters copy input arrays, reject NaN/Inf inputs, validate frequency/order/
  quality/axis parameters, and raise a project-level ValueError for too-short
  zero-phase inputs.
- apply_preprocess now supports lowpass, highpass, bandpass, bandstop, and
  notch steps while preserving existing Phase 3A preprocessing behavior.
- examples/filter_file.py applies filters only to bounded preview data from
  create_preview and saves a filtered waterfall. It does not export processed
  full-size DAS arrays.

### Old-code migration judgment

| Old source | Function/topic | Judgment | New location | Tests | Interface or dimension changes |
|---|---|---|---|---|---|
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | lowpass | Reimplemented after refactor | das_view/processing/filters.py::lowpass | tests/test_filters.py | Uses sample_rate_hz/cutoff_hz, default axis=0, SOS, zero_phase option. |
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | highpass | Reimplemented after refactor | das_view/processing/filters.py::highpass | tests/test_filters.py | Same conventions as lowpass; validates cutoff < Nyquist. |
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | bandpass | Reimplemented after refactor | das_view/processing/filters.py::bandpass | tests/test_filters.py | Uses freqmin_hz/freqmax_hz and explicit DAS axis semantics. |
| old_code/old_code1/tools/analysis_tools.py | bandstop | Reimplemented after refactor | das_view/processing/filters.py::bandstop | tests/test_filters.py | Rewritten with SOS and validation. |
| old_code/old_code1/tools/analysis_tools.py; old_code/old_code4/hcz_signal_preprocess.py | notch | Reference only | das_view/processing/filters.py::notch | tests/test_filters.py | Reimplemented with iirnotch + tf2sos; validates notch_hz and quality. |
| old_code/old_code1/tools/analysis_tools.py | taper_filter | Already covered by Phase 3A | das_view/processing/preprocess.py::taper | tests/test_preprocess.py | Kept as preprocessing, not filtering. |

No old_code files were imported, copied directly, or modified.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 117 passed.

### Not completed

- STFT/FK/PSD are not implemented.
- GUI filter parameter panel is not implemented.
- Full-size filtered DAS export is not implemented.
- Real large-file filtering performance has not been validated.

### Suggested next round

Phase 3C: add basic amplitude spectrum, power spectrum, and spectrogram smoke
paths; or Phase 2D: add QThread background loading, cancel, and progress
feedback for the GUI.

## 2026-06-21: Phase 3C basic spectrum analysis and plotting

### Added files

- examples/spectrum_file.py
- tests/test_spectrum_analysis.py
- tests/test_spectrum_plotting.py
- tests/test_spectrum_example.py

### Modified files

- das_view/analysis/spectrum.py
- das_view/analysis/__init__.py
- das_view/plotting/spectra.py
- das_view/plotting/__init__.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- Implemented SpectrumResult and SpectrogramResult containers in the analysis layer.
- amplitude_spectrum and power_spectrum accept numpy arrays or DASData. DASData
  input can supply sample_rate_hz from metadata.
- The default axis=0 follows data.shape == (n_samples, n_channels), so frequency
  analysis is along time by default.
- Spectrum helpers support channel selection and optional channel-average spectra
  for 2-D DAS arrays.
- single_channel_spectrogram uses scipy.signal.spectrogram for a bounded,
  single-channel smoke path only. It is not a full STFT analysis platform.
- plot_spectrum and plot_spectrogram are Matplotlib-only helpers in the plotting
  layer and do not depend on PyQt5.
- examples/spectrum_file.py reads a bounded trace through read_trace, optionally
  applies a bandpass step through apply_preprocess, and saves an amplitude,
  power, or spectrogram image. It does not export full-size data.

### Old-code migration judgment

| Old source | Function/topic | Judgment | New location | Tests | Interface or dimension changes |
|---|---|---|---|---|---|
| old_code/old_code1/tools/analysis_tools.py::get_fp; old_code/old_code4/hcz_signal_analyse.py::plot_FS | amplitude spectrum | Reimplemented after refactor | das_view/analysis/spectrum.py::amplitude_spectrum | tests/test_spectrum_analysis.py | Adds DASData input, sample_rate_hz validation, default axis=0, nfft validation, channel selection, and channel averaging. |
| old_code/old_code1/tools/analysis_tools.py::psd_periodogram/psd_welch | power spectrum idea | Reference only | das_view/analysis/spectrum.py::power_spectrum | tests/test_spectrum_analysis.py | Implements simple FFT-derived power spectrum; full PSD/Welch remains deferred. |
| old_code/old_code1/tools/analysis_tools.py::get_tfp/tfp_analysis; old_code/old_code4/hcz_signal_analyse.py::plot_TF | spectrogram/STFT idea | Reimplemented after refactor | das_view/analysis/spectrum.py::single_channel_spectrogram | tests/test_spectrum_analysis.py | Uses scipy.signal.spectrogram for one selected channel; no GUI plotting coupling. |
| old_code/old_code4/hcz_signal_analyse.py::plot_analysis | combined analysis plot | Reference only | das_view/plotting/spectra.py | tests/test_spectrum_plotting.py | Plotting separated from analysis results. |
| old_code historical advanced FK/F-J/MASW and advanced PSD sections | advanced analysis | Deferred | Not implemented | Not applicable | Historical audit only; not in current main roadmap. |

No old_code files were imported, copied directly, or modified.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 134 passed.

### Not completed

- Full STFT workflows are not implemented.
- PSD/Welch service helpers are not implemented.
- FK visualization and FK-domain smoke filtering are not yet implemented.
- GUI spectrum panel is not implemented.
- Real large-file spectrum performance has not been validated.

### Suggested next round

Phase 3D: add PSD/Welch and spectrum service helpers; or Phase 2D: add QThread
background loading, cancel, and progress feedback for the GUI.

## 2026-06-21: Phase 3D PSD/Welch analysis and spectrum service

### Added files

- das_view/analysis/service.py
- tests/test_spectrum_service.py

### Modified files

- das_view/analysis/spectrum.py
- das_view/analysis/__init__.py
- das_view/plotting/spectra.py
- das_view/plotting/__init__.py
- examples/spectrum_file.py
- tests/test_spectrum_analysis.py
- tests/test_spectrum_plotting.py
- tests/test_spectrum_example.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md

### Design decisions

- Added PSDResult plus periodogram_psd and welch_psd in the analysis layer.
- PSD functions accept numpy arrays or DASData. DASData input can provide
  sample_rate_hz from metadata.
- The default axis=0 follows data.shape == (n_samples, n_channels), so PSD is
  estimated along time for each channel by default.
- PSD functions support channel selection and optional channel averaging for
  2-D DAS arrays.
- NaN/Inf inputs are rejected to avoid silently contaminated spectral estimates.
- plot_psd is a Matplotlib-only plotting helper and supports optional dB display
  with safe handling for zero or tiny values.
- das_view/analysis/service.py provides bounded file-level helpers for spectrum,
  PSD, and spectrogram workflows. It reads traces through read_trace and can
  apply preprocessing/filter steps through apply_preprocess before analysis.
- examples/spectrum_file.py now uses the analysis service and supports
  amplitude, power, periodogram PSD, Welch PSD, dB PSD display, spectrogram, and
  optional bandpass preprocessing.

### Old-code migration judgment

| Old source | Function/topic | Judgment | New location | Tests | Interface or dimension changes |
|---|---|---|---|---|---|
| old_code/old_code1/tools/analysis_tools.py::psd_periodogram | Periodogram PSD | Reimplemented after refactor | das_view/analysis/spectrum.py::periodogram_psd | tests/test_spectrum_analysis.py | Uses sample_rate_hz, default axis=0, channel selection/averaging, and explicit nfft/scaling validation. |
| old_code/old_code1/tools/analysis_tools.py::psd_welch | Welch PSD | Reimplemented after refactor | das_view/analysis/spectrum.py::welch_psd | tests/test_spectrum_analysis.py | Uses nperseg/noverlap/nfft validation and DASData metadata sample-rate support. |
| old_code/old_code4/hcz_signal_analyse.py plotting workflows | PSD/spectrum plotting ideas | Reference only | das_view/plotting/spectra.py::plot_psd | tests/test_spectrum_plotting.py | Plotting is separated from analysis and remains PyQt5-independent. |
| Old combined scripts/workflows | File-level spectrum workflow | New implementation | das_view/analysis/service.py | tests/test_spectrum_service.py | Uses read_trace and apply_preprocess services instead of embedding IO/filter logic in examples. |
| old_code historical advanced FK/F-J/MASW sections | Advanced analysis | Deferred | Not implemented | Not applicable | Historical audit only; not in current main roadmap. |

No old_code files were imported, copied directly, or modified.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 150 passed.

### Not completed

- FK visualization and FK-domain smoke filtering are not yet implemented.
- GUI spectrum panel is not implemented.
- Full STFT workflow is not implemented.
- Full-size spectral analysis/export workflow is not implemented.
- Real large-file PSD/Welch performance has not been validated.

### Suggested next round

Phase 3E: add a minimal GUI spectrum panel for amplitude/PSD/spectrogram; or
Phase 2D: add QThread background loading, cancel, and progress feedback for the
GUI; or Phase 4A: FK transform smoke path.

## 2026-06-21: Phase 2D GUI QThread background loading

### Modified files

- das_view/gui/workers.py
- das_view/gui/models.py
- das_view/gui/main_window.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Kept PreviewWorker as a no-Qt callable wrapper around create_preview and added
  WaveformWorker as a no-Qt callable wrapper around read_trace.
- Added QtPreviewWorker and QtWaveformWorker as QObject workers intended to run
  in QThread. They emit started, progress, finished, failed, and cancelled
  signals.
- MainWindow now runs preview and waveform data reads in a single active
  background task at a time. Open/preview controls and waveform controls are
  disabled while a task is running.
- Added a Cancel button plus an indeterminate/busy QProgressBar for background
  work. The progress signal carries stage text and simple stage values, but the
  GUI displays busy mode because the current readers do not provide true
  byte/sample-level progress.
- Cancellation is soft/cooperative. It cannot forcefully interrupt synchronous
  create_preview or read_trace calls already inside a reader, but it sets a
  cancellation flag and prevents cancelled or stale task results from being
  applied to the GUI.
- Matplotlib drawing remains on the main thread. Workers return service results;
  MainWindow applies the latest non-cancelled result and then calls
  plot_waterfall or plot_waveform.
- Task cleanup is connected to worker completion/failure/cancellation and QThread
  finished signals so worker/thread objects are released and controls are
  restored safely.
- GUI state helpers such as task_control_state, format_task_status, and
  should_apply_task_result live in das_view/gui/models.py so they can be tested
  without PyQt5.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for this phase. This
round only changed the new GUI worker/state wiring around existing services.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest tests/test_gui_smoke.py -p no:cacheprovider
- Result: 22 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 157 passed.

### Not completed

- Hard cancellation of lower-level synchronous reader IO is not implemented.
- Real large-file GUI responsiveness and cancellation timing have not been
  validated with production samples.
- GUI preprocessing, filter, and spectrum panels are not implemented.
- FK visualization, full time-frequency workflows, and complete
  processing/analysis export remain deferred.

### Suggested next round

Phase 3E: add a minimal GUI spectrum panel for amplitude/PSD/spectrogram after
the QThread loading foundation; or Phase 2E: real sample validation if local
real data paths are provided.

## 2026-06-21: Phase 3E minimal GUI spectrum panel

### Modified files

- das_view/gui/workers.py
- das_view/gui/models.py
- das_view/gui/main_window.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added a minimal Spectrum tab to MainWindow with a single-channel input,
  analysis type selector, optional nfft/nperseg/noverlap text fields, a PSD dB
  checkbox, Run spectrum button, info area, and Matplotlib canvas.
- Added SpectrumWorker as a no-Qt callable wrapper around the existing analysis
  service layer, and QtSpectrumWorker as a QObject worker for QThread execution.
- SpectrumWorker calls only compute_spectrum_for_file, compute_psd_for_file, or
  compute_spectrogram_for_file. No new frequency-domain algorithms were added in
  this phase.
- Matplotlib rendering remains in the main GUI thread. The worker returns a
  SpectrumServiceResult; MainWindow then calls plot_spectrum, plot_psd, or
  plot_spectrogram for the latest non-cancelled task.
- Spectrum tasks reuse the Phase 2D single-active-task model, busy progress bar,
  Cancel button, stale-result guard, and thread cleanup path.
- Cancellation remains soft/cooperative. It cannot forcibly interrupt
  synchronous reader IO or analysis calls already in progress, but cancelled or
  stale spectrum results are not applied to the GUI.
- Added PyQt-free GUI model helpers for optional integer parsing, spectrum
  request validation, analysis type normalization, and display status formatting.
  The PSD dB flag is preserved for plotting only and is not passed as an
  analysis-service computation parameter.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for this phase. This
round only connected the new GUI to existing das_view.analysis.service and
das_view.plotting.spectra APIs.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest tests/test_gui_smoke.py -p no:cacheprovider
- Result: 31 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 166 passed.

### Not completed

- GUI preprocessing and filter panels are not implemented.
- FK visualization, FK-domain smoke filtering, and a complete time-frequency
  workflow are not implemented.
- Full processing/analysis export is not implemented.
- Real large-file spectrum performance and cancellation timing have not been
  validated with production samples.

### Suggested next round

Phase 2E: real sample validation if local real data paths are provided; or
Phase 4A: FK transform smoke path.

## 2026-06-21: Phase 4A FK transform smoke path

### Added files

- das_view/analysis/fk.py
- das_view/plotting/fk.py
- examples/fk_file.py
- tests/test_fk_analysis.py
- tests/test_fk_plotting.py
- tests/test_fk_service.py
- tests/test_fk_example.py

### Modified files

- das_view/analysis/service.py
- das_view/analysis/__init__.py
- das_view/plotting/__init__.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added FKResult and fk_transform as GUI-independent analysis primitives.
- fk_transform accepts numpy arrays or DASData. DASData input can supply
  metadata.sample_rate_hz and metadata.dx_m.
- The default axes follow the project convention: data.shape ==
  (n_samples, n_channels), axis=0 is time, and axis=1 is the spatial/channel
  axis.
- The FK transform uses a one-sided real FFT along time and a full complex FFT
  along space, with optional wavenumber fftshift. Output values are shaped as
  (n_frequencies, n_wavenumbers).
- Supported FK outputs are amplitude and power. Invalid sample rate, dx, nfft,
  axis, dimensionality, NaN/Inf input, and too-short selections raise clear
  ValueError messages.
- Added compute_fk_for_file to the analysis service. It reads bounded 2-D
  selections through read_selection, optionally applies apply_preprocess, and
  then calls fk_transform. It does not inspect concrete reader internals.
- Added plot_fk as a Matplotlib-only helper. Plotting remains outside the
  analysis worker/service layer and does not depend on PyQt5.
- Added examples/fk_file.py for bounded FK image generation. It defaults to a
  4096 sample by 512 channel selection, supports amplitude/power and dB display,
  and can reuse the existing bandpass processing step.

### Old-code migration judgment

Reviewed read-only:

- old_code/old_code1/tools/analysis_tools.py
- old_code/old_code4/hcz_signal_analyse.py

old_code/old_code1/tools/analysis_tools.py contains useful FK transform ideas
using rfft2/rfftfreq/fftfreq/fftshift, but it transposes data internally, uses
older (channel, time) assumptions, and is coupled to FK filtering/fan-mask
workflows. Phase 4A reimplemented only the basic transform smoke path for the
new (n_samples, n_channels) interface. FK filter, velocity fan filter, and
inverse FK filtering remain deferred. Historical topic-specific old-code
sections are not in the current main roadmap. No old_code files were copied,
imported, or modified.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_fk_analysis.py tests\test_fk_plotting.py tests\test_fk_service.py tests\test_fk_example.py
- Result: 24 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 190 passed.

### Not completed

- FK filter is not implemented.
- Velocity fan filtering is not implemented.
- Specialized inversion or picking workflows are not in the current main
  roadmap.
- GUI FK panel is not implemented.
- Real large-file FK performance has not been validated.
- Full processing/analysis export is not implemented.

### Suggested next round

Phase 4B: add an FK filter smoke path; or Phase 2E: real sample validation if
local_validation_paths.txt with real/quasi-real DAS sample paths is provided.

## 2026-06-21: Phase 4B FK velocity filter smoke path

### Goal

Implement the smallest end-to-end FK filter workflow: construct an FK-domain
velocity fan mask, apply it to a phase-preserving complex FK spectrum, invert
back to the time-channel domain, expose a file-level service and CLI example,
and keep the implementation independent from GUI code.

### Added files

- das_view/analysis/fk_filter.py
- examples/fk_filter_file.py
- tests/test_fk_filter_analysis.py
- tests/test_fk_filter_service.py
- tests/test_fk_filter_example.py

### Modified files

- das_view/analysis/service.py
- das_view/analysis/__init__.py
- das_view/plotting/fk.py
- das_view/plotting/__init__.py
- tests/test_fk_plotting.py
- README.md
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added FKFilterResult, velocity_fan_mask, apply_fk_mask, and
  fk_velocity_filter in das_view/analysis/fk_filter.py.
- velocity_fan_mask returns a mask shaped as (n_frequencies, n_wavenumbers).
  Apparent velocity is approximated as abs(f / k). k=0 is handled explicitly
  via include_zero_wavenumber to avoid divide-by-zero failures.
- apply_fk_mask recomputes the complex FK spectrum, multiplies by the shifted
  mask while preserving phase, applies inverse space/time FFTs, and crops the
  result back to the original data shape.
- fk_velocity_filter accepts numpy arrays or DASData. DASData input can supply
  metadata.sample_rate_hz and metadata.dx_m.
- Added compute_fk_filter_for_file to the analysis service. It reads bounded
  selections through read_selection, optionally applies apply_preprocess, then
  calls fk_velocity_filter. The service does not inspect concrete reader
  internals.
- Added examples/fk_filter_file.py for bounded filtered waterfall output and
  optional filtered FK image output. It defaults to 4096 samples by 512 channels.
- Added plot_fk_mask as a small Matplotlib-only helper for smoke validation.
- The implementation is intentionally not an engineering-grade FK denoising
  workflow. It has no tapered fan edges, interactive velocity editor, or GUI FK
  panel. Specialized inversion or picking workflows are not in the current main
  roadmap.

### Old-code migration judgment

Reviewed read-only:

- old_code/old_code1/tools/analysis_tools.py
- old_code/old_code4/hcz_signal_analyse.py

old_code/old_code1/tools/analysis_tools.py contains fk_fan_mask and fk_filter
concepts using fan masks and inverse real FFTs. Phase 4B did not copy that code
because it transposes data internally, assumes older (channel, time) orientation,
and combines padding/tapering/decomposition options outside the new service
boundary. The new implementation reuses only the high-level idea and rewrites
it for (n_samples, n_channels), axis=0 time, axis=1 space. No old_code files
were copied, imported, or modified.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_fk_filter_analysis.py tests\test_fk_filter_service.py tests\test_fk_filter_example.py tests\test_fk_plotting.py
- Result: 30 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 216 passed.

### Not completed

- Engineering-grade FK filter is not implemented.
- GUI FK panel is not implemented.
- Specialized inversion or picking workflows are not in the current main
  roadmap.
- Real large-file FK filter performance has not been validated.
- Full processing/analysis export is not implemented.

### Suggested next round

Phase 2E: real sample validation if local_validation_paths.txt with
real/quasi-real DAS sample paths is provided; otherwise Phase 4C: GUI FK panel
smoke path.

## 2026-06-21: Phase 4C GUI FK panel smoke path

### Goal

Add the smallest GUI entry point for existing FK transform and FK velocity
filter services. Keep FK reading/calculation in QThread workers, keep
Matplotlib drawing in the main GUI thread, and do not add new FK algorithms.

### Modified files

- das_view/gui/main_window.py
- das_view/gui/workers.py
- das_view/gui/models.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added a minimal FK tab with time/channel selection controls, FK mode, output
  mode, dB display flag, vmin/vmax velocity parameters, pass-inside/reject
  behavior, Run FK button, status text, and Matplotlib canvas.
- Added FKAnalysisRequest and PyQt-free parser/status helpers in
  das_view/gui/models.py. Empty start/stop fields remain None in the request,
  while bounded_time_slice and bounded_channel_slice apply safe default limits
  before service calls.
- Added FKWorker and QtFKWorker in das_view/gui/workers.py. The callable worker
  calls only compute_fk_for_file or compute_fk_filter_for_file. The Qt worker
  emits started/progress/finished/failed/cancelled and supports the same soft
  cancellation model as preview, waveform, and spectrum workers.
- MainWindow applies FK transform results by calling plot_fk in the main thread.
  FK velocity-filter results are displayed as a filtered waterfall plus the
  velocity fan mask using plot_waterfall and plot_fk_mask in the main thread.
- Opening a new file clears the old FK panel. Cancelled or stale FK results are
  not applied.
- The GUI still does not inspect concrete HDF5/DAT paths and does not implement
  FK transform or FK filter algorithms.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_gui_smoke.py
- Result: 42 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_fk_service.py tests\test_fk_filter_service.py tests\test_fk_plotting.py tests\test_gui_smoke.py
- Result: 52 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 227 passed.

### Not completed

- Engineering-grade FK filter is not implemented.
- Velocity fan polish, mask limits, and safer defaults remain future work.
- Specialized inversion or picking workflows are not in the current main
  roadmap.
- Real large-file FK GUI performance has not been validated.
- Full processing/analysis export is not implemented.

### Suggested next round

Phase 2E: real sample validation if local_validation_paths.txt with
real/quasi-real DAS sample paths is provided; otherwise Phase 4D: FK polish /
mask limits / safer defaults.

## 2026-06-22: Phase 4D FK polish / mask limits / safer defaults

### Goal

Tighten FK transform / FK velocity-filter smoke-path guardrails without adding
new FK algorithms. Focus on velocity-limit defaults, pass/reject semantics,
GUI/CLI error messages, and regression tests.

### Modified files

- README.md
- das_view/analysis/fk_filter.py
- das_view/gui/main_window.py
- das_view/gui/models.py
- examples/fk_filter_file.py
- tests/test_fk_filter_analysis.py
- tests/test_fk_filter_example.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- FK velocity filtering now requires at least one of vmin_mps or vmax_mps.
  Silent all-pass behavior is avoided because it can make a filter command look
  successful while doing no meaningful velocity selection.
- A vmin-only mask means apparent velocity >= vmin_mps. A vmax-only mask means
  apparent velocity <= vmax_mps. Providing both requires vmin_mps < vmax_mps.
- pass_inside=True means pass the selected velocity range; pass_inside=False
  means reject the selected velocity range.
- k=0 is still handled explicitly via include_zero_wavenumber and never divides
  by zero. f=0 remains a finite row in the velocity mask.
- GUI FK transform mode still allows empty vmin/vmax because velocity limits do
  not apply to a plain transform. GUI FK velocity-filter mode fails early with
  a clear user-facing error when both limits are empty.
- examples/fk_filter_file.py now validates --vmin/--vmax before reading data
  and prints pass/reject action, selected limits, selection, and output path.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_fk_filter_analysis.py tests\test_fk_filter_service.py tests\test_fk_filter_example.py tests\test_gui_smoke.py
- Result: 77 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 238 passed.

### Not completed

- Engineering-grade FK filter is not implemented.
- GUI preprocessing/filter panel is not implemented.
- Specialized inversion or picking workflows are not in the current main
  roadmap.
- Real large-file FK performance has not been validated.
- Full processing/analysis export is not implemented.

### Suggested next round

Phase 2E: real sample validation if local_validation_paths.txt with
real/quasi-real DAS sample paths is provided; otherwise Phase 5A: analysis
feature statistics.

## 2026-06-22: Phase R1 project target realignment

### Goal

Realign the project target around a general DAS Viewer / DAS Analysis package
and remove misleading current-roadmap language that implied a specialized
surface-wave analysis direction.

### Modified files

- README.md
- AGENTS.md
- das_view/analysis/fk_filter.py
- tests/test_gui_smoke.py
- docs/02_architecture.md
- docs/03_old_code_review.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- The project target is now stated as DAS file reading, metadata display,
  time-channel visualization, waveform/spectrum/spectrogram/FK visualization,
  preprocessing, filtering, feature extraction, GUI interaction, testing,
  documentation, packaging, and long-term maintainability.
- F-J / MASW / dispersion picking / surface-wave imaging are explicitly removed
  from the current main roadmap. If needed later, they should be separate
  plugins or topic-specific extensions.
- FK remains in scope as DAS 2D wavefield visualization and FK-domain smoke
  filtering.
- The next mainline development direction is DAS analysis: statistics, spectral
  attributes, envelope/STA-LTA, event candidates, ROI/annotation/export, GUI
  analysis panels, packaging, and plugin extension boundaries.
- This round did not add algorithms, readers, GUI features, or numerical logic.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
Historical old-code audit entries were clarified as not in the current main
roadmap.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 238 passed.

### Not completed

- Real sample validation is not completed.
- Statistics and DAS attribute analysis are not implemented.
- Band energy and spectral attributes are not implemented.
- Envelope / STA-LTA / event candidate detection is not implemented.
- ROI / annotation / export workflows are not implemented.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.

### Suggested next round

Phase 2E: real sample validation if real/quasi-real data paths are provided.
Otherwise, Phase 5A: Analysis feature statistics.

## 2026-06-22: Phase 5A Analysis feature statistics

### Goal

Add basic DAS statistics analysis as the first post-realignment analysis
capability. Keep the implementation GUI-independent, reader-independent through
the data service, and bounded by default for file-level workflows.

### Added files

- das_view/analysis/statistics.py
- examples/statistics_file.py
- tests/test_statistics_analysis.py
- tests/test_statistics_service.py
- tests/test_statistics_example.py

### Modified files

- README.md
- das_view/analysis/__init__.py
- das_view/analysis/service.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added FiniteSummary and StatisticsResult containers.
- basic_statistics accepts numpy arrays or DASData and supports axis=None
  global summaries, axis=0 time-axis reductions with one output per channel,
  and axis=1 channel-axis reductions with one output per time sample.
- Statistics include count, finite_count, nan_count, posinf_count,
  neginf_count, mean, std, min, max, median, percentiles, RMS, abs_mean,
  peak-to-peak, and energy.
- nan_policy="omit" computes statistics from finite values and records
  non-finite counts. nan_policy="raise" rejects NaN/Inf inputs.
- All-nonfinite inputs return stable NaN-valued summary statistics with energy
  equal to 0.0 rather than crashing inside reductions.
- compute_statistics_for_file reads bounded selections through read_selection,
  optionally applies apply_preprocess, and then calls basic_statistics. It does
  not inspect HDF5/DAT internal paths and does not depend on GUI code.
- examples/statistics_file.py provides bounded CLI statistics with JSON output
  for all modes and global CSV output for scalar summaries.
- No GUI analysis panel, event detection, band energy, FK expansion, reader
  changes, or plotting additions were included in this phase.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
Phase 5A was implemented directly against the new DASData, data service, and
analysis service interfaces.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_statistics_analysis.py tests\test_statistics_service.py tests\test_statistics_example.py
- Result: 23 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 261 passed.

### Not completed

- Real sample validation is not completed.
- Band energy and spectral attributes are not implemented.
- Envelope / STA-LTA / event candidate detection is not implemented.
- ROI / annotation / export workflows are not implemented.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.

### Suggested next round

Phase 2E: real sample validation if real/quasi-real data paths are provided.
Otherwise, Phase 5B: Band energy and spectral attributes.

## 2026-06-22: Phase 5B Band energy and spectral attributes

### Goal

Add frequency-band energy and spectral attribute analysis for general DAS
signal/wavefield inspection. Keep the implementation GUI-independent,
reader-independent through the data service, and bounded by default for
file-level workflows.

### Added files

- das_view/analysis/spectral_attributes.py
- examples/spectral_attributes_file.py
- tests/test_spectral_attributes_analysis.py
- tests/test_spectral_attributes_service.py
- tests/test_spectral_attributes_example.py

### Modified files

- README.md
- das_view/analysis/__init__.py
- das_view/analysis/service.py
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Design decisions

- Added BandEnergyResult and SpectralAttributesResult containers.
- band_energy accepts numpy arrays or DASData, uses DAS axis=0 by default,
  supports per-channel and average-channel outputs, and reports band_energy,
  band_power, total_energy, band_energy_ratio, frequencies_hz, sample_rate_hz,
  axis, nfft, and scaling.
- spectral_attributes accepts numpy arrays or DASData and reports dominant
  frequency, peak power, spectral centroid, spectral bandwidth, spectral
  rolloff, low/high analysis frequencies, and total energy.
- Frequency bands must satisfy 0 <= fmin < fmax <= Nyquist and include at least
  one FFT frequency bin. frequency_range and rolloff values are validated
  explicitly.
- nan_policy="raise" rejects NaN/Inf inputs. nan_policy="omit" replaces
  non-finite samples with zero before FFT-based attribute computation.
- compute_band_energy_for_file and compute_spectral_attributes_for_file read
  bounded selections through read_selection, optionally call apply_preprocess,
  then call the spectral attribute analysis helpers. They do not inspect
  HDF5/DAT internals and do not depend on GUI code.
- examples/spectral_attributes_file.py provides bounded CLI band-energy or
  spectral-attribute workflows with JSON and CSV output.
- No GUI analysis panel, event detection, FK expansion, reader changes, or
  plotting additions were included in this phase.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
Phase 5B was implemented directly against the new DASData, data service, and
analysis service interfaces.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_spectral_attributes_analysis.py tests\test_spectral_attributes_service.py tests\test_spectral_attributes_example.py
- Result: 32 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 293 passed.

### Not completed

- Real sample validation is not completed.
- Envelope / STA-LTA / event candidate detection is not implemented.
- ROI / annotation / export workflows are not implemented.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.

### Suggested next round

Phase 2E: real sample validation if real/quasi-real data paths are provided.
Otherwise, Phase 5C: Envelope / STA-LTA / event candidate detection.

## 2026-06-22: Phase 2E real sample validation

### Goal

Validate existing DAS Viewer / DAS Analysis workflows on user-provided local
real/quasi-real sample directories without committing input data, generated
outputs, local path lists, or local absolute paths.

### Local validation scope

- Local validation directories provided: 2.
- Candidate files discovered: 33 total.
- Candidate formats discovered: 31 DAT files and 2 HDF5 files.
- Selected validation samples: 5 total, with at most 3 DAT and 2 HDF5 samples.
- Formats observed in selected samples: Puniu DAT and ZD HDF5.
- Batch validation result after reader/tooling fixes: 5 passed, 0 failed.

### Anonymized sample summary

| Sample | Extension | Size | Reader | n_samples | n_channels | sample_rate_hz | dt_s | dx_m | duration_s | Preview shape | Downsample | Warnings | Deep smoke status |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|
| sample_001 | .dat | medium | puniu_dat | 15000 | 113 | 250 | 0.004 | 1.0 | 60 | (1875, 113) | (8, 1) | 1 | passed |
| sample_002 | .dat | medium | puniu_dat | 15000 | 113 | 250 | 0.004 | 1.0 | 60 | (1875, 113) | (8, 1) | 1 | passed |
| sample_003 | .dat | medium | puniu_dat | 15000 | 113 | 250 | 0.004 | 1.0 | 60 | (1875, 113) | (8, 1) | 1 | passed |
| sample_004 | .h5 | large | zd_hdf5 | 60000 | 1027 | 1000 | 0.001 | about 1.0225 | 60 | (2000, 343) | (30, 3) | 1 | passed |
| sample_005 | .h5 | large | zd_hdf5 | 60000 | 1027 | 1000 | 0.001 | about 1.0225 | 60 | (2000, 343) | (30, 3) | 1 | passed |

For each selected sample, bounded service-level smoke checks passed for
metadata, preview, waveform, spectrum, Welch PSD, spectrogram, statistics,
spectral attributes, FK transform, and FK velocity-filter smoke path.

### Added or modified files

- .gitignore
- das_view/io/hdf5_zd.py
- das_view/io/puniu_dat.py
- examples/plot_waveform.py
- examples/validate_local_samples.py
- tests/test_hdf5_zd_reader.py
- tests/test_puniu_dat_reader.py
- tests/test_validation_scripts.py
- docs/04_data_formats.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Fixes from real/quasi-real validation

- Puniu DAT: accepted a validated layout variant where the header seek field
  stores the file size while the float32 payload starts immediately after the
  fixed 80-byte header. The effective payload offset remains validated against
  n_samples * n_channels.
- ZD HDF5: accepted files where Count stores the total raw value count and
  NumberOfLoci identifies the channel axis.
- Local validation path parsing: stripped UTF-8 BOM from local path-list input
  and made error printing safer on narrow Windows consoles.
- Waveform example: added the same repository-root import bootstrap used by
  other examples so direct script execution works.
- .gitignore: added *.json to keep local validation JSON summaries ignored.

### GUI validation

Manual GUI validation was not executed in this non-interactive tool session
because the assistant cannot operate a native file dialog or visually inspect
the running PyQt5 window. Existing GUI smoke tests remain part of the full test
suite, but real manual GUI validation should still be performed by the project
owner on a local desktop.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase only hardened existing new readers and validation/example tooling
based on real/quasi-real sample behavior.

### Test result

- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_puniu_dat_reader.py tests\test_hdf5_zd_reader.py tests\test_validation_scripts.py
- Result: 27 passed.
- D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
- Result: 297 passed.

### Data policy confirmation

No real DAS input data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute paths, or local output files were
staged for commit.

### Not completed

- Broader real-data coverage across more acquisition variants is not completed.
- Manual GUI validation remains to be performed by the project owner.
- Envelope / STA-LTA / event candidate detection is not implemented.
- ROI / annotation / export workflows are not implemented.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.

### Suggested next round

Phase 5C: Envelope / STA-LTA / event candidate detection, or Phase 5D:
ROI / annotation / export.

## 2026-06-22: Phase 5C Envelope / STA-LTA / event candidate detection

### Goal

Add DAS event candidate analysis as a general DAS Viewer / DAS Analysis
capability. This phase adds envelope, energy envelope, STA/LTA, threshold
crossing, and event candidate table support. It does not add earthquake
location, source location, inversion, surface-wave imaging, MASW, F-J, or
dispersion-picking workflows.

### Added or modified files

- das_view/analysis/events.py
- das_view/analysis/service.py
- das_view/analysis/__init__.py
- examples/event_detection_file.py
- tests/test_events_analysis.py
- tests/test_events_service.py
- tests/test_event_detection_example.py
- tests/test_tutorial_notebook.py
- docs/09_tutorial_user_manual.ipynb
- README.md
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Implemented analysis

- amplitude_envelope uses scipy.signal.hilbert and returns same-shaped
  amplitude envelope arrays.
- energy_envelope returns point energy or same-shaped sliding-window energy.
- sta_lta_ratio computes classic energy-based STA/LTA ratios from x**2 moving
  averages.
- detect_threshold_events builds channel-wise event candidate tables from
  threshold crossings.
- detect_stalta_events computes STA/LTA and detects candidates using trigger-on
  and optional trigger-off thresholds.

EventCandidate records event_id, start_sample, end_sample, duration_samples,
channel_start, channel_end, peak_sample, peak_channel, peak_value, mean_value,
max_value, and score. Outputs are event candidates only and do not represent
locations or interpretation results.

### Implemented services and example

- compute_envelope_for_file reads bounded 2-D selections through read_selection,
  optionally applies apply_preprocess, then computes amplitude envelope.
- compute_stalta_for_file reads bounded 2-D selections through read_selection,
  optionally applies apply_preprocess, then computes STA/LTA ratio.
- detect_events_for_file supports stalta and envelope modes on bounded
  selections and returns reader name, metadata, selection, preprocessing
  history, and detection result.
- examples/event_detection_file.py supports bounded CLI use with JSON and CSV
  event-candidate table output.

### Tutorial notebook

- Added docs/09_tutorial_user_manual.ipynb as the stable Jupyter tutorial and
  operation manual.
- The notebook covers DAS Viewer / DAS Analysis positioning, time x channel
  convention, reading/metadata, waterfall/waveform views, preprocessing,
  filters, spectrum/PSD/spectrogram, statistics, spectral attributes, FK
  inspection, envelope/STA-LTA/event candidates, CLI usage, GUI usage, and
  interpretation boundaries.
- It uses synthetic data and placeholder paths only. It does not contain real
  data paths, development logs, commit history, or test-run records.

### Tests

- Added event analysis tests for envelope shape, sinusoid envelope behavior,
  energy envelope, sliding energy, STA/LTA shape and validation, threshold
  candidates, min duration, merge gap, max events, DASData input, NaN/Inf
  rejection, and no in-place mutation.
- Added event service tests for synthetic ZD HDF5 envelope, STA/LTA, event
  detection, bounded time/channel selection, preprocessing history, and
  metadata/reader/selection reporting.
- Added event example tests for STA/LTA and envelope argument parsing plus JSON
  and CSV output to pytest tmp_path.
- Added notebook tests for valid ipynb JSON, nbformat, key formulas/keywords,
  and absence of local paths or development/test content.
- Focused result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_events_analysis.py tests\test_events_service.py tests\test_event_detection_example.py tests\test_tutorial_notebook.py
  Result: 26 passed.
- Full test result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
  Result: 323 passed.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase implements event candidate analysis directly in the new
GUI-independent analysis/service structure.

### Data policy confirmation

No real DAS input data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute paths, JSON/CSV outputs, or local
output files are intended for commit.

### Not completed

- Larger real-data event candidate validation is not completed.
- ROI / annotation / export workflows are not implemented.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.
- The tutorial notebook should continue to be maintained as features mature.

### Suggested next round

Phase 5D: ROI / annotation / export, or Phase 5E: GUI analysis panel.

## 2026-06-22: Phase 5D ROI / annotation / export

### Goal

Add ROI, annotation, export, and ROI summary workflows as DAS data review and
analysis aids. This phase does not add source location, earthquake location,
inversion, surface-wave imaging, MASW, F-J, or dispersion-picking workflows.

### Residual work recovery

The previous incomplete Phase 5D turn left an untracked
das_view/analysis/roi.py file. The useful TimeChannelROI, Annotation, ROISet,
ROIAnalysisResult, and rois_from_event_candidates structure was retained.
Small validation fixes were added for required ROI and annotation IDs/labels.
No reset, checkout, clean, or deletion of user work was performed.

### Added or modified files

- AGENTS.md
- README.md
- das_view/analysis/roi.py
- das_view/analysis/service.py
- das_view/analysis/__init__.py
- das_view/io/export.py
- das_view/plotting/roi.py
- das_view/plotting/__init__.py
- examples/roi_export_file.py
- tests/test_roi_analysis.py
- tests/test_roi_service.py
- tests/test_export.py
- tests/test_roi_plotting.py
- tests/test_roi_export_example.py
- tests/test_tutorial_notebook.py
- docs/09_tutorial_user_manual.ipynb
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Implemented ROI / annotation / export capabilities

- TimeChannelROI stores half-open sample and channel intervals, label, score,
  metadata, duration_samples, n_channels, and to_dict/from_dict helpers.
- Annotation stores label, optional description/category/confidence/creator,
  metadata, and to_dict/from_dict helpers.
- ROISet manages multiple ROIs with add/remove/filter/sort/limit helpers.
- rois_from_event_candidates converts EventCandidate tables to padded ROIs
  without producing location or interpretation results.
- compute_roi_statistics_for_file reads each ROI through read_selection,
  optionally applies apply_preprocess, then calls basic_statistics.
- compute_roi_spectral_attributes_for_file reads each ROI through
  read_selection and computes averaged spectral attributes or band energy.
- das_view/io/export.py provides JSON/CSV export helpers for dataclasses,
  numpy values, event candidates, ROIs, annotations, and ROI analysis
  summaries.
- das_view/plotting/roi.py overlays ROIs or event candidates on Matplotlib
  waterfall axes without PyQt5 dependencies.
- examples/roi_export_file.py supports manual ROIs, event-candidate to ROI
  conversion, event/ROI JSON/CSV export, and ROI statistics summary export.

### Tutorial notebook

- docs/09_tutorial_user_manual.ipynb was updated with ROI, annotation,
  event-candidate to ROI conversion, ROI statistics/spectral summaries,
  JSON/CSV export examples, and interpretation boundaries.
- The notebook remains a user tutorial and operation manual. It does not
  include development logs, test process, commit history, real data paths, or
  real data.
- AGENTS.md now requires future mature user-facing functionality to update the
  tutorial notebook in the same round.

### Tests

- Focused result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_tutorial_notebook.py tests\test_roi_analysis.py tests\test_roi_service.py tests\test_export.py tests\test_roi_plotting.py tests\test_roi_export_example.py
  Result: 33 passed.
- Full test result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
  Result: 353 passed.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase implements ROI/export workflows directly in the new analysis, IO,
plotting, service, and example layers.

### Data policy confirmation

No real DAS input data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute paths, JSON/CSV outputs, or local
output files are intended for commit.

### Not completed

- Larger real-data ROI/export validation is not completed.
- GUI analysis panel is not implemented.
- Packaging and release hardening are not completed.
- The tutorial notebook should continue to be maintained as features mature.

### Suggested next round

Phase 5E: GUI analysis panel, or Phase 6A: Packaging and release hardening.

## 2026-06-22: Phase 5E GUI analysis panel

### Goal

Add a minimal service-backed GUI Analysis tab for mature DAS analysis
workflows. This phase does not add new analysis algorithms, surface-wave
imaging, MASW, F-J, dispersion picking, source location, or geologic
interpretation workflows.

### Added or modified files

- README.md
- AGENTS.md
- das_view/analysis/service.py
- das_view/gui/models.py
- das_view/gui/workers.py
- das_view/gui/main_window.py
- tests/test_gui_smoke.py
- tests/test_tutorial_notebook.py
- docs/09_tutorial_user_manual.ipynb
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Implemented GUI Analysis capabilities

- Added AnalysisRequest and PyQt-free parsing helpers for time/channel
  selection, percentiles, band ranges, frequency ranges, STA/LTA parameters,
  envelope-threshold parameters, ROI text, and analysis type mapping.
- Added AnalysisWorker and QtAnalysisWorker. The worker dispatches to existing
  service-layer functions for statistics, band energy, spectral attributes,
  event candidates, and ROI statistics.
- Added an Analysis tab with common bounded selection controls, analysis type
  selection, task-specific parameters, Run analysis, Export JSON, Export CSV,
  Clear results, a summary text area, and a result table.
- Analysis runs in the existing QThread-backed background-task framework with
  soft cancellation and stale-result protection.
- JSON/CSV export uses das_view/io/export.py helpers. GUI code does not
  implement serialization details.
- The GUI still does not read HDF5/DAT internal paths or implement analysis
  algorithms directly.

### Tutorial notebook

- docs/09_tutorial_user_manual.ipynb was updated with GUI Analysis panel,
  Statistics operation, Band energy / spectral attributes operation, Event
  candidate detection operation, ROI statistics and JSON/CSV export, and GUI
  interpretation-boundary sections.
- The notebook remains a user tutorial and operation manual. It does not
  include development logs, test process, commit history, real data paths, or
  real data.

### Tests

- Focused GUI result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_gui_smoke.py -q
  Result: 57 passed.
- Full test result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
  Result: 367 passed. The first full run failed because Windows denied access to the default pytest temp directory; rerunning with TMP/TEMP set to .tmp_pytest passed.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase connects existing service-layer analysis and export workflows to
the GUI.

### Data policy confirmation

No real DAS input data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute paths, JSON/CSV outputs, or local
output files are intended for commit.

### Not completed

- Larger real-data GUI Analysis validation is not completed.
- Packaging and release hardening are not completed.
- The tutorial notebook should continue to be maintained as features mature.

### Suggested next round

Phase 6A: Packaging and release hardening.

## 2026-06-22: Phase 6A Packaging and release hardening

### Goal

Harden HCZ DAS View as an installable, runnable, packageable DAS Viewer /
DAS Analysis software package. This phase does not add analysis algorithms,
readers, GUI analysis features, surface-wave imaging, MASW, F-J, dispersion
picking, location, or inversion workflows.

### Added or modified files

- pyproject.toml
- .gitignore
- README.md
- AGENTS.md
- das_view/cli/__init__.py
- das_view/cli/validate.py
- das_view/cli/preview.py
- das_view/cli/statistics.py
- das_view/cli/spectrum.py
- das_view/cli/events.py
- das_view/gui/app.py
- packaging/README_windows_packaging.md
- packaging/build_windows.ps1
- packaging/hcz_das_view.spec
- tests/test_packaging.py
- tests/test_cli_entrypoints.py
- docs/09_tutorial_user_manual.ipynb
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Packaging and entry points

- pyproject.toml now includes build-system metadata, project metadata,
  optional dependency groups for gui/dev/packaging, package discovery, console
  scripts, and GUI scripts.
- Added installed CLI wrappers under das_view/cli for validation, preview,
  statistics, spectrum/PSD/spectrogram, and event-candidate workflows.
- Added hcz-das-view and retained das-view-gui as GUI scripts. GUI help can run
  without starting a Qt event loop.
- CLI wrappers call existing service-layer APIs and do not treat examples/ as
  package API.

### Windows packaging and release checklist

- Added packaging/README_windows_packaging.md for Windows Conda setup, GUI
  launch, PyInstaller packaging, hidden-import/backend notes, artifact policy,
  exe validation, and limitations.
- Added packaging/build_windows.ps1 as a local PyInstaller build helper.
- Added packaging/hcz_das_view.spec using relative paths and no real data.
- README.md, docs/07_roadmap.md, and docs/08_project_handoff.md now include a
  release checklist covering version metadata, full pytest, local real-sample
  smoke validation, CLI/GUI smoke, wheel/sdist build, Windows packaging smoke,
  notebook/docs freshness, artifact safety, tags, and release notes.

### Tutorial notebook

- docs/09_tutorial_user_manual.ipynb was updated with installation, installed
  CLI entry points, GUI launch, Windows packaging/exe usage, and release usage
  notes.
- The notebook remains a user tutorial and operation manual. It does not
  include development logs, test process, commit history, real data paths, or
  real data.

### Tests

- Focused packaging result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_packaging.py tests\test_cli_entrypoints.py -q
  Result: 16 passed.
- Full test result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
  Result: 383 passed. TMP/TEMP were set to .tmp_pytest to avoid the known
  Windows default temp-directory permission issue.
- Packaging smoke:
  D:\HczApp\Anaconda\envs\mywork\python.exe -m pip show build
  Result: build is not installed in the current environment, so wheel/sdist
  build smoke is deferred rather than forcing a network install.
- Editable install smoke:
  D:\HczApp\Anaconda\envs\mywork\python.exe -m pip install -e . --no-deps
  Result: hcz-das-view 0.1.0.dev0 installed successfully in editable mode.
- Entrypoint help smoke:
  hcz-das-validate --help, hcz-das-preview --help, hcz-das-stats --help,
  hcz-das-spectrum --help, hcz-das-events --help, and
  python -m das_view.gui.app --help completed successfully.
- pip check:
  D:\HczApp\Anaconda\envs\mywork\python.exe -m pip check
  Result: the current Conda environment reports pre-existing platform metadata
  issues for several installed packages; this is not introduced by hcz-das-view.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase hardens packaging, installed entry points, and release documentation.

### Data and artifact policy confirmation

No real DAS input data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute paths, JSON/CSV outputs, build/dist
artifacts, wheels, archives, exe files, or local output files are intended for
commit.

### Not completed

- Larger real-data packaging validation is not completed.
- Automated release CI is not implemented.
- Windows exe signing is not implemented.
- Packaging has not yet been validated across multiple clean machines.
- The tutorial notebook should continue to be maintained as features mature.

### Suggested next round

Phase 6B: Plugin / extension architecture, or Phase 6C: Release polishing and
clean-environment install validation.

## 2026-06-22: Phase 6C Release polishing and clean-environment install validation

### Goal

Polish release-candidate validation for HCZ DAS View without adding analysis
algorithms, readers, GUI features, surface-wave imaging, MASW, F-J,
dispersion picking, location, or inversion workflows.

### Added or modified files

- .gitignore
- README.md
- AGENTS.md
- packaging/README_windows_packaging.md
- tests/test_release_validation.py
- docs/09_tutorial_user_manual.ipynb
- docs/02_architecture.md
- docs/05_development_log.md
- docs/06_testing.md
- docs/07_roadmap.md
- docs/08_project_handoff.md

### Release validation

- Reviewed pyproject.toml metadata, optional dependency groups, console
  scripts, GUI script, and package discovery.
- Added .tmp_release_venv/ to ignored local artifacts.
- Created a temporary clean venv and ran an editable install smoke with
  `pip install -e . --no-deps`; package metadata and `pip show hcz-das-view`
  succeeded. Importing das_view in that no-deps venv fails until runtime
  dependencies such as numpy and scipy are installed, which is the expected
  limitation of a no-deps validation.
- The current environment does not have the `build` package installed, so
  wheel/sdist build smoke is deferred instead of forcing a network install.
- Installed CLI entrypoint help smoke passed for hcz-das-validate,
  hcz-das-preview, hcz-das-stats, hcz-das-spectrum, and hcz-das-events.
- GUI help smoke passed through `python -m das_view.gui.app --help`; on this
  Windows shell the gui-scripts executable returns success but does not echo
  visible help text.
- Example help smoke passed for validate_file.py, statistics_file.py,
  spectral_attributes_file.py, event_detection_file.py, and roi_export_file.py.

### Tests

- Focused release tests:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider tests\test_packaging.py tests\test_cli_entrypoints.py tests\test_release_validation.py tests\test_tutorial_notebook.py -q
  Result: 30 passed.
- Full test result:
  D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider
  Result: 394 passed. The first attempt hit the known Windows default
  temp-directory permission issue; TMP/TEMP were set to .tmp_pytest and the
  suite passed. Test count increased from 383 to 394 because Phase 6C added 11
  release validation tests.
- pip show hcz-das-view in the main environment reports hcz-das-view
  0.1.0.dev0 installed in editable mode.
- pip check in the main Conda environment reports pre-existing "not supported
  on this platform" metadata messages for unrelated installed packages. No
  hcz-das-view dependency conflict is reported.

### Old-code migration judgment

No old_code files were copied, imported, modified, or used for implementation.
This phase only polishes release validation, packaging policy, and
documentation.

### Data and artifact policy confirmation

No real DAS data, generated images, validation_outputs artifacts,
local_validation_paths.txt, local absolute data paths, JSON/CSV outputs,
build/dist artifacts, wheels, archives, exe files, or local output files are
intended for commit.

### Not completed

- Wheel/sdist build smoke remains deferred until the `build` package is
  available in the environment.
- Larger real-data release validation is not completed.
- Automated release CI is not implemented.
- Windows exe signing is not implemented.
- Packaging has not yet been validated across multiple clean machines.
- The tutorial notebook should continue to be maintained as features mature.

### Suggested next round

Phase 6B: Plugin / extension architecture, or Phase 6D: Release CI planning.
