# HCZ DAS View

HCZ DAS View is a DAS Viewer / DAS Analysis package.

It focuses on DAS file reading, metadata display, time-channel visualization,
waveform analysis, spectrum/spectrogram/FK visualization, preprocessing,
filtering, feature extraction, GUI interaction, testing, documentation,
packaging, and long-term maintainability.

It is not a dedicated surface-wave inversion, MASW, F-J, or
dispersion-picking package.

本项目定位为 DAS 数据查看与分析软件包，不是面波成像、MASW、F-J
或频散拾取软件。
The current implementation provides a testable baseline for supported DAS file
readers, bounded preview and trace loading, metadata display, waterfall and
waveform plotting, basic preprocessing/filtering, spectrum/PSD/spectrogram
analysis, FK visualization, FK-domain smoke filtering, and an optional GUI.

## Current status

Implemented so far:

- ZD HDF5 reader.
- Puniu DAT reader.
- Unified metadata and internal data shape convention.
- Metadata formatting helpers.
- Reader registry and preview API.
- Matplotlib waterfall plot.
- Matplotlib waveform plot.
- Reader-independent data selection service for bounded windows and traces.
- Minimal optional PyQt5 GUI with waterfall preview and waveform tab.
- Basic preprocessing functions: demean, linear detrend, taper, normalize,
  standardize, and clipping.
- Basic scipy-based filters: lowpass, highpass, bandpass, bandstop, and notch.
- DASData preprocessing service that records processing history in metadata.
- Basic amplitude spectrum, power spectrum, periodogram PSD, Welch PSD, and
  single-channel spectrogram analysis helpers with Matplotlib plotting.
- File-level spectrum analysis service for CLI and future GUI reuse.
- Basic FK transform, simple velocity fan FK filter, file-level FK services,
  and Matplotlib FK plotting smoke paths.
- Basic DAS statistics analysis for global, time-wise, channel-wise, and
  bounded time/channel selections, including finite/NaN/Inf summaries.
- Basic spectral attribute analysis, including band energy, band energy ratio,
  dominant/peak frequency, spectral centroid, spectral bandwidth, and spectral
  rolloff.
- Event candidate analysis, including amplitude envelope, energy envelope,
  STA/LTA ratio, threshold crossing, and event candidate tables.
- ROI and annotation helpers, event-candidate to ROI conversion, ROI statistics
  and spectral summaries, JSON/CSV export helpers, and Matplotlib ROI overlay
  helpers.
- Advanced DAS QC and feature analysis, including channel quality metrics, bad
  channel flags, noise-floor and SNR estimates, multiband energy maps,
  spectral-attribute maps, and local channel coherence.
- Large-file workflow hardening with metadata-only memory estimates, optional
  analysis size guards, GUI metadata size hints, and bounded local performance
  smoke diagnostics.
- GUI Analysis tab for bounded statistics, band energy, spectral attributes,
  event candidates, ROI statistics, QC reports, bad-channel tables, multiband
  map summaries, denoise/enhancement reports, moveout summaries, directional
  energy summaries, and JSON/CSV export.
- Packaging metadata, installed CLI/GUI entry points, Windows PyInstaller
  packaging notes, and a release checklist.
- Lightweight plugin / extension metadata, registry, optional entry point
  discovery, and an installed extension-inspection CLI.
- Tutorial/user manual notebook at docs/09_tutorial_user_manual.ipynb for
  stable user-facing concepts, CLI examples, GUI workflow, and interpretation
  boundaries.
- Release-candidate validation package for local real/quasi-real DAS sample
  checks with bounded selections and path-free summaries.
- Optional GUI display backend exploration with Matplotlib default,
  experimental PyQtGraph waterfall/image preview, lazy VisPy detection, and
  shared display downsampling helpers.
- Synthetic tests for core readers and preview workflows.

Still intentionally deferred:

- Broader real/quasi-real sample validation coverage beyond the initial local
  validation set and beyond the local release-candidate validation package.
- Full time-frequency analysis platform beyond the current single-channel
  spectrogram smoke path.
- Remote GitHub Actions result confirmation, signed Windows executables, and
  broader clean-environment release validation across more machines.
- Full-file preprocessing export.
- GUI filter parameter panel.
- SEGY/SAC/TDMS support.
- Deep VisPy/OpenGL tiled or streaming display integration.
- Real DAS data committed to the repository.

## Install

For a standard local install from the repository root:

    pip install .

For development and tests:

    pip install -e .[dev]

For the optional GUI:

    pip install -e .[gui]

For optional experimental GUI display backends:

    pip install -e ".[display]"
    pip install -e ".[opengl]"

