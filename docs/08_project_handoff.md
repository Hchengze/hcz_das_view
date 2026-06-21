# Project handoff summary

This document is the handoff point for starting a new Codex conversation on
hcz_das_view. It records the current repository state after Phase 3E and the
rules that should be preserved before any further development.

## 1. Project identity

- Project name: hcz_das_view, with the Python package named das_view.
- Project role: a maintainable DAS data viewing, preview, basic processing,
  and basic analysis package.
- Development model: the new das_view/ package is being rebuilt after auditing
  legacy material under old_code/.
- New runtime code must not depend on, import, or call old_code.
- Latest functional development commit: 818c756 Add PSD Welch analysis and
  spectrum service.
- Latest handoff commit: 41382a3 Add project handoff summary.
- Latest GUI responsiveness commit: current HEAD after Phase 2D,
  Add GUI background loading with cancel and progress.
- Latest GUI spectrum commit: current HEAD after Phase 3E,
  Add minimal GUI spectrum panel.
- Latest FK smoke-path commit: pending this Phase 4A commit,
  Add FK transform smoke path.
- Current phase: Phase 4A, FK transform smoke path.
- Current test result after Phase 4A: 190 passed.

## 2. Repository and environment

- GitHub repository: https://github.com/Hchengze/hcz_das_view
- Local project path:

      E:\HczDocument\BaiduDisk\BaiduSyncdisk\HCZ_work\CodexProject\HCZ_das_view

- Python environment:

      D:\HczApp\Anaconda\envs\mywork\python.exe

- Common test command:

      D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider

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
8. core, io, processing, analysis, and plotting must not depend on PyQt5.
9. PyQt5 should only appear in das_view/gui/ or GUI startup entry points.
10. Every development round must update docs/05_development_log.md.
11. Keep docs/ at eight files or fewer unless the project owner approves an
    expansion.

## 4. Current package architecture

- das_view/core/: core data structures, metadata formatting, and package
  exceptions.
- das_view/io/: file readers, reader registry, preview generation, and data
  selection services.
- das_view/processing/: pure preprocessing functions, scipy-based filters, and
  DASData-level processing service.
- das_view/analysis/: spectrum, spectrogram, PSD/Welch, FK functions, and
  file-level analysis service.
- das_view/plotting/: Matplotlib plotting helpers independent of PyQt5.
- das_view/gui/: optional PyQt5 application, main window, models, and worker
  scaffolding.
- das_view/utils/: shared utilities, including slicing helpers.
- examples/: small CLI and GUI entry points for supported workflows.
- tests/: synthetic-data tests for readers, services, processing, analysis,
  plotting, examples, and GUI smoke behavior.
- docs/: compact project documentation and phase history.

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
  - service.py: ordered preprocessing/filter steps on DASData with history.
- Analysis:
  - spectrum.py: amplitude spectrum, power spectrum, spectrogram, periodogram
    PSD, and Welch PSD.
  - service.py: file-level spectrum/PSD/spectrogram workflows for CLI and
    future GUI reuse, plus a bounded FK service.
  - fk.py: FKResult and basic FK transform.
- Plotting:
  - waterfall.py: waterfall preview plotting.
  - waveform.py: waveform trace plotting.
  - spectra.py: spectrum, spectrogram, and PSD plotting.
  - fk.py: FK plotting.
- GUI:
  - main_window.py: minimal GUI with metadata, waterfall, waveform, and
    spectrum tabs.
  - app.py: GUI application entry point.
  - models.py: GUI-independent parsing and small models.
  - workers.py: no-Qt callable service wrappers plus QThread QObject workers for
    preview, waveform, and spectrum background loading.

## 5. Completed phase history

### Phase 0: development baseline

- Goal: establish package layout, core data model, docs, old-code rules, and
  initial tests.
- Key modules: das_view/core/, docs/01_project_baseline.md, initial tests.
- Test result: initial baseline tests passed.
- Not completed: real readers, plotting, GUI, processing, and analysis.

### Phase 1A: reader workflow + non-GUI waterfall plotting

- Goal: implement the first supported reader path and a non-GUI waterfall smoke
  workflow.
