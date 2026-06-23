# Roadmap

## Project target

HCZ DAS View is a DAS Viewer / DAS Analysis package.

It focuses on DAS file reading, metadata display, time-channel visualization,
waveform analysis, spectrum/spectrogram/FK visualization, preprocessing,
filtering, feature extraction, GUI interaction, testing, documentation,
packaging, and long-term maintainability.

It is not a dedicated surface-wave inversion, MASW, F-J, or
dispersion-picking package.

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J
或频散拾取软件。
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
- GUI integration was added in Phase 5E through the service-backed Analysis
  tab.

Recommended next: Phase 6A.

### Phase 5D: ROI / annotation / export

Goal:

    Support GUI selection of time windows, channel ranges, and ROI regions;
    save analysis summaries as CSV / JSON; export figures; and support simple
    annotations.

Scope:

- ROI and annotation support are interpretation aids for DAS data review.
- Keep saved outputs explicit and user-directed; never commit generated output
  directories.

Status:

- Completed in Phase 5D for TimeChannelROI, Annotation, ROISet,
  event-candidate to ROI conversion, ROI statistics/spectral summaries,
  JSON/CSV export helpers, ROI overlay plotting, bounded CLI export workflows,
  and tutorial notebook updates.
- GUI analysis panel integration was added in Phase 5E.

Recommended next: Phase 6A.

### Phase 5E: GUI analysis panel

Goal:

    Connect statistics, band energy, envelope, and event candidate workflows to
    the GUI.

Scope:

- GUI code should call service-layer APIs.
- GUI-independent parser/state logic should remain testable without PyQt5.
- Heavy analysis should use the existing background-worker pattern.

Status:

- Completed in Phase 5E for a minimal Analysis tab with bounded statistics,
  band energy, spectral attributes, STA/LTA event candidates,
  envelope-threshold event candidates, ROI statistics, background workers,
  result tables, and JSON/CSV export through shared helpers.
- The GUI Analysis tab is a service integration layer only. It does not add
  new analysis algorithms and does not produce location or geologic
  interpretation results.

Recommended next: Phase 6A.

### Phase 6A: Packaging and release hardening

Goal:

    Complete pyproject metadata, console scripts, versioning, packaging docs,
    release checklist, and example-data strategy.

Scope:

- Keep optional GUI dependencies optional.
- Document how to validate local samples without committing data.
- Add release checklist coverage for tests, docs, examples, and ignored outputs.

Status:

- Completed in Phase 6A for package metadata, installed CLI/GUI entry points,
  Windows PyInstaller packaging notes, packaging smoke tests, and release
  checklist documentation.
- Clean-environment install validation is covered further in Phase 6C.
  Automated release CI and signed Windows executables remain follow-up work.

Release checklist:

- Check version metadata in pyproject.toml.
- Run full pytest.
- Run real/quasi-real sample smoke validation locally without committing data.
- Run installed CLI `--help` smoke and GUI launch smoke.
- Run example script `--help` smoke.
- Build wheel/sdist smoke artifacts.
- Run clean venv editable/install smoke.
- Run Windows PyInstaller smoke when preparing an exe.
- Update README and docs/09_tutorial_user_manual.ipynb.
- Confirm no real data, output artifacts, build/dist files, wheels, archives,
  or exe files are staged.
- Tag the release and prepare GitHub release notes.

Recommended next: Phase 6B or Phase 6C.

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

Status:

- Completed in Phase 6B for lightweight extension metadata,
  reader/processing/analysis/plotting/export extension wrappers, an in-memory
  extension registry, built-in capability metadata, optional on-demand Python
  entry point discovery, and the hcz-das-extensions inspection CLI.
- The plugin layer is an extension boundary for future packages. It does not
  replace the existing reader registry, IO data service, analysis service,
  plotting helpers, export helpers, or GUI workflows.

Recommended next: Phase 6D or Phase 7A.

### Phase 6C: Release polishing and clean-environment install validation

Goal:

    Validate wheel/sdist install in clean environments, refine release notes,
    and prepare optional automated release checks.

Scope:

- Keep release automation separate from analysis and reader features.
- Validate installed CLI/GUI entry points without committing build artifacts.
- Do not add real DAS data or generated outputs to the repository.

Status:

