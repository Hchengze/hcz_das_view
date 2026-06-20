# Project Baseline

## Goal

das_view is the new DAS Viewer / DAS Analysis package. It will be rebuilt from the old prototypes in old_code/, but the new runtime package must be cleanly layered, testable, and maintainable.

Initial focus:

1. Read DAS data.
2. Represent metadata consistently.
3. Preserve a strict internal data dimension convention.
4. Provide small, testable IO and algorithm modules.
5. Add plotting and GUI only as layers above core logic.

## Non-goals for the baseline phase

- Do not complete the full GUI.
- Do not migrate all old algorithms at once.
- Do not support every historical data format immediately.
- Do not depend on old_code at runtime.

## Development principles

- Do not modify old code in place.
- New code must not import old_code.
- Data correctness comes first, performance second, GUI appearance third.
- IO, core data structures, processing, analysis, plotting, and GUI must be separated.
- Algorithm functions should be pure where practical.
- GUI code should not contain complex algorithm implementation.
- GUI code should not depend on concrete HDF5 internal paths.
- Large DAS files require slicing, downsampling, or memory-aware handling.
- Every development phase must update docs and the development log.

## Internal data dimension convention

All internal arrays use:

    data.shape == (n_samples, n_channels)

- Axis 0: time samples.
- Axis 1: spatial channels.
- Every reader must convert external data into this convention.
- Original shape/orientation should be recorded in metadata extra_attrs when relevant.

## Metadata baseline

The unified metadata object is das_view.core.data_model.DASMetadata.

Required/standard fields:

- n_samples
- n_channels
- sample_rate_hz
- dt_s
- dx_m
- gauge_length_m
- start_channel
- start_time
- source_format
- source_path
- extra_attrs

## First reader priorities

First priority:

1. ZD HDF5.
2. Puniu DAT.

Second priority:

1. Generic HDF5.
2. Small TXT/CSV.
3. NPY/NPZ.

Future optional:

1. SEGY.
2. SAC.
3. TDMS.
4. Other vendor formats.

## GUI baseline

Initial GUI direction remains PyQt5 + Matplotlib because the old prototypes already used that stack. The GUI must be optional: das_view.core, das_view.io, das_view.processing, and das_view.analysis must not require PyQt5.