The `display` extra installs PyQtGraph for experimental waterfall/image
preview acceleration inside the GUI. The `opengl` extra installs VisPy and
PyOpenGL for capability exploration only. Matplotlib remains the default and
most stable display backend, and neither optional display extra is required
for CLI, analysis services, CI, or CPU-only use.

For optional GPU compute experiments, keep the package install CPU-first and
install the CuPy wheel that matches the local CUDA runtime separately, for
example:

    pip install -e .[gpu]
    pip install cupy-cuda12x

The `gpu` extra is intentionally empty because CuPy publishes CUDA-specific
wheel names. Do not install GPU dependencies into CI or CPU-only deployments
unless that machine is meant to run GPU compute.

For local packaging smoke work:

    pip install -e .[packaging]

The installed distribution name is `hcz-das-view`; the Python package remains
`das_view`.

For a release-candidate smoke check, use a temporary local virtual environment
that is ignored by git:

    python -m venv .tmp_release_venv
    .tmp_release_venv\Scripts\python -m pip install -e . --no-deps
    .tmp_release_venv\Scripts\python -m pip show hcz-das-view

The `--no-deps` form validates package metadata and editable installation only.
Importing or running analysis commands still requires runtime dependencies such
as numpy and scipy.

## Test

    python -m pytest

For cache-free agent/development runs:

    python -B -m pytest -p no:cacheprovider

CI-equivalent local release checks:

    python -B -m pytest -p no:cacheprovider --basetemp .tmp_pytest\local_full
    python tools/check_cli_help.py
    python tools/check_notebook_safety.py
    python tools/check_artifacts.py
    python -m build

The GitHub Actions workflows run synthetic-data tests, CLI help smoke, notebook
safety, artifact safety, and packaging smoke. They do not require real local
DAS data paths.

## Release candidate readiness

The current version remains `0.1.0.dev0` while the package is in development
and release-candidate preparation. A suitable next planning label is
`0.1.0-rc0`; do not create tags, publish GitHub Releases, or upload packages
until the project owner explicitly requests that release step.

Release candidate readiness checklist:

1. `git status clean` has been confirmed and the branch is synchronized with the intended remote.
2. Full pytest passes with repository-local temporary directories when needed.
3. CLI help smoke passes through `python tools/check_cli_help.py`.
4. Notebook safety passes through `python tools/check_notebook_safety.py`.
5. Artifact safety passes through `python tools/check_artifacts.py`.
6. Build smoke passes with `python -m build` when build tooling is installed.
7. The real-world validation package runs on local user-owned DAS samples.
8. Bounded performance smoke runs on representative local files.
9. GPU info smoke runs with `hcz-das-gpu --info` without requiring CuPy.
10. GUI help smoke runs with `python -m das_view.gui.app --help`.
11. Manual GUI open-file smoke is checked on at least one small supported file.
12. Windows PyInstaller smoke is checked if an exe candidate is planned.
13. GitHub Actions CI status is confirmed on the GitHub Actions page.
14. Release-smoke workflow status is confirmed when preparing a tag candidate.
15. Known limitations are current.
16. Version metadata is checked and the release notes draft is reviewed.
17. Candidate tag naming is planned but no tag is created automatically.

Release-candidate signoff checklist:

1. `git status clean` is confirmed.
2. Full pytest passes.
3. CLI help smoke, notebook safety, and artifact safety pass.
4. Real-world validation package, performance smoke, and GPU info smoke are
   reviewed.
5. GUI manual validation checklist is completed on a supported local file.
6. Windows packaging smoke is reviewed if an exe candidate is planned.
7. GitHub Actions status is checked on the GitHub Actions page.
8. Known limitations, version metadata, and release notes draft are reviewed.
9. Tag planning is manual only; no tag, PyPI release, or GitHub Release is
   created during signoff preparation.

## Examples

## Installed entry points

After installation, the package provides these command names. These are the
stable user-facing entry points:

    hcz-das-validate --help
    hcz-das-preview --help
    hcz-das-stats --help
    hcz-das-spectrum --help
    hcz-das-events --help
    hcz-das-extensions --help
    hcz-das-qc --help
    hcz-das-denoise --help
    hcz-das-moveout --help
    hcz-das-gpu --help
    hcz-das-view --help

The command-line tools use bounded service-layer workflows and do not read
HDF5/DAT internals directly. `hcz-das-view` launches the optional PyQt5 GUI.
The older `das-view-gui` GUI script is retained for compatibility.
On Windows, a `gui-scripts` executable may not echo help text in every shell;
`python -m das_view.gui.app --help` is the visible GUI-help smoke path.

