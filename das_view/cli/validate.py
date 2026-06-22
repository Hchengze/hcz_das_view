"""Installed validation CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.core.metadata_format import format_metadata
from das_view.io.data_service import read_trace
from das_view.io.preview import create_preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a supported DAS file.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    parser.add_argument("--channel", type=int, default=0, help="Optional waveform channel")
    parser.add_argument("--time-step", type=int, default=1, help="Waveform time downsampling step")
    parser.add_argument("--waveform-output", type=Path, default=None, help="Optional waveform image path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preview = create_preview(
        args.input,
        max_samples=args.max_samples,
        max_channels=args.max_channels,
    )
    print(format_metadata(preview.metadata))
    print(f"reader_name: {preview.reader_name}")
    print(f"preview_shape: {preview.preview.data.shape}")
    print(f"preview_downsample: {preview.downsample}")
    trace = read_trace(args.input, channel=args.channel, downsample=(args.time_step, 1))
    print(f"waveform_shape: {trace.das_data.data.shape}")
    print(f"waveform_downsample: {trace.downsample}")
    if args.waveform_output is not None:
        from das_view.plotting.waveform import plot_waveform

        fig, _ = plot_waveform(trace.das_data, channels=[0])
        args.waveform_output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.waveform_output, dpi=150, bbox_inches="tight")
        print(f"saved_waveform: {args.waveform_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
