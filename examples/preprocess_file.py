"""Apply basic preprocessing to a bounded preview and save a waterfall image.

Usage:

    python examples/preprocess_file.py input.h5 --output preview_processed.png --demean --taper 0.05 --normalize
    python examples/preprocess_file.py input.dat --output preview_processed.png --demean --normalize
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
    parser = argparse.ArgumentParser(
        description="Apply basic preprocessing to a bounded DAS preview."
    )
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("das_preview_processed.png"),
        help="Output preview image path",
    )
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    parser.add_argument("--demean", action="store_true", help="Remove mean along time axis")
    parser.add_argument(
        "--detrend",
        action="store_true",
        help="Remove linear trend along time axis",
    )
    parser.add_argument(
        "--taper",
        type=float,
        default=None,
        metavar="RATIO",
        help="Apply Hann edge taper along time axis, e.g. 0.05",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize preview by maximum absolute finite amplitude",
    )
    parser.add_argument(
        "--standardize",
        action="store_true",
        help="Standardize preview to finite z-scores",
    )
    parser.add_argument("--clip-min", type=float, default=None, help="Minimum clip value")
    parser.add_argument("--clip-max", type=float, default=None, help="Maximum clip value")
    parser.add_argument(
        "--clip-percentile",
        type=float,
        nargs="+",
        default=None,
        metavar="P",
        help="Percentile clipping: one value P means [P, 100-P], or provide LOW HIGH",
    )
    return parser


def build_steps_from_args(args: argparse.Namespace) -> list[tuple[str, dict[str, Any]]]:
    steps: list[tuple[str, dict[str, Any]]] = []
    if args.demean:
        steps.append(("demean", {"axis": 0}))
    if args.detrend:
        steps.append(("detrend_linear", {"axis": 0}))
    if args.taper is not None:
        steps.append(("taper", {"axis": 0, "ratio": args.taper}))
    if args.standardize:
        steps.append(("standardize", {"axis": None}))
    if args.normalize:
        steps.append(("normalize", {"axis": None, "mode": "maxabs"}))
    if args.clip_min is not None or args.clip_max is not None or args.clip_percentile is not None:
        percentile = None
        if args.clip_percentile is not None:
            if len(args.clip_percentile) == 1:
                percentile = args.clip_percentile[0]
            elif len(args.clip_percentile) == 2:
                percentile = tuple(args.clip_percentile)
            else:
                raise ValueError("--clip-percentile accepts one value or LOW HIGH")
        steps.append(
            (
                "clip",
                {
                    "min_value": args.clip_min,
                    "max_value": args.clip_max,
                    "percentile": percentile,
                },
            )
        )
    return steps


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        steps = build_steps_from_args(args)
        result = create_preview(
            args.input,
            max_samples=args.max_samples,
            max_channels=args.max_channels,
        )
        processed = apply_preprocess(result.preview, steps)

        print(format_metadata(result.metadata))
        print(f"reader_name: {result.reader_name}")
        print(f"preview_shape: {result.preview.data.shape}")
        print(f"preview_downsample: {result.downsample}")
        print(f"preprocessing_steps: {steps if steps else 'none'}")
        for warning in result.warnings:
            print(f"warning: {warning}")

        fig, _ = plot_waterfall(processed, title="Processed DAS preview")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_processed_preview: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"preprocessing failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