Examples:

    hcz-das-validate input.h5
    hcz-das-preview input.h5 --output preview.png
    hcz-das-stats input.h5 --axis global --output stats.json
    hcz-das-spectrum input.h5 --channel 10 --mode welch --output welch.png
    hcz-das-events input.h5 --method stalta --sta 50 --lta 500 --trigger-on 3.0 --output events.csv
    hcz-das-extensions --list
    hcz-das-extensions --kind analysis --json
    hcz-das-qc input.h5 --quality-report --output qc_report.json
    hcz-das-qc input.h5 --bad-channels --output bad_channels.csv
    hcz-das-qc input.h5 --multiband 1 5 5 20 20 80 --window-samples 1024 --step-samples 512 --output multiband.json
    hcz-das-qc input.h5 --coherence --channel-lag 1 --output coherence.json
    hcz-das-denoise input.h5 --common-mode median --output-report denoise_report.json
    hcz-das-denoise input.h5 --despike --z-threshold 8.0 --channel-balance rms --output-report enhancement_report.json
    hcz-das-moveout input.h5 --directional-energy --output direction.json
    hcz-das-moveout input.h5 --apparent-moveout --channel-lag 1 --window-samples 1024 --step-samples 512 --output moveout.json
    hcz-das-moveout input.h5 --summary --channel-lag 1 --output moveout_summary.json
    hcz-das-gpu --info
    hcz-das-gpu --benchmark --backend cpu --shape 4096 512
    hcz-das-gpu --compare --shape 4096 512
    hcz-das-gpu --validate-numeric --shape 1024 128
    hcz-das-stats input.h5 --max-estimated-mb 256
    hcz-das-stats input.h5 --backend gpu --max-estimated-mb 256
    hcz-das-qc input.h5 --quality-report --max-estimated-mb 256
    hcz-das-qc input.h5 --quality-report --backend gpu --max-estimated-mb 256
    hcz-das-denoise input.h5 --common-mode median --max-estimated-mb 256
    hcz-das-moveout input.h5 --summary --max-estimated-mb 256
    hcz-das-moveout input.h5 --directional-energy --backend gpu --max-estimated-mb 256

Generated outputs are local user artifacts and should not be committed.

Developer/example scripts are separate from installed CLI entry points. They
are intended for local validation, smoke checks, and usage examples:

    python examples/validate_file.py input.h5
    python examples/validate_local_samples.py
    python examples/real_world_validation_package.py --paths-file local_validation_paths.txt --quick
    python examples/performance_smoke.py input.h5 --operations preview,statistics,qc
    python examples/gpu_benchmark.py --info
    python examples/preview_file.py input.h5 --output preview.png
    python examples/statistics_file.py input.h5 --output stats.json
    python examples/spectral_attributes_file.py input.h5 --bands 1 5 5 20
    python examples/event_detection_file.py input.h5 --method stalta
    python examples/roi_export_file.py input.h5 --roi 0 1000 0 100
    python examples/qc_file.py input.h5 --quality-report
    python examples/denoise_file.py input.h5 --common-mode median
    python examples/moveout_file.py input.h5 --summary

Use placeholder paths in documentation and keep real path lists local.

## Optional GPU compute backend

Phase 9A adds an optional compute acceleration layer under
`das_view.acceleration`. The default backend is always CPU, and
`backend="auto"` currently resolves to CPU as well. GPU compute is used only
when a function or CLI receives `backend="gpu"` / `--backend gpu`.

Current optional GPU paths are limited to low-risk numerical kernels:

- `basic_statistics` reductions.
- `channel_quality_metrics` / `data_quality_report` QC reductions.
- `band_energy`, `spectral_attributes`, `multiband_energy_map`, and
  `spectral_attribute_map` FFT-backed feature calculations.
- `fk_transform`, `fk_directional_energy`, and moveout summary directional
  energy.

CuPy is imported lazily only when GPU is explicitly requested. Importing
`das_view` does not import CuPy, CI does not require a GPU, and all GPU-backed
results are copied back to NumPy arrays before they are returned. If CuPy is
not installed, `--backend gpu` reports a user-readable error; use
`--backend cpu` for the stable default. Phase 9A is compute-only and does not
add PyQtGraph, VisPy, OpenGL, PyTorch, TensorFlow, or deep-learning workflows.

Phase 9A.1 adds GPU diagnostics and synthetic benchmark workflows:

    hcz-das-gpu --info
    hcz-das-gpu --benchmark --backend cpu --shape 4096 512
    hcz-das-gpu --benchmark --backend gpu --shape 4096 512
    hcz-das-gpu --compare --shape 4096 512
    hcz-das-gpu --validate-numeric --shape 1024 128
    python examples/gpu_benchmark.py --info
    python examples/gpu_benchmark.py --benchmark --backend cpu --shape 4096 512

