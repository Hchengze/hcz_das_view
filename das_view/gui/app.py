"""Application entry point for the optional PyQt5 GUI."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    """Start the DAS View GUI."""

    args = sys.argv if argv is None else argv
    if any(arg in {"-h", "--help"} for arg in args):
        print("usage: hcz-das-view [--help]\n\nStart the optional HCZ DAS View GUI.")
        return 0
    from PyQt5 import QtWidgets
    from das_view.gui.main_window import MainWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    window = MainWindow()
    window.show()
    return int(app.exec_())


def main(argv: list[str] | None = None) -> int:
    """Console-script compatible GUI entry point."""

    return run(sys.argv if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
