"""Installed statistics CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from das_view.analysis.service import compute_statistics_for_file
from das_view.io.export import save_csv_rows, save_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS statistics.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0, help="Start sample")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop sample")
    parser.add_argument("--time-step", type=int, default=1, help="Sample step")
    parser.add_argument("--channel-start", type=int, default=0, help="Start channel")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel step")
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument("--axis", choices=("global", "time", "channel"), default="global")
    parser.add_argument("--percentiles", type=float, nargs="+", default=[1, 5, 25, 50, 75, 95, 99])
    parser.add_argument("--nan-policy", choices=("omit", "raise"), default="omit")
    parser.add_argument("--output", type=Path, default=None, help="Optional .json or .csv output")
    return parser


def axis_from_label(label: str) -> int | None:
    if label == "global":
        return None
    if label == "time":
        return 0
    if label == "channel":
        return 1
    raise ValueError(f"unsupported axis: {label}")


def result_summary_rows(result) -> list[dict[str, Any]]:
    stats = result.result
    return [
        {
            "reader_name": result.reader_name,
            "axis": stats.axis,
            "count": stats.count,
            "finite_count": stats.finite_count,
            "nan_count": stats.nan_count,
            "mean": stats.mean,
            "std": stats.std,
            "rms": stats.rms,
            "energy": stats.energy,
            "min": stats.min,
            "max": stats.max,
        }
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service_result = compute_statistics_for_file(
        args.input,
        time_slice=slice(args.time_start, args.time_stop, args.time_step),
        channel_slice=slice(args.channel_start, args.channel_stop, args.channel_step),
        max_samples=args.max_samples,
        max_channels=args.max_channels,
        axis=axis_from_label(args.axis),
        percentiles=args.percentiles,
        nan_policy=args.nan_policy,
    )
    rows = result_summary_rows(service_result)
    print(f"reader_name: {service_result.reader_name}")
    print(f"selection_shape: {service_result.das_data.data.shape}")
    print(f"mean: {service_result.result.mean}")
    print(f"std: {service_result.result.std}")
    print(f"rms: {service_result.result.rms}")
    print(f"energy: {service_result.result.energy}")
    if args.output is not None:
        if args.output.suffix.lower() == ".csv":
            save_csv_rows(rows, args.output)
        else:
            save_json({"summary": rows}, args.output)
        print(f"saved_output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
