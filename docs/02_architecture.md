# Architecture

## Package layout

    das_view/
    - __init__.py
    - core/
      - data_model.py
      - metadata_format.py
      - exceptions.py
      - config.py
    - io/
      - base.py
      - registry.py
      - preview.py
      - data_service.py
      - hdf5_zd.py
      - puniu_dat.py
    - processing/
      - preprocess.py
      - filters.py
      - service.py
    - analysis/
      - spectrum.py
      - service.py
    - plotting/
      - waterfall.py
      - waveform.py
      - spectra.py
    - gui/
      - app.py
      - main_window.py
      - models.py
      - workers.py
    - utils/
      - slicing.py
      - validation.py
      - logging.py

## Layer responsibilities

- core: data model, metadata display formatting, package-wide constants, and exceptions.
- io: data readers, metadata readers, format registry, GUI-independent preview workflow, and bounded data selection services.
- processing: GUI-independent preprocessing operations such as demean, linear
  detrend, taper, normalization, standardization, clipping, and later filtering/resampling.
- analysis: GUI-independent scientific analysis. Phase 3D includes basic
  amplitude spectrum, power spectrum, periodogram PSD, Welch PSD,
  single-channel spectrogram smoke-path helpers, and file-level spectrum
  services. Full STFT/FK workflows remain deferred.
- plotting: Matplotlib plotting helpers independent from GUI widgets, including
  waterfall, waveform, spectrum, and spectrogram views.
- gui: optional PyQt5 layer that calls preview, formatting, and plotting services.
- utils: validation, slicing, logging, and shared small helpers.

## Dependency direction

Allowed:

    gui -> plotting -> analysis/processing -> io/core
    io -> core/utils
    processing/analysis -> core/utils
    plotting -> core

Not allowed:

    core -> GUI
    io -> GUI
    processing/analysis -> GUI
    das_view -> old_code

## Reader design

Readers implement BaseDASReader and return DASData.

Reader responsibilities:

- Identify whether a path can be read.
- Read metadata without loading large data arrays.
- Read data into (n_samples, n_channels).
- Support slicing and simple downsampling where practical.
- Record source format and source path.
- Preserve source-specific information in extra_attrs.

## Metadata display and preview service

- das_view/core/metadata_format.py converts DASMetadata into stable dictionaries,
  summary lines, and text blocks for CLI and GUI display.
- das_view/io/preview.py owns the lightweight preview workflow:
  path -> reader selection -> metadata read -> bounded slice/downsample read -> PreviewResult.
- PreviewResult includes full-file metadata, preview DASData, reader name, normalized
  slices, downsampling steps, and warnings.
- max_samples and max_channels are used to compute simple integer downsampling before
  data is read, so large files are not loaded blindly for preview.

## Data service

- das_view/io/data_service.py provides GUI/CLI reusable bounded data access helpers.
- read_selection selects a reader, validates time/channel slices in internal coordinates,
  and delegates actual IO to the reader with optional downsampling.
- read_trace reads one or a small set of channels for waveform views. Single-channel
  requests are passed to the reader as a narrow channel slice; non-contiguous multi-channel
  requests read the smallest enclosing channel window and then keep the requested columns.
- SelectionResult records the selected reader, normalized slices, downsampling, and
  requested channels. Callers should use this service instead of duplicating reader logic.

## Plotting services

- plot_waterfall draws variable-density DAS previews from DASData.
- plot_waveform draws one or more channel traces from DASData with optional normalization
  and offsets. It is pure Matplotlib and does not depend on PyQt5.
- plot_spectrum and plot_spectrogram draw results from the analysis layer. They
  do not compute spectra and do not depend on PyQt5.
- Plotting helpers assume the internal data convention (n_samples, n_channels).

## Analysis services

- das_view/analysis/spectrum.py provides SpectrumResult, PSDResult, and
  SpectrogramResult containers plus amplitude_spectrum, power_spectrum,
  periodogram_psd, welch_psd, and single_channel_spectrogram.
