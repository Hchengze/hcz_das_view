"""Bounded local real-world validation package for release-candidate checks.

The paths file is intentionally local-only. Summaries use sample indices and
file suffixes, never source paths or file names.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from das_view.acceleration import format_acceleration_report
from das_view.analysis.service import (
    compute_enhancement_report_for_file,
    compute_moveout_summary_for_file,
    compute_multiband_map_for_file,
    compute_quality_report_for_file,
    compute_statistics_for_file,
)
from das_view.io.data_service import read_trace
from das_view.io.export import to_jsonable
from das_view.io.preview import create_preview
from das_view.io.registry import default_registry

DEFAULT_PATHS_FILE = Path("local_validation_paths.txt")
DEFAULT_BANDS = ((1.0, 80.0), (80.0, 250.0))


@dataclass(frozen=True, slots=True)
class OperationStatus:
    operation: str
    status: str
    shape: tuple[int, ...] | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class SampleValidationSummary:
    file_index: int
    suffix: str
    reader: str | None
    shape: tuple[int, int] | None
    operations: tuple[OperationStatus, ...]


def parse_path_list(lines: Iterable[str]) -> list[Path]:
    """Parse local validation paths while ignoring comments and blanks."""

    paths: list[Path] = []
    for raw_line in lines:
        line = raw_line.lstrip("\ufeff").strip()
        if not line or line.startswith("#"):
            continue
        paths.append(Path(line))
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded real-world release-candidate validation on local DAS paths."
    )
    parser.add_argument("--paths-file", type=Path, default=DEFAULT_PATHS_FILE)
    parser.add_argument("--quick", action="store_true", help="Run the smaller quick validation matrix")
    parser.add_argument("--include-gpu-info", action="store_true", help="Add optional GPU availability diagnostics")
    parser.add_argument("--output", type=Path, default=None, help="Optional local JSON summary output")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--max-channels", type=int, default=None)
    parser.add_argument("--max-estimated-mb", type=float, default=256.0)
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    return parser


def run_validation_package(
    *,
    paths_file: Path = DEFAULT_PATHS_FILE,
    quick: bool = False,
    include_gpu_info: bool = False,
    output: Path | None = None,
    max_samples: int | None = None,
    max_channels: int | None = None,
    max_estimated_mb: float = 256.0,
    backend: str = "cpu",
) -> dict[str, object]:
    """Run a bounded local validation matrix and return a path-free summary."""

    if not paths_file.exists():
        summary = {
            "status": "skipped",
            "reason": "paths_file_not_found",
            "paths_file": paths_file.name,
            "samples": [],
        }
        _write_optional_summary(summary, output)
        return summary

    paths = parse_path_list(paths_file.read_text(encoding="utf-8-sig").splitlines())
    if not paths:
        summary = {
            "status": "skipped",
            "reason": "no_sample_paths",
            "paths_file": paths_file.name,
            "samples": [],
        }
        _write_optional_summary(summary, output)
        return summary

    resolved_max_samples = max_samples if max_samples is not None else (512 if quick else 4096)
    resolved_max_channels = max_channels if max_channels is not None else (64 if quick else 512)
    max_estimated_bytes = int(max_estimated_mb * 1024 * 1024) if max_estimated_mb is not None else None

    samples = [
        asdict(
            _validate_sample(
                path,
                file_index=index,
                quick=quick,
                max_samples=resolved_max_samples,
                max_channels=resolved_max_channels,
                max_estimated_bytes=max_estimated_bytes,
                backend=backend,
            )
        )
        for index, path in enumerate(paths, start=1)
    ]
    summary: dict[str, object] = {
        "status": "ok",
        "mode": "quick" if quick else "full",
        "sample_count": len(samples),
        "max_samples": resolved_max_samples,
        "max_channels": resolved_max_channels,
        "max_estimated_mb": max_estimated_mb,
        "backend": backend,
        "samples": samples,
    }
    if include_gpu_info:
        summary["gpu_info"] = format_acceleration_report(backend, as_text=False)
    _write_optional_summary(summary, output)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_validation_package(
        paths_file=args.paths_file,
        quick=args.quick,
        include_gpu_info=args.include_gpu_info,
        output=args.output,
        max_samples=args.max_samples,
        max_channels=args.max_channels,
        max_estimated_mb=args.max_estimated_mb,
        backend=args.backend,
    )
    print(json.dumps(to_jsonable(summary), indent=2))
    return 0


def _validate_sample(
    path: Path,
    *,
    file_index: int,
    quick: bool,
    max_samples: int,
    max_channels: int,
    max_estimated_bytes: int | None,
    backend: str,
) -> SampleValidationSummary:
    reader_name: str | None = None
    shape: tuple[int, int] | None = None
    operations: list[OperationStatus] = []

    registry = default_registry()
    try:
        reader = registry.get_reader(path)
        metadata = reader.read_metadata(path)
        reader_name = reader.name
        shape = (int(metadata.n_samples), int(metadata.n_channels))
        operations.append(OperationStatus("metadata", "ok", shape=shape))
    except Exception as exc:  # noqa: BLE001 - batch validation should continue.
        operations.append(OperationStatus("metadata", "error", message=_safe_message(exc, path)))
        return SampleValidationSummary(file_index, path.suffix.lower(), reader_name, shape, tuple(operations))

    operation_plan: list[tuple[str, Callable[[], object]]] = [
        ("preview", lambda: create_preview(path, max_samples=max_samples, max_channels=max_channels)),
        ("waveform", lambda: read_trace(path, channel=0, time_slice=slice(0, max_samples))),
        (
            "statistics",
            lambda: compute_statistics_for_file(
                path,
                max_samples=max_samples,
                max_channels=max_channels,
                max_estimated_bytes=max_estimated_bytes,
                backend=backend,
            ),
        ),
        (
            "qc",
            lambda: compute_quality_report_for_file(
                path,
                max_samples=max_samples,
                max_channels=max_channels,
                max_estimated_bytes=max_estimated_bytes,
                backend=backend,
            ),
        ),
    ]
    if not quick:
        operation_plan.extend(
            [
                (
                    "multiband",
                    lambda: compute_multiband_map_for_file(
                        path,
                        bands=DEFAULT_BANDS,
                        window_samples=min(256, max_samples),
                        step_samples=max(1, min(128, max_samples // 2)),
                        max_samples=max_samples,
                        max_channels=max_channels,
                        max_estimated_bytes=max_estimated_bytes,
                        backend=backend,
                    ),
                ),
                (
                    "denoise_report",
                    lambda: compute_enhancement_report_for_file(
                        path,
                        max_samples=max_samples,
                        max_channels=max_channels,
                        max_estimated_bytes=max_estimated_bytes,
                        denoise_steps=[("common_mode_removal", {"method": "median"})],
                    ),
                ),
                (
                    "moveout_summary",
                    lambda: compute_moveout_summary_for_file(
                        path,
                        max_samples=max_samples,
                        max_channels=max_channels,
                        max_estimated_bytes=max_estimated_bytes,
                        window_samples=min(256, max_samples),
                        step_samples=max(1, min(128, max_samples // 2)),
                        backend=backend,
                    ),
                ),
            ]
        )

    for operation, callback in operation_plan:
        operations.append(_run_operation(operation, callback, path))
    return SampleValidationSummary(file_index, path.suffix.lower(), reader_name, shape, tuple(operations))


def _run_operation(operation: str, callback: Callable[[], object], path: Path) -> OperationStatus:
    try:
        result = callback()
    except Exception as exc:  # noqa: BLE001 - local validation should summarize all failures.
        return OperationStatus(operation, "error", message=_safe_message(exc, path))
    shape = _result_shape(result)
    return OperationStatus(operation, "ok", shape=shape)


def _result_shape(result: object) -> tuple[int, ...] | None:
    das_data = getattr(result, "das_data", None)
    if das_data is not None and hasattr(das_data, "data"):
        return tuple(int(value) for value in das_data.data.shape)
    preview = getattr(result, "preview", None)
    if preview is not None and hasattr(preview, "data"):
        return tuple(int(value) for value in preview.data.shape)
    if hasattr(result, "das_data") and hasattr(result.das_data, "data"):
        return tuple(int(value) for value in result.das_data.data.shape)
    return None


def _safe_message(exc: Exception, path: Path) -> str:
    message = str(exc)
    replacements = {str(path), path.as_posix(), path.name}
    try:
        replacements.add(str(path.resolve()))
        replacements.add(path.resolve().as_posix())
    except OSError:
        pass
    for value in sorted(replacements, key=len, reverse=True):
        if value:
            message = message.replace(value, "<sample_path>")
    return message


def _write_optional_summary(summary: dict[str, object], output: Path | None) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(to_jsonable(summary), indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
