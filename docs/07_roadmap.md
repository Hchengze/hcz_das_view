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
- Phase 2D moved GUI preview and waveform data loading to QThread-backed
  workers, added a Cancel button, busy progress feedback, and stale/cancelled
  result protection while keeping plotting in the main thread.

Acceptance:

- Reader tests cover orientation and metadata.
- Large files are not blindly loaded for plotting.
- CLI workflows can create bounded waterfall previews and waveform trace plots.
- The GUI can show both bounded waterfall previews and simple waveform traces.
- The GUI loads preview and waveform data through background workers for better
  responsiveness; cancellation is soft and does not forcibly interrupt
  synchronous reader IO already in progress.
- Next work should run the prepared validation tools on real local samples,
  add a minimal GUI spectrum panel, or begin FK smoke-path work.

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
- Phase 3D added periodogram PSD, Welch PSD, PSD plotting with optional dB
  display, and a reusable analysis service for bounded spectrum/PSD/spectrogram
  file workflows.
- Phase 3E added a minimal GUI Spectrum tab that runs amplitude, power,
  periodogram PSD, Welch PSD, and spectrogram tasks through QThread-backed
  service workers, with main-thread plotting and Phase 2D cancel/progress state
  reuse.

Acceptance:

- Basic preprocessing operations are covered by numerical tests.
- Basic filters are covered by numerical tests and service integration tests.
- Basic spectrum, PSD/Welch, and spectrogram smoke paths are covered by
  numerical, plotting, service, and CLI parsing tests.
- The GUI can launch minimal spectrum/PSD/spectrogram service tasks from the
  Spectrum tab without embedding analysis algorithms in the GUI layer.
- GUI can run operations without blocking for typical data sizes.
- Next work can validate real local samples in Phase 2E, or begin FK smoke-path
  work in Phase 4A.

## Phase 4: Advanced analysis

Goal:

- Add FK, FK filtering, and optional advanced methods such as surface-wave analysis.
- Phase 4A added a basic FK transform smoke path with FKResult, FK plotting,
  a bounded FK CLI example, file-level service integration, and synthetic tests.

Acceptance:

- Algorithms have synthetic-data smoke tests.
- Parameters and results are reproducible.
- Current Phase 4A support is limited to basic FK amplitude/power transform and
  plotting. FK filter, velocity fan filter, F-J, MASW, dispersion picking, and
  GUI FK panels remain deferred.
- Next work can enter Phase 4B FK filter smoke path, or Phase 2E real sample
  validation if local data paths are provided.

## Phase 5: Documentation, packaging, and release

Goal:

- Prepare user docs, examples, packaging, and release checks.

Acceptance:

- A new environment can install and run the package.
- Tests and docs describe the supported workflows clearly.
