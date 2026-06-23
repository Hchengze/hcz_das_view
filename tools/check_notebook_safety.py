"""Check the tutorial notebook for private paths and development-only content."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_NOTEBOOK = Path("docs/09_tutorial_user_manual.ipynb")
FORBIDDEN_SUBSTRINGS = (
    "E:\\HczDocument",
    "development log",
    "commit",
    "local_validation_paths",
    "validation_outputs",
    "test session starts",
    "collected ",
    " passed in ",
    " failed in ",
)


def notebook_text(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in payload.get("cells", []))


def find_forbidden_text(text: str) -> list[str]:
    lowered = text.lower()
    return [needle for needle in FORBIDDEN_SUBSTRINGS if needle.lower() in lowered]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check tutorial notebook content safety.")
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK)
    args = parser.parse_args(argv)
    text = notebook_text(args.notebook)
    violations = find_forbidden_text(text)
    if violations:
        print("Forbidden notebook content found:", file=sys.stderr)
        for needle in violations:
            print(f"  {needle}", file=sys.stderr)
        return 1
    print("Notebook safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
