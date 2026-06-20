# Testing

## Test goals

The project should test core logic independently from the GUI.

Current coverage:

- DASMetadata initialization.
- DASData dimension convention.
- Dimension mismatch errors.
- Reader registry registration and lookup.
- ZD HDF5 metadata read, full read, time slicing, channel slicing, downsampling, orientation transpose, missing path errors, and ambiguous orientation errors.
- ZD HDF5 edge cases for numpy scalar attrs, bytes attrs, missing RawData,
  Count/NumberOfLoci mismatches, ambiguous orientation, and empty selections.
- Puniu DAT header parsing, full read, slicing, downsampling, start_time conversion, and length mismatch errors.
- Puniu DAT edge cases for incomplete headers, invalid seek, unaligned payloads,
  invalid timestamps, and empty/out-of-range selections.
- plot_waterfall smoke test with non-interactive Matplotlib backend and image save.
- Metadata formatting to dict, text summary, missing-value display, and duration calculation.
- Reader preview API for synthetic ZD HDF5 and Puniu DAT, including automatic downsampling, unsupported formats, and metadata error wrapping.
- plot_waterfall edge cases for constant matrices and empty data.
- GUI smoke coverage: PyQt-free GUI model helpers, and MainWindow creation when PyQt5 and Matplotlib Qt support are available.
- GUI preview limit parsing, status summary formatting, and error formatting.
- Data service coverage for synthetic ZD HDF5 and Puniu DAT selections, trace reads,
  slicing, downsampling, invalid channels, empty selections, and unsupported formats.
- Phase 2B extends data service trace coverage to contiguous multi-channel reads,
  non-contiguous reads, non-increasing channel order, duplicate channels, negative
  channels, empty channel selections, non-integer channel sequences, and metadata
  spacing behavior for non-contiguous selections.
- plot_waveform coverage for single-channel, multi-channel, image save with Agg,
  invalid channels, and constant/zero data.
- GUI waveform smoke coverage checks that the Waveform tab and controls can be
  constructed when PyQt5 is available.
- Channel parser tests are PyQt-free and cover single channel input, comma-separated
  input, spaces, duplicate preservation, empty input, non-integer input, and negative
  input.
- Local validation script tests cover path-list parsing, missing path-list friendly
  exit behavior, and path-safe preview summaries.
- Basic preprocessing function tests cover demean, linear detrend, taper,
  maxabs/minmax normalization, standardization, clipping, invalid parameters,
  NaN/Inf behavior, and no in-place modification.
- Preprocessing service tests cover DASData copying, metadata preservation,
  preprocessing_history records, multi-step ordering, unknown steps, and invalid
  parameters.
- Preprocessing example tests cover CLI step construction without requiring real
  DAS input files.

Future coverage:

- Filter functions.
- STFT/FK/PSD numerical smoke tests.
- Reader edge cases with real small sample files.
- Additional plot types beyond waterfall and waveform.
- GUI load-file behavior with real small files.

## Command

    python -m pytest

For cache-free runs during agent work:

    python -B -m pytest -p no:cacheprovider

## Optional dependency strategy

- h5py tests use pytest.importorskip("h5py").
- matplotlib plotting tests use pytest.importorskip("matplotlib") and the Agg backend.
- Waveform plotting tests also use the Agg backend and write only to pytest tmp_path.
- GUI smoke tests use pytest.importorskip("PyQt5") and pytest.importorskip("matplotlib"). If PyQt5 is not installed, GUI creation tests skip cleanly while core/io/plotting tests continue to run.
- GUI waveform tests avoid real file dialogs and real DAS data; they only instantiate
  widgets and test GUI-independent parser/model helpers.
- GUI automation is deferred; GUI-independent state and worker logic should still be testable.
- Real or quasi-real file validation should use examples/validate_file.py and
  examples/plot_waveform.py with local data paths. Do not commit the input data
  or generated preview/waveform images.
- Batch real/quasi-real validation should use examples/validate_local_samples.py
  with local_validation_paths.txt. The path file and validation output directories
  are ignored by git.
