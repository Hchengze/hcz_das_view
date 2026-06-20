"""Plot one or more DAS channel waveforms from a supported file.

Usage:

    python examples/plot_waveform.py input.h5 --channel 10 --output trace.png
    python examples/plot_waveform.py input.dat --channels 10 20 30 --output traces.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.io.data_service import read_trace
from das_view.plotting.waveform import plot_waveform


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot DAS waveform traces from a supported file.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--channel", type=int, default=None, help="Single channel index to plot")
    parser.add_argument(
        "--channels",
        type=int,
        nargs="+",
        default=None,
        help="One or more channel indices to plot",
    )
    parser.add_argument("--output", type=Path, default=Path("das_waveform.png"), help="Output image path")
    parser.add_argument("--time-start", type=int, default=None, help="Start sample index")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop sample index")
    parser.add_argument("--time-step", type=int, default=1, help="Time downsampling step")
    parser.add_argument("--time-unit", choices=("s", "ms"), default="s", help="Time axis unit")
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Plot raw amplitudes instead of per-trace normalized amplitudes",
    )
    parser.add_argument(
        "--offset-mode",
        choices=("auto", "none", "index"),
        default="auto",
        help="How to offset multiple traces",
    )
    return parser


def _selected_channels(channel: int | None, channels: list[int] | None) -> int | list[int]:
    if channel is not None and channels is not None:
        raise ValueError("Use either --channel or --channels, not both")
    if channels is not None:
        return channels
    if channel is not None:
        return channel
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = _selected_channels(args.channel, args.channels)
    result = read_trace(
        args.input,
        channel=selected,
        time_slice=slice(args.time_start, args.time_stop),
        downsample=(args.time_step, 1),
    )
    print(f"reader_name: {result.reader_name}")
    print(f"waveform_shape: {result.das_data.data.shape}")
    print(f"selected_channels: {result.requested_channels}")
    print(f"downsample: {result.downsample}")

    fig, _ = plot_waveform(
        result.das_data,
        channels=list(range(result.das_data.n_channels)),
        time_unit=args.time_unit,
        offset_mode=args.offset_mode,
        normalize=not args.no_normalize,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150, bbox_inches="tight")
    print(f"saved_waveform: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