- Key modules: ZD HDF5 reader, reader registry, waterfall plotting,
  examples/read_and_plot_zd_h5.py.
- Test result: 19 passed.
- Not completed: metadata display service, preview API, GUI, Puniu DAT.

### Phase 1B: metadata formatting + preview API

- Goal: add formatted metadata output and a bounded preview service independent
  of GUI code.
- Key modules: metadata_format.py, preview.py, examples/preview_file.py.
- Test result: 28 passed.
- Not completed: GUI and broader reader validation.

### Phase 1C: minimal PyQt5 preview GUI

- Goal: create the smallest GUI that opens a supported file, displays metadata,
  and draws a bounded waterfall preview.
- Key modules: das_view/gui/main_window.py, app.py, examples/run_gui.py.
- Test result: 30 passed.
- Not completed: background loading, waveform, analysis panels.

### Phase 1D: GUI stabilization + README + validation entry

- Goal: stabilize preview GUI basics, improve user entry points, and document
  the workflow.
- Key modules: README updates, GUI robustness, validation entry path.
- Test result: 34 passed.
- Not completed: waveform plotting, QThread loading, real systematic data
  validation.

### Phase 2A: waveform plotting + data selection service

- Goal: add bounded data selection helpers and waveform plotting outside the
  GUI.
- Key modules: data_service.py, waveform.py, examples/plot_waveform.py.
- Test result: 46 passed.
- Not completed: GUI waveform integration and full reader edge-case hardening.

### Phase 2B: GUI waveform tab

- Goal: integrate waveform plotting into the minimal GUI and add channel input
  parsing.
- Key modules: GUI waveform tab, models.py channel parser, expanded
  data-service tests.
- Test result: 61 passed.
- Not completed: real sample validation and background GUI loading.

### Phase 2C: local sample validation + reader edge-case checks

- Goal: prepare local real/quasi-real validation tooling and harden ZD HDF5 /
  Puniu DAT reader boundaries.
- Key modules: examples/validate_file.py, examples/validate_local_samples.py,
  reader edge-case tests.
- Test result: 72 passed.
- Not completed: systematic real sample validation and GUI responsiveness.

### Phase 2D: GUI QThread background loading

- Goal: move preview and waveform data loading out of the GUI thread and add
  cancel/progress feedback.
- Key modules: QThread-backed preview/waveform workers, MainWindow task-state
  wiring, progress bar, Cancel button, and GUI-independent task state helpers.
- Test result: 157 passed.
- Not completed: hard interruption of synchronous reader IO and real large-file
  responsiveness validation.

### Phase 3A: basic preprocessing

- Goal: migrate small preprocessing operations into pure numpy functions and a
  reusable service.
- Key modules: preprocess.py, processing/service.py,
  examples/preprocess_file.py.
- Test result: 97 passed.
- Not completed: filters, spectrum analysis, GUI processing panel.

### Phase 3B: basic filters

- Goal: add lowpass, highpass, bandpass, bandstop, and notch filters and connect
  them to the processing service.
- Key modules: filters.py, filter steps in processing/service.py,
  examples/filter_file.py.
- Test result: 117 passed.
- Not completed: spectrum analysis, GUI filter panel, full-data export.

### Phase 3C: basic spectrum + spectrogram smoke path

- Goal: add amplitude spectrum, power spectrum, and a single-channel
  spectrogram smoke path.
- Key modules: analysis/spectrum.py, plotting/spectra.py,
  examples/spectrum_file.py.
- Test result: 134 passed.
- Not completed: PSD/Welch service, FK, GUI spectrum panel.

### Phase 3D: PSD / Welch + spectrum service

- Goal: add periodogram PSD, Welch PSD, PSD plotting, and reusable file-level
  analysis service helpers.
- Key modules: periodogram_psd, welch_psd, plot_psd, analysis/service.py,
  enhanced examples/spectrum_file.py.
- Test result: 150 passed.
- Not completed: FK, F-J/MASW, GUI spectrum panel, QThread responsiveness, real
  large-data performance validation.

### Phase 3E: minimal GUI spectrum panel

- Goal: connect existing amplitude, power, PSD, Welch PSD, and spectrogram
  services to the GUI without adding new algorithms.
