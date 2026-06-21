"""Compute and save a bounded DAS FK image.

Usage:

    python examples/fk_file.py input.h5 --output fk.png
    python examples/fk_file.py input.dat --output fk.png --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512
    python examples/fk_file.py input.h5 --output fk_db.png --db
    python examples/fk_file.py input.h5 --output fk_power.png --output-mode power
    python examples/fk_file.py input.h5 --output fk_filtered.png --bandpass 1 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.fk import fk_transform
from das_view.core.metadata_format import format_metadata
from das_view.io.data_service import read_selection
from das_view.plotting.fk import plot_fk
from das_view.processing.service import apply_preprocess


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute a bounded DAS FK transform image.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--output", type=Path, default=Path("das_fk.png"), help="Output image path")
    parser.add_argument("--max-samples", type=int, default=4096, help="Default maximum time samples")
    parser.add_argument("--max-channels", type=int, default=512, help="Default maximum channels")
    parser.add_argument("--time-start", type=int, default=0, help="Time selection start sample")
    parser.add_argument("--time-stop", type=int, default=None, help="Time selection stop sample")
    parser.add_argument("--channel-start", type=int, default=0, help="Channel selection start index")
    parser.add_argument("--channel-stop", type=int, default=None, help="Channel selection stop index")
    parser.add_argument("--time-step", type=int, default=1, help="Time selection step")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel selection step")
    parser.add_argument("--downsample-time", type=int, default=1, help="Additional reader time downsample")
    parser.add_argument("--downsample-channel", type=int, default=1, help="Additional reader channel downsample")
    parser.add_argument("--nfft-time", type=int, default=None, help="FK time FFT length")
    parser.add_argument("--nfft-space", type=int, default=None, help="FK space FFT length")
    parser.add_argument("--window-time", default=None, help="Optional named window along time")
    parser.add_argument("--window-space", default=None, help="Optional named window along channel/space")
    parser.add_argument("--output-mode", choices=("amplitude", "power"), default="amplitude")
    parser.add_argument("--db", action="store_true", help="Plot FK values in dB")
    parser.add_argument(
        "--bandpass",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Optional bounded-data bandpass before FK analysis",
    )
    parser.add_argument("--order", type=int, default=4, help="Bandpass filter order")
    parser.add_argument("--causal", action="store_true", help="Use causal bandpass filtering")
    return parser


def build_time_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default time slice from parsed CLI args."""

    stop = args.time_stop if args.time_stop is not None else args.time_start + args.max_samples
    return slice(args.time_start, stop, args.time_step)


def build_channel_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default channel slice from parsed CLI args."""

    stop = args.channel_stop if args.channel_stop is not None else args.channel_start + args.max_channels
    return slice(args.channel_start, stop, args.channel_step)


def build_processing_steps_from_args(
    args: argparse.Namespace,
    *,
    sample_rate_hz: float,
) -> list[tuple[str, dict[str, Any]]]:
    """Build optional preprocessing/filter steps from parsed CLI args."""

    if args.bandpass is None:
        return []
    return [
        (
            "bandpass",
            {
                "sample_rate_hz": sample_rate_hz,
                "freqmin_hz": args.bandpass[0],
                "freqmax_hz": args.bandpass[1],
                "axis": 0,
                "order": args.order,
                "causal": args.causal,
            },
        )
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        selection = read_selection(
            args.input,
            time_slice=build_time_slice_from_args(args),
            channel_slice=build_channel_slice_from_args(args),
            downsample=(args.downsample_time, args.downsample_channel),
        )
        sample_rate_hz = selection.metadata.sample_rate_hz
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for FK analysis but was not found")
        steps = build_processing_steps_from_args(args, sample_rate_hz=sample_rate_hz)
        das_data = apply_preprocess(selection.das_data, steps) if steps else selection.das_data
        result = fk_transform(
            das_data,
            nfft_time=args.nfft_time,
            nfft_space=args.nfft_space,
            window_time=args.window_time,
            window_space=args.window_space,
            output=args.output_mode,
        )
        fig, _ = plot_fk(result, db=args.db)

        print(format_metadata(das_data.metadata))
        print(f"reader_name: {selection.reader_name}")
        print(f"selection_shape: {das_data.data.shape}")
        print(f"time_slice: {selection.time_slice}")
        print(f"channel_slice: {selection.channel_slice}")
        print(f"downsample: {selection.downsample}")
        print(f"processing_steps: {steps}")
        print(
            "fk: "
            f"output={result.output}, values={result.values.shape}, "
            f"frequencies={result.frequencies_hz.shape}, "
            f"wavenumbers={result.wavenumbers_cycles_per_m.shape}, "
            f"nfft_time={result.nfft_time}, nfft_space={result.nfft_space}"
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_fk_image: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"FK analysis failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
