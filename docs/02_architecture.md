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
    - analysis/
    - plotting/
      - waterfall.py
      - waveform.py
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
- processing: preprocessing operations such as demean, detrend, taper, filtering, and resampling.
- analysis: scientific analysis such as spectrum, STFT, FK, and PSD.
- plotting: Matplotlib plotting helpers independent from GUI widgets, including waterfall and waveform views.
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
- Plotting helpers assume the internal data convention (n_samples, n_channels).

## GUI design direction

The GUI should call preview, reader, processing, analysis, and plotting services. It should not know details like /Acquisition/Raw[0]/RawData except through reader-facing abstractions.

Phase 1C GUI rules:

- PyQt5 imports live only in das_view/gui/ or GUI entry points.
- MainWindow calls PreviewWorker, which is a thin wrapper around create_preview.
- MainWindow exposes max_samples and max_channels controls; these values are
  validated in GUI model helpers and then passed to PreviewWorker/create_preview.
- Metadata text comes from format_metadata.
- The image panel uses plot_waterfall with an embedded Matplotlib Qt canvas.
- Future waveform GUI views should call read_trace/read_selection plus plot_waveform,
  not concrete ZD HDF5 or Puniu DAT reader internals.
- Current loading is synchronous and may briefly block for larger files; a later worker/QThread pass should move PreviewWorker into the background without changing reader logic.
