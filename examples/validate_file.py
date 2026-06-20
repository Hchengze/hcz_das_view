"""Validate a real or quasi-real DAS file without adding data to the repo.

Usage:

    python examples/validate_file.py input.h5
    python examples/validate_file.py input.dat
    python examples/validate_file.py input.h5 --output preview.png
    python examples/validate_file.py input.h5 --waveform-output trace.png --channel 10
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
from das_view.io.data_service import read_trace
from das_view.io.preview import PreviewResult, create_preview
from das_view.plotting.waveform import plot_waveform


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a supported DAS file.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--output", type=Path, default=None, help="Optional preview image path")
    parser.add_argument(
        "--waveform-output",
        type=Path,
        default=None,
        help="Optional waveform image path. Requires --channel or defaults to channel 0.",
    )
    parser.add_argument("--channel", type=int, default=0, help="Channel index for waveform validation")
    parser.add_argument("--max-samples", type=int, default=2000, help="Maximum preview samples")
    parser.add_argument("--max-channels", type=int, default=500, help="Maximum preview channels")
    parser.add_argument("--time-step", type=int, default=1, help="Waveform time downsampling step")
    return parser


def preview_summary(result: PreviewResult) -> dict[str, Any]:
    """Return a compact validation summary with no path-specific secrets."""

    extra = result.metadata.extra_attrs
    return {
        "reader_name": result.reader_name,
        "source_format": result.metadata.source_format,
        "n_samples": result.metadata.n_samples,
        "n_channels": result.metadata.n_channels,
        "sample_rate_hz": result.metadata.sample_rate_hz,
        "dx_m": result.metadata.dx_m,
        "raw_shape": extra.get("raw_shape"),
        "raw_orientation": extra.get("raw_orientation"),
        "preview_shape": result.preview.data.shape,
        "downsample": result.downsample,
        "warnings": tuple(result.warnings),
    }


def validate_file(
    path: Path,
    *,
    output: Path | None = None,
    waveform_output: Path | None = None,
    validate_waveform: bool = False,
    channel: int = 0,
    max_samples: int = 2000,
    max_channels: int = 500,
    time_step: int = 1,
) -> dict[str, Any]:
    """Validate metadata, preview, and optionally waveform plotting."""

    result = create_preview(
        path,
        max_samples=max_samples,
        max_channels=max_channels,
    )
    summary = preview_summary(result)
    print("Metadata")
    print(format_metadata(result.metadata))
    print("")
    print("Preview")
    for key, value in summary.items():
        if key == "warnings":
            continue
        print(f"{key}: {value}")
    for warning in result.warnings:
        print(f"warning: {warning}")

    if output is not None:
        from das_view.plotting.waterfall import plot_waterfall

        fig, _ = plot_waterfall(result.preview)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=150, bbox_inches="tight")
        print(f"saved_preview: {output}")

    if validate_waveform or waveform_output is not None:
        trace_result = read_trace(path, channel=channel, downsample=(time_step, 1))
        print("Waveform")
        print(f"waveform_reader_name: {trace_result.reader_name}")
        print(f"waveform_channel: {trace_result.requested_channels}")
        print(f"waveform_shape: {trace_result.das_data.data.shape}")
        print(f"waveform_downsample: {trace_result.downsample}")
        if waveform_output is not None:
            fig, _ = plot_waveform(
                trace_result.das_data,
                channels=list(range(trace_result.das_data.n_channels)),
            )
            waveform_output.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(waveform_output, dpi=150, bbox_inches="tight")
            print(f"saved_waveform: {waveform_output}")
        summary["waveform_shape"] = trace_result.das_data.data.shape
        summary["waveform_downsample"] = trace_result.downsample

    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_file(
            args.input,
            output=args.output,
            waveform_output=args.waveform_output,
            validate_waveform=False,
            channel=args.channel,
            max_samples=args.max_samples,
            max_channels=args.max_channels,
            time_step=args.time_step,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"validation failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
