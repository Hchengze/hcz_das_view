"""Minimal FK-domain velocity fan filtering helpers.

The implementation follows the project-wide DAS convention:
``data.shape == (n_samples, n_channels)``.  Axis 0 is time by default and
axis 1 is the spatial/channel axis.

This module is intentionally a smoke path.  It builds simple boolean masks in
frequency-wavenumber coordinates, applies them to a complex FK spectrum while
preserving phase, and transforms back to the time-channel domain.  It does not
attempt engineering-grade FK denoising, tapered fan edges, or specialized
interpretation workflows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from das_view.analysis.fk import (
    FKResult,
    _normalize_axis,
    _normalize_nfft,
    _positive_float,
    _window_values,
    fk_transform,
)
from das_view.core.data_model import DASData, DASMetadata


@dataclass(frozen=True, slots=True)
class FKFilterResult:
    """Result from a minimal FK-domain filtering operation."""

    das_data: DASData
    mask: np.ndarray
    frequencies_hz: np.ndarray
    wavenumbers_cycles_per_m: np.ndarray
    sample_rate_hz: float
    dx_m: float
    vmin_mps: float | None
    vmax_mps: float | None
    pass_inside: bool
    nfft_time: int
    nfft_space: int
    original_shape: tuple[int, int]
    time_axis: int = 0
    channel_axis: int = 1
    input_fk: FKResult | None = None
    filtered_fk: FKResult | None = None

    @property
    def filtered_data(self) -> np.ndarray:
        """Shortcut for the filtered time-channel array."""

        return self.das_data.data


def velocity_fan_mask(
    frequencies_hz,
    wavenumbers_cycles_per_m,
    *,
    vmin_mps: float | None = None,
    vmax_mps: float | None = None,
    pass_inside: bool = True,
    include_zero_wavenumber: bool = True,
) -> np.ndarray:
    """Build a boolean velocity fan mask shaped ``(n_frequencies, n_wavenumbers)``.

    Apparent velocity is approximated as ``abs(f / k)`` in the FK plane.  The
    ``k == 0`` column is undefined; this smoke-path helper either keeps it in
    the inside mask or excludes it based on ``include_zero_wavenumber``.
    """

    frequencies = _finite_1d_array(frequencies_hz, name="frequencies_hz")
    wavenumbers = _finite_1d_array(wavenumbers_cycles_per_m, name="wavenumbers_cycles_per_m")
    vmin, vmax = _validate_velocity_limits(vmin_mps, vmax_mps)

    frequency_grid = np.abs(frequencies).reshape(-1, 1)
    wavenumber_grid = np.abs(wavenumbers).reshape(1, -1)
    zero_wavenumber = wavenumber_grid == 0.0
    velocity = np.divide(
        frequency_grid,
        wavenumber_grid,
        out=np.full((frequencies.size, wavenumbers.size), np.inf, dtype=float),
        where=~zero_wavenumber,
    )

    inside = np.ones_like(velocity, dtype=bool)
    if vmin is not None:
        inside &= velocity >= vmin
    if vmax is not None:
        inside &= velocity <= vmax

    zero_columns = zero_wavenumber.reshape(-1)
    if include_zero_wavenumber:
        inside[:, zero_columns] = True
    else:
        inside[:, zero_columns] = False

    return inside if pass_inside else ~inside


def apply_fk_mask(
    data,
    mask,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    time_axis: int = 0,
    channel_axis: int = 1,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    window_time: str | Sequence[float] | np.ndarray | None = None,
    window_space: str | Sequence[float] | np.ndarray | None = None,
    return_fk: bool = False,
) -> FKFilterResult:
    """Apply a precomputed shifted FK mask and invert back to time-channel data."""

    array, metadata, sample_rate_hz, dx_m = _as_array_metadata_sample_rate_and_dx(
        data,
        sample_rate_hz,
        dx_m,
    )
    working, time_axis, channel_axis = _prepare_working_array(array, time_axis, channel_axis)
    n_samples, n_channels = working.shape
    nfft_time = _normalize_nfft(nfft_time, minimum=n_samples, name="nfft_time")
    nfft_space = _normalize_nfft(nfft_space, minimum=n_channels, name="nfft_space")
    mask_array = _validate_mask(mask, nfft_time=nfft_time, nfft_space=nfft_space)

    spectrum = _complex_shifted_fk(
        working,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        window_time=window_time,
        window_space=window_space,
    )
    filtered_shifted = spectrum * mask_array
    unshifted = np.fft.ifftshift(filtered_shifted, axes=1)
    frequency_space = np.fft.ifft(unshifted, n=nfft_space, axis=1)
    recovered = np.fft.irfft(frequency_space, n=nfft_time, axis=0).real
    recovered = recovered[:n_samples, :n_channels]
    filtered = np.moveaxis(recovered, (0, 1), (time_axis, channel_axis))

    filtered_data = _filtered_das_data(
        filtered,
        metadata=metadata,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        pass_inside=True,
        vmin_mps=None,
        vmax_mps=None,
    )
    frequencies = np.fft.rfftfreq(nfft_time, d=1.0 / sample_rate_hz)
    wavenumbers = np.fft.fftshift(np.fft.fftfreq(nfft_space, d=dx_m))
    input_fk = None
    filtered_fk = None
    if return_fk:
        input_fk = fk_transform(
            data,
            sample_rate_hz=sample_rate_hz,
            dx_m=dx_m,
            time_axis=time_axis,
            channel_axis=channel_axis,
            nfft_time=nfft_time,
            nfft_space=nfft_space,
            window_time=window_time,
            window_space=window_space,
            output="amplitude",
        )
        filtered_fk = fk_transform(
            filtered_data,
            nfft_time=nfft_time,
            nfft_space=nfft_space,
            output="amplitude",
        )

    return FKFilterResult(
        das_data=filtered_data,
        mask=mask_array,
        frequencies_hz=frequencies,
        wavenumbers_cycles_per_m=wavenumbers,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        vmin_mps=None,
        vmax_mps=None,
        pass_inside=True,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        original_shape=tuple(int(value) for value in array.shape),
        time_axis=time_axis,
        channel_axis=channel_axis,
        input_fk=input_fk,
        filtered_fk=filtered_fk,
    )


def fk_velocity_filter(
    data,
    *,
    sample_rate_hz: float | None = None,
    dx_m: float | None = None,
    vmin_mps: float | None = None,
    vmax_mps: float | None = None,
    pass_inside: bool = True,
    include_zero_wavenumber: bool = True,
    time_axis: int = 0,
    channel_axis: int = 1,
    nfft_time: int | None = None,
    nfft_space: int | None = None,
    window_time: str | Sequence[float] | np.ndarray | None = None,
    window_space: str | Sequence[float] | np.ndarray | None = None,
    return_fk: bool = False,
) -> FKFilterResult:
    """Apply a simple apparent-velocity fan mask in the FK domain."""

    array, metadata, sample_rate_hz, dx_m = _as_array_metadata_sample_rate_and_dx(
        data,
        sample_rate_hz,
        dx_m,
    )
    working, normalized_time_axis, normalized_channel_axis = _prepare_working_array(
        array,
        time_axis,
        channel_axis,
    )
    n_samples, n_channels = working.shape
    nfft_time = _normalize_nfft(nfft_time, minimum=n_samples, name="nfft_time")
    nfft_space = _normalize_nfft(nfft_space, minimum=n_channels, name="nfft_space")
    frequencies = np.fft.rfftfreq(nfft_time, d=1.0 / sample_rate_hz)
    wavenumbers = np.fft.fftshift(np.fft.fftfreq(nfft_space, d=dx_m))
    mask = velocity_fan_mask(
        frequencies,
        wavenumbers,
        vmin_mps=vmin_mps,
        vmax_mps=vmax_mps,
        pass_inside=pass_inside,
        include_zero_wavenumber=include_zero_wavenumber,
    )
    result = apply_fk_mask(
        data,
        mask,
        sample_rate_hz=sample_rate_hz,
        dx_m=dx_m,
        time_axis=normalized_time_axis,
        channel_axis=normalized_channel_axis,
        nfft_time=nfft_time,
        nfft_space=nfft_space,
        window_time=window_time,
        window_space=window_space,
        return_fk=return_fk,
    )
    return replace(
        result,
        vmin_mps=_optional_positive_float(vmin_mps, name="vmin_mps"),
        vmax_mps=_optional_positive_float(vmax_mps, name="vmax_mps"),
        pass_inside=bool(pass_inside),
        das_data=_filtered_das_data(
            result.das_data.data,
            metadata=metadata,
            sample_rate_hz=sample_rate_hz,
            dx_m=dx_m,
            nfft_time=nfft_time,
            nfft_space=nfft_space,
            pass_inside=pass_inside,
            vmin_mps=vmin_mps,
            vmax_mps=vmax_mps,
        ),
    )


def _as_array_metadata_sample_rate_and_dx(
    data,
    sample_rate_hz: float | None,
    dx_m: float | None,
) -> tuple[np.ndarray, DASMetadata | None, float, float]:
    metadata = data.metadata if isinstance(data, DASData) else None
    if metadata is not None:
        if sample_rate_hz is None:
            sample_rate_hz = metadata.sample_rate_hz
        if dx_m is None:
            dx_m = metadata.dx_m
        array = np.array(data.data, dtype=float, copy=True)
    else:
        array = np.array(data, dtype=float, copy=True)
    sample_rate_hz = _positive_float(sample_rate_hz, name="sample_rate_hz")
    dx_m = _positive_float(dx_m, name="dx_m")
    if array.size == 0:
        raise ValueError("FK filter input data must not be empty")
    return array, metadata, sample_rate_hz, dx_m


def _prepare_working_array(array: np.ndarray, time_axis: int, channel_axis: int) -> tuple[np.ndarray, int, int]:
    if array.ndim != 2:
        raise ValueError("FK filter expects 2-D data shaped as (n_samples, n_channels)")
    if not np.all(np.isfinite(array)):
        raise ValueError("FK filter input must contain only finite values; NaN/Inf are not supported")
    normalized_time_axis = _normalize_axis(time_axis, array.ndim, name="time_axis")
    normalized_channel_axis = _normalize_axis(channel_axis, array.ndim, name="channel_axis")
    if normalized_time_axis == normalized_channel_axis:
        raise ValueError("time_axis and channel_axis must be different")
    working = np.array(
        np.moveaxis(array, (normalized_time_axis, normalized_channel_axis), (0, 1)),
        dtype=float,
        copy=True,
    )
    if working.shape[0] < 2:
        raise ValueError("FK filter requires at least 2 time samples")
    if working.shape[1] < 2:
        raise ValueError("FK filter requires at least 2 channels")
    return working, normalized_time_axis, normalized_channel_axis


def _complex_shifted_fk(
    working: np.ndarray,
    *,
    nfft_time: int,
    nfft_space: int,
    window_time,
    window_space,
) -> np.ndarray:
    n_samples, n_channels = working.shape
    time_window = _window_values(window_time, n_samples, name="window_time")
    space_window = _window_values(window_space, n_channels, name="window_space")
    transformed = np.array(working, dtype=float, copy=True)
    if time_window is not None:
        transformed = transformed * time_window.reshape(-1, 1)
    if space_window is not None:
        transformed = transformed * space_window.reshape(1, -1)
    frequency_space = np.fft.rfft(transformed, n=nfft_time, axis=0)
    fk_values = np.fft.fft(frequency_space, n=nfft_space, axis=1)
    return np.fft.fftshift(fk_values, axes=1)


def _validate_mask(mask, *, nfft_time: int, nfft_space: int) -> np.ndarray:
    mask_array = np.asarray(mask, dtype=float)
    expected = (nfft_time // 2 + 1, nfft_space)
    if mask_array.shape != expected:
        raise ValueError(f"mask shape must be {expected} to match FK spectrum shape")
    if not np.all(np.isfinite(mask_array)):
        raise ValueError("mask must contain only finite values")
    return mask_array


def _filtered_das_data(
    data: np.ndarray,
    *,
    metadata: DASMetadata | None,
    sample_rate_hz: float,
    dx_m: float,
    nfft_time: int,
    nfft_space: int,
    pass_inside: bool,
    vmin_mps: float | None,
    vmax_mps: float | None,
) -> DASData:
    array = np.asarray(data, dtype=float)
    entry = {
        "name": "fk_velocity_filter",
        "vmin_mps": None if vmin_mps is None else float(vmin_mps),
        "vmax_mps": None if vmax_mps is None else float(vmax_mps),
        "pass_inside": bool(pass_inside),
        "nfft_time": int(nfft_time),
        "nfft_space": int(nfft_space),
    }
    if metadata is None:
        new_metadata = DASMetadata(
            n_samples=int(array.shape[0]),
            n_channels=int(array.shape[1]),
            sample_rate_hz=sample_rate_hz,
            dx_m=dx_m,
            extra_attrs={"fk_filter": entry},
        )
    else:
        extra_attrs = dict(metadata.extra_attrs)
        extra_attrs["fk_filter"] = entry
        new_metadata = replace(
            metadata,
            n_samples=int(array.shape[0]),
            n_channels=int(array.shape[1]),
            sample_rate_hz=sample_rate_hz,
            dx_m=dx_m,
            extra_attrs=extra_attrs,
        )
    return DASData(data=array, metadata=new_metadata)


def _finite_1d_array(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _optional_positive_float(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    return _positive_float(value, name=name)


def _validate_velocity_limits(
    vmin_mps: float | None,
    vmax_mps: float | None,
) -> tuple[float | None, float | None]:
    vmin = _optional_positive_float(vmin_mps, name="vmin_mps")
    vmax = _optional_positive_float(vmax_mps, name="vmax_mps")
    if vmin is None and vmax is None:
        raise ValueError("at least one of vmin_mps or vmax_mps must be provided for FK velocity filtering")
    if vmin is not None and vmax is not None and vmin >= vmax:
        raise ValueError("vmin_mps must be smaller than vmax_mps")
    return vmin, vmax
