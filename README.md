# HCZ DAS View

HCZ DAS View is an early-stage DAS data viewing and analysis package. The
current focus is a small, testable workflow for reading DAS files, displaying
metadata, creating bounded preview data, and showing a waterfall image.

## Current status

Implemented so far:

- ZD HDF5 reader.
- Puniu DAT reader.
- Unified metadata and internal data shape convention.
- Metadata formatting helpers.
- Reader registry and preview API.
- Matplotlib waterfall plot.
- Minimal optional PyQt5 GUI.
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

Run the minimal GUI:

    python examples/run_gui.py

If installed with the console script, the GUI can also be started with:

    das-view-gui

## Data policy

Do not commit real DAS data or generated preview images. Large files should be
opened through slicing/downsampling preview workflows. The internal array
convention is always:

    data.shape == (n_samples, n_channels)

Reader implementations convert external formats into this convention and store
source-specific details in metadata extra_attrs.

## Development principles

- New runtime code must not import old_code.
- old_code/ is local reference material only.
- GUI code calls services such as create_preview, format_metadata, and
  plot_waterfall; it must not implement HDF5/DAT internals directly.
- Core, IO, processing, analysis, and plotting layers must not depend on PyQt5.
