"""Create/export DAS ROIs, annotations, and ROI analysis summaries.

Usage:

    python examples/roi_export_file.py input.h5 --detect-events --method stalta --sta 50 --lta 500 --trigger-on 3.0 --output-rois rois.json
    python examples/roi_export_file.py input.h5 --detect-events --method envelope --threshold 0.8 --output-events events.csv --output-rois rois.json
    python examples/roi_export_file.py input.h5 --roi 0 1000 0 100 --output-summary roi_summary.json
    python examples/roi_export_file.py input.h5 --roi 0 1000 0 100 --output-summary roi_summary.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from das_view.analysis.roi import ROISet, TimeChannelROI, rois_from_event_candidates
from das_view.analysis.service import compute_roi_statistics_for_file, detect_events_for_file
from das_view.core.metadata_format import format_metadata
from das_view.io.export import (
    analysis_summary_to_rows,
    event_candidates_to_rows,
    rois_to_rows,
    save_csv_rows,
    save_json,
    to_jsonable,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export DAS ROIs and ROI analysis summaries.")
    parser.add_argument("input", type=Path, help="Path to a supported DAS file")
    parser.add_argument(
        "--roi",
        type=int,
        nargs=4,
        action="append",
        metavar=("T0", "T1", "C0", "C1"),
        help="Manual ROI as start_sample end_sample channel_start channel_end; repeatable",
    )
    parser.add_argument("--detect-events", action="store_true", help="Detect event candidates and convert them to ROIs")
    parser.add_argument("--method", choices=("stalta", "envelope"), default="stalta")
    parser.add_argument("--threshold", type=float, default=None, help="Envelope threshold")
    parser.add_argument("--sta", type=int, default=50, help="STA samples")
    parser.add_argument("--lta", type=int, default=500, help="LTA samples")
    parser.add_argument("--trigger-on", type=float, default=3.0, help="STA/LTA trigger-on")
    parser.add_argument("--trigger-off", type=float, default=None, help="STA/LTA trigger-off")
    parser.add_argument("--time-start", type=int, default=0)
    parser.add_argument("--time-stop", type=int, default=None)
    parser.add_argument("--channel-start", type=int, default=0)
    parser.add_argument("--channel-stop", type=int, default=None)
    parser.add_argument("--max-samples", type=int, default=4096)
    parser.add_argument("--max-channels", type=int, default=512)
    parser.add_argument("--padding-samples", type=int, default=0)
    parser.add_argument("--padding-channels", type=int, default=0)
    parser.add_argument("--max-rois", type=int, default=None)
    parser.add_argument("--output-events", type=Path, default=None, help="Optional event candidates .json or .csv")
    parser.add_argument("--output-rois", type=Path, default=None, help="Optional ROI .json or .csv")
    parser.add_argument("--output-summary", type=Path, default=None, help="Optional ROI statistics summary .json or .csv")
    return parser


def parse_manual_rois(values) -> ROISet:
    rois = ROISet()
    for index, item in enumerate(values or []):
        start_sample, end_sample, channel_start, channel_end = item
        rois.add(
            TimeChannelROI(
                roi_id=f"manual_{index + 1:03d}",
                start_sample=start_sample,
                end_sample=end_sample,
                channel_start=channel_start,
                channel_end=channel_end,
                label="manual_roi",
            )
        )
    return rois


def build_time_slice_from_args(args: argparse.Namespace) -> slice:
    stop = args.time_stop if args.time_stop is not None else args.max_samples
    return slice(args.time_start, stop)


def build_channel_slice_from_args(args: argparse.Namespace) -> slice:
    stop = args.channel_stop if args.channel_stop is not None else args.max_channels
    return slice(args.channel_start, stop)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rois = parse_manual_rois(args.roi)
        event_result = None
        if args.detect_events:
            event_result = detect_events_for_file(
                args.input,
                time_slice=build_time_slice_from_args(args),
                channel_slice=build_channel_slice_from_args(args),
                method=args.method,
                threshold=args.threshold,
                sta_samples=args.sta,
                lta_samples=args.lta,
                trigger_on=args.trigger_on,
                trigger_off=args.trigger_off,
                max_events=args.max_rois,
            )
            event_rois = rois_from_event_candidates(
                event_result.result.candidates,
                padding_samples=args.padding_samples,
                padding_channels=args.padding_channels,
                max_rois=args.max_rois,
            )
            for roi in event_rois:
                rois.add(roi)
            print(format_metadata(event_result.metadata))
            print(f"reader_name: {event_result.reader_name}")
            print(f"event_candidates: {len(event_result.result.candidates)}")

        if args.output_events is not None:
            if event_result is None:
                raise ValueError("--output-events requires --detect-events")
            _write_rows_or_json(args.output_events, event_candidates_to_rows(event_result.result.candidates))
            print(f"saved_event_candidates: {args.output_events}")

        if args.output_rois is not None:
            _write_rows_or_json(args.output_rois, rois_to_rows(rois))
            print(f"saved_rois: {args.output_rois}")

        if args.output_summary is not None:
            if len(rois) == 0:
                raise ValueError("--output-summary requires at least one ROI")
            summary = compute_roi_statistics_for_file(args.input, rois)
            _write_rows_or_json(args.output_summary, analysis_summary_to_rows(summary.results))
            print(f"saved_roi_summary: {args.output_summary}")

        if not any([args.output_events, args.output_rois, args.output_summary]):
            print(f"roi_count: {len(rois)}")
    except Exception as exc:  # noqa: BLE001 - CLI boundary should report user-facing failures.
        raise SystemExit(f"ROI export failed: {exc}") from exc
    return 0


def _write_rows_or_json(path: Path, rows) -> None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        save_json(rows, path)
        return
    if suffix == ".csv":
        save_csv_rows(rows, path)
        return
    raise ValueError("output path must use .json or .csv")


if __name__ == "__main__":
    raise SystemExit(main())
