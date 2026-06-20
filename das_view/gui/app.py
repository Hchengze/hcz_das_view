"""Application entry point for the optional PyQt5 GUI."""

from __future__ import annotations

import sys

from das_view.gui.main_window import MainWindow


def run(argv: list[str] | None = None) -> int:
    """Start the DAS View GUI."""

    from PyQt5 import QtWidgets

    args = sys.argv if argv is None else argv
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(args)
    window = MainWindow()
    window.show()
    return int(app.exec_())
