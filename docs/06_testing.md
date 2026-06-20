# Testing

## Test goals

The project should test core logic independently from the GUI.

Current coverage:

- DASMetadata initialization.
- DASData dimension convention.
- Dimension mismatch errors.
- Reader registry registration and lookup.
- ZD HDF5 metadata read, full read, time slicing, channel slicing, downsampling, orientation transpose, missing path errors, and ambiguous orientation errors.
- Puniu DAT header parsing, full read, slicing, downsampling, start_time conversion, and length mismatch errors.
- plot_waterfall smoke test with non-interactive Matplotlib backend and image save.
- Metadata formatting to dict, text summary, missing-value display, and duration calculation.
- Reader preview API for synthetic ZD HDF5 and Puniu DAT, including automatic downsampling, unsupported formats, and metadata error wrapping.
- plot_waterfall edge cases for constant matrices and empty data.
- GUI smoke coverage: PyQt-free GUI model helpers, and MainWindow creation when PyQt5 and Matplotlib Qt support are available.

Future coverage:

- Preprocessing functions.
- Filter functions.
- STFT/FK/PSD numerical smoke tests.
- Reader edge cases with real small sample files.
- Additional plot types.
- GUI load-file behavior with real small files.

## Command

    python -m pytest

For cache-free runs during agent work:

    python -B -m pytest -p no:cacheprovider

## Optional dependency strategy

- h5py tests use pytest.importorskip("h5py").
- matplotlib plotting tests use pytest.importorskip("matplotlib") and the Agg backend.
- GUI smoke tests use pytest.importorskip("PyQt5") and pytest.importorskip("matplotlib"). If PyQt5 is not installed, GUI creation tests skip cleanly while core/io/plotting tests continue to run.
- GUI automation is deferred; GUI-independent state and worker logic should still be testable.
