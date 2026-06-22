# Roadmap

## Project target

HCZ DAS View is a DAS Viewer / DAS Analysis package.

It focuses on DAS file reading, metadata display, time-channel visualization,
waveform analysis, spectrum/spectrogram/FK visualization, preprocessing,
filtering, feature extraction, GUI interaction, testing, documentation,
packaging, and long-term maintainability.

It is not a dedicated surface-wave inversion, MASW, F-J, or
dispersion-picking package.

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J 或频散拾取软件。

## Completed baseline

### Phase 0: Development baseline

- Established package structure, documentation, data convention, metadata
  model, reader interfaces, and initial tests.

### Phase 1: Minimal DAS Viewer

- Added the first reader workflow, metadata display, bounded preview service,
  waterfall plotting, and the minimal optional PyQt5 GUI.

### Phase 2A-2D: Stable IO, plotting, and GUI responsiveness

- Added bounded time/channel selection, waveform plotting, local validation
  tooling, and QThread-backed GUI preview/waveform loading with soft
  cancellation.

### Phase 2E: Real sample validation

- Validated representative local real/quasi-real Puniu DAT and ZD HDF5 samples
  without committing input data, local path lists, generated outputs, or local
  absolute paths.
- Hardened Puniu DAT seek handling, ZD HDF5 Count-as-total-values orientation
  inference, local path-list BOM parsing, and direct waveform example execution.
- Confirmed bounded metadata, preview, waveform, spectrum/PSD/spectrogram,
  statistics, spectral attributes, FK transform, and FK-filter smoke paths on
  selected samples.

### Phase 3A-3E: Common preprocessing and spectrum analysis

- Added demean, detrend, taper, normalization, clipping, lowpass/highpass/
  bandpass/bandstop/notch filters, amplitude/power spectrum, periodogram PSD,
  Welch PSD, single-channel spectrogram smoke paths, file-level services, and
  a minimal GUI Spectrum tab.

### Phase 4A-4D: FK visualization and FK-domain smoke filtering

- Added bounded FK transform, FK plotting, simple FK-domain velocity fan mask
  filtering, a minimal GUI FK tab, and safer FK velocity-limit validation.
- FK is retained as DAS 2D wavefield analysis / FK visualization /
  FK-domain smoke filtering for bounded time-channel selections.
- FK work is not a mainline path toward specialized inversion or picking
  workflows. Such topic-specific algorithms, if ever needed, should live in
  independent plugins or extensions rather than the current core roadmap.

### Phase 5A: Analysis feature statistics

- Added basic DAS statistics analysis for numpy arrays and DASData.
- Added global summaries, time-axis reductions, channel-axis reductions, local
  window statistics, finite/NaN/Inf summaries, percentiles, RMS, absolute mean,
  peak-to-peak, and energy.
- Added file-level compute_statistics_for_file service and
  examples/statistics_file.py for bounded CLI use with JSON/global CSV output.

### Phase 5B: Band energy and spectral attributes

- Added frequency-band energy, band power, band energy ratio, dominant
  frequency, peak power, spectral centroid, spectral bandwidth, spectral
  rolloff, and total spectral energy analysis.
- Added per-channel and average-channel support for numpy arrays and DASData.
- Added file-level compute_band_energy_for_file and
  compute_spectral_attributes_for_file services plus
  examples/spectral_attributes_file.py for bounded CLI use with JSON/CSV
  output.

## Recommended next phases

### Phase 2E: Real sample validation

Goal:

    Use local_validation_paths.txt to run read-only validation on real or
    quasi-real ZD HDF5 / Puniu DAT samples, then fix reader, metadata, slice,
    preview, and GUI boundary issues discovered by those files.

Acceptance:

- No real DAS data, generated images, validation outputs, or path lists are
  committed.
- Reader metadata, orientation, bounded reads, previews, waveform traces, and
  GUI loading behavior are checked against available local samples.
- Any reader/metadata fixes preserve the internal
  `data.shape == (n_samples, n_channels)` convention.

Status:

- Completed for the provided local validation directories with representative
  Puniu DAT and ZD HDF5 samples.
- Broader real-data coverage and project-owner manual GUI validation remain
  future validation work.

### Phase 5A: Analysis feature statistics

Goal:

    Add DAS data statistics and attribute analysis:
    mean / std / rms / max / min / percentile / peak-to-peak / abs_mean /
    energy.

Status:

- Completed in Phase 5A for basic global, time-wise, channel-wise, and bounded
  window statistics.
- Remaining follow-up belongs to later export/GUI phases, not core statistics
  computation.

Scope:

- Support time-wise statistics, channel-wise statistics, local time windows,
  and channel ranges.
- Include finite / NaN / Inf summaries and clipping / saturation summaries
  where practical.
- Keep computation GUI-independent and covered by synthetic tests.

