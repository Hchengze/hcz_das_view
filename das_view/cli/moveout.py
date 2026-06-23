"""Installed DAS wavefield moveout assisted-analysis CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.analysis.service import (
    compute_apparent_moveout_for_file,
    compute_directional_energy_for_file,
    compute_moveout_summary_for_file,
)
from das_view.io.export import save_json, to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS moveout and directional-energy attributes.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0)
    parser.add_argument("--time-stop", type=int, default=None)
    parser.add_argument("--time-step", type=int, default=1)
    parser.add_argument("--channel-start", type=int, default=0)
    parser.add_argument("--channel-stop", type=int, default=None)
    parser.add_argument("--channel-step", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument("--directional-energy", action="store_true")
    parser.add_argument("--apparent-moveout", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--channel-lag", type=int, default=1)
    parser.add_argument("--window-samples", type=int, default=None)
    parser.add_argument("--step-samples", type=int, default=None)
    parser.add_argument("--max-lag-samples", type=int, default=None)
    parser.add_argument("--nan-policy", choices=("omit", "raise"), default="raise")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    return parser


def _selection(args):
    return {
        "time_slice": slice(args.time_start, args.time_stop, args.time_step),
        "channel_slice": slice(args.channel_start, args.channel_stop, args.channel_step),
        "max_samples": args.max_samples,
        "max_channels": args.max_channels,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.directional_energy or args.apparent_moveout or args.summary):
        args.summary = True
    common = _selection(args)
    payload = {}
    try:
        if args.directional_energy:
            result = compute_directional_energy_for_file(args.input, nan_policy=args.nan_policy, **common)
            payload["directional_energy"] = result.result
            print(f"dominant_direction: {result.result.dominant_direction}")
            print(f"directional_ratio: {result.result.directional_ratio}")
        if args.apparent_moveout:
            result = compute_apparent_moveout_for_file(
                args.input,
                channel_lag=args.channel_lag,
                window_samples=args.window_samples,
                step_samples=args.step_samples,
                max_lag_samples=args.max_lag_samples,
                nan_policy=args.nan_policy,
                **common,
            )
            payload["apparent_moveout"] = result.result
            print(f"moveout_shape: {result.result.lag_samples.shape}")
        if args.summary:
            result = compute_moveout_summary_for_file(
                args.input,
                channel_lag=args.channel_lag,
                window_samples=args.window_samples,
                step_samples=args.step_samples,
                nan_policy=args.nan_policy,
                **common,
            )
            payload["summary"] = result.result
            print(f"summary_direction: {result.result.summary['dominant_direction']}")
            print(f"mean_abs_correlation_peak: {result.result.summary['mean_abs_correlation_peak']}")
    except ValueError as exc:
        raise SystemExit(f"moveout analysis error: {exc}") from exc
    if args.output is not None:
        save_json(to_jsonable(payload), args.output)
        print(f"saved_output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
