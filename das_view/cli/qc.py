"""Installed DAS QC and multiband feature CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.analysis.qc import channel_quality_rows
from das_view.analysis.service import (
    compute_coherence_for_file,
    compute_multiband_map_for_file,
    compute_quality_report_for_file,
)
from das_view.core.exceptions import ReaderError
from das_view.io.export import save_csv_rows, save_json, to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS QC and multiband feature summaries.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0)
    parser.add_argument("--time-stop", type=int, default=None)
    parser.add_argument("--time-step", type=int, default=1)
    parser.add_argument("--channel-start", type=int, default=0)
    parser.add_argument("--channel-stop", type=int, default=None)
    parser.add_argument("--channel-step", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument(
        "--max-estimated-mb",
        type=float,
        default=None,
        help="Reject selections estimated above this MiB limit; defaults stay bounded by max samples/channels.",
    )
    parser.add_argument("--quality-report", action="store_true", help="Compute a QC report")
    parser.add_argument("--bad-channels", action="store_true", help="Export bad-channel table rows")
    parser.add_argument("--multiband", type=float, nargs="+", help="Band limits as fmin fmax pairs")
    parser.add_argument("--window-samples", type=int, default=1024)
    parser.add_argument("--step-samples", type=int, default=512)
    parser.add_argument("--normalize", choices=("total", "max"), default=None)
    parser.add_argument("--coherence", action="store_true", help="Compute local channel coherence")
    parser.add_argument("--channel-lag", type=int, default=1)
    parser.add_argument("--nan-policy", choices=("omit", "raise"), default="omit")
    parser.add_argument("--output", type=Path, default=None, help="Optional .json or .csv output")
    return parser


def parse_band_pairs(values: list[float] | None):
    if values is None:
        return None
    if len(values) % 2:
        raise ValueError("--multiband expects an even number of band limits")
    return tuple((float(values[i]), float(values[i + 1])) for i in range(0, len(values), 2))


def _selection(args):
    return {
        "time_slice": slice(args.time_start, args.time_stop, args.time_step),
        "channel_slice": slice(args.channel_start, args.channel_stop, args.channel_step),
        "max_samples": args.max_samples,
        "max_channels": args.max_channels,
        "max_estimated_bytes": _max_estimated_bytes(args.max_estimated_mb),
    }


def _max_estimated_bytes(value: float | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("--max-estimated-mb must be non-negative")
    return int(value * 1024 * 1024)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.quality_report or args.bad_channels or args.multiband or args.coherence):
        args.quality_report = True

    payload = {}
    rows = None
    try:
        common = _selection(args)
        if args.quality_report or args.bad_channels:
            result = compute_quality_report_for_file(args.input, nan_policy=args.nan_policy, **common)
            rows = channel_quality_rows(result.result)
            payload["quality_report"] = result.result
            print(f"reader_name: {result.reader_name}")
            print(f"bad_channel_count: {len(result.result.bad_channel_indices)}")
            print(f"mean_quality_score: {result.result.global_summary['mean_quality_score']}")

        bands = parse_band_pairs(args.multiband)
        if bands is not None:
            result = compute_multiband_map_for_file(
                args.input,
                bands=bands,
                window_samples=args.window_samples,
                step_samples=args.step_samples,
                normalize=args.normalize,
                nan_policy=args.nan_policy,
                **common,
            )
            payload["multiband"] = result.result
            print(f"multiband_shape: {result.result.values.shape}")

        if args.coherence:
            result = compute_coherence_for_file(
                args.input,
                channel_lag=args.channel_lag,
                window_samples=args.window_samples,
                step_samples=args.step_samples,
                nan_policy=args.nan_policy,
                **common,
            )
            payload["coherence"] = result.result
            print(f"coherence_shape: {result.result.coherence.shape}")
    except (ReaderError, ValueError) as exc:
        raise SystemExit(f"qc error: {exc}") from exc

    if args.output is not None:
        if args.output.suffix.lower() == ".csv":
            if rows is None:
                raise ValueError("CSV output is supported for QC channel rows; use JSON for maps")
            save_csv_rows(rows, args.output)
        else:
            save_json(to_jsonable(payload), args.output)
        print(f"saved_output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
