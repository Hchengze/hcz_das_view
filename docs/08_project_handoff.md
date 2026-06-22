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
- 本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J 或频散拾取软件。
- Development model: the new das_view/ package is being rebuilt after auditing
  legacy material under old_code/.
- New runtime code must not depend on, import, or call old_code.
- Latest project state: current HEAD after Phase 5B Band energy and spectral
  attributes.
- Current phase: Phase 5B, DAS spectral attributes analysis.
- Current expected test result after Phase 5B: 293 passed.

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
12. FK visualization and FK-domain smoke filtering may remain as DAS 2D
    wavefield inspection capabilities, but should not be treated as a mainline
    path toward specialized inversion or picking workflows.

## 4. Current package architecture

- das_view/core/: core data structures, metadata formatting, and package
  exceptions.
- das_view/io/: file readers, reader registry, preview generation, and data
  selection services.
- das_view/processing/: pure preprocessing functions, scipy-based filters, and
  DASData-level processing service.
- das_view/analysis/: spectrum, spectrogram, PSD/Welch, spectral attributes,
  FK visualization, FK-domain smoke filtering, basic statistics, and file-level
  analysis services.
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
  - statistics.py: FiniteSummary, StatisticsResult, finite_summary,
    basic_statistics, and window_statistics.
  - spectral_attributes.py: BandEnergyResult, SpectralAttributesResult,
    band_energy, and spectral_attributes.
  - spectrum.py: amplitude spectrum, power spectrum, spectrogram, periodogram
    PSD, and Welch PSD.
  - service.py: file-level spectrum/PSD/spectrogram workflows for CLI and GUI
    reuse, plus bounded FK/FK-filter services.
  - fk.py: FKResult and bounded FK transform.
  - fk_filter.py: FKFilterResult, simple velocity fan mask, FK-domain mask
    application, and inverse FK smoke path.
- Plotting:
  - waterfall.py: waterfall preview plotting.
  - waveform.py: waveform trace plotting.
  - spectra.py: spectrum, spectrogram, and PSD plotting.
  - fk.py: FK plotting and FK mask plotting.
- GUI:
  - main_window.py: minimal GUI with metadata, waterfall, waveform, spectrum,
    and FK tabs.
  - app.py: GUI application entry point.
  - models.py: GUI-independent parsing and small models.
  - workers.py: no-Qt callable service wrappers plus QThread QObject workers.

## 5. Completed phase history

- Phase 0: established layout, core data model, old-code rules, and baseline
  tests.
- Phase 1A-1D: added ZD HDF5 workflow, metadata formatting, bounded preview,
  waterfall plotting, minimal GUI, and validation entry points.
- Phase 2A-2D: added reader-independent selection services, waveform plotting,
  Puniu DAT validation tooling, reader edge-case checks, and QThread-backed GUI
  preview/waveform loading with soft cancellation.
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
- FK mask plots for smoke-path validation.

### GUI

- Open supported files.
- Display formatted metadata.
- Show bounded waterfall preview tab.
- Show waveform tab.
- Show Spectrum tab for single-channel amplitude spectrum, power spectrum,
  PSD periodogram, PSD Welch, and spectrogram tasks.
- Show FK tab for bounded FK transform and FK velocity filter service tasks.
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

## 7. Current examples

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
- examples/fk_file.py: compute bounded FK amplitude or power plots, optionally
  after a filter step.
- examples/fk_filter_file.py: apply a minimal bounded FK velocity fan filter
  and save a filtered waterfall, optionally saving the filtered FK image.
- examples/run_gui.py: launch the optional PyQt5 GUI.

## 8. Current tests

Current coverage includes:

- Core data model, metadata formatting, and dimension validation.
- ZD HDF5 and Puniu DAT readers, registry behavior, bounded reads, slicing,
  downsampling, and edge cases.
- Preview, selection, and trace data services.
- Waterfall, waveform, spectrum, spectrogram, PSD, FK, and FK mask plotting.
- Preprocessing and filter functions plus DASData service integration.
- Spectrum, PSD/Welch, spectrogram, FK, and FK filter analysis helpers.
- Statistics analysis, service, and example tests for global, axis-wise,
  bounded, NaN/Inf-aware, and JSON/CSV-output workflows.
- Spectral attributes analysis, service, and example tests for band energy,
  band ratios, dominant frequency, centroid, bandwidth, rolloff, bounded
  services, and JSON/CSV-output workflows.
- CLI example argument construction and no-real-data smoke behavior.
- GUI-independent parser/model helpers and optional PyQt5 smoke tests for
  preview, waveform, spectrum, and FK panels.

Current full test command and expected result:

      D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider

      293 passed

## 9. Old code migration status

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

## 10. Known limitations and risks

1. ZD HDF5 and Puniu DAT have not been systematically validated with real
   production samples.
2. GUI preview, waveform, spectrum, and FK tasks use QThread workers, but real
   production large-file responsiveness has not been validated.
3. GUI cancellation is soft and cannot forcibly interrupt synchronous reader IO
   or analysis calls already in progress.
4. There is no GUI preprocessing or filter panel.
5. FK visualization and FK-domain filtering are bounded smoke paths for DAS 2D
   wavefield inspection, not polished production denoising workflows.
6. A broader time-frequency workflow is not implemented.
7. Full processing/analysis result export is not implemented.
8. Envelope / STA-LTA / event candidate detection is not implemented.
9. ROI / annotation / export workflows are not implemented.
10. GUI analysis panel is not implemented.
11. Packaging and release hardening are not completed.
12. SEGY, SAC, and TDMS are not implemented.

## 11. Recommended next phases

### Option A: Phase 2E real sample validation

Goal:

      Use local_validation_paths.txt to validate real/quasi-real ZD HDF5 and Puniu DAT samples.

If real sample paths are provided, prioritize this before expanding analysis
features.

### Option B: Phase 5C Envelope / STA-LTA / event candidate detection

Goal:

      Add envelope, energy envelope, STA/LTA, threshold picker, and event
      candidate table support.

If no real sample paths are available, prioritize this as the next mainline DAS
analysis feature phase.

Lower-priority FK documentation or example polish may still be useful later,
but it should remain below real sample validation and DAS analysis expansion.

## 12. DAS Analysis capability roadmap

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

## 13. External references for target alignment

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

## 14. Suggested first prompt for the new Codex chat

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
    D:\HczApp\Anaconda\envs\mywork\python.exe -B -m pytest -p no:cacheprovider

    请先返回当前仓库状态、最新 HEAD、测试结果和你对下一步的建议，不要直接修改代码。

    如果我提供真实数据路径，则建议进入：
    Phase 2E：real sample validation

    如果我没有真实数据路径，则建议进入：
    Phase 5C：Envelope / STA-LTA / event candidate detection
