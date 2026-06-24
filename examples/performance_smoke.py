"""Bounded local performance smoke utility for supported DAS files."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from das_view.acceleration import AccelerationRuntimeError, format_acceleration_report, is_cupy_available
from das_view.acceleration.benchmark import GpuRuntimeError
from das_view.analysis.service import (
    compute_multiband_map_for_file,
    compute_quality_report_for_file,
    compute_statistics_for_file,
)
from das_view.core.exceptions import ReaderError
from das_view.io.export import to_jsonable
from das_view.io.preview import create_preview
from das_view.utils.memory import format_nbytes


@dataclass(frozen=True, slots=True)
class OperationTiming:
    operation: str
    elapsed_seconds: float
    selection_shape: tuple[int, int] | None
    estimated_mb: float | None
    status: str
    backend: str = "cpu"
    message: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run bounded DAS performance smoke operations for local diagnostics."
    )
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument(
        "--operations",
        default="preview,statistics,qc",
        help="Comma-separated operations: preview,statistics,qc,multiband",
    )
    parser.add_argument(
        "--multiband",
        type=float,
        nargs="+",
        default=[1.0, 10.0, 10.0, 50.0],
        help="Band limits for the multiband smoke operation as fmin fmax pairs.",
    )
    parser.add_argument("--window-samples", type=int, default=256)
    parser.add_argument("--step-samples", type=int, default=128)
    parser.add_argument(
        "--max-estimated-mb",
        type=float,
        default=256.0,
        help="Reject analysis selections estimated above this MiB limit.",
    )
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--compare-backends", action="store_true", help="Run CPU plus GPU when CuPy is available")
    parser.add_argument("--gpu-info", action="store_true", help="Print optional GPU backend diagnostics")
    parser.add_argument("--output-json", type=Path, default=None, help="Optional JSON timing output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    operations = _parse_operations(args.operations)
    max_bytes = _max_estimated_bytes(args.max_estimated_mb)
    if args.gpu_info:
        print(format_acceleration_report(args.backend, as_text=True))
    timings: list[OperationTiming] = []
    backends = _requested_backends(args.backend, compare_backends=args.compare_backends)
    for backend in backends:
        for operation in operations:
            timing = _time_operation(
                operation,
                backend,
                lambda op=operation, selected_backend=backend: _run_operation(
                    op,
                    args.input,
                    max_samples=args.max_samples,
                    max_channels=args.max_channels,
                    max_estimated_bytes=max_bytes,
                    bands=_parse_band_pairs(args.multiband),
                    window_samples=args.window_samples,
                    step_samples=args.step_samples,
                    backend=selected_backend,
                ),
            )
            timings.append(timing)
            _print_timing(timing)
    if args.output_json is not None:
        args.output_json.write_text(json.dumps(to_jsonable([asdict(item) for item in timings]), indent=2), encoding="utf-8")
        print(f"saved_output: {args.output_json}")
    return 0


def _parse_operations(value: str) -> tuple[str, ...]:
    allowed = {"preview", "statistics", "qc", "multiband"}
    operations = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    if not operations:
        raise ValueError("--operations must include at least one operation")
    unknown = sorted(set(operations) - allowed)
    if unknown:
        raise ValueError(f"unsupported operations: {', '.join(unknown)}")
    return operations


def _parse_band_pairs(values: list[float]) -> tuple[tuple[float, float], ...]:
    if len(values) % 2:
        raise ValueError("--multiband expects an even number of band limits")
    return tuple((float(values[i]), float(values[i + 1])) for i in range(0, len(values), 2))


def _run_operation(
    operation: str,
    path: Path,
    *,
    max_samples: int,
    max_channels: int,
    max_estimated_bytes: int | None,
    bands: tuple[tuple[float, float], ...],
    window_samples: int,
    step_samples: int,
    backend: str,
):
    if operation == "preview":
        return create_preview(path, max_samples=max_samples, max_channels=max_channels)
    kwargs = {
        "max_samples": max_samples,
        "max_channels": max_channels,
        "max_estimated_bytes": max_estimated_bytes,
    }
    if operation == "statistics":
        return compute_statistics_for_file(path, backend=backend, **kwargs)
    if operation == "qc":
        return compute_quality_report_for_file(path, backend=backend, **kwargs)
    if operation == "multiband":
        return compute_multiband_map_for_file(
            path,
            bands=bands,
            window_samples=window_samples,
            step_samples=step_samples,
            backend=backend,
            **kwargs,
        )
    raise ValueError(f"unsupported operation: {operation}")


def _time_operation(operation: str, backend: str, callback: Callable[[], object]) -> OperationTiming:
    started = time.perf_counter()
    try:
        result = callback()
    except (AccelerationRuntimeError, GpuRuntimeError, ImportError, ReaderError, RuntimeError, ValueError) as exc:
        return OperationTiming(
            operation=operation,
            elapsed_seconds=time.perf_counter() - started,
            selection_shape=None,
            estimated_mb=None,
            status="error",
            backend=backend,
            message=str(exc),
        )
    elapsed = time.perf_counter() - started
    selection = getattr(result, "selection", None)
    if selection is not None:
        data = selection.das_data.data
        shape = tuple(int(value) for value in data.shape)
        estimated_nbytes = selection.estimated_nbytes
    else:
        preview = getattr(result, "preview", None)
        data = None if preview is None else preview.data
        shape = None if data is None else tuple(int(value) for value in data.shape)
        estimated_nbytes = None if data is None else int(data.nbytes)
    estimated_mb = None if estimated_nbytes is None else estimated_nbytes / (1024 * 1024)
    return OperationTiming(
        operation=operation,
        elapsed_seconds=elapsed,
        selection_shape=shape,
        estimated_mb=estimated_mb,
        status="ok",
        backend=backend,
    )


def _print_timing(timing: OperationTiming) -> None:
    shape = "N/A" if timing.selection_shape is None else str(timing.selection_shape)
    estimated = "N/A" if timing.estimated_mb is None else format_nbytes(int(timing.estimated_mb * 1024 * 1024))
    print(
        f"operation={timing.operation} backend={timing.backend} status={timing.status} "
        f"elapsed={timing.elapsed_seconds:.4f}s selection_shape={shape} estimated={estimated}"
    )
    if timing.message:
        print(f"message={timing.message}")


def _max_estimated_bytes(value: float | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("--max-estimated-mb must be non-negative")
    return int(value * 1024 * 1024)


def _requested_backends(backend: str, *, compare_backends: bool) -> tuple[str, ...]:
    if not compare_backends:
        return (backend,)
    if is_cupy_available():
        return ("cpu", "gpu")
    print("compare_backends: CuPy is not available; GPU run skipped.")
    return ("cpu",)


if __name__ == "__main__":
    raise SystemExit(main())