`hcz-das-gpu --info` succeeds on CPU-only machines and reports that CuPy/GPU is
unavailable when appropriate. `--compare` and `--validate-numeric` skip GPU
work cleanly without CuPy. Explicit `--benchmark --backend gpu` requires CuPy
and reports a readable error if it is unavailable. Synthetic benchmark timings
are diagnostic only; they do not represent all real large-file IO, slicing, or
plotting costs.

Phase 9C adds validation against a separate local CuPy environment. That pass
confirmed that diagnostics can detect CuPy, CUDA runtime/driver fields, one
CUDA device, and GPU memory. Phase 9C.2 reran validation after activating the
Conda GPU environment first. Activation made the NVRTC builtins DLL visible
and a simple CuPy arithmetic kernel succeeded, but the reduction kernels used
by the project still timed out. GPU diagnostics now distinguish import/device
visibility from working reduction-kernel runtime readiness. GPU acceleration
remains experimental and environment-dependent; the default backend is still
CPU. GPU benchmark, numeric validation, and bounded real-data smoke report this
as a user-readable GPU runtime error. On Windows with Conda, activate the GPU
environment before validation; direct environment-python calls can miss Conda
DLL search path setup.

## Large-file workflow

Large DAS files should be opened through bounded selections rather than full
array reads. Preview and analysis services use safe defaults such as
`max_samples` and `max_channels`; key CLI tools also accept
`--max-estimated-mb` to reject selections whose estimated dense array size is
too large for the intended workflow.

The GUI metadata panel displays sample count, channel count, duration, spacing,
and estimated full array size. This estimate is derived from metadata and does
not read the full data matrix.

The GUI also applies the same large-file principle before heavier tab actions:
Waterfall preview uses bounded `max_samples` / `max_channels`, Waveform,
Spectrum, FK, and Analysis estimate planned selection memory before running,
and oversized selections are stopped with a user-readable message. Safe working
presets are intentionally conservative: small preview is about 2000 samples x
256 channels, medium/analysis selection is about 4096 samples x 512 channels,
and FK starts from about 2048 samples x 256 channels. GUI advanced analysis
types such as multiband summary, moveout summary, and directional energy use a
more conservative run-before memory limit because they are heavier than simple
reductions. Export buttons stay disabled until a current Analysis result
exists; generated JSON/CSV files are local user artifacts and should not be
committed.

## GUI advanced analysis

The optional PyQt5 GUI Analysis tab now exposes selected mature service-backed
DAS analysis reports:

- `QC report` shows channel count, bad-channel count, dead/noisy/low-energy
  counts, mean quality score, and NaN/Inf/clipping/spike summaries.
- `Bad channels` shows a focused table of channel, reason flags, quality
  score, RMS, STD, spike count, and clipping fraction.
- `Multiband map summary` shows band/window dimensions and per-band global
  mean/max/ratio rows without drawing a full heat map.
- `Denoise report` runs traditional enhancement workflows and displays
  before/after RMS, energy, finite count, and per-step rows.
- `Moveout summary` and `Directional energy` display wavefield-assisted
  attributes from existing services.

These GUI actions call `das_view.analysis.service` through GUI workers. The GUI
does not implement QC, denoise, multiband, FK, or moveout algorithms, and it
does not inspect HDF5/DAT internal paths. Moveout/apparent velocity values are
auxiliary wavefield attributes only. Directional energy is an FK-domain review
attribute. Event candidates, ROI rows, denoise reports, QC flags, and moveout
summaries are data-review aids, not location, inversion, velocity-model, or
geologic interpretation results.

## Optional GUI display backends

The GUI waterfall preview keeps Matplotlib as the default backend. Phase 9B
adds an optional display-backend layer for future large-array display work:

- `matplotlib` is always selected by default and remains the stable path.
- `pyqtgraph` is an experimental waterfall/image preview path. It is imported
  lazily only when the GUI checks or uses that backend.
- `vispy` and `PyOpenGL` are checked lazily for installation and capability
  reporting only; deep OpenGL display integration is deferred.

Install optional display packages only on machines intended to test the GUI
display backend:

    pip install -e ".[gui,display]"
    pip install -e ".[gui,opengl]"

The display backend affects only the waterfall/image preview path. It does not
change waveform, spectrum, FK, Analysis tab behavior, CLI tools, service APIs,
or the optional GPU compute backend. If PyQtGraph or VisPy is unavailable, the
GUI falls back to Matplotlib or reports the optional backend as unavailable.
Large selections are still downsampled for display through shared
GUI-independent helpers, and screenshots or display benchmark outputs are local
artifacts that should not be committed.

