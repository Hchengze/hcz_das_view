"""Installed traditional DAS denoising/enhancement CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.analysis.service import compute_denoised_selection_for_file, compute_enhancement_report_for_file
from das_view.io.export import save_json, to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply bounded traditional DAS signal enhancement helpers.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0)
    parser.add_argument("--time-stop", type=int, default=None)
    parser.add_argument("--time-step", type=int, default=1)
    parser.add_argument("--channel-start", type=int, default=0)
    parser.add_argument("--channel-stop", type=int, default=None)
    parser.add_argument("--channel-step", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument("--common-mode", choices=("median", "mean"), default=None)
    parser.add_argument("--despike", action="store_true")
    parser.add_argument("--z-threshold", type=float, default=8.0)
    parser.add_argument("--running-median", type=int, default=None)
    parser.add_argument("--channel-balance", choices=("rms", "std", "maxabs"), default=None)
    parser.add_argument("--local-normalize", type=int, default=None, metavar="WINDOW")
    parser.add_argument("--time-space-median", nargs=2, type=int, metavar=("TIME", "CHANNEL"))
    parser.add_argument("--robust-clip", nargs=2, type=float, metavar=("LOW", "HIGH"))
    parser.add_argument("--workflow", default=None, help="Comma-separated step names")
    parser.add_argument("--output-report", type=Path, default=None, help="Optional JSON report path")
    return parser


def build_steps(args) -> list[tuple[str, dict]]:
    steps: list[tuple[str, dict]] = []
    if args.workflow:
        for raw_name in args.workflow.split(","):
            name = raw_name.strip()
            if name:
                steps.append((name, {}))
    if args.common_mode:
        steps.append(("common_mode_removal", {"method": args.common_mode}))
    if args.despike:
        steps.append(("despike", {"z_threshold": args.z_threshold}))
    if args.running_median is not None:
        steps.append(("running_median_filter", {"size": args.running_median}))
    if args.channel_balance:
        steps.append(("channel_balance", {"target": args.channel_balance}))
    if args.local_normalize is not None:
        steps.append(("local_normalize", {"window_samples": args.local_normalize}))
    if args.time_space_median:
        steps.append(
            (
                "time_space_median_filter",
                {"time_size": args.time_space_median[0], "channel_size": args.time_space_median[1]},
            )
        )
    if args.robust_clip:
        steps.append(
            (
                "robust_clip",
                {"lower_percentile": args.robust_clip[0], "upper_percentile": args.robust_clip[1]},
            )
        )
    if not steps:
        steps.append(("common_mode_removal", {"method": "median"}))
    return steps


def _selection(args):
    return {
        "time_slice": slice(args.time_start, args.time_stop, args.time_step),
        "channel_slice": slice(args.channel_start, args.channel_stop, args.channel_step),
        "max_samples": args.max_samples,
        "max_channels": args.max_channels,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    steps = build_steps(args)
    common = _selection(args)
    result = compute_denoised_selection_for_file(args.input, denoise_steps=steps, **common)
    print(f"reader_name: {result.reader_name}")
    print(f"selection_shape: {result.selection.das_data.data.shape}")
    print(f"denoised_shape: {result.result.data.shape}")
    print(f"before_rms: {result.result.report.before['rms']}")
    print(f"after_rms: {result.result.report.after['rms']}")
    if args.output_report is not None:
        report = compute_enhancement_report_for_file(args.input, denoise_steps=steps, **common)
        save_json(to_jsonable(report.result), args.output_report)
        print(f"saved_report: {args.output_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
