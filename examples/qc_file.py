"""Run DAS QC, multiband, or coherence analysis on a supported file."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from das_view.cli.qc import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
