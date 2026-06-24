"""Manual GUI entry point for local testing.

This script is intentionally kept at the repository root so users can start
the HCZ DAS View GUI with:

    python das_view_main.py

The package entry point remains ``das_view.gui.app:main``.
"""

from __future__ import annotations

from das_view.gui.app import main


if __name__ == "__main__":
    raise SystemExit(main())
