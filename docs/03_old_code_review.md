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

## Phase 3A preprocessing migration decision

The following old files were reviewed read-only for basic preprocessing:

- old_code/old_code1/tools/analysis_tools.py
- old_code/old_code4/hcz_signal_preprocess.py

No old_code files are imported by the new runtime, and old_code/ was not
modified. The old functions are mostly single-trace helpers, often scipy-based,
and do not consistently document DAS dimensions. Phase 3A therefore reimplemented
the small, well-understood operations with numpy and explicit
(n_samples, n_channels) axis semantics.

| Function | Old source | Judgment | New location | Tests | Interface / dimension changes |
|---|---|---|---|---|---|
| demean | old_code/old_code1/tools/analysis_tools.py::demeaning; old_code/old_code4/hcz_signal_preprocess.py::demeaning | 重构后复写 | das_view/processing/preprocess.py::demean | tests/test_preprocess.py | Adds axis argument; default axis=0 removes per-channel time mean for DAS arrays; finite statistics ignore NaN/Inf. |
| detrend_linear | old_code/old_code1/tools/analysis_tools.py::detrending; old_code/old_code4/hcz_signal_preprocess.py::delineaaar_trend | 仅参考 | das_view/processing/preprocess.py::detrend_linear | tests/test_preprocess.py | Rewritten without scipy; operates along explicit axis; finite samples are fitted per trace. |
| taper | old_code/old_code1/tools/analysis_tools.py::taper/taper_filter; old_code/old_code4/hcz_signal_preprocess.py::taper | 重构后复写 | das_view/processing/preprocess.py::taper | tests/test_preprocess.py | Uses ratio instead of taper_point; default axis=0; currently supports Hann edge taper only. |
| normalize | old_code/old_code4/hcz_signal_preprocess.py::normalization | 重构后复写 | das_view/processing/preprocess.py::normalize | tests/test_preprocess.py | Adds mode=maxabs/minmax, axis, and eps; all-zero/constant inputs are safe. |
| standardize | old_code/old_code4/hcz_signal_preprocess.py::standardization | 重构后复写 | das_view/processing/preprocess.py::standardize | tests/test_preprocess.py | Adds axis and eps; constant finite slices become zero. |
| clip | No focused old helper found in reviewed files | 新实现 | das_view/processing/preprocess.py::clip | tests/test_preprocess.py | Adds explicit min/max and percentile clipping over finite values. |
| simple preprocessing workflow | old_code/old_code4/hcz_signal_preprocess.py::data_preprocess | 废弃 | das_view/processing/service.py::apply_preprocess | tests/test_preprocessing_service.py | Old workflow is empty/pass; new service applies explicit ordered steps and records metadata history. |

## Phase 3B filter migration decision

The same old files were reviewed read-only for basic filters:

- old_code/old_code1/tools/analysis_tools.py
- old_code/old_code4/hcz_signal_preprocess.py

The old code uses scipy.signal Butterworth and notch filters, which is the right
general approach, but parameter names and dimension assumptions are inconsistent
and error handling is minimal. Phase 3B reimplemented the filter API with
explicit DAS axis semantics, SOS-based filtering, and validation.

| Function | Old source | Judgment | New location | Tests | Interface / dimension changes |
|---|---|---|---|---|---|
| lowpass | analysis_tools.py::filter_butter_lowpass; hcz_signal_preprocess.py::filter_butter_lowpass | 重构后复写 | das_view/processing/filters.py::lowpass | tests/test_filters.py | Uses sample_rate_hz/cutoff_hz, default axis=0, SOS filters, zero_phase option. |
| highpass | analysis_tools.py::filter_butter_highpass; hcz_signal_preprocess.py::filter_butter_highpass | 重构后复写 | das_view/processing/filters.py::highpass | tests/test_filters.py | Same API conventions as lowpass; validates cutoff < Nyquist. |
| bandpass | analysis_tools.py::filter_butter_bandpass; hcz_signal_preprocess.py::filter_butter_bandpass | 重构后复写 | das_view/processing/filters.py::bandpass | tests/test_filters.py | Uses freqmin_hz/freqmax_hz and validates freqmin < freqmax < Nyquist. |
| bandstop | analysis_tools.py::filter_butter_bandstop | 重构后复写 | das_view/processing/filters.py::bandstop | tests/test_filters.py | New explicit DAS-axis API and SOS implementation. |
| notch | analysis_tools.py::filter_fir_notch; hcz_signal_preprocess.py::filter_iirnotch | 仅参考 | das_view/processing/filters.py::notch | tests/test_filters.py | Reimplemented with scipy.signal.iirnotch plus SOS conversion; validates quality and notch_hz. |
| taper_filter | analysis_tools.py::taper_filter | 已由 Phase 3A 覆盖 | das_view/processing/preprocess.py::taper | tests/test_preprocess.py | Kept separate from filtering; ratio-based Hann taper. |

## Phase 3C spectrum and spectrogram migration decision

The following old files were reviewed read-only for spectrum and time-frequency
ideas:

- old_code/old_code1/tools/analysis_tools.py
- old_code/old_code4/hcz_signal_analyse.py

The old code contains useful FFT amplitude-scaling and scipy.signal.stft ideas,
but the functions are either single-trace only, directly coupled to plotting, or
mixed with broader FK/PSD workflows. Phase 3C therefore reimplemented a small
GUI-independent spectrum module with explicit DAS axis semantics and separate
plotting helpers.

| Function/topic | Old source | Judgment | New location | Tests | Interface / dimension changes |
|---|---|---|---|---|---|
| amplitude spectrum | analysis_tools.py::get_fp; hcz_signal_analyse.py::plot_FS | Reimplemented after refactor | das_view/analysis/spectrum.py::amplitude_spectrum | tests/test_spectrum_analysis.py | Accepts numpy or DASData, default axis=0, optional channel selection/averaging, explicit sample_rate_hz and nfft validation. |
| power spectrum | analysis_tools.py::psd_periodogram/psd_welch ideas | Reference only | das_view/analysis/spectrum.py::power_spectrum | tests/test_spectrum_analysis.py | Implements a simple FFT-derived power path only; full PSD/Welch is deferred to Phase 3D. |
| spectrogram smoke path | analysis_tools.py::get_tfp/tfp_analysis; hcz_signal_analyse.py::plot_TF | Reimplemented after refactor | das_view/analysis/spectrum.py::single_channel_spectrogram | tests/test_spectrum_analysis.py | Uses scipy.signal.spectrogram for one selected channel; no GUI coupling and no full STFT analysis platform. |
| spectrum plotting | hcz_signal_analyse.py::plot_FS/plot_analysis | Reference only | das_view/plotting/spectra.py | tests/test_spectrum_plotting.py | Plotting is separated from analysis results and remains Matplotlib-only. |
| FK/F-J/MASW and advanced PSD | analysis_tools.py FK/PSD sections | Deferred | Not implemented | Not applicable | Out of scope for Phase 3C. |
