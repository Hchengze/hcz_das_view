"""Compute and save a bounded DAS spectrum, PSD, or spectrogram image.

Usage:

    python examples/spectrum_file.py input.h5 --channel 10 --output spectrum.png
    python examples/spectrum_file.py input.h5 --channel 10 --power --output power.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd periodogram --output psd.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd welch --nperseg 512 --output welch.png
    python examples/spectrum_file.py input.h5 --channel 10 --psd welch --db --output welch_db.png
    python examples/spectrum_file.py input.h5 --channel 10 --spectrogram --output spectrogram.png
    python examples/spectrum_file.py input.h5 --channel 10 --bandpass 1 50 --psd welch --output filtered_welch.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.service import (
    SpectrumServiceResult,
    compute_psd_for_file,
    compute_spectrogram_for_file,
    compute_spectrum_for_file,
)
from das_view.analysis.spectrum import PSDResult, SpectrogramResult, SpectrumResult
from das_view.core.metadata_format import format_metadata
from das_view.plotting.spectra import plot_psd, plot_spectrogram, plot_spectrum


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS spectrum/PSD/spectrogram output.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--channel", type=int, default=0, help="Zero-based channel index")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("das_spectrum.png"),
        help="Output image path",
    )
    parser.add_argument("--max-samples", type=int, default=4096, help="Maximum time samples to read")
    parser.add_argument("--nfft", type=int, default=None, help="FFT length for spectrum/PSD modes")
    parser.add_argument("--window", default=None, help="Optional window name")
    parser.add_argument("--power", action="store_true", help="Plot FFT-derived power spectrum")
    parser.add_argument(
        "--psd",
        choices=("periodogram", "welch"),
        default=None,
        help="Plot periodogram or Welch PSD instead of amplitude/power spectrum",
    )
    parser.add_argument("--db", action="store_true", help="Plot PSD in dB with 10*log10(values)")
    parser.add_argument("--spectrogram", action="store_true", help="Plot a single-channel spectrogram")
    parser.add_argument("--nperseg", type=int, default=256, help="Welch/spectrogram segment length")
    parser.add_argument("--noverlap", type=int, default=None, help="Welch/spectrogram overlap")
    parser.add_argument(
        "--bandpass",
        type=float,
        nargs=2,
        metavar=("FREQMIN", "FREQMAX"),
        help="Optional bounded-data bandpass before analysis",
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


def choose_analysis_mode(args: argparse.Namespace) -> Literal["amplitude", "power", "psd", "spectrogram"]:
    """Return the requested analysis mode with simple conflict validation."""

    selected = sum(bool(value) for value in (args.power, args.psd is not None, args.spectrogram))
    if selected > 1:
        raise ValueError("choose only one of --power, --psd, or --spectrogram")
    if args.spectrogram:
        return "spectrogram"
    if args.psd is not None:
        return "psd"
    if args.power:
        return "power"
    return "amplitude"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        mode = choose_analysis_mode(args)
        initial = compute_spectrum_for_file(
            args.input,
            channel=args.channel,
            max_samples=args.max_samples,
            kind="amplitude",
            nfft=args.nfft,
            window=args.window,
        )
        sample_rate_hz = initial.metadata.sample_rate_hz
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for spectrum analysis but was not found")
        steps = build_processing_steps_from_args(args, sample_rate_hz=sample_rate_hz)
        service_result = _compute_requested_result(args, mode=mode, steps=steps)
        fig = _plot_service_result(service_result, channel=args.channel, db=args.db)

        print(format_metadata(service_result.metadata))
        print(f"reader_name: {service_result.reader_name}")
        print(f"trace_shape: {service_result.das_data.data.shape}")
        print(f"channel: {args.channel}")
        print(f"analysis_mode: {mode}")
        print(f"processing_steps: {steps}")
        print(_result_summary(service_result.result))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"saved_spectrum_image: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"spectrum analysis failed: {exc}") from exc
    return 0


def _compute_requested_result(
    args: argparse.Namespace,
    *,
    mode: str,
    steps: list[tuple[str, dict[str, Any]]],
) -> SpectrumServiceResult:
    common = {
        "channel": args.channel,
        "max_samples": args.max_samples,
        "preprocessing_steps": steps,
    }
    if mode == "spectrogram":
        return compute_spectrogram_for_file(
            args.input,
            nperseg=args.nperseg,
            noverlap=args.noverlap,
            window=args.window or "hann",
            **common,
        )
    if mode == "psd":
        return compute_psd_for_file(
            args.input,
            method=args.psd,
            nperseg=args.nperseg,
            noverlap=args.noverlap,
            nfft=args.nfft,
            window=args.window or "hann",
            **common,
        )
    return compute_spectrum_for_file(
        args.input,
        kind="power" if mode == "power" else "amplitude",
        nfft=args.nfft,
        window=args.window,
        **common,
    )


def _plot_service_result(service_result: SpectrumServiceResult, *, channel: int, db: bool):
    result = service_result.result
    if isinstance(result, PSDResult):
        fig, _ = plot_psd(result, title=f"{result.method.title()} PSD - channel {channel}", db=db)
        return fig
    if isinstance(result, SpectrogramResult):
        fig, _ = plot_spectrogram(result, title=f"Spectrogram - channel {channel}")
        return fig
    if isinstance(result, SpectrumResult):
        title = f"{result.kind.title()} spectrum - channel {channel}"
        fig, _ = plot_spectrum(result, title=title)
        return fig
    raise ValueError(f"unsupported analysis result type: {type(result).__name__}")


def _result_summary(result: SpectrumResult | PSDResult | SpectrogramResult) -> str:
    if isinstance(result, PSDResult):
        return (
            f"psd: method={result.method}, frequencies={result.frequencies_hz.shape}, "
            f"values={result.values.shape}, scaling={result.scaling}"
        )
    if isinstance(result, SpectrogramResult):
        return (
            "spectrogram: "
            f"frequencies={result.frequencies_hz.shape}, times={result.times_s.shape}, "
            f"values={result.values.shape}"
        )
    return f"{result.kind}_spectrum: frequencies={result.frequencies_hz.shape}, values={result.values.shape}"


if __name__ == "__main__":
    raise SystemExit(main())