- Completed in Phase 6C for pyproject metadata review, ignored clean-venv
  install smoke, installed CLI help smoke, GUI help smoke through the module
  path, example help smoke, release validation tests, Windows packaging doc
  polish, release checklist updates, and tutorial notebook release-operation
  notes.
- The current environment does not have the `build` package installed, so
  wheel/sdist build smoke remains deferred rather than forcing a network
  install. Automated release CI and Windows exe signing remain future work.

Recommended next: Phase 6D.

### Phase 7A: API stability and documentation cleanup

Goal:

    Stabilize the public API inventory, import boundaries, compatibility
    policy, documentation consistency, and tutorial notebook guidance without
    adding algorithms, readers, GUI features, or plugin capabilities.

Scope:

- Keep public imports stable where practical.
- Verify that core/io/processing/analysis/plotting/plugins do not depend on
  PyQt5.
- Confirm that importing das_view does not trigger plugin discovery, data
  reads, GUI startup, or heavy computation.
- Keep event candidates, ROIs, and FK views documented as data-review aids,
  not location, inversion, or geologic interpretation outputs.

Status:

- Completed in Phase 7A for top-level/core exception exports, public API
  inventory, API compatibility policy, import-boundary tests, public API
  stability tests, handoff/roadmap consistency cleanup, and tutorial notebook
  public API / troubleshooting sections.
- The plugin API remains lightweight and still needs real third-party package
  validation before stronger external compatibility promises are made.

Recommended next: Phase 6D or Phase 7B.

### Phase 7B: Advanced DAS QC and multiband feature analysis

Goal:

    Add practical DAS data-quality, multiband feature-map, and local coherence
    analysis while keeping the project focused on general DAS Viewer / DAS
    Analysis workflows.

Scope:

- Implement Level 1 core QC report, bad-channel flags, noise-floor estimates,
  and SNR estimates.
- Implement Level 2 multiband energy maps and spectral attribute maps.
- Implement Level 3 local channel coherence as a spatial-continuity aid.
- Keep Level 4 traditional denoising/enhancement and Level 5 wavefield /
  apparent-moveout work as roadmap-only planning in this phase.
- Do not add surface-wave imaging, MASW, F-J, dispersion picking, source
  location, inversion, or deep-learning models.

Status:

- Completed in Phase 7B for DAS QC helpers, multiband feature maps, local
  channel coherence, bounded service functions, hcz-das-qc, example wrapper,
  Matplotlib plotting helpers, plugin metadata, tests, and tutorial updates.

Recommended next: Phase 6D or Phase 7C.

### Phase 7C: Traditional robust denoising and wavefield enhancement

Goal:

    Add Level 4 traditional, explainable, low-dependency signal-enhancement
    helpers for bounded DAS selections without adding deep learning, source
    location, inversion, MASW, F-J, dispersion picking, or GUI expansion.

Scope:

- Implement common-mode removal, despike, running median filtering, channel
  balancing, local normalization, time-space median filtering, and robust
  clipping.
- Add apply_denoise_workflow with before/after RMS, energy, finite-count
  metrics, and per-step history.
- Add bounded service functions, hcz-das-denoise, example wrapper, Matplotlib
  before/after and report-metric plotting helpers, plugin metadata, tests, and
  tutorial updates.
- Keep Level 5 wavefield decomposition / apparent moveout as deferred planning.

Status:

- Completed in Phase 7C for the core Level 4 traditional denoising and
  enhancement helpers. Outputs are signal-enhancement and data-review aids
  only, not geologic interpretation results.

Recommended next: Phase 6D or Phase 7D.

### Phase 7D: Wavefield decomposition and apparent moveout assisted analysis

Goal:

    Add Level 5 lightweight wavefield-assisted attributes for bounded DAS
    selections without adding source location, velocity inversion, surface-wave
    imaging, MASW, F-J, dispersion picking, or geologic interpretation.

Scope:

- Implement FK directional energy summaries and directional-energy ratios.
- Implement cross-correlation apparent slope and apparent velocity attributes.
- Implement local moveout coherence and a compact moveout summary report.
- Add bounded service functions, hcz-das-moveout, example wrapper, Matplotlib
  plotting helpers, plugin metadata, tests, and tutorial updates.
- Keep apparent velocity and direction labels documented as auxiliary
  attributes only.