- Key modules: Spectrum tab in MainWindow, SpectrumWorker / QtSpectrumWorker,
  spectrum request parser/status helpers, and GUI smoke tests.
- Test result: 166 passed.
- Not completed: GUI preprocessing/filter panels, FK/F-J/MASW, complete STFT,
  full export, and real large-file spectrum performance validation.

### Phase 4A: FK transform smoke path

- Goal: add a minimal FK transform, FK result object, FK plotting helper, file
  service, CLI example, and synthetic tests.
- Key modules: das_view/analysis/fk.py, compute_fk_for_file in
  analysis/service.py, das_view/plotting/fk.py, examples/fk_file.py.
- Test result: 190 passed.
- Not completed: FK filter, velocity fan filter, F-J/MASW, dispersion picking,
  GUI FK panel, and real large-file FK performance validation.

## 6. Current supported capabilities

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

### Plotting

- Waterfall preview plots.
- Waveform trace plots.
- Spectrum plots.
- Spectrogram plots.
- PSD plots, including optional dB display.
- FK amplitude/power plots.

### GUI

- Open supported files.
- Display formatted metadata.
- Show bounded waterfall preview tab.
- Show waveform tab.
- Show Spectrum tab for single-channel amplitude spectrum, power spectrum,
  PSD periodogram, PSD Welch, and spectrogram tasks.
- Configure max_samples and max_channels.
- Parse single or comma-separated channel input.
- Preview, waveform, and spectrum tasks run in QThread-backed background
  workers with busy progress feedback and soft cancellation.
- Current limitation: cancellation cannot forcibly interrupt synchronous reader
  IO or analysis calls already in progress; cancelled results are ignored when
  they return.

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

### Analysis

- amplitude_spectrum.
- power_spectrum.
- single_channel_spectrogram.
- periodogram_psd.
- welch_psd.
- fk_transform.
- compute_spectrum_for_file.
- compute_psd_for_file.
- compute_spectrogram_for_file.
- compute_fk_for_file.

## 7. Current examples and how to use them

- examples/read_and_plot_zd_h5.py: read a ZD HDF5 file and save a waterfall
  smoke plot.

      python examples/read_and_plot_zd_h5.py input.h5 --output preview.png

- examples/preview_file.py: create a bounded preview from any registered
  reader.

      python examples/preview_file.py input.h5 --output preview.png

- examples/validate_file.py: validate one HDF5/DAT file, print metadata and
  preview information, and optionally save preview/waveform images.

      python examples/validate_file.py input.h5 --waveform-output trace.png --channel 10

- examples/validate_local_samples.py: batch-validate paths listed in ignored
  local_validation_paths.txt.

      python examples/validate_local_samples.py

- examples/plot_waveform.py: plot one or more bounded waveform traces.

      python examples/plot_waveform.py input.dat --channels 10 20 30 --output traces.png

- examples/preprocess_file.py: apply preview-level preprocessing and save a
  processed waterfall image.

      python examples/preprocess_file.py input.h5 --output preview_processed.png --demean --taper 0.05 --normalize

- examples/filter_file.py: apply preview-level filtering and save a filtered
  waterfall image.

      python examples/filter_file.py input.h5 --output preview_filtered.png --bandpass 1 50

- examples/spectrum_file.py: compute bounded amplitude, power, PSD/Welch, or
  spectrogram plots, optionally after a filter step.

      python examples/spectrum_file.py input.h5 --channel 10 --psd welch --nperseg 512 --output welch.png

- examples/fk_file.py: compute bounded FK amplitude or power plots, optionally
  after a filter step.

      python examples/fk_file.py input.h5 --output fk.png
      python examples/fk_file.py input.h5 --output fk_power.png --output-mode power

- examples/run_gui.py: launch the optional PyQt5 GUI.

      python examples/run_gui.py

## 8. Current tests

Current coverage includes:

- Reader tests for ZD HDF5, Puniu DAT, and reader registry behavior.
- Preview API tests for bounded preview shape, downsampling, and metadata.
- Plotting tests for waterfall, waveform, spectrum, spectrogram, and PSD output.
- GUI smoke tests that cleanly skip when optional PyQt5 is unavailable.
- GUI spectrum smoke tests for parser/model helpers, Spectrum tab controls,
  worker construction, and soft cancellation state.
