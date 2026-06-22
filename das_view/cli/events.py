"""Installed event-candidate CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.analysis.service import detect_events_for_file
from das_view.io.export import event_candidates_to_rows, save_csv_rows, save_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect bounded DAS event candidates.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0, help="Start sample")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop sample")
    parser.add_argument("--time-step", type=int, default=1, help="Sample step")
    parser.add_argument("--channel-start", type=int, default=0, help="Start channel")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel step")
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument("--method", choices=("stalta", "envelope"), default="stalta")
    parser.add_argument("--threshold", type=float, default=None, help="Envelope threshold")
    parser.add_argument("--sta", type=int, default=50, help="STA samples")
    parser.add_argument("--lta", type=int, default=500, help="LTA samples")
    parser.add_argument("--trigger-on", type=float, default=3.0)
    parser.add_argument("--trigger-off", type=float, default=None)
    parser.add_argument("--min-duration-samples", type=int, default=1)
    parser.add_argument("--merge-gap-samples", type=int, default=0)
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--nan-policy", choices=("omit", "raise"), default="raise")
    parser.add_argument("--output", type=Path, default=None, help="Optional .json or .csv output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service_result = detect_events_for_file(
        args.input,
        time_slice=slice(args.time_start, args.time_stop, args.time_step),
        channel_slice=slice(args.channel_start, args.channel_stop, args.channel_step),
        max_samples=args.max_samples,
        max_channels=args.max_channels,
        downsample=(1, 1),
        method=args.method,
        threshold=args.threshold,
        sta_samples=args.sta,
        lta_samples=args.lta,
        trigger_on=args.trigger_on,
        trigger_off=args.trigger_off,
        min_duration_samples=args.min_duration_samples,
        merge_gap_samples=args.merge_gap_samples,
        max_events=args.max_events,
        nan_policy=args.nan_policy,
    )
    rows = event_candidates_to_rows(service_result.result.candidates)
    print(f"reader_name: {service_result.reader_name}")
    print(f"method: {service_result.result.method}")
    print(f"candidate_count: {len(rows)}")
    if args.output is not None:
        if args.output.suffix.lower() == ".csv":
            save_csv_rows(rows, args.output)
        else:
            save_json(
                {
                    "reader_name": service_result.reader_name,
                    "method": service_result.result.method,
                    "parameters": service_result.result.parameters,
                    "candidates": rows,
                },
                args.output,
            )
        print(f"saved_output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
