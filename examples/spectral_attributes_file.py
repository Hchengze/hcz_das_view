"""Compute bounded DAS band energy or spectral attributes.

Usage:

    python examples/spectral_attributes_file.py input.h5 --bands 1 5 5 20 20 80
    python examples/spectral_attributes_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --bands 1 10 10 50
    python examples/spectral_attributes_file.py input.h5 --attributes
    python examples/spectral_attributes_file.py input.h5 --attributes --frequency-range 1 80
    python examples/spectral_attributes_file.py input.h5 --bands 1 5 5 20 --average-channels
    python examples/spectral_attributes_file.py input.h5 --output attrs.json
    python examples/spectral_attributes_file.py input.h5 --output band_energy.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.service import (
    BandEnergyServiceResult,
    SpectralAttributesServiceResult,
    compute_band_energy_for_file,
    compute_spectral_attributes_for_file,
)
from das_view.analysis.spectral_attributes import BandEnergyResult, SpectralAttributesResult
from das_view.core.metadata_format import format_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute bounded DAS spectral attributes.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0, help="Start time/sample index")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop time/sample index")
    parser.add_argument("--time-step", type=int, default=1, help="Time/sample step")
    parser.add_argument("--channel-start", type=int, default=0, help="Start channel index")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel index")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel step")
    parser.add_argument("--max-samples", type=int, default=4096, help="Default stop when --time-stop is omitted")
    parser.add_argument("--max-channels", type=int, default=512, help="Default stop when --channel-stop is omitted")
    parser.add_argument("--nfft", type=int, default=None, help="FFT length")
    parser.add_argument(
        "--bands",
        type=float,
        nargs="+",
        default=None,
        metavar=("FMIN", "FMAX"),
        help="Band pairs such as --bands 1 5 5 20",
    )
    parser.add_argument("--attributes", action="store_true", help="Compute spectral attributes instead of bands")
    parser.add_argument("--frequency-range", type=float, nargs=2, default=None, metavar=("LOW", "HIGH"))
    parser.add_argument("--rolloff", type=float, default=0.95, help="Spectral rolloff fraction")
    parser.add_argument("--average-channels", action="store_true", help="Average spectra across selected channels")
    parser.add_argument(
        "--nan-policy",
        choices=("omit", "raise"),
        default="raise",
        help="Omit non-finite values or raise on NaN/Inf",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional .json or .csv output path")
    return parser


def build_time_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default time slice from parsed CLI args."""

    stop = args.time_stop if args.time_stop is not None else args.max_samples
    return slice(args.time_start, stop, args.time_step)


def build_channel_slice_from_args(args: argparse.Namespace) -> slice:
    """Build a bounded default channel slice from parsed CLI args."""

    stop = args.channel_stop if args.channel_stop is not None else args.max_channels
    return slice(args.channel_start, stop, args.channel_step)