- das_view/analysis/service.py provides file-level helpers such as
  compute_spectrum_for_file, compute_psd_for_file, and
  compute_spectrogram_for_file. They read bounded traces through the data
  service, optionally apply preprocessing/filter steps, and return the analysis
  result with reader metadata and preprocessing history.
- The default axis=0 follows the DAS convention and treats each column as an
  independent channel through time.
- Spectrum helpers accept numpy arrays or DASData. DASData input can provide
  sample_rate_hz from metadata.
- The current spectrogram path is intentionally single-channel and smoke-test
  oriented. CLI/GUI integration should call analysis service and plotting
  helpers instead of implementing FFT/STFT/PSD logic in examples or
  das_view/gui/.

## Processing services

- das_view/processing/preprocess.py provides pure numpy array functions. The
  default axis=0 follows the DAS convention and processes each channel along
  time.
- das_view/processing/filters.py provides scipy.signal based lowpass, highpass,
  bandpass, bandstop, and notch filters. The default axis=0 filters each
  channel independently along time.
- das_view/processing/service.py applies named preprocessing steps to DASData,
  returns a new DASData, preserves metadata, and appends preprocessing_history
  in metadata.extra_attrs.
- The service accepts simple step definitions such as ("demean", {"axis": 0})
  and is the intended integration point for future GUI or CLI workflows.
- Phase 3A/3B processing examples are preview-level and in-memory only. They do
  not export processed full-size DAS files and do not implement STFT/FK/PSD.
- Filtering is part of the processing layer and depends on scipy. Future GUI
  filter controls should call apply_preprocess instead of implementing filter
  design or scipy.signal calls in das_view/gui/.

## GUI design direction

The GUI should call preview, data-service, processing, analysis, and plotting services. It should not know details like /Acquisition/Raw[0]/RawData except through reader-facing abstractions.

GUI rules:

- PyQt5 imports live only in das_view/gui/ or GUI entry points.
- MainWindow calls PreviewWorker / QtPreviewWorker, which wrap create_preview.
- MainWindow exposes max_samples and max_channels controls; these values are
  validated in GUI model helpers and then passed to PreviewWorker/create_preview.
- Metadata text comes from format_metadata.
- The image panel uses plot_waterfall with an embedded Matplotlib Qt canvas.
- Phase 2B adds a Waveform tab. It parses zero-based channel indices in GUI
  model helpers, then calls read_trace through WaveformWorker / QtWaveformWorker
  and plot_waveform in the main GUI thread. The GUI does not implement channel
  slicing, downsampling algorithms, or concrete reader paths.
- Non-contiguous, reordered, or duplicate channel waveform selections are
  represented in metadata extra_attrs. dx_m is cleared for non-contiguous
  selections so downstream displays do not pretend the selected traces are
  evenly spaced.
- Phase 2D moves preview and waveform data loading into QThread-backed QObject
  workers. The workers call only service-layer functions: preview loading calls
  create_preview, and waveform loading calls read_trace.
- Matplotlib Qt canvas drawing remains in the main thread. Background workers
  return data/service results; MainWindow applies the latest non-cancelled result
  and then calls plot_waterfall or plot_waveform.
- The GUI supports a single active background task at a time. Open/preview and
  waveform controls are disabled while a task is running, a Cancel button requests
  soft cancellation, and a busy progress bar shows that work is ongoing.
- Phase 2D cancellation is cooperative. It cannot forcibly interrupt synchronous
  reader IO already in progress, but cancelled or stale task results are not
  applied to the GUI.
- Phase 3E adds a minimal Spectrum tab. It parses a single channel plus nfft,
  nperseg, noverlap, analysis type, and PSD dB display options in GUI model
  helpers, then starts a QThread-backed spectrum worker.
- Spectrum workers call only das_view.analysis.service helpers:
  compute_spectrum_for_file, compute_psd_for_file, and
  compute_spectrogram_for_file. They do not inspect HDF5/DAT internal paths and
  do not implement FFT, PSD, or spectrogram algorithms in the GUI layer.
- Spectrum plotting remains in the main GUI thread. MainWindow receives the
  latest non-cancelled service result and calls plot_spectrum, plot_psd, or
  plot_spectrogram on the embedded Matplotlib Qt canvas.
