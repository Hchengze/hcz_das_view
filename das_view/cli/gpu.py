"""GPU diagnostics and synthetic benchmark CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from das_view.acceleration import (
    AccelerationRuntimeError,
    compare_cpu_gpu_benchmark,
    format_acceleration_report,
    run_array_backend_benchmark,
)
from das_view.acceleration.benchmark import GpuRuntimeError
from das_view.acceleration.validation import validate_cpu_gpu_numeric_consistency
from das_view.io.export import to_jsonable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect optional GPU backend and run synthetic benchmarks.")
    parser.add_argument("--info", action="store_true", help="Print GPU/CuPy availability information")
    parser.add_argument("--benchmark", action="store_true", help="Run a synthetic benchmark")
    parser.add_argument("--compare", action="store_true", help="Compare CPU and GPU synthetic benchmark timings")
    parser.add_argument("--validate-numeric", action="store_true", help="Validate CPU/GPU numeric consistency")
    parser.add_argument("--backend", choices=("cpu", "gpu", "auto"), default="cpu")
    parser.add_argument("--shape", type=int, nargs=2, default=(4096, 512), metavar=("SAMPLES", "CHANNELS"))
    parser.add_argument("--dtype", default="float32")
    parser.add_argument("--operations", nargs="+", default=("mean", "std", "rms", "energy", "fft_time"))
    parser.add_argument("--functions", nargs="+", default=("statistics", "band_energy", "multiband_energy_map", "fk_transform"))
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rtol", type=float, default=1e-5)
    parser.add_argument("--atol", type=float, default=1e-6)
    parser.add_argument("--json-output", type=Path, default=None, help="Optional local JSON output artifact")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.info or args.benchmark or args.compare or args.validate_numeric):
        args.info = True
    payload: dict[str, object] = {}
    try:
        if args.info:
            report = format_acceleration_report(args.backend)
            payload["info"] = report
            print(format_acceleration_report(args.backend, as_text=True))
        if args.benchmark:
            result = run_array_backend_benchmark(
                shape=tuple(args.shape),
                dtype=args.dtype,
                operations=tuple(args.operations),
                backend=args.backend,
                warmup=args.warmup,
                repeats=args.repeats,
                seed=args.seed,
            )
            payload["benchmark"] = [item.to_dict() for item in result]
            for item in result:
                print(
                    f"benchmark operation={item.operation} backend={item.backend} "
                    f"elapsed={item.elapsed_seconds:.6f}s shape={item.shape} dtype={item.dtype}"
                )
        if args.compare:
            result = compare_cpu_gpu_benchmark(
                shape=tuple(args.shape),
                dtype=args.dtype,
                operations=tuple(args.operations),
                warmup=args.warmup,
                repeats=args.repeats,
                seed=args.seed,
            )
            payload["compare"] = result
            print(f"compare status={result['status']} reason={result.get('reason')}")
            for operation, speedup in result.get("speedup", {}).items():
                print(f"speedup {operation}: {speedup:.3f}x")
        if args.validate_numeric:
            result = validate_cpu_gpu_numeric_consistency(
                shape=tuple(args.shape),
                dtype=args.dtype,
                functions=tuple(args.functions),
                rtol=args.rtol,
                atol=args.atol,
                seed=args.seed,
            )
            payload["numeric_validation"] = result
            print(f"numeric_validation status={result['status']} reason={result.get('reason')}")
            for item in result["checks"]:
                print(f"check {item['function']}: {item['status']} max_abs_diff={item['max_abs_diff']}")
    except (AccelerationRuntimeError, GpuRuntimeError, ImportError, ValueError) as exc:
        raise SystemExit(f"gpu error: {exc}") from exc
    if args.json_output is not None:
        args.json_output.write_text(json.dumps(to_jsonable(payload), indent=2), encoding="utf-8")
        print(f"saved_output: {args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
