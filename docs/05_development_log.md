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
| old_code FK/F-J/MASW and advanced PSD sections | advanced analysis | Deferred | Not implemented | Not applicable | Out of scope for Phase 3C. |

No old_code files were imported, copied directly, or modified.

### Test result

- python -B -m pytest -p no:cacheprovider
- Result: 134 passed.

### Not completed

- Full STFT workflows are not implemented.
- PSD/Welch service helpers are not implemented.
- FK/F-J/MASW are not implemented.
- GUI spectrum panel is not implemented.
- Real large-file spectrum performance has not been validated.

### Suggested next round

Phase 3D: add PSD/Welch and spectrum service helpers; or Phase 2D: add QThread
background loading, cancel, and progress feedback for the GUI.
