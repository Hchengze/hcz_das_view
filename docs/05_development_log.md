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
