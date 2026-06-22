"""Inspect HCZ DAS View extension metadata."""

from __future__ import annotations

import argparse
import json

from das_view.plugins.base import VALID_EXTENSION_KINDS
from das_view.plugins.builtins import register_builtin_extensions
from das_view.plugins.registry import ExtensionRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect DAS View extension metadata.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List extensions. This is the default action.",
    )
    parser.add_argument(
        "--kind",
        choices=VALID_EXTENSION_KINDS,
        default=None,
        help="Filter by extension kind.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write JSON instead of a text table.",
    )
    parser.add_argument(
        "--disabled",
        action="store_true",
        help="Include disabled extensions.",
    )
    return parser


def _metadata_rows(registry: ExtensionRegistry, *, kind: str | None, include_disabled: bool):
    enabled = None if include_disabled else True
    return [extension.metadata.to_dict() for extension in registry.list(kind=kind, enabled=enabled)]


def _format_text(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "No extensions registered."
    header = f"{'name':24} {'kind':12} {'version':12} description"
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{str(row['name']):24} {str(row['kind']):12} "
            f"{str(row.get('version') or ''):12} {row.get('description') or ''}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = ExtensionRegistry()
    register_builtin_extensions(registry=registry)
    rows = _metadata_rows(registry, kind=args.kind, include_disabled=args.disabled)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(_format_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
