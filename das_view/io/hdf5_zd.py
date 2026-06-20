"""ZD HDF5 reader.

This module reimplements useful format facts from old_code1/tools/data_tools.py
without importing old code.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import ReaderError
from das_view.io.base import BaseDASReader
from das_view.utils.slicing import (
    SliceLike,
    apply_step,
    first_index,
    normalize_downsample,
    normalize_slice,
    slice_length,
)

ZD_RAW_DATASET = "/Acquisition/Raw[0]/RawData"
ZD_RAW_GROUP = "/Acquisition/Raw[0]"
ZD_ACQUISITION_GROUP = "/Acquisition"
ZD_TIME_GROUP = "/Acquisition/Raw[0]/RawDataTime"


class ZDHDF5Reader(BaseDASReader):
    """Reader for the known ZD DAS HDF5 layout."""

    name = "zd_hdf5"
    supported_extensions = (".h5", ".hdf5")

    def can_read(self, path: str | Path) -> bool:
        source = Path(path)
        if source.suffix.lower() not in self.supported_extensions:
            return False
        if not source.exists():
            return True
        try:
            h5py = _import_h5py()
            with h5py.File(source, "r") as handle:
                return ZD_RAW_DATASET in handle
        except ReaderError:
            return True
        except OSError:
            return False

    def read_metadata(self, path: str | Path) -> DASMetadata:
        h5py = _import_h5py()
        source = Path(path)
        with h5py.File(source, "r") as handle:
            if ZD_RAW_DATASET not in handle:
                raise ReaderError(
                    f"Missing ZD HDF5 raw dataset '{ZD_RAW_DATASET}' in {source}"
                )
            dataset = handle[ZD_RAW_DATASET]
            raw_shape = tuple(int(v) for v in dataset.shape)
            attrs = _collect_zd_attrs(handle, dataset)
            n_channels_hint = _as_optional_int(attrs.get("NumberOfLoci"))
            n_samples_hint = _as_optional_int(attrs.get("Count"))
            n_samples, n_channels, orientation = _infer_internal_shape(
                raw_shape, n_samples_hint, n_channels_hint
            )

        sample_rate = _as_optional_float(attrs.get("OutputDataRate"))
        dx_m = _as_optional_float(attrs.get("SpatialSamplingInterval"))
        gauge_length = _as_optional_float(attrs.get("GaugeLength"))
        extra_attrs = dict(attrs)
        extra_attrs.update(
            {
                "hdf5_raw_dataset": ZD_RAW_DATASET,
                "hdf5_raw_group": ZD_RAW_GROUP,
                "hdf5_acquisition_group": ZD_ACQUISITION_GROUP,
                "hdf5_time_group": ZD_TIME_GROUP,
                "raw_shape": raw_shape,
                "raw_orientation": orientation,
                "orientation_basis": "Count/NumberOfLoci and raw dataset shape",
            }
        )
        return DASMetadata(
            n_samples=n_samples,
            n_channels=n_channels,
            sample_rate_hz=sample_rate,
            dx_m=dx_m,
            gauge_length_m=gauge_length,
            source_format=self.name,
            source_path=source,
            extra_attrs=extra_attrs,
        )

    def read(
        self,
        path: str | Path,
        time_slice: SliceLike = None,
        channel_slice: SliceLike = None,
        downsample: int | tuple[int, int] | None = None,
    ) -> DASData:
        """Read ZD HDF5 data with optional slicing and simple downsampling."""

        h5py = _import_h5py()
        full_metadata = self.read_metadata(path)
        time_step, channel_step = normalize_downsample(downsample)
        internal_time_slice = apply_step(
            normalize_slice(time_slice, full_metadata.n_samples, axis_name="time"),
            time_step,
        )
        internal_channel_slice = apply_step(
            normalize_slice(channel_slice, full_metadata.n_channels, axis_name="channel"),
            channel_step,
        )
        _ensure_non_empty(internal_time_slice, axis_name="time")
        _ensure_non_empty(internal_channel_slice, axis_name="channel")

        with h5py.File(path, "r") as handle:
            dataset = handle[ZD_RAW_DATASET]
            raw_selection = _raw_selection(
                full_metadata.extra_attrs["raw_orientation"],
                internal_time_slice,
                internal_channel_slice,
            )
            raw = np.asarray(dataset[raw_selection])

        data = _orient_raw_array(
            raw,
            slice_length(internal_time_slice),
            slice_length(internal_channel_slice),
            full_metadata.extra_attrs.get("raw_orientation"),
        )
        metadata = _slice_metadata(
            full_metadata,
            internal_time_slice=internal_time_slice,
            internal_channel_slice=internal_channel_slice,
            downsample=(time_step, channel_step),
        )
        return DASData(data=data, metadata=metadata)


def _import_h5py():
    try:
        import h5py
    except ImportError as exc:
        raise ReaderError("h5py is required to read ZD HDF5 files") from exc
    return h5py


def _collect_zd_attrs(handle: Any, dataset: Any) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for h5_path in (ZD_RAW_GROUP, ZD_ACQUISITION_GROUP, ZD_TIME_GROUP):
        if h5_path in handle:
            attrs.update({key: _scalarize(value) for key, value in handle[h5_path].attrs.items()})
    attrs.update({key: _scalarize(value) for key, value in dataset.attrs.items()})
    return attrs


def _infer_internal_shape(
    raw_shape: tuple[int, ...],
    n_samples_hint: int | None,
    n_channels_hint: int | None,
) -> tuple[int, int, str]:
    if len(raw_shape) != 2:
        raise ReaderError(f"ZD raw dataset must be 2-D, got shape {raw_shape}")

    rows, cols = raw_shape
    candidates: list[tuple[int, int, str]] = []
    if n_samples_hint is not None and n_channels_hint is not None:
        if raw_shape == (n_samples_hint, n_channels_hint):
            candidates.append((n_samples_hint, n_channels_hint, "time_channel"))
        if raw_shape == (n_channels_hint, n_samples_hint):
            candidates.append((n_samples_hint, n_channels_hint, "channel_time"))
    elif n_channels_hint is not None:
        if cols == n_channels_hint:
            candidates.append((rows, cols, "time_channel"))
        if rows == n_channels_hint:
            candidates.append((cols, rows, "channel_time"))
    elif n_samples_hint is not None:
        if rows == n_samples_hint:
            candidates.append((rows, cols, "time_channel"))
        if cols == n_samples_hint:
            candidates.append((cols, rows, "channel_time"))

    unique = {(n_samples, n_channels, orientation) for n_samples, n_channels, orientation in candidates}
    if len(unique) == 1:
        return next(iter(unique))
    if len(unique) > 1:
        raise ReaderError(
            "Ambiguous ZD HDF5 raw data orientation. "
            f"raw_shape={raw_shape}, Count={n_samples_hint}, NumberOfLoci={n_channels_hint}"
        )
    raise ReaderError(
        "Cannot infer ZD HDF5 raw data orientation. "
        f"raw_shape={raw_shape}, Count={n_samples_hint}, NumberOfLoci={n_channels_hint}. "
        "Expected metadata attributes Count and/or NumberOfLoci to match one dataset axis."
    )


def _raw_selection(orientation: str, time_slice: slice, channel_slice: slice) -> tuple[slice, slice]:
    if orientation == "time_channel":
        return time_slice, channel_slice
    if orientation == "channel_time":
        return channel_slice, time_slice
    raise ReaderError(f"Unsupported ZD raw orientation: {orientation}")


def _orient_raw_array(
    raw: np.ndarray,
    n_samples: int,
    n_channels: int,
    orientation: Any,
) -> np.ndarray:
    if orientation == "channel_time":
        raw = raw.T
    elif orientation != "time_channel":
        raise ReaderError(f"Unsupported ZD raw orientation: {orientation}")
    data = np.asarray(raw)
    if data.shape != (n_samples, n_channels):
        raise ReaderError(
            f"Oriented ZD data shape {data.shape} does not match {(n_samples, n_channels)}"
        )
    return data


def _slice_metadata(
    metadata: DASMetadata,
    *,
    internal_time_slice: slice,
    internal_channel_slice: slice,
    downsample: tuple[int, int],
) -> DASMetadata:
    time_stride = internal_time_slice.step
    channel_stride = internal_channel_slice.step
    extra_attrs = dict(metadata.extra_attrs)
    extra_attrs.update(
        {
            "original_n_samples": metadata.n_samples,
            "original_n_channels": metadata.n_channels,
            "time_slice": _slice_to_tuple(internal_time_slice),
            "channel_slice": _slice_to_tuple(internal_channel_slice),
            "downsample": downsample,
        }
    )
    sample_rate = None if metadata.sample_rate_hz is None else metadata.sample_rate_hz / time_stride
    dt_s = None if metadata.dt_s is None else metadata.dt_s * time_stride
    dx_m = None if metadata.dx_m is None else metadata.dx_m * channel_stride
    start_channel = metadata.start_channel
    if start_channel is not None:
        start_channel = start_channel + first_index(internal_channel_slice)
    return replace(
        metadata,
        n_samples=slice_length(internal_time_slice),
        n_channels=slice_length(internal_channel_slice),
        sample_rate_hz=sample_rate,
        dt_s=dt_s,
        dx_m=dx_m,
        start_channel=start_channel,
        extra_attrs=extra_attrs,
    )


def _slice_to_tuple(value: slice) -> tuple[int, int, int]:
    return int(value.start), int(value.stop), int(value.step)


def _ensure_non_empty(value: slice, *, axis_name: str) -> None:
    if slice_length(value) <= 0:
        raise ReaderError(f"{axis_name} selection is empty")


def _scalarize(value: Any) -> Any:
    if hasattr(value, "shape"):
        shape = getattr(value, "shape", None)
        if shape == ():
            value = value.item()
        elif getattr(value, "size", None) == 1:
            value = np.asarray(value).reshape(-1)[0].item()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value
    return value


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ReaderError(f"Cannot convert HDF5 attribute value {value!r} to int") from exc


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ReaderError(f"Cannot convert HDF5 attribute value {value!r} to float") from exc
