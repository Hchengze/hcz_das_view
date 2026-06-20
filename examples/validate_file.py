"""Validate a real or quasi-real DAS file without adding data to the repo.

Usage:

    python examples/validate_file.py input.h5
    python examples/validate_file.py input.dat --output preview.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.core.metadata_format import format_metadata
from das_view.io.preview import create_preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a supported DAS file.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--output", type=Path, default=None, help="Optional preview image path")
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    return parser


def validate_file(
    path: Path,
    *,
    output: Path | None = None,
    max_samples: int = 2000,
    max_channels: int = 500,
) -> int:
    result = create_preview(
        path,
        max_samples=max_samples,
        max_channels=max_channels,
    )
    print("Metadata")
    print(format_metadata(result.metadata))
    print("")
    print("Preview")
    print(f"reader_name: {result.reader_name}")
    print(f"preview_shape: {result.preview.data.shape}")
    print(f"downsample: {result.downsample}")
    for warning in result.warnings:
        print(f"warning: {warning}")

    if output is not None:
        from das_view.plotting.waterfall import plot_waterfall

        fig, _ = plot_waterfall(result.preview)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=150, bbox_inches="tight")
        print(f"saved_preview: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return validate_file(
        args.input,
        output=args.output,
        max_samples=args.max_samples,
        max_channels=args.max_channels,
    )


if __name__ == "__main__":
    raise SystemExit(main())
