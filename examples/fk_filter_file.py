"""Apply a minimal FK velocity fan filter to a bounded DAS selection.

Usage:

    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.dat --output filtered_waterfall.png --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --reject --vmin 300 --vmax 3000
    python examples/fk_filter_file.py input.h5 --output filtered_waterfall.png --save-fk --vmin 300 --vmax 3000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.service import compute_fk_filter_for_file
from das_view.core.metadata_format import format_metadata
from das_view.io.data_service import read_selection
from das_view.plotting.fk import plot_fk
from das_view.plotting.waterfall import plot_waterfall


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a minimal bounded DAS FK velocity filter.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--output", type=Path, default=Path("das_fk_filtered.png"), help="Filtered waterfall output")
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
    parser.add_argument(
        "--vmin",
        dest="vmin_mps",
        type=float,
        default=None,
        help="Minimum apparent velocity in m/s for the selected range",
    )
    parser.add_argument(
        "--vmax",
        dest="vmax_mps",
        type=float,
        default=None,
        help="Maximum apparent velocity in m/s for the selected range",
    )
    parser.add_argument("--reject", action="store_true", help="Reject selected velocity range instead of passing it")
    parser.add_argument("--exclude-zero-wavenumber", action="store_true", help="Do not force the k=0 column into the pass fan")
    parser.add_argument("--nfft-time", type=int, default=None, help="FK time FFT length")
    parser.add_argument("--nfft-space", type=int, default=None, help="FK space FFT length")
    parser.add_argument("--window-time", default=None, help="Optional named window along time")
    parser.add_argument("--window-space", default=None, help="Optional named window along channel/space")
    parser.add_argument("--save-fk", action="store_true", help="Also save the filtered FK amplitude image")
    parser.add_argument("--fk-output", type=Path, default=None, help="Filtered FK image path when --save-fk is used")
    parser.add_argument("--db", action="store_true", help="Plot filtered FK values in dB")
    parser.add_argument(
        "--bandpass",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Optional bounded-data bandpass before FK filtering",
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


def build_fk_filter_kwargs_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Build validated FK velocity-filter keyword arguments from parsed CLI args."""

    vmin = args.vmin_mps
    vmax = args.vmax_mps
    if vmin is None and vmax is None:
        raise ValueError("at least one of --vmin or --vmax must be provided for FK velocity filtering")
    if vmin is not None and vmin <= 0:
        raise ValueError("--vmin must be positive")
    if vmax is not None and vmax <= 0:
        raise ValueError("--vmax must be positive")
    if vmin is not None and vmax is not None and vmin >= vmax:
        raise ValueError("--vmin must be smaller than --vmax")
    return {
        "vmin_mps": vmin,
        "vmax_mps": vmax,
        "pass_inside": not args.reject,
        "include_zero_wavenumber": not args.exclude_zero_wavenumber,
    }


def fk_output_path_from_args(args: argparse.Namespace) -> Path:
    """Return the FK image path used when --save-fk is enabled."""

    if args.fk_output is not None:
        return args.fk_output
    return args.output.with_name(f"{args.output.stem}_fk{args.output.suffix or '.png'}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        time_slice = build_time_slice_from_args(args)
        channel_slice = build_channel_slice_from_args(args)
        downsample = (args.downsample_time, args.downsample_channel)
        fk_filter_kwargs = build_fk_filter_kwargs_from_args(args)

        # This bounded metadata/sample-rate read keeps optional preprocessing
        # construction outside concrete reader internals.
        sample_selection = read_selection(
            args.input,
            time_slice=time_slice,
            channel_slice=channel_slice,
            downsample=downsample,
        )
        sample_rate_hz = sample_selection.metadata.sample_rate_hz
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for FK filtering but was not found")
        steps = build_processing_steps_from_args(args, sample_rate_hz=sample_rate_hz)

        service_result = compute_fk_filter_for_file(
            args.input,
            time_slice=time_slice,
            channel_slice=channel_slice,
            downsample=downsample,
            **fk_filter_kwargs,
            nfft_time=args.nfft_time,
            nfft_space=args.nfft_space,
            window_time=args.window_time,
            window_space=args.window_space,
            preprocessing_steps=steps,
            return_fk=args.save_fk,
        )

        fig, _ = plot_waterfall(
            service_result.das_data,
            title="FK-filtered DAS waterfall",
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")

        print(format_metadata(service_result.metadata))
        print(f"reader_name: {service_result.reader_name}")
        print(f"selection_shape: {service_result.das_data.data.shape}")
        print(f"time_slice: {service_result.selection.time_slice}")
        print(f"channel_slice: {service_result.selection.channel_slice}")
        print(f"downsample: {service_result.selection.downsample}")
        print(f"processing_steps: {steps}")
        print(f"filter_action: {'pass selected velocity range' if fk_filter_kwargs['pass_inside'] else 'reject selected velocity range'}")
        print(f"vmin_mps: {fk_filter_kwargs['vmin_mps']}")
        print(f"vmax_mps: {fk_filter_kwargs['vmax_mps']}")
        print(f"output: {args.output}")
        print(f"fk_filter_parameters: {service_result.filter_parameters}")
        print(f"mask_shape: {service_result.result.mask.shape}")
        print(f"saved_filtered_waterfall: {args.output}")

        if args.save_fk:
            if service_result.result.filtered_fk is None:
                raise ValueError("filtered FK result was not returned")
            fk_output = fk_output_path_from_args(args)
            fk_fig, _ = plot_fk(service_result.result.filtered_fk, db=args.db)
            fk_output.parent.mkdir(parents=True, exist_ok=True)
            fk_fig.savefig(fk_output, dpi=150, bbox_inches="tight")
            print(f"saved_filtered_fk_image: {fk_output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"FK velocity filtering failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