### Phase 5B: Band energy and spectral attributes

Goal:

    Add band energy, dominant frequency, spectral centroid, spectral bandwidth,
    spectral peak frequency, and band energy ratio analysis.

Scope:

- Reuse existing bounded data access and spectrum service patterns.
- Support per-channel and averaged summaries.
- Keep plotting/export separate from numerical analysis.

Status:

- Completed in Phase 5B for bounded per-channel and average-channel spectral
  attributes.
- Remaining follow-up belongs to later GUI/ROI/export phases, not core spectral
  attribute computation.

### Phase 5C: Envelope / STA-LTA / event candidate detection

Goal:

    Add envelope, energy envelope, STA/LTA, threshold picker, and event
    candidate table support.

Scope:

- This is DAS data analysis and event candidate detection only.
- Do not add event location, inversion, or domain-specific interpretation
  algorithms in this phase.
- Candidate outputs should include time/channel ranges, scores, and summary
  attributes suitable for GUI display and CSV/JSON export.

Status:

- Completed in Phase 5C for amplitude envelope, energy envelope, classic
  energy-based STA/LTA ratio, threshold crossing, STA/LTA-triggered candidate
  tables, bounded file-level services, CLI JSON/CSV output, and synthetic tests.
- Candidate outputs remain event candidates only; they are not location,
  inversion, or interpretation results.
- GUI integration remains deferred to Phase 5E.

Recommended next: Phase 5D or Phase 5E.

### Phase 5D: ROI / annotation / export

Goal:

    Support GUI selection of time windows, channel ranges, and ROI regions;
    save analysis summaries as CSV / JSON; export figures; and support simple
    annotations.

Scope:

- ROI and annotation support are interpretation aids for DAS data review.
- Keep saved outputs explicit and user-directed; never commit generated output
  directories.

### Phase 5E: GUI analysis panel

Goal:

    Connect statistics, band energy, envelope, and event candidate workflows to
    the GUI.

Scope:

- GUI code should call service-layer APIs.
- GUI-independent parser/state logic should remain testable without PyQt5.
- Heavy analysis should use the existing background-worker pattern.

### Phase 6A: Packaging and release hardening

Goal:

    Complete pyproject metadata, console scripts, versioning, packaging docs,
    release checklist, and example-data strategy.

Scope:

- Keep optional GUI dependencies optional.
- Document how to validate local samples without committing data.
- Add release checklist coverage for tests, docs, examples, and ignored outputs.

### Phase 6B: Plugin / extension architecture

Goal:

    Reserve plugin-style extension interfaces for additional readers,
    processing functions, and analysis algorithms.

Scope:

- Keep the core package focused on general DAS viewing and analysis.
- Specialized or topic-specific algorithms should be isolated behind extension
  boundaries when they are needed.
- Do not add heavy optional dependencies to the core package without a clear
  maintenance reason.

## DAS Analysis capability roadmap

## Tutorial notebook maintenance

- docs/09_tutorial_user_manual.ipynb is the stable user tutorial and operation
  manual.
- The existing eight markdown docs remain the project documentation set; the
  notebook is the single allowed additional tutorial file.
- Future rounds should update the notebook only for mature, user-facing
  capabilities.
- The notebook must not include development logs, test runs, commit history,
  real data paths, generated output artifacts, or private local paths.

### 1. Basic statistics

- time-wise statistics
- channel-wise statistics
- windowed statistics
- RMS
- peak-to-peak
- percentile
- energy
- finite / NaN / Inf summary
- clipping / saturation summary

### 2. Spectral attributes

- band energy
- dominant frequency
- spectral centroid
- spectral bandwidth
- band energy ratio
- spectral peak frequency

### 3. Time-frequency attributes

- spectrogram summary
- band-limited energy image
- time-varying dominant frequency

### 4. Event / anomaly candidates

- envelope
- STA/LTA
- short-window energy
- threshold crossing
- event candidate table
- time-channel bounding box

### 5. Interpretation support

- ROI selection
- annotation
- comparison before/after processing
- summary export
- figure export
- analysis report skeleton

Interpretation support here means DAS data review and analysis assistance. It
does not mean geologic inversion or specialized imaging.

## External references for target alignment

- DASCore / DASDAE: useful reference direction for DAS data management,
  analysis, visualization, processing conversion, and format IO organization.
- Xdas: useful reference direction for DAS data management, processing,
  visualization, metadata abstraction, and large-data/lazy-processing patterns.
- DASPy: useful reference direction for DAS processing toolbox organization,
  including preprocessing, filtering, spectral analysis, visualization,
  denoising, wavefield decomposition, and channel analysis.
- ObsPy: useful reference direction for general seismic time-series processing,
  filtering, visualization, and signal-processing API style.

These projects are target-alignment references only. No external project code is
copied, and this roadmap does not add new dependencies.
