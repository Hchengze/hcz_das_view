# HCZ DAS View

HCZ DAS View is an early-stage DAS data viewing and analysis package. The
current focus is a small, testable workflow for reading DAS files, displaying
metadata, creating bounded preview data, and showing a waterfall image.
Phase 2A also adds bounded data selection helpers and waveform plotting.

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
- Synthetic tests for core readers and preview workflows.

Still intentionally deferred:

- Full analysis platform.
- STFT/FK/PSD and advanced processing.
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
opened through slicing/downsampling preview workflows. The internal array
convention is always:

    data.shape == (n_samples, n_channels)

Reader implementations convert external formats into this convention and store
source-specific details in metadata extra_attrs.

local_validation_paths.txt, validation_outputs/, outputs/, DAS data files, and
generated images are intentionally ignored by git.

## Development principles

- New runtime code must not import old_code.
- old_code/ is local reference material only.
- GUI code calls services such as create_preview, read_trace, format_metadata,
  plot_waterfall, and plot_waveform; it must not implement HDF5/DAT internals
  directly.
- Core, IO, processing, analysis, and plotting layers must not depend on PyQt5.
