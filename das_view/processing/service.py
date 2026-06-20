"""DASData-level preprocessing service helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from das_view.core.data_model import DASData
from das_view.processing import preprocess


@dataclass(frozen=True, slots=True)
class PreprocessStep:
    """One named preprocessing operation and its keyword parameters."""

    name: str
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PreprocessResult:
    """Future-friendly result container for preprocessing workflows."""

    das_data: DASData
    steps: tuple[PreprocessStep, ...]


def apply_preprocess(
    das_data: DASData,
    steps: Sequence[PreprocessStep | tuple[str, Mapping[str, Any]] | str],
) -> DASData:
    """Apply preprocessing steps to a DASData copy and return a new DASData.

    The input DASData and its metadata are not modified. Processing history is
    appended to metadata.extra_attrs["preprocessing_history"].
    """

    normalized_steps = tuple(_normalize_step(step) for step in steps)
    data = np.array(das_data.data, dtype=float, copy=True)
    history_entries: list[dict[str, Any]] = []

    for step in normalized_steps:
        func = _STEP_FUNCTIONS.get(step.name)
        if func is None:
            raise ValueError(f"unknown preprocessing step: {step.name}")
        try:
            data = func(data, **dict(step.params))
        except TypeError as exc:
            raise ValueError(f"invalid parameters for preprocessing step {step.name}: {exc}") from exc
        history_entries.append(
            {
                "name": step.name,
                "params": _json_friendly_params(step.params),
            }
        )

    extra_attrs = dict(das_data.metadata.extra_attrs)
    existing_history = extra_attrs.get("preprocessing_history", [])
    if isinstance(existing_history, list):
        history = [*existing_history, *history_entries]
    else:
        history = [existing_history, *history_entries]
    extra_attrs["preprocessing_history"] = history

    metadata = replace(
        das_data.metadata,
        n_samples=int(data.shape[0]),
        n_channels=int(data.shape[1]),
        extra_attrs=extra_attrs,
    )
    return DASData(data=data, metadata=metadata)


def _normalize_step(step: PreprocessStep | tuple[str, Mapping[str, Any]] | str) -> PreprocessStep:
    if isinstance(step, PreprocessStep):
        return step
    if isinstance(step, str):
        return PreprocessStep(name=step, params={})
    if isinstance(step, tuple) and len(step) == 2:
        name, params = step
        if not isinstance(name, str):
            raise ValueError("preprocessing step name must be a string")
        if not isinstance(params, Mapping):
            raise ValueError("preprocessing step params must be a mapping")
        return PreprocessStep(name=name, params=dict(params))
    raise ValueError("steps must contain PreprocessStep, step names, or (name, params) tuples")


def _json_friendly_params(params: Mapping[str, Any]) -> dict[str, Any]:
    friendly: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, np.generic):
            friendly[key] = value.item()
        elif isinstance(value, np.ndarray):
            friendly[key] = value.tolist()
        elif isinstance(value, tuple):
            friendly[key] = list(value)
        else:
            friendly[key] = value
    return friendly


_STEP_FUNCTIONS = {
    "demean": preprocess.demean,
    "detrend_linear": preprocess.detrend_linear,
    "taper": preprocess.taper,
    "normalize": preprocess.normalize,
    "standardize": preprocess.standardize,
    "clip": preprocess.clip,
}
