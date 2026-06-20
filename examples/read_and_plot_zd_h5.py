"""Read a ZD HDF5 DAS file and save a waterfall preview image.

Usage:

    python examples/read_and_plot_zd_h5.py input.h5 --output preview.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from das_view.io.hdf5_zd import ZDHDF5Reader
from das_view.plotting.waterfall import plot_waterfall


def main() -> int:
    parser = argparse.ArgumentParser(description="Read a ZD HDF5 file and save a waterfall preview.")
    parser.add_argument("input", type=Path, help="Path to a ZD HDF5 file")
    parser.add_argument("--output", type=Path, default=Path("zd_h5_preview.png"), help="Output image path")
    parser.add_argument("--time-start", type=int, default=None, help="Start sample index")
    parser.add_argument("--time-stop", type=int, default=None, help="Stop sample index")
    parser.add_argument("--channel-start", type=int, default=None, help="Start channel index")
    parser.add_argument("--channel-stop", type=int, default=None, help="Stop channel index")
    parser.add_argument("--time-step", type=int, default=1, help="Time downsampling step")
    parser.add_argument("--channel-step", type=int, default=1, help="Channel downsampling step")
    args = parser.parse_args()

    reader = ZDHDF5Reader()
    metadata = reader.read_metadata(args.input)
    print("ZD HDF5 metadata")
    print(f"  source_path: {metadata.source_path}")
    print(f"  n_samples: {metadata.n_samples}")
    print(f"  n_channels: {metadata.n_channels}")
    print(f"  sample_rate_hz: {metadata.sample_rate_hz}")
    print(f"  dt_s: {metadata.dt_s}")
    print(f"  dx_m: {metadata.dx_m}")
    print(f"  raw_shape: {metadata.extra_attrs.get('raw_shape')}")
    print(f"  raw_orientation: {metadata.extra_attrs.get('raw_orientation')}")

    das_data = reader.read(
        args.input,
        time_slice=slice(args.time_start, args.time_stop),
        channel_slice=slice(args.channel_start, args.channel_stop),
        downsample=(args.time_step, args.channel_step),
    )
    fig, _ = plot_waterfall(das_data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150, bbox_inches="tight")
    print(f"Saved preview image: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
