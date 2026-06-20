# Roadmap

## Phase 0: Development baseline

Goal:

- Establish package structure, documentation, data convention, metadata model, reader interfaces, and tests.

Acceptance:

- Core package imports.
- Initial tests pass.
- Docs record old-code reuse rules and development decisions.

## Phase 1: Minimal DAS Viewer

Goal:

- Support one first-priority format end to end.
- Open a file, read metadata, and display a downsampled DAS image.
- Phase 1A completed the first reader and non-GUI waterfall smoke path.
- Phase 1B completed metadata display helpers and GUI-independent preview service.
- Phase 1C completed the minimal PyQt5 GUI for opening a supported file, displaying metadata, and drawing a preview waterfall.

Acceptance:

- A small sample file can be opened.
- Metadata and a basic waterfall/variable-density plot are shown.
- The GUI calls create_preview instead of implementing file IO directly.
- Next stabilization should focus on real-data validation, error handling, and moving preview loading to a background worker if needed.

## Phase 2: Stable IO and basic plotting

Goal:

- Stabilize ZD HDF5 and Puniu DAT readers.
- Support time/channel slicing and memory-aware plotting.

Acceptance:

- Reader tests cover orientation and metadata.
- Large files are not blindly loaded for plotting.

## Phase 3: Common preprocessing and interactive analysis

Goal:

- Add demean, detrend, taper, filtering, resampling, single-channel waveform, spectrum, and STFT.

Acceptance:

- Core operations are covered by numerical tests.
- GUI can run operations without blocking for typical data sizes.

## Phase 4: Advanced analysis

Goal:

- Add FK, PSD, FK filtering, and optional advanced methods such as surface-wave analysis.

Acceptance:

- Algorithms have synthetic-data smoke tests.
- Parameters and results are reproducible.

## Phase 5: Documentation, packaging, and release

Goal:

- Prepare user docs, examples, packaging, and release checks.

Acceptance:

- A new environment can install and run the package.
- Tests and docs describe the supported workflows clearly.