Phase 9B.1 adds explicit VisPy / PyOpenGL capability validation helpers. They
report VisPy import status, PyOpenGL import status, versions when available,
and whether a minimal OpenGL context probe was requested. OpenGL context probes
are optional and return `context_unavailable` instead of failing in headless
environments. On machines where VisPy or PyOpenGL cannot be installed, the
report remains readable and the GUI continues to use Matplotlib by default.

For local performance diagnosis on user-owned data, run bounded smoke
operations:

    python examples/performance_smoke.py input.h5 --max-samples 4096 --max-channels 512
    python examples/performance_smoke.py input.dat --operations preview,statistics,qc --max-estimated-mb 256
    python examples/performance_smoke.py input.h5 --backend cpu --operations statistics,qc
    python examples/performance_smoke.py input.h5 --gpu-info --compare-backends --operations statistics

The smoke utility prints operation name, elapsed seconds, selection shape, and
estimated memory. Optional JSON timing output is a local artifact and should
not be committed.

## Advanced DAS QC and multiband features

The Phase 7B analysis layer adds general DAS data-quality and interpretable
feature workflows:

- `channel_quality_metrics` and `data_quality_report` summarize per-channel
  RMS, standard deviation, absolute mean, energy, NaN/Inf/zero fractions,
  clipping fraction, spike count, dead/quiet/noisy/low-energy flags, quality
  score, and bad-channel table rows.
- `estimate_noise_floor` and `estimate_snr` provide simple per-channel
  noise-floor and signal-to-noise estimates for bounded selections.
- `multiband_energy_map` computes time-window x channel x band energy maps.
- `spectral_attribute_map` computes windowed dominant-frequency, centroid,
  bandwidth, and rolloff maps.
- `local_channel_coherence` computes adjacent or lagged channel correlation as
  a spatial-continuity aid.

These outputs are DAS data-quality and feature summaries. They are not
earthquake/source locations, velocity inversions, MASW, F-J, dispersion picking,
surface-wave imaging, or geologic interpretation results.

## Traditional DAS denoising and enhancement

The Phase 7C processing layer adds Level 4 traditional signal-enhancement
helpers for bounded DAS selections:

- `common_mode_removal` subtracts per-sample common mode across channels.
- `despike` replaces robust outliers with median-baseline values.
- `running_median_filter` and `time_space_median_filter` provide small
  median-based smoothing helpers.
- `channel_balance` scales channels toward comparable RMS, STD, or max-abs
  levels.
- `local_normalize` normalizes by a local running RMS/STD/max-abs scale.
- `robust_clip` performs percentile winsorization.
- `apply_denoise_workflow` records step history and before/after RMS, energy,
  and finite-count metrics.

These helpers are traditional signal-enhancement tools. They do not perform
deep-learning denoising, source location, inversion, MASW, F-J, dispersion
picking, surface-wave imaging, or geologic interpretation.

## Level 5 wavefield / apparent moveout assistance

The Phase 7D analysis layer adds lightweight wavefield-assisted attributes:

- `fk_directional_energy` summarizes positive/negative/zero wavenumber FK
  energy as a directionality aid.
- `directional_energy_ratio` reports a balanced directional-energy attribute.
- `estimate_apparent_slope_xcorr` estimates a local apparent slope in
  seconds per metre from bounded channel pairs.
- `apparent_velocity_from_slope` converts an apparent slope attribute into an
  apparent-velocity attribute.
- `local_moveout_coherence` summarizes local moveout correlation peaks.
- `moveout_summary_report` combines FK directional energy and moveout
  attributes into one report.

These are wavefield-assisted analysis attributes only. They are not source
locations, velocity inversions, surface-wave imaging, MASW, F-J, dispersion
picking, or geologic interpretation results. Apparent velocity is an attribute,
not a measured propagation velocity.

## Extension architecture

`das_view.plugins` provides a lightweight extension metadata and registry layer
for future readers, processing operations, analysis functions, plotting helpers,
and export helpers. Built-in extension metadata describes the current stable
package capabilities such as ZD HDF5, Puniu DAT, statistics, event candidates,
ROI summaries, waterfall/waveform/FK plots, and JSON/CSV export.

The extension registry is intentionally not a replacement for the existing
reader registry or service APIs. Existing workflows continue to call stable
services directly. Plugin discovery through Python entry points is explicit and
on-demand; importing `das_view` does not scan external plugins, read data, or
start GUI code.

## Public API and compatibility

Stable public API:

- `das_view`: core data containers and project exceptions.
- `das_view.io`: reader-independent preview, selection, and trace services.
- `das_view.processing`: documented preprocessing/filter functions and
  `apply_preprocess`.
