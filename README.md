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
- Minimal GUI Analysis tab for bounded statistics, band energy, spectral
  attributes, event candidates, ROI statistics, and JSON/CSV export.
- Packaging metadata, installed CLI/GUI entry points, Windows PyInstaller
  packaging notes, and a release checklist.
- Lightweight plugin / extension metadata, registry, optional entry point
  discovery, and an installed extension-inspection CLI.
- Tutorial/user manual notebook at docs/09_tutorial_user_manual.ipynb for
  stable user-facing concepts, CLI examples, GUI workflow, and interpretation
  boundaries.
- Synthetic tests for core readers and preview workflows.

Still intentionally deferred:

- Broader real/quasi-real sample validation coverage beyond the initial local
  validation set.
- Full time-frequency analysis platform beyond the current single-channel
  spectrogram smoke path.
- Automated release CI, signed Windows executables, and broader
  clean-environment release validation across more machines.
- Full-file preprocessing export.
- GUI filter parameter panel.
- SEGY/SAC/TDMS support.
- Real DAS data committed to the repository.

## Install

For a standard local install from the repository root:

    pip install .

For development and tests:

    pip install -e .[dev]

For the optional GUI:

    pip install -e .[gui]

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

## Examples

## Installed entry points

After installation, the package provides these command names:

    hcz-das-validate --help
    hcz-das-preview --help
    hcz-das-stats --help
    hcz-das-spectrum --help
    hcz-das-events --help
    hcz-das-extensions --help
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

Generated outputs are local user artifacts and should not be committed.

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
2. Run the full pytest suite.
3. Run installed CLI `--help` smoke.
4. Run GUI `--help` smoke and GUI launch smoke.
5. Run example script `--help` smoke.
6. Run real/quasi-real sample smoke validation locally without committing data.
7. Build wheel and sdist smoke artifacts when the `build` package is available.
8. Run clean venv editable/install smoke.
9. Run Windows PyInstaller smoke if releasing an exe.
10. Update README and `docs/09_tutorial_user_manual.ipynb`.
11. Confirm no real data, output directories, images, JSON/CSV outputs,
    build/dist artifacts, wheels, archives, or exe files are staged.
12. Create the release tag and GitHub release notes.

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
opened through slicing/downsampling preview workflows. The preprocessing,
filter, spectrum, statistics, spectral-attributes, and FK examples work on
bounded preview/trace data only; they do not export processed full-size DAS arrays. Filtering and spectrogram
analysis depend on scipy.signal. Spectrum and FK examples cover bounded
traces/previews only and do not export full processed arrays. Specialized
inversion or picking workflows are outside the current main roadmap and would
belong in separate plugins or topic-specific extensions. The internal array
convention is always:

    data.shape == (n_samples, n_channels)

Reader implementations convert external formats into this convention and store
source-specific details in metadata extra_attrs.

local_validation_paths.txt, validation_outputs/, outputs/, DAS data files, and
generated images are intentionally ignored by git.

## Development principles

- New runtime code must not import old_code.
- old_code/ is local reference material only.
- GUI code calls services such as create_preview, read_trace, analysis
  services, export helpers, format_metadata, plot_waterfall, and plot_waveform;
  it must not implement HDF5/DAT internals directly.
- Core, IO, processing, analysis, plotting, and plugins layers must not depend
  on PyQt5.
