"""Check that tracked repository files do not include release/data artifacts."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = (
    "*.h5",
    "*.hdf5",
    "*.dat",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.csv",
    "*.exe",
    "*.whl",
    "*.tar.gz",
    "build/*",
    "dist/*",
    "validation_outputs/*",
    "outputs/*",
    "benchmarks/*",
    "benchmark_outputs/*",
    "gpu_benchmarks/*",
    "gpu_benchmark_outputs/*",
    "*benchmark*.json",
    "*benchmark*.csv",
    "local_validation_paths.txt",
    ".tmp_release_venv/*",
    ".tmp_pytest/*",
)

FORBIDDEN_JSON_PATTERNS = ("*.json",)
JSON_ALLOWLIST = frozenset()


def tracked_files(root: Path) -> list[str]:
    """Return tracked files relative to root, preferring git when available."""

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts
        ]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def find_forbidden(paths: list[str]) -> list[str]:
    """Return tracked paths that match forbidden artifact patterns."""

    violations: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in JSON_ALLOWLIST:
            continue
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in FORBIDDEN_JSON_PATTERNS):
            violations.append(path)
            continue
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in FORBIDDEN_PATTERNS):
            violations.append(path)
    return sorted(set(violations))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check tracked files for forbidden data/build artifacts.")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    violations = find_forbidden(tracked_files(root))
    if violations:
        print("Forbidden tracked artifacts found:", file=sys.stderr)
        for path in violations:
            print(f"  {path}", file=sys.stderr)
        return 1
    print("Artifact safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