- `das_view.analysis`: documented analysis helpers and file-level services.
- `das_view.plotting`: documented Matplotlib plotting helpers.
- `das_view.plugins`: lightweight extension metadata, registry, builtins, and
  explicit entry point discovery helpers.
- Installed CLI entry points such as `hcz-das-validate`, `hcz-das-stats`,
  `hcz-das-events`, and `hcz-das-extensions`.

Experimental API:

- The plugin extension API is intentionally lightweight and may be adjusted as
  real third-party packages are validated.
- GUI internals, worker classes, and model implementation details are not
  guaranteed as long-term public API.

Internal helpers:

- Underscore-prefixed functions, private parsing helpers, concrete reader
  internals, and module-local implementation details may change without notice.

Compatibility policy:

- Public API is kept stable within the current development line when practical.
- CLI entry points are user-facing and should remain backward compatible where
  reasonable.
- The internal data shape convention is always `(n_samples, n_channels)`.
- Event candidates and ROI are data analysis aids, not source-location,
  earthquake-location, inversion, or geologic interpretation results.

## Script examples

Create a preview image from a supported file:

    python examples/preview_file.py input.h5 --output preview.png

Validate a real or quasi-real sample without adding data to the repo:

    python examples/validate_file.py input.h5
    python examples/validate_file.py input.dat --output preview.png
    python examples/validate_file.py input.h5 --waveform-output trace.png --channel 10

Batch-validate local samples listed in an ignored local_validation_paths.txt:

    python examples/validate_local_samples.py
    python examples/validate_local_samples.py --save-preview-dir validation_outputs

Run bounded local performance smoke checks:

    python examples/performance_smoke.py input.h5 --operations preview,statistics,qc
    python examples/performance_smoke.py input.dat --max-samples 4096 --max-channels 512 --max-estimated-mb 256

Run the release-candidate real-world validation package on a local path list:

    python examples/real_world_validation_package.py --paths-file local_validation_paths.txt --quick
    python examples/real_world_validation_package.py --paths-file local_validation_paths.txt --include-gpu-info
    python examples/real_world_validation_package.py --paths-file local_validation_paths.txt --output validation_summary.json

The validation package reads only bounded selections. Its JSON summary records
sample index, suffix, reader, shape, and operation status, but not full paths
or file names. `local_validation_paths.txt` and generated validation summaries
are local artifacts and must stay out of version control.

Plot one or more waveform traces:

    python examples/plot_waveform.py input.h5 --channel 10 --output trace.png
    python examples/plot_waveform.py input.dat --channels 10 20 30 --output traces.png

Apply basic preprocessing to a bounded preview and save a processed waterfall:

    python examples/preprocess_file.py input.h5 --output preview_processed.png --demean --taper 0.05 --normalize
    python examples/preprocess_file.py input.dat --output preview_processed.png --demean --normalize

Apply a basic filter to a bounded preview and save a filtered waterfall:

    python examples/filter_file.py input.h5 --output preview_filtered.png --bandpass 1 50
    python examples/filter_file.py input.dat --output preview_filtered.png --lowpass 80
    python examples/filter_file.py input.h5 --output preview_filtered.png --notch 50

Compute a basic single-channel spectrum, PSD/Welch estimate, or spectrogram:

    python examples/spectrum_file.py input.h5 --channel 10 --output spectrum.png
    python examples/spectrum_file.py input.dat --channel 10 --power --output power.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd periodogram --output psd.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd welch --nperseg 512 --output welch.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd welch --db --output welch_db.png
    python examples/spectrum_file.py input.h5 --channel 10 --spectrogram --output spectrogram.png
    python examples/spectrum_file.py input.h5 --channel 10 --bandpass 1 50 --psd welch --output filtered_welch.png

Compute a bounded FK transform and save an FK image:

    python examples/fk_file.py input.h5 --output fk.png
    python examples/fk_file.py input.dat --output fk.png --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512
    python examples/fk_file.py input.h5 --output fk_db.png --db
    python examples/fk_file.py input.h5 --output fk_power.png --output-mode power
    python examples/fk_file.py input.h5 --output fk_filtered.png --bandpass 1 50

The FK example reads a bounded time/channel selection by default. It supports
basic FK amplitude or power plots only.

Apply a minimal FK velocity fan filter to a bounded selection:

    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.dat --output filtered_waterfall.png --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --reject --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --save-fk --vmin 300 --vmax 3000

The FK filter example is a smoke path only for DAS 2D wavefield inspection. It
builds a simple velocity fan mask in FK coordinates, applies it to a bounded
selection, inverts back to time-channel data, and saves a filtered waterfall.
At least one of `--vmin` or `--vmax` is required: `--vmin` means velocities
greater than or equal to that limit, `--vmax` means velocities less than or
equal to that limit, and both together select the closed velocity range. By
default the selected range is passed; `--reject` rejects the selected velocity
range. It is an FK-domain smoke filter, not a specialized inversion or picking
workflow.

