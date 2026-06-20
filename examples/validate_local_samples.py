"""Batch-validate local DAS samples listed in local_validation_paths.txt.

The path list is intentionally ignored by git. Blank lines and lines starting
with # are skipped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from examples.validate_file import validate_file
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback.
    from validate_file import validate_file

DEFAULT_PATH_LIST = Path("local_validation_paths.txt")


def parse_path_list(lines: Iterable[str]) -> list[Path]:
    """Parse local validation paths, ignoring comments and blank lines."""

    paths: list[Path] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(Path(line))
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local DAS sample paths.")
    parser.add_argument(
        "--path-list",
        type=Path,
        default=DEFAULT_PATH_LIST,
        help="Text file with one local sample path per line",
    )
    parser.add_argument("--max-samples", type=int, default=2000)
    parser.add_argument("--max-channels", type=int, default=500)
    parser.add_argument(
        "--waveform-channel",
        type=int,
        default=None,
        help="Optional channel index for waveform validation",
    )
    parser.add_argument(
        "--save-preview-dir",
        type=Path,
        default=None,
        help="Optional ignored output directory for preview PNGs",
    )
    return parser


def validate_local_samples(
    *,
    path_list: Path = DEFAULT_PATH_LIST,
    max_samples: int = 2000,
    max_channels: int = 500,
    waveform_channel: int | None = None,
    save_preview_dir: Path | None = None,
) -> int:
    if not path_list.exists():
        print(
            f"{path_list} not found. Create it locally with one DAS file path per line "
            "to run real/quasi-real sample validation."
        )
        return 0

    paths = parse_path_list(path_list.read_text(encoding="utf-8").splitlines())
    if not paths:
        print(f"{path_list} contains no sample paths.")
        return 0

    failures = 0
    for index, path in enumerate(paths, start=1):
        print(f"=== sample {index} ===")
        try:
            preview_output = None
            if save_preview_dir is not None:
                preview_output = save_preview_dir / f"sample_{index:03d}_preview.png"
            waveform_output = None
            if waveform_channel is not None and save_preview_dir is not None:
                waveform_output = save_preview_dir / f"sample_{index:03d}_waveform.png"
            summary = validate_file(
                path,
                output=preview_output,
                waveform_output=waveform_output,
                validate_waveform=waveform_channel is not None,
                channel=0 if waveform_channel is None else waveform_channel,
                max_samples=max_samples,
                max_channels=max_channels,
            )
            print(
                "summary: "
                f"reader={summary['reader_name']}, "
                f"format={summary['source_format']}, "
                f"samples={summary['n_samples']}, "
                f"channels={summary['n_channels']}, "
                f"sample_rate_hz={summary['sample_rate_hz']}, "
                f"dx_m={summary['dx_m']}, "
                f"preview_shape={summary['preview_shape']}"
            )
        except Exception as exc:  # noqa: BLE001 - batch tool should continue after one failure.
            failures += 1
            print(f"error: {exc}")
    print(f"validated: {len(paths) - failures}/{len(paths)} passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return validate_local_samples(
        path_list=args.path_list,
        max_samples=args.max_samples,
        max_channels=args.max_channels,
        waveform_channel=args.waveform_channel,
        save_preview_dir=args.save_preview_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
