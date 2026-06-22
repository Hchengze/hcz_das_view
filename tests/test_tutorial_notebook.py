import json
from pathlib import Path


NOTEBOOK = Path("docs/09_tutorial_user_manual.ipynb")


def test_tutorial_notebook_exists_and_is_valid_json():
    assert NOTEBOOK.exists()

    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    assert payload["nbformat"] == 4
    assert "cells" in payload
    assert payload["cells"]


def test_tutorial_notebook_contains_user_manual_keywords():
    text = NOTEBOOK.read_text(encoding="utf-8")

    assert "DAS Viewer / DAS Analysis" in text
    assert "RMS" in text
    assert "STA/LTA" in text
    assert "Spectral centroid" in text
    assert "FK apparent velocity" in text
    assert "ROI" in text
    assert "Annotation" in text
    assert "JSON / CSV" in text


def test_tutorial_notebook_avoids_local_paths_and_development_content():
    text = NOTEBOOK.read_text(encoding="utf-8")

    assert "E:\\HczDocument" not in text
    assert "development log" not in text.lower()
    assert "commit" not in text.lower()
    assert "pytest" not in text.lower()
