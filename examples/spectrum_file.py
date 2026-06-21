"""Compute and save a basic spectrum or spectrogram for one DAS channel.

Usage:

    python examples/spectrum_file.py input.h5 --channel 10 --output spectrum.png
    python examples/spectrum_file.py input.dat --channel 10 --power --output power.png
    python examples/spectrum_file.py input.h5 --channel 10 --spectrogram --output spectrogram.png
    python examples/spectrum_file.py input.h5 --channel 10 --bandpass 1 50 --output spectrum_filtered.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.spectrum import (
    amplitude_spectrum,
    power_spectrum,
    single_channel_spectrogram,
)
from das_view.core.metadata_format import format_metadata
from das_view.io.data_service import read_trace
from das_view.plotting.spectra import plot_spectrogram, plot_spectrum
from das_view.processing.service import apply_preprocess


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute a basic DAS spectrum from a bounded trace.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--channel", type=int, default=0, help="Zero-based channel index")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("das_spectrum.png"),
        help="Output image path",
    )
    parser.add_argument("--max-samples", type=int, default=4096, help="Maximum time samples to read")
    parser.add_argument("--nfft", type=int, default=None, help="FFT length for spectrum modes")
    parser.add_argument("--window", default=None, help="Optional window name for spectrum modes")
    parser.add_argument("--power", action="store_true", help="Plot power spectrum instead of amplitude")
    parser.add_argument("--spectrogram", action="store_true", help="Plot a single-channel spectrogram")
    parser.add_argument("--nperseg", type=int, default=256, help="Spectrogram segment length")
    parser.add_argument("--noverlap", type=int, default=None, help="Spectrogram overlap")
    parser.add_argument(
        "--bandpass",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Optional preview-level bandpass before spectrum calculation",
    )
    return parser


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
            },
        )
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        time_slice = slice(0, args.max_samples)
        trace_result = read_trace(args.input, channel=args.channel, time_slice=time_slice)
        das_data = trace_result.das_data
        sample_rate_hz = das_data.metadata.sample_rate_hz
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for spectrum analysis but was not found")

        steps = build_processing_steps_from_args(args, sample_rate_hz=sample_rate_hz)
        if steps:
            das_data = apply_preprocess(das_data, steps)

        print(format_metadata(trace_result.metadata))
        print(f"reader_name: {trace_result.reader_name}")
        print(f"trace_shape: {das_data.data.shape}")
        print(f"channel: {args.channel}")
        print(f"processing_steps: {steps}")

        if args.spectrogram:
            result = single_channel_spectrogram(
                das_data,
                channel=0,
                nperseg=args.nperseg,
                noverlap=args.noverlap,
            )
            fig, _ = plot_spectrogram(result, title=f"Spectrogram - channel {args.channel}")
            print(
                "spectrogram: "
                f"frequencies={result.frequencies_hz.shape}, times={result.times_s.shape}, "
                f"values={result.values.shape}"
            )
        elif args.power:
            result = power_spectrum(das_data, channels=0, nfft=args.nfft, window=args.window)
            fig, _ = plot_spectrum(result, title=f"Power spectrum - channel {args.channel}")
            print(f"power_spectrum: frequencies={result.frequencies_hz.shape}, values={result.values.shape}")
        else:
            result = amplitude_spectrum(das_data, channels=0, nfft=args.nfft, window=args.window)
            fig, _ = plot_spectrum(result, title=f"Amplitude spectrum - channel {args.channel}")
            print(
                f"amplitude_spectrum: frequencies={result.frequencies_hz.shape}, "
                f"values={result.values.shape}"
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_spectrum_image: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"spectrum analysis failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