Compute bounded DAS statistics:

    python examples/statistics_file.py input.h5
    python examples/statistics_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512
    python examples/statistics_file.py input.h5 --axis time
    python examples/statistics_file.py input.h5 --axis channel
    python examples/statistics_file.py input.h5 --percentiles 1 5 50 95 99
    python examples/statistics_file.py input.h5 --output stats.json
    python examples/statistics_file.py input.h5 --output stats.csv

The statistics example reads a bounded time/channel selection by default. It
reports count, finite/NaN/Inf counts, mean, standard deviation, min, max,
median, percentiles, RMS, absolute mean, peak-to-peak, and energy. `--axis
time` reduces along the time/sample axis and returns one value per channel;
`--axis channel` reduces along the channel axis and returns one value per time
sample. This is a general DAS analysis feature, not a specialized imaging
workflow.

Compute bounded DAS band energy or spectral attributes:

    python examples/spectral_attributes_file.py input.h5 --bands 1 5 5 20 20 80
    python examples/spectral_attributes_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --bands 1 10 10 50
    python examples/spectral_attributes_file.py input.h5 --attributes
    python examples/spectral_attributes_file.py input.h5 --attributes --frequency-range 1 80
    python examples/spectral_attributes_file.py input.h5 --bands 1 5 5 20 --average-channels
    python examples/spectral_attributes_file.py input.h5 --output attrs.json
    python examples/spectral_attributes_file.py input.h5 --output band_energy.csv

The spectral attributes example reads a bounded time/channel selection by
default. It supports frequency-band energy, band power, band energy ratio,
dominant or peak frequency, peak power, spectral centroid, spectral bandwidth,
spectral rolloff, and optional channel averaging. This is a general DAS
analysis feature for signal and wavefield inspection.

Detect bounded DAS event candidates:

    python examples/event_detection_file.py input.h5 --method stalta --sta 50 --lta 500 --trigger-on 3.0
    python examples/event_detection_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --method stalta --sta 25 --lta 250 --trigger-on 3.0 --trigger-off 1.5
    python examples/event_detection_file.py input.h5 --method envelope --threshold 0.8
    python examples/event_detection_file.py input.h5 --output events.json
    python examples/event_detection_file.py input.h5 --output events.csv

The event detection example reads a bounded time/channel selection by default.
It supports STA/LTA and envelope-threshold event candidate workflows, writing
candidate tables to JSON or CSV. Candidate outputs are screening aids for DAS
data review; they are not earthquake locations, source locations, or final
interpretation results.

Create/export DAS ROIs and ROI summaries:

    python examples/roi_export_file.py input.h5 --detect-events --method stalta --sta 50 --lta 500 --trigger-on 3.0 --output-rois rois.json
    python examples/roi_export_file.py input.h5 --detect-events --method envelope --threshold 0.8 --output-events events.csv --output-rois rois.json
    python examples/roi_export_file.py input.h5 --roi 0 1000 0 100 --output-summary roi_summary.json
    python examples/roi_export_file.py input.h5 --roi 0 1000 0 100 --output-summary roi_summary.csv

ROI tools use half-open time/channel windows and bounded reads. Event
candidates can be converted to ROIs for review, export, and summary analysis.
ROIs and annotations are data review aids; they are not source locations,
earthquake locations, inversion outputs, or geologic interpretation results.

Run the minimal GUI:

    python examples/run_gui.py

In the GUI, open a supported file first, then use the Waveform tab to enter a
zero-based channel index such as 10 or comma-separated indices such as
10,20,30. The GUI calls the shared data service; it does not read format
internals directly.

For large files, review the file-summary panel before running tab operations.
It shows reader name, sample/channel counts, sample spacing when available,
estimated full array size, safe preview/analysis hints, and a large-file
warning when the dense array would be too large for blind full reads.
Waterfall, Waveform, Spectrum, FK, and Analysis actions run a metadata-only
selection estimate before dispatching background work; reduce the time/channel
range or increase downsampling when the warning appears.

The Analysis tab runs bounded service-backed tasks for statistics, band energy,
spectral attributes, STA/LTA event candidates, envelope-threshold event
candidates, and ROI statistics. Analysis results are shown as summaries and
tables, and can be exported as JSON or CSV through the shared export helpers.
Event candidates, ROI statistics, and exported tables are DAS data review aids;
they are not source-location or geologic interpretation results.

If installed with the console script, the GUI can also be started with:

    hcz-das-view
    das-view-gui

