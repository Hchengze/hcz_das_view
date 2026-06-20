# Old Code Review Summary

This document condenses the read-only audit of old_code/.

## High-value old assets

| Old location | Judgment | New target | Notes |
|---|---|---|---|
| old_code/old_code1/tools/analysis_tools.py | Rewrite after refactor | das_view/processing/, das_view/analysis/ | Contains useful preprocessing, filters, STFT, FK, and PSD logic. Requires dimension normalization and tests. |
| old_code/old_code1/tools/data_tools.py | Rewrite after refactor | das_view/io/hdf5_zd.py | ZD HDF5 paths and metadata attributes are useful, but old code is too format-hardcoded for GUI use. |
| old_code/old_code3/dy_view.py::read_puniu_dat_file | Rewrite after refactor | das_view/io/puniu_dat.py | Puniu DAT header parsing is valuable and should be isolated from GUI code. |
| old_code/old_code1/tools/ui_tools.py | Reference only | das_view/gui/ | Useful workflow ideas, but the old file is too large and coupled to copy directly. |
| old_code/old_code4/hcz_signal_analyse.py | Reference only / local rewrite later | das_view/analysis/ | Spectrum, envelope, correlation, and CWT ideas may be useful later. |

## Assets to avoid direct reuse

- old_code/old_code1/tools/test.py
- old_code/old_code1/tools/test2.py
- old_code/old_code4/demo.py
- __pycache__/
- scripts with hardcoded local paths or top-level side effects

## Current reuse decision

The current code does not import old_code. It reimplements small, well-understood format facts from the audit:

- ZD HDF5 raw data path and common metadata attribute names.
- Puniu DAT header layout: 10 float64 values followed by float32 data.
- Basic non-GUI DAS waterfall plotting follows the old GUI workflow idea but is implemented as a clean plotting helper.

These are covered by synthetic tests.