def parse_band_pairs(values) -> tuple[tuple[float, float], ...]:
    """Parse a flat CLI band list into frequency pairs."""

    if values is None:
        return ()
    if len(values) % 2 != 0:
        raise ValueError("--bands must contain an even number of frequency limits")
    pairs = []
    for index in range(0, len(values), 2):
        pairs.append((float(values[index]), float(values[index + 1])))
    return tuple(pairs)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        time_slice = build_time_slice_from_args(args)
        channel_slice = build_channel_slice_from_args(args)
        if args.attributes:
            service_result = compute_spectral_attributes_for_file(
                args.input,
                time_slice=time_slice,
                channel_slice=channel_slice,
                nfft=args.nfft,
                frequency_range=args.frequency_range,
                rolloff=args.rolloff,
                average_channels=args.average_channels,
                nan_policy=args.nan_policy,
            )
        else:
            bands = parse_band_pairs(args.bands)
            if not bands:
                raise ValueError("--bands is required unless --attributes is used")
            service_result = compute_band_energy_for_file(
                args.input,
                bands=bands,
                time_slice=time_slice,
                channel_slice=channel_slice,
                nfft=args.nfft,
                average_channels=args.average_channels,
                nan_policy=args.nan_policy,
            )

        print(format_metadata(service_result.metadata))
        print(f"reader_name: {service_result.reader_name}")
        print(f"selection_shape: {service_result.das_data.data.shape}")
        print(_text_summary(service_result.result))
        if args.output is not None:
            write_output(service_result, args.output)
            print(f"saved_spectral_attributes: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"spectral attribute analysis failed: {exc}") from exc
    return 0


def write_output(
    service_result: BandEnergyServiceResult | SpectralAttributesServiceResult,
    output: Path,
) -> None:
    """Write spectral output as JSON or CSV."""

    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".json":
        output.write_text(json.dumps(service_result_to_dict(service_result), indent=2), encoding="utf-8")
        return
    if suffix == ".csv":
        if isinstance(service_result.result, BandEnergyResult):
            write_band_energy_csv(service_result.result, output)
        else:
            write_spectral_attributes_csv(service_result.result, output)
        return
    raise ValueError("spectral attribute output must use .json or .csv")


def service_result_to_dict(
    service_result: BandEnergyServiceResult | SpectralAttributesServiceResult,
) -> dict[str, Any]:
    """Convert a service result to JSON-friendly builtin containers."""

    result = service_result.result
    payload: dict[str, Any] = {
        "reader_name": service_result.reader_name,
        "selection": {
            "time_slice": _slice_to_dict(service_result.selection.time_slice),
            "channel_slice": _slice_to_dict(service_result.selection.channel_slice),
            "downsample": list(service_result.selection.downsample),
        },
        "metadata": {
            "n_samples": service_result.metadata.n_samples,
            "n_channels": service_result.metadata.n_channels,
            "sample_rate_hz": service_result.metadata.sample_rate_hz,
            "dt_s": service_result.metadata.dt_s,
            "dx_m": service_result.metadata.dx_m,
            "source_format": service_result.metadata.source_format,
            "source_path": service_result.metadata.source_path,
        },
        "preprocessing_history": service_result.preprocessing_history,
    }
    if isinstance(result, BandEnergyResult):
        payload["band_energy"] = band_energy_result_to_dict(result)
    else:
        payload["spectral_attributes"] = spectral_attributes_result_to_dict(result)
    return payload


def band_energy_result_to_dict(result: BandEnergyResult) -> dict[str, Any]:
    return {
        "bands": [list(band) for band in result.bands],
        "band_energy": _json_value(result.band_energy),
        "band_power": _json_value(result.band_power),
        "total_energy": _json_value(result.total_energy),
        "band_energy_ratio": _json_value(result.band_energy_ratio),
        "frequencies_hz": _json_value(result.frequencies_hz),
        "sample_rate_hz": result.sample_rate_hz,
        "axis": result.axis,
        "nfft": result.nfft,
        "scaling": result.scaling,
        "average_channels": result.average_channels,
    }


def spectral_attributes_result_to_dict(result: SpectralAttributesResult) -> dict[str, Any]:
    return {
        "dominant_frequency_hz": _json_value(result.dominant_frequency_hz),
        "peak_amplitude_or_power": _json_value(result.peak_amplitude_or_power),
        "spectral_centroid_hz": _json_value(result.spectral_centroid_hz),
        "spectral_bandwidth_hz": _json_value(result.spectral_bandwidth_hz),
        "spectral_rolloff_hz": _json_value(result.spectral_rolloff_hz),
        "low_frequency_hz": result.low_frequency_hz,
        "high_frequency_hz": result.high_frequency_hz,
        "total_energy": _json_value(result.total_energy),
        "frequencies_hz": _json_value(result.frequencies_hz),
        "sample_rate_hz": result.sample_rate_hz,
        "axis": result.axis,
        "nfft": result.nfft,
        "rolloff": result.rolloff,
        "frequency_range": None if result.frequency_range is None else list(result.frequency_range),
        "average_channels": result.average_channels,
    }


def write_band_energy_csv(result: BandEnergyResult, output: Path) -> None:
    rows = []
    energy = np.asarray(result.band_energy)
    power = np.asarray(result.band_power)
    ratio = np.asarray(result.band_energy_ratio)
    if energy.ndim == 1:
        for band_index, (fmin, fmax) in enumerate(result.bands):
            rows.append(
                {
                    "band_index": band_index,
                    "channel_index": "average",
                    "fmin_hz": fmin,
                    "fmax_hz": fmax,
                    "band_energy": energy[band_index],
                    "band_power": power[band_index],
                    "band_energy_ratio": ratio[band_index],
                }
            )
    else:
        for band_index, (fmin, fmax) in enumerate(result.bands):
            for channel_index in range(energy.shape[1]):
                rows.append(
                    {
                        "band_index": band_index,
                        "channel_index": channel_index,
                        "fmin_hz": fmin,
                        "fmax_hz": fmax,
                        "band_energy": energy[band_index, channel_index],
                        "band_power": power[band_index, channel_index],
                        "band_energy_ratio": ratio[band_index, channel_index],
                    }
                )
    _write_rows(output, rows)


def write_spectral_attributes_csv(result: SpectralAttributesResult, output: Path) -> None:
    dominant = np.atleast_1d(result.dominant_frequency_hz)
    rows = []
    for index in range(dominant.size):
        rows.append(
            {
                "channel_index": "average" if result.average_channels else index,
                "dominant_frequency_hz": np.atleast_1d(result.dominant_frequency_hz)[index],
                "peak_amplitude_or_power": np.atleast_1d(result.peak_amplitude_or_power)[index],
                "spectral_centroid_hz": np.atleast_1d(result.spectral_centroid_hz)[index],
                "spectral_bandwidth_hz": np.atleast_1d(result.spectral_bandwidth_hz)[index],
                "spectral_rolloff_hz": np.atleast_1d(result.spectral_rolloff_hz)[index],
                "total_energy": np.atleast_1d(result.total_energy)[index],
            }
        )
    _write_rows(output, rows)


def _write_rows(output: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no rows to write")
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _text_summary(result: BandEnergyResult | SpectralAttributesResult) -> str:
    if isinstance(result, BandEnergyResult):
        return (
            f"band_energy: bands={len(result.bands)}, shape={result.band_energy.shape}, "
            f"average_channels={result.average_channels}"
        )
    return (
        "spectral_attributes: "
        f"dominant={_short_value(result.dominant_frequency_hz)}, "
        f"centroid={_short_value(result.spectral_centroid_hz)}, "
        f"bandwidth={_short_value(result.spectral_bandwidth_hz)}, "
        f"rolloff={_short_value(result.spectral_rolloff_hz)}"
    )


def _slice_to_dict(value: slice) -> dict[str, int | None]:
    return {"start": value.start, "stop": value.stop, "step": value.step}


def _json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _short_value(value) -> str:
    if isinstance(value, np.ndarray):
        return f"array(shape={value.shape})"
    return f"{value:.6g}" if isinstance(value, float) else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