Status:

- Completed in Phase 7D for the base Level 5 wavefield-assisted attribute
  layer. Outputs are review aids only and are not location, inversion, imaging,
  or geologic interpretation results.

Recommended next: Phase 6D or Phase 8A.

## DAS Analysis capability roadmap

## Five-level / 五级 DAS Analysis roadmap

### Level 1: DAS data quality / QC analysis

Highest priority. This layer helps determine whether DAS data are healthy,
which channels are trustworthy, and which time windows have poor quality.

- bad channel detection
- dead / quiet channel detection
- noisy channel detection
- clipping / saturation detection
- spike detection
- NaN / Inf / zero fraction
- channel RMS / STD / energy stability
- noise floor estimate
- SNR estimate
- channel quality score
- time-window quality score
- QC report JSON / CSV export

This is general DAS data quality control, not location, inversion, or geologic
interpretation.

### Level 2: Multiband / multispectral DAS feature map

This layer expands band energy and spectral attributes into interpretable
time-channel feature maps for DAS monitoring and assisted review.

- time-window x channel x band energy map
- low / middle / high frequency energy map
- band energy ratio map
- dominant frequency map
- spectral centroid map
- spectral bandwidth map
- spectral rolloff map
- multiband feature export
- ROI-based multiband summary

This is frequency-band and spectral-attribute analysis only, not dispersion
picking, MASW, F-J, or surface-wave imaging.

### Level 3: Cross-channel coherence / local similarity / spatial continuity

This layer uses DAS spatial continuity to support QC, coupling review, local
event screening, and spatial continuity monitoring.

- adjacent-channel correlation
- local channel coherence
- local similarity
- channel-lag coherence
- windowed spatial continuity score
- coherence map
- channel delay / lag estimate as an optional experimental feature

This layer is for data quality and spatial-continuity support only. It does not
perform velocity inversion, source location, or geologic interpretation.

### Level 4: Robust denoising / enhancement using traditional methods

Core traditional methods are implemented as of Phase 7C. Continue to prefer
interpretable, testable, low-dependency methods.

- common-mode removal
- median filter
- despike
- channel balancing
- local normalization
- time-space 2D median filtering
- robust clipping
- directional FK-domain pass / reject polish
- simple wavefield enhancement helpers

The implemented core covers common-mode removal, despike, running median
filtering, channel balancing, local normalization, time-space median filtering,
robust clipping, workflow history, service, CLI, and plotting helpers. More
directional wavefield enhancement remains future work. Deep-learning denoising
is not part of the current mainline and should remain future experimental/plugin
work.

### Level 5: Wavefield decomposition / apparent moveout assisted analysis

Base lightweight wavefield assistance is implemented as of Phase 7D. This
remains DAS analysis support, not a specialized imaging or inversion package.

- apparent slope attribute
- apparent velocity attribute
- directional energy ratio
- upgoing / downgoing or left-going / right-going energy helper
- FK directional energy summary
- event moveout auxiliary attributes

The implemented core covers FK directional energy, directional-energy ratio,
apparent slope by cross-correlation, apparent velocity attributes, local moveout
coherence, moveout summary reports, service, CLI, plotting, and plugin
metadata. Apparent velocity is an attribute, not a true subsurface velocity.
This is not surface-wave imaging, MASW, F-J, dispersion picking, source
location, or inversion. Any such interpretation workflow must be planned as a
separate experimental/plugin direction.

Priority order:

1. Level 1: DAS QC / channel quality
2. Level 2: Multiband feature map
3. Level 3: Local coherence / spatial continuity
4. Level 4: Traditional robust denoising / enhancement
5. Level 5: Wavefield decomposition / apparent moveout assisted analysis

## Tutorial notebook maintenance

- docs/09_tutorial_user_manual.ipynb is the stable user tutorial and operation
  manual.
- The existing eight markdown docs remain the project documentation set; the
  notebook is the single allowed additional tutorial file.
- Future rounds should update the notebook only for mature, user-facing
  capabilities.
- The notebook must not include development logs, test runs, commit history,
  real data paths, generated output artifacts, or private local paths.
- The notebook should explain method principles, key formulas, CLI examples,
  GUI workflows, and interpretation boundaries for stable functionality.

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
