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
      - hdf5_zd.py
      - puniu_dat.py
    - processing/
    - analysis/
    - plotting/
      - waterfall.py
    - gui/
    - utils/
      - slicing.py
      - validation.py
      - logging.py

## Layer responsibilities

- core: data model, metadata display formatting, package-wide constants, and exceptions.
- io: data readers, metadata readers, format registry, and GUI-independent preview workflow.
- processing: preprocessing operations such as demean, detrend, taper, filtering, and resampling.
- analysis: scientific analysis such as spectrum, STFT, FK, and PSD.
- plotting: Matplotlib plotting helpers independent from GUI widgets.
- gui: optional PyQt5 layer that calls core APIs.
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

## GUI design direction

The GUI should call preview, reader, processing, analysis, and plotting services. It should not know details like /Acquisition/Raw[0]/RawData except through reader-facing abstractions. The first minimal GUI should call create_preview rather than opening DAS files directly.
