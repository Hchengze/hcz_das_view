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
- Phase 1D stabilized the preview GUI basics, added preview limit controls, and documented user/developer entry points.

Acceptance:

- A small sample file can be opened.
- Metadata and a basic waterfall/variable-density plot are shown.
- The GUI calls create_preview instead of implementing file IO directly.
- Next stabilization should focus on real-data validation, waveform plotting, and moving preview loading to a background worker if needed.

## Phase 2: Stable IO and basic plotting

Goal:

- Stabilize ZD HDF5 and Puniu DAT readers.
- Support time/channel slicing and memory-aware plotting.
- Phase 2A added a reader-independent data selection service, waveform plotting,
  and a waveform CLI example.
- Phase 2B integrated waveform plotting into the minimal GUI, added channel input
  parsing, and expanded data-service boundary tests for reordered, duplicate, and
  non-contiguous channel selections.
- Phase 2C added local real/quasi-real sample validation tools and expanded
  ZD HDF5/Puniu DAT edge-case tests without committing real data.

Acceptance:

- Reader tests cover orientation and metadata.
- Large files are not blindly loaded for plotting.
- CLI workflows can create bounded waterfall previews and waveform trace plots.
- The GUI can show both bounded waterfall previews and simple waveform traces.
- Next work should run the prepared validation tools on real local samples,
  add background GUI loading, or begin small preprocessing functions.

## Phase 3: Common preprocessing and interactive analysis

Goal:

- Add demean, detrend, taper, filtering, resampling, spectrum, and STFT.
- Phase 3A added numpy-only basic preprocessing functions, a DASData service
  that records preprocessing history, and a preview-level preprocessing CLI
  example.
- Phase 3B added scipy-based lowpass, highpass, bandpass, bandstop, and notch
  filters, integrated them with apply_preprocess, and added a preview-level
  filter CLI example.
- Phase 3C added basic amplitude spectrum, power spectrum, and single-channel
  spectrogram smoke paths, plus Matplotlib spectrum/spectrogram plotting and a
  bounded trace CLI example.

Acceptance:

- Basic preprocessing operations are covered by numerical tests.
- Basic filters are covered by numerical tests and service integration tests.
- Basic spectrum and spectrogram smoke paths are covered by numerical and
  plotting tests.
- GUI can run operations without blocking for typical data sizes.
- Next work can add PSD/Welch service helpers in Phase 3D or improve GUI
  background loading in Phase 2D.

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
