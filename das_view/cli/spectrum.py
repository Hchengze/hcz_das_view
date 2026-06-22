"""Installed spectrum/PSD CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.analysis.service import (
    compute_psd_for_file,
    compute_spectrogram_for_file,
    compute_spectrum_for_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS spectrum/PSD/spectrogram output.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--channel", type=int, default=0, help="Zero-based channel index")
    parser.add_argument("--max-samples", type=int, default=4096, help="Maximum samples to read")
    parser.add_argument("--nfft", type=int, default=None, help="FFT length")
    parser.add_argument("--mode", choices=("amplitude", "power", "periodogram", "welch", "spectrogram"), default="amplitude")
    parser.add_argument("--nperseg", type=int, default=256, help="Welch/spectrogram segment length")
    parser.add_argument("--noverlap", type=int, default=None, help="Welch/spectrogram overlap")
    parser.add_argument("--db", action="store_true", help="Plot PSD in dB")
    parser.add_argument("--output", type=Path, default=None, help="Optional image output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode in {"amplitude", "power"}:
        service_result = compute_spectrum_for_file(
            args.input,
            channel=args.channel,
            max_samples=args.max_samples,
            kind=args.mode,
            nfft=args.nfft,
        )
    elif args.mode in {"periodogram", "welch"}:
        service_result = compute_psd_for_file(
            args.input,
            channel=args.channel,
            max_samples=args.max_samples,
            method=args.mode,
            nfft=args.nfft,
            nperseg=args.nperseg,
            noverlap=args.noverlap,
        )
    else:
        service_result = compute_spectrogram_for_file(
            args.input,
            channel=args.channel,
            max_samples=args.max_samples,
            nperseg=args.nperseg,
            noverlap=args.noverlap,
        )
    print(f"reader_name: {service_result.reader_name}")
    print(f"mode: {args.mode}")
    print(f"frequency_bins: {len(service_result.result.frequencies_hz)}")
    if args.output is not None:
        from das_view.plotting.spectra import plot_psd, plot_spectrogram, plot_spectrum

        if args.mode in {"amplitude", "power"}:
            fig, _ = plot_spectrum(service_result.result)
        elif args.mode in {"periodogram", "welch"}:
            fig, _ = plot_psd(service_result.result, db=args.db)
        else:
            fig, _ = plot_spectrogram(service_result.result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
