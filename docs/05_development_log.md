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
