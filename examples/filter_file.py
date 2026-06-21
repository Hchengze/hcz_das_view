"""Apply a basic filter to a bounded preview and save a waterfall image.

Usage:

    python examples/filter_file.py input.h5 --output preview_filtered.png --bandpass 1 50
    python examples/filter_file.py input.dat --output preview_filtered.png --lowpass 80
    python examples/filter_file.py input.h5 --output preview_filtered.png --notch 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.core.metadata_format import format_metadata
from das_view.io.preview import create_preview
from das_view.plotting.waterfall import plot_waterfall
from das_view.processing.service import apply_preprocess


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter a bounded DAS preview.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("das_preview_filtered.png"),
        help="Output preview image path",
    )
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    parser.add_argument("--order", type=int, default=4, help="Butterworth filter order")
    parser.add_argument(
        "--causal",
        action="store_true",
        help="Use causal filtering instead of zero-phase filtering",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lowpass", type=float, metavar="HZ", help="Low-pass cutoff frequency")
    group.add_argument("--highpass", type=float, metavar="HZ", help="High-pass cutoff frequency")
    group.add_argument(
        "--bandpass",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Band-pass frequency range",
    )
    group.add_argument(
        "--bandstop",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Band-stop frequency range",
    )
    group.add_argument("--notch", type=float, metavar="HZ", help="Notch frequency")
    parser.add_argument("--quality", type=float, default=30.0, help="Notch quality factor")
    return parser


def build_filter_steps_from_args(
    args: argparse.Namespace,
    *,
    sample_rate_hz: float,
) -> list[tuple[str, dict[str, Any]]]:
    common = {
        "sample_rate_hz": sample_rate_hz,
        "axis": 0,
        "zero_phase": not args.causal,
    }
    if args.lowpass is not None:
        return [("lowpass", {**common, "cutoff_hz": args.lowpass, "order": args.order})]
    if args.highpass is not None:
        return [("highpass", {**common, "cutoff_hz": args.highpass, "order": args.order})]
    if args.bandpass is not None:
        return [
            (
                "bandpass",
                {
                    **common,
                    "freqmin_hz": args.bandpass[0],
                    "freqmax_hz": args.bandpass[1],
                    "order": args.order,
                },
            )
        ]
    if args.bandstop is not None:
        return [
            (
                "bandstop",
                {
                    **common,
                    "freqmin_hz": args.bandstop[0],
                    "freqmax_hz": args.bandstop[1],
                    "order": args.order,
                },
            )
        ]
    if args.notch is not None:
        return [
            (
                "notch",
                {
                    **common,
                    "notch_hz": args.notch,
                    "quality": args.quality,
                },
            )
        ]
    raise ValueError("one filter option is required")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = create_preview(
            args.input,
            max_samples=args.max_samples,
            max_channels=args.max_channels,
        )
        sample_rate_hz = result.preview.metadata.sample_rate_hz or result.metadata.sample_rate_hz
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for filtering but was not found in metadata")
        steps = build_filter_steps_from_args(args, sample_rate_hz=sample_rate_hz)
        filtered = apply_preprocess(result.preview, steps)

        print(format_metadata(result.metadata))
        print(f"reader_name: {result.reader_name}")
        print(f"preview_shape: {result.preview.data.shape}")
        print(f"preview_downsample: {result.downsample}")
        print(f"filter_steps: {steps}")
        for warning in result.warnings:
            print(f"warning: {warning}")

        fig, _ = plot_waterfall(filtered, title="Filtered DAS preview")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_filtered_preview: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"filtering failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
