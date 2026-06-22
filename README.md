# HCZ DAS View

HCZ DAS View is an early-stage DAS data viewing and analysis package. The
current focus is a small, testable workflow for reading DAS files, displaying
metadata, creating bounded preview data, and showing a waterfall image.
Phase 2A also adds bounded data selection helpers and waveform plotting. Phase
3A adds small preview-level preprocessing helpers. Phase 3D adds basic spectrum,
PSD/Welch, and single-channel spectrogram smoke paths. Phase 4A adds a
minimal FK transform and FK plotting smoke path. Phase 4B adds a minimal FK
velocity fan filter smoke path, and Phase 4D tightens FK mask-limit defaults
and user-facing validation.

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
- Synthetic tests for core readers and preview workflows.

Still intentionally deferred:

- Full analysis platform.
- Full STFT and advanced processing.
- Engineering-grade FK filter, F-J, and MASW workflows.
- Full-file preprocessing export.
- GUI filter parameter panel.
- SEGY/SAC/TDMS support.
- Real DAS data committed to the repository.

## Install

For development and tests:

    pip install -e .[dev]

For the optional GUI:

    pip install -e .[gui]

## Test

    python -m pytest

For cache-free agent/development runs:

    python -B -m pytest -p no:cacheprovider

## Examples

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

The FK filter example is a smoke path only. It builds a simple velocity fan
mask in FK coordinates, applies it to a bounded selection, inverts back to
time-channel data, and saves a filtered waterfall. At least one of `--vmin` or
`--vmax` is required: `--vmin` means velocities greater than or equal to that
limit, `--vmax` means velocities less than or equal to that limit, and both
together select the closed velocity range. By default the selected range is
passed; `--reject` rejects the selected velocity range. It does not implement
engineering-grade FK denoising, tapered interactive masks, F-J, MASW, or
dispersion picking.

Run the minimal GUI:

    python examples/run_gui.py

In the GUI, open a supported file first, then use the Waveform tab to enter a
zero-based channel index such as 10 or comma-separated indices such as
10,20,30. The GUI calls the shared data service; it does not read format
internals directly.

If installed with the console script, the GUI can also be started with:

    das-view-gui

## Data policy

Do not commit real DAS data or generated preview images. Large files should be
opened through slicing/downsampling preview workflows. The preprocessing,
filter, spectrum, and FK examples work on bounded preview/trace data only; they
do not export processed full-size DAS arrays. Filtering and spectrogram
analysis depend on scipy.signal. Spectrum and FK examples cover bounded
traces/previews only: they do not implement F-J, MASW, dispersion picking, or
export full processed arrays. The internal array convention is always:

    data.shape == (n_samples, n_channels)

Reader implementations convert external formats into this convention and store
source-specific details in metadata extra_attrs.

local_validation_paths.txt, validation_outputs/, outputs/, DAS data files, and
generated images are intentionally ignored by git.

## Development principles

- New runtime code must not import old_code.
- old_code/ is local reference material only.
- GUI code calls services such as create_preview, read_trace, format_metadata,
  plot_waterfall, plot_waveform, and preprocessing service helpers; it must not
  implement HDF5/DAT internals directly.
- Core, IO, processing, analysis, and plotting layers must not depend on PyQt5.
