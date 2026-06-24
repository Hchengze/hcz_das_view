import sys

import numpy as np
import pytest


def test_pyqtgraph_canvas_module_import_is_lazy():
    sys.modules.pop("pyqtgraph", None)

    import das_view.gui.pyqtgraph_canvas as canvas

    assert canvas.PyQtGraphWaterfallView
    assert "pyqtgraph" not in sys.modules


def test_prepare_waterfall_image_downsamples_without_pyqtgraph():
    from das_view.gui.pyqtgraph_canvas import (
        prepare_waterfall_image,
        prepare_waterfall_image_for_pyqtgraph,
    )

    data = np.arange(100 * 50, dtype=float).reshape(100, 50)
    image = prepare_waterfall_image(data, max_samples=20, max_channels=10)
    prepared = prepare_waterfall_image_for_pyqtgraph(data, max_samples=20, max_channels=10)

    assert image.shape[0] <= 20
    assert image.shape[1] <= 10
    assert prepared.data.shape == image.shape
    assert prepared.image.shape == (image.shape[1], image.shape[0])
    assert prepared.rect[2] > 0
    assert prepared.rect[3] > 0


def test_prepare_waterfall_image_rejects_invalid_rank():
    from das_view.gui.pyqtgraph_canvas import prepare_waterfall_image

    with pytest.raises(ValueError, match="2-D"):
        prepare_waterfall_image(np.arange(10))


def test_pyqtgraph_widget_creation_and_set_image_smoke():
    pytest.importorskip("pyqtgraph")
    pytest.importorskip("PyQt5")

    from PyQt5 import QtWidgets
    from das_view.gui.pyqtgraph_canvas import create_pyqtgraph_waterfall_widget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    view = create_pyqtgraph_waterfall_widget()
    shown = view.set_waterfall_image(np.arange(64 * 16, dtype=float).reshape(64, 16))

    assert shown.data.shape == (64, 16)
    assert shown.image.shape == (16, 64)
    assert view.last_shape == (64, 16)
    view.widget.close()
    app.processEvents()
