"""Compute bounded DAS statistics from a supported file.

Usage:

    python examples/statistics_file.py input.h5
    python examples/statistics_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512
    python examples/statistics_file.py input.h5 --axis channel
    python examples/statistics_file.py input.h5 --axis time
    python examples/statistics_file.py input.h5 --percentiles 1 5 50 95 99
    python examples/statistics_file.py input.h5 --output stats.json
    python examples/statistics_file.py input.h5 --output stats.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.service import StatisticsServiceResult, compute_statistics_for_file
from das_view.analysis.statistics import StatisticsResult
from das_view.core.metadata_format import format_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS statistics.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0, help="Start time/sample index")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop time/sample index")
    parser.add_argument("--time-step", type=int, default=1, help="Time/sample step")
    parser.add_argument("--channel-start", type=int, default=0, help="Start channel index")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel index")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel step")
    parser.add_argument("--max-samples", type=int, default=4096, help="Default stop when --time-stop is omitted")
    parser.add_argument("--max-channels", type=int, default=512, help="Default stop when --channel-stop is omitted")
    parser.add_argument(
        "--axis",
        choices=("global", "time", "channel"),
        default="global",
        help="global, time-wise reduced over samples, or channel-wise reduced over channels",
    )
    parser.add_argument(
        "--percentiles",
        type=float,
        nargs="+",
        default=[1, 5, 25, 50, 75, 95, 99],
        help="Percentiles to compute",
    )
    parser.add_argument(
        "--nan-policy",
        choices=("omit", "raise"),
        default="omit",
        help="Omit non-finite values or raise on NaN/Inf",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional .json or .csv output path")
    return parser


def build_time_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default time slice from parsed CLI args."""

    stop = args.time_stop if args.time_stop is not None else args.max_samples
    return slice(args.time_start, stop, args.time_step)


def build_channel_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default channel slice from parsed CLI args."""

    stop = args.channel_stop if args.channel_stop is not None else args.max_channels
    return slice(args.channel_start, stop, args.channel_step)


def axis_from_arg(value: str) -> int | None:
    """Map CLI axis names to numpy reduction axes."""

    if value == "global":
        return None
    if value == "time":
        return 0
    if value == "channel":
        return 1
    raise ValueError("axis must be global, time, or channel")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        service_result = compute_statistics_for_file(
            args.input,
            time_slice=build_time_slice_from_args(args),
            channel_slice=build_channel_slice_from_args(args),
            axis=axis_from_arg(args.axis),
            percentiles=args.percentiles,
            nan_policy=args.nan_policy,
        )
        print(format_metadata(service_result.metadata))
        print(f"reader_name: {service_result.reader_name}")
        print(f"selection_shape: {service_result.das_data.data.shape}")
        print(f"axis: {args.axis}")
        print(_text_summary(service_result.result))
        if args.output is not None:
            write_output(service_result, args.output)
            print(f"saved_statistics: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"statistics analysis failed: {exc}") from exc
    return 0


def write_output(service_result: StatisticsServiceResult, output: Path) -> None:
    """Write statistics output as JSON or global-statistics CSV."""

    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".json":
        output.write_text(json.dumps(service_result_to_dict(service_result), indent=2), encoding="utf-8")
        return
    if suffix == ".csv":
        write_global_csv(service_result.result, output)
        return
    raise ValueError("statistics output must use .json or .csv")


def write_global_csv(result: StatisticsResult, output: Path) -> None:
    """Write global scalar statistics as CSV."""

    if result.axis is not None:
        raise ValueError("CSV output currently supports only global statistics; use JSON for axis output")
    row = _global_result_row(result)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)


def service_result_to_dict(service_result: StatisticsServiceResult) -> dict[str, Any]:
    """Convert a service result to JSON-friendly builtin containers."""

    return {
        "reader_name": service_result.reader_name,
        "selection": {
            "time_slice": _slice_to_dict(service_result.selection.time_slice),
            "channel_slice": _slice_to_dict(service_result.selection.channel_slice),
            "downsample": list(service_result.selection.downsample),
        },
        "metadata": {
            "n_samples": service_result.metadata.n_samples,
            "n_channels": service_result.metadata.n_channels,
            "sample_rate_hz": service_result.metadata.sample_rate_hz,
            "dt_s": service_result.metadata.dt_s,
            "dx_m": service_result.metadata.dx_m,
            "source_format": service_result.metadata.source_format,
            "source_path": service_result.metadata.source_path,
        },
        "preprocessing_history": service_result.preprocessing_history,
        "statistics": statistics_result_to_dict(service_result.result),
    }


def statistics_result_to_dict(result: StatisticsResult) -> dict[str, Any]:
    """Convert StatisticsResult to JSON-friendly builtin containers."""

    return {
        "axis": result.axis,
        "input_shape": list(result.input_shape),
        "count": _json_value(result.count),
        "finite_count": _json_value(result.finite_count),
        "nan_count": _json_value(result.nan_count),
        "posinf_count": _json_value(result.posinf_count),
        "neginf_count": _json_value(result.neginf_count),
        "mean": _json_value(result.mean),
        "std": _json_value(result.std),
        "min": _json_value(result.min),
        "max": _json_value(result.max),
        "median": _json_value(result.median),
        "percentiles": {str(key): _json_value(value) for key, value in result.percentiles.items()},
        "rms": _json_value(result.rms),
        "abs_mean": _json_value(result.abs_mean),
        "peak_to_peak": _json_value(result.peak_to_peak),
        "energy": _json_value(result.energy),
        "nan_policy": result.nan_policy,
        "source_metadata": result.source_metadata,
    }


def _text_summary(result: StatisticsResult) -> str:
    prefix = "statistics"
    if result.axis == 0:
        prefix = "time-wise statistics"
    elif result.axis == 1:
        prefix = "channel-wise statistics"
    return (
        f"{prefix}: input_shape={result.input_shape}, finite_count={_short_value(result.finite_count)}, "
        f"mean={_short_value(result.mean)}, std={_short_value(result.std)}, "
        f"rms={_short_value(result.rms)}, energy={_short_value(result.energy)}"
    )


def _global_result_row(result: StatisticsResult) -> dict[str, Any]:
    row = {
        "count": result.count,
        "finite_count": result.finite_count,
        "nan_count": result.nan_count,
        "posinf_count": result.posinf_count,
        "neginf_count": result.neginf_count,
        "mean": result.mean,
        "std": result.std,
        "min": result.min,
        "max": result.max,
        "median": result.median,
        "rms": result.rms,
        "abs_mean": result.abs_mean,
        "peak_to_peak": result.peak_to_peak,
        "energy": result.energy,
    }
    for percentile, value in result.percentiles.items():
        row[f"p{percentile:g}"] = value
    return row


def _slice_to_dict(value: slice) -> dict[str, int | None]:
    return {"start": value.start, "stop": value.stop, "step": value.step}


def _json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _short_value(value) -> str:
    if isinstance(value, np.ndarray):
        return f"array(shape={value.shape})"
    return f"{value:.6g}" if isinstance(value, float) else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
