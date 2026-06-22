"""Detect bounded DAS event candidates from a supported file.

Usage:

    python examples/event_detection_file.py input.h5 --method stalta --sta 50 --lta 500 --trigger-on 3.0
    python examples/event_detection_file.py input.dat --time-start 0 --time-stop 5000 --channel-start 0 --channel-stop 512 --method stalta --sta 25 --lta 250 --trigger-on 3.0 --trigger-off 1.5
    python examples/event_detection_file.py input.h5 --method envelope --threshold 0.8
    python examples/event_detection_file.py input.h5 --output events.json
    python examples/event_detection_file.py input.h5 --output events.csv
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

from das_view.analysis.events import EventCandidate, EventDetectionResult
from das_view.analysis.service import EventDetectionServiceResult, detect_events_for_file
from das_view.core.metadata_format import format_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect bounded DAS event candidates.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument("--time-start", type=int, default=0, help="Start time/sample index")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop time/sample index")
    parser.add_argument("--time-step", type=int, default=1, help="Time/sample step")
    parser.add_argument("--channel-start", type=int, default=0, help="Start channel index")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel index")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel step")
    parser.add_argument("--max-samples", type=int, default=4096, help="Default stop when --time-stop is omitted")
    parser.add_argument("--max-channels", type=int, default=512, help="Default stop when --channel-stop is omitted")
    parser.add_argument("--method", choices=("stalta", "envelope"), default="stalta")
    parser.add_argument("--threshold", type=float, default=None, help="Envelope feature threshold")
    parser.add_argument("--sta", type=int, default=50, help="STA window length in samples")
    parser.add_argument("--lta", type=int, default=500, help="LTA window length in samples")
    parser.add_argument("--trigger-on", type=float, default=3.0, help="STA/LTA trigger-on threshold")
    parser.add_argument("--trigger-off", type=float, default=None, help="STA/LTA trigger-off threshold")
    parser.add_argument("--min-duration-samples", type=int, default=1)
    parser.add_argument("--merge-gap-samples", type=int, default=0)
    parser.add_argument("--max-events", type=int, default=None)
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        service_result = detect_events_for_file(
            args.input,
            time_slice=build_time_slice_from_args(args),
            channel_slice=build_channel_slice_from_args(args),
            method=args.method,
            threshold=args.threshold,
            sta_samples=args.sta,
            lta_samples=args.lta,
            trigger_on=args.trigger_on,
            trigger_off=args.trigger_off,
            min_duration_samples=args.min_duration_samples,
            merge_gap_samples=args.merge_gap_samples,
            max_events=args.max_events,
            nan_policy=args.nan_policy,
        )
        print(format_metadata(service_result.metadata))
        print(f"reader_name: {service_result.reader_name}")
        print(f"selection_shape: {service_result.das_data.data.shape}")
        print(_text_summary(service_result.result))
        if args.output is not None:
            write_output(service_result, args.output)
            print(f"saved_event_candidates: {args.output}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"event candidate detection failed: {exc}") from exc
    return 0


def write_output(service_result: EventDetectionServiceResult, output: Path) -> None:
    """Write event-candidate output as JSON or CSV."""

    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix == ".json":
        output.write_text(json.dumps(service_result_to_dict(service_result), indent=2), encoding="utf-8")
        return
    if suffix == ".csv":
        write_candidates_csv(service_result.result.candidates, output)
        return
    raise ValueError("event candidate output must use .json or .csv")


def service_result_to_dict(service_result: EventDetectionServiceResult) -> dict[str, Any]:
    """Convert service output to JSON-friendly builtin containers."""

    return {
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
        "event_detection": event_detection_result_to_dict(service_result.result),
    }


def event_detection_result_to_dict(result: EventDetectionResult) -> dict[str, Any]:
    return {
        "method": result.method,
        "axis": result.axis,
        "input_shape": list(result.input_shape),
        "feature_shape": list(result.feature.shape),
        "parameters": result.parameters,
        "candidate_count": len(result.candidates),
        "candidates": [candidate_to_dict(candidate) for candidate in result.candidates],
    }


def candidate_to_dict(candidate: EventCandidate) -> dict[str, Any]:
    return {
        "event_id": candidate.event_id,
        "start_sample": candidate.start_sample,
        "end_sample": candidate.end_sample,
        "duration_samples": candidate.duration_samples,
        "channel_start": candidate.channel_start,
        "channel_end": candidate.channel_end,
        "peak_sample": candidate.peak_sample,
        "peak_channel": candidate.peak_channel,
        "peak_value": candidate.peak_value,
        "mean_value": candidate.mean_value,
        "max_value": candidate.max_value,
        "score": candidate.score,
    }


def write_candidates_csv(candidates: tuple[EventCandidate, ...], output: Path) -> None:
    rows = [candidate_to_dict(candidate) for candidate in candidates]
    fieldnames = [
        "event_id",
        "start_sample",
        "end_sample",
        "duration_samples",
        "channel_start",
        "channel_end",
        "peak_sample",
        "peak_channel",
        "peak_value",
        "mean_value",
        "max_value",
        "score",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _text_summary(result: EventDetectionResult) -> str:
    if not result.candidates:
        return f"event_candidates: method={result.method}, count=0"
    top = result.candidates[0]
    return (
        f"event_candidates: method={result.method}, count={len(result.candidates)}, "
        f"top=start:{top.start_sample}, end:{top.end_sample}, "
        f"channel:{top.channel_start}, score:{_short_value(top.score)}"
    )


def _slice_to_dict(value: slice) -> dict[str, int | None]:
    return {"start": value.start, "stop": value.stop, "step": value.step}


def _short_value(value) -> str:
    if isinstance(value, np.ndarray):
        return f"array(shape={value.shape})"
    return f"{value:.6g}" if isinstance(value, float) else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
