"""Run CLI help smoke checks without requiring installed console scripts."""

from __future__ import annotations

import argparse
import importlib
import io
from contextlib import redirect_stdout


CLI_MODULES = (
    ("hcz-das-validate", "das_view.cli.validate", ["--help"]),
    ("hcz-das-preview", "das_view.cli.preview", ["--help"]),
    ("hcz-das-stats", "das_view.cli.statistics", ["--help"]),
    ("hcz-das-spectrum", "das_view.cli.spectrum", ["--help"]),
    ("hcz-das-events", "das_view.cli.events", ["--help"]),
    ("hcz-das-qc", "das_view.cli.qc", ["--help"]),
    ("hcz-das-denoise", "das_view.cli.denoise", ["--help"]),
    ("hcz-das-moveout", "das_view.cli.moveout", ["--help"]),
    ("hcz-das-gpu", "das_view.cli.gpu", ["--help"]),
    ("hcz-das-extensions", "das_view.cli.extensions", ["--help"]),
    ("hcz-das-view", "das_view.gui.app", ["hcz-das-view", "--help"]),
)


def run_help(name: str, module_name: str, argv: list[str]) -> str:
    module = importlib.import_module(module_name)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        try:
            code = module.main(argv)
        except SystemExit as exc:
            code = exc.code
    if code not in (0, None):
        raise RuntimeError(f"{name} help exited with {code}")
    output = buffer.getvalue()
    if "usage:" not in output:
        raise RuntimeError(f"{name} help did not print usage text")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CLI module help smoke checks.")
    parser.parse_args(argv)
    for name, module_name, help_argv in CLI_MODULES:
        run_help(name, module_name, list(help_argv))
        print(f"{name}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
