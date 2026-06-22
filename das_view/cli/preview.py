"""Installed preview CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.core.metadata_format import format_metadata
from das_view.io.preview import create_preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview a supported DAS file.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--output", type=Path, default=None, help="Optional preview image path")
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    parser.add_argument("--time-start", type=int, default=None, help="Optional start sample")
    parser.add_argument("--time-stop", type=int, default=None, help="Optional stop sample")
    parser.add_argument("--channel-start", type=int, default=None, help="Optional start channel")
    parser.add_argument("--channel-stop", type=int, default=None, help="Optional stop channel")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = create_preview(
        args.input,
        time_slice=slice(args.time_start, args.time_stop),
        channel_slice=slice(args.channel_start, args.channel_stop),
        max_samples=args.max_samples,
        max_channels=args.max_channels,
    )
    print(format_metadata(result.metadata))
    print(f"reader_name: {result.reader_name}")
    print(f"preview_shape: {result.preview.data.shape}")
    print(f"preview_downsample: {result.downsample}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    if args.output is not None:
        from das_view.plotting.waterfall import plot_waterfall

        fig, _ = plot_waterfall(result.preview)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_preview: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