## Windows packaging

Windows PyInstaller packaging notes live at:

    packaging/README_windows_packaging.md

The helper script is:

    packaging/build_windows.ps1

The PyInstaller spec is:

    packaging/hcz_das_view.spec

Build artifacts under `build/` and `dist/`, wheels, archives, and exe files are
local artifacts and must not be committed.
Clean release-validation environments such as `.tmp_release_venv/` are also
local artifacts and must not be committed.

## Release checklist

Before tagging or publishing a release:

1. Check version metadata in `pyproject.toml`.
2. Run the full pytest suite or confirm the CI test matrix has passed.
3. Run CLI `--help` smoke through `python tools/check_cli_help.py`.
4. Run notebook and artifact safety checks.
5. Run example script `--help` smoke when examples are changed.
6. Run real/quasi-real sample smoke validation locally without committing data.
7. Build wheel and sdist smoke artifacts when the `build` package is available.
8. Run clean venv editable/install smoke.
9. Run Windows PyInstaller smoke if releasing an exe.
10. Update README and `docs/09_tutorial_user_manual.ipynb`.
11. Confirm no real data, output directories, images, JSON/CSV outputs,
    build/dist artifacts, wheels, archives, or exe files are staged.
12. Review the release notes draft and candidate tag name.
13. Create a release tag only after explicit project-owner approval.

GitHub Actions:

- `.github/workflows/ci.yml` runs ubuntu and Windows tests, CLI help smoke,
  notebook safety, artifact safety, and packaging smoke.
- `.github/workflows/release-smoke.yml` runs manually or on `v*` tags. It
  builds and installs local artifacts for smoke validation only; it does not
  publish to PyPI or create a GitHub Release.

## Tutorial notebook

The user-facing tutorial and operation manual lives at:

    docs/09_tutorial_user_manual.ipynb

It covers the stable DAS Viewer / DAS Analysis workflow, data shape convention,
metadata, waterfall/waveform views, preprocessing, filters, spectrum/PSD/
spectrogram, statistics, spectral attributes, FK inspection, event candidates,
ROI/annotation/export workflows, CLI usage, GUI usage including the Analysis
tab, and interpretation boundaries. It uses synthetic data and placeholder
paths only.

## Data policy

Do not commit real DAS data or generated preview images. Large files should be
opened through slicing/downsampling preview workflows and bounded analysis
selections. The preprocessing, filter, spectrum, statistics,
spectral-attributes, QC, denoise, moveout, and FK examples work on bounded
preview/trace/selection data only; they do not export processed full-size DAS arrays. Filtering and spectrogram
analysis depend on scipy.signal. Spectrum and FK examples cover bounded
traces/previews only and do not export full processed arrays. Specialized
inversion or picking workflows are outside the current main roadmap and would
belong in separate plugins or topic-specific extensions. The internal array
convention is always:

    data.shape == (n_samples, n_channels)

Reader implementations convert external formats into this convention and store
source-specific details in metadata extra_attrs.

local_validation_paths.txt, validation_outputs/, outputs/, DAS data files,
generated images, JSON/CSV outputs, and temporary pytest/performance artifacts
are intentionally ignored by git.

## Known limitations

- Supported file formats currently focus on ZD HDF5 and Puniu DAT.
- Larger real-world validation across more instruments, durations, and file
  sizes is still needed.
- GUI manual user experience still needs more user feedback.
- GPU compute requires a user-installed CuPy wheel matching the local CUDA
  runtime; CPU remains the default.
- GPU acceleration remains experimental and environment-dependent.
- GPU benchmark results require both a detected CUDA device and a working CuPy
  reduction runtime; a device-only environment is not sufficient.
- Optional PyQtGraph waterfall display is experimental and needs real large-file
  GUI validation.
- VisPy / PyOpenGL capability validation is import-only by default; no-context
  environments cleanly report unavailable or deferred status.
- VisPy/OpenGL deep display acceleration is deferred.
- Windows exe artifacts are currently unsigned.
- Plugin APIs still need validation with real third-party packages.
- Moveout and apparent velocity outputs are auxiliary attributes only, not
  ground-truth velocities, source location, inversion, imaging, or geologic
  interpretation.
- Event candidates are screening aids, not localization results.
- ROI is an analysis window, not an interpretation conclusion.

## Development principles

- New runtime code must not import old_code.
- old_code/ is local reference material only.
- GUI code calls services such as create_preview, read_trace, analysis
  services, export helpers, format_metadata, plot_waterfall, and plot_waveform;
  it must not implement HDF5/DAT internals directly.
- Core, IO, processing, analysis, plotting, and plugins layers must not depend
  on PyQt5.