- Data service tests for read_selection, read_trace, and channel boundary
  behavior.
- Validation script tests for path-list parsing and no-real-data workflows.
- Preprocessing tests for demean, detrend, taper, normalize, standardize, clip,
  service history, and no in-place mutation.
- Filter tests for lowpass, highpass, bandpass, bandstop, notch, validation,
  scipy behavior, and service integration.
- Spectrum tests for amplitude/power spectrum, spectrogram, plotting, example
  parsing, and DASData metadata handling.
- PSD/Welch service tests for periodogram, Welch, channel selection/averaging,
  plotting, file-level service calls, and example integration.
- FK tests for synthetic plane waves, plotting, file-level service calls, and
  example argument helpers.

Current full test command and result:

      D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider

      190 passed

## 9. Old code migration status

- old_code/old_code1/tools/data_tools.py: reader and metadata ideas were
  audited; useful ZD HDF5 concepts were reimplemented through the new reader,
  metadata, and preview interfaces.
- old_code/old_code3/dy_view.py: Puniu DAT header and payload concepts were
  audited; the new Puniu reader reimplements the necessary behavior with clear
  validation and the (n_samples, n_channels) convention.
- old_code/old_code1/tools/analysis_tools.py: preprocessing, filtering,
  spectrum, PSD/Welch, and basic FK ideas were audited; selected simple
  numerical logic was reimplemented with explicit numpy/scipy interfaces.
  Advanced FK filter, fan mask, inverse filtering, F-J, and MASW sections remain
  deferred.
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

## 10. Known limitations and risks

1. ZD HDF5 and Puniu DAT have not been systematically validated with real
   production samples.
2. GUI preview, waveform, and spectrum tasks use QThread workers, but real
   production large-file responsiveness has not been validated.
3. GUI cancellation is soft and cannot forcibly interrupt synchronous reader IO
   or analysis calls already in progress.
4. There is no GUI preprocessing, filter, or FK panel.
5. FK filter and velocity fan filter are not implemented.
6. F-J / MASW analysis is not implemented.
7. A complete STFT workflow is not implemented.
8. Full processing/analysis result export is not implemented.
9. SEGY, SAC, and TDMS are not implemented.
10. Real large-data performance has not been validated.

## 11. Recommended next phases

### Option A: Phase 2E real sample validation

Goal:

      Use local_validation_paths.txt to validate real/quasi-real ZD HDF5 and Puniu DAT samples.

If real sample paths are provided, prioritize this before expanding analysis features.

### Option B: Phase 4B FK filter smoke path

Goal:

      Add a minimal FK filter smoke path building on Phase 4A.

Keep this to a smoke path first; do not add F-J/MASW or surface-wave analysis in the same round.

## 12. Suggested first prompt for the new Codex chat

Copy this into the next Codex conversation:

    璇峰厛涓嶈寮€鍙戞柊鍔熻兘銆傝鍏堥槄璇伙細

    - AGENTS.md
    - README.md
    - docs/08_project_handoff.md
    - docs/05_development_log.md
    - docs/07_roadmap.md

    鐒跺悗鎵ц锛?
    git status --short
    git branch -vv
    git log --oneline -8
    D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider

    璇峰厛杩斿洖褰撳墠浠撳簱鐘舵€併€佹渶鏂?HEAD銆佹祴璇曠粨鏋滃拰浣犲涓嬩竴姝ョ殑寤鸿锛屼笉瑕佺洿鎺ヤ慨鏀逛唬鐮併€?
    榛樿涓嬩竴姝ュ缓璁繘鍏ワ細

    Phase 2D锛欸UI QThread 鍚庡彴鍔犺浇銆佸彇娑堜笌杩涘害鎻愮ず

    浣嗗鏋滄垜鏄庣‘鎻愪緵鐪熷疄鏁版嵁璺緞锛屽垯浼樺厛杩涘叆锛?
    Phase 2E锛歳eal sample validation
