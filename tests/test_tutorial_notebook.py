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
    assert "GUI Analysis panel" in text
    assert "Statistics" in text
    assert "Band energy" in text
    assert "Event candidate" in text
    assert "ROI statistics" in text
    assert "Installation" in text
    assert "hcz-das-validate" in text
    assert "hcz-das-view" in text
    assert "Windows packaging" in text
    assert "Release usage notes" in text
    assert "Extensions and plugins" in text
    assert "hcz-das-extensions" in text
    assert "das_view.plugins" in text
    assert "Public API" in text
    assert "Data shape convention" in text
    assert "CLI / GUI / plugin" in text
    assert "Interpretation boundaries" in text
    assert "Troubleshooting" in text
    assert "DAS QC metrics" in text
    assert "Bad channel detection" in text
    assert "noise floor" in text
    assert "Multiband feature map" in text
    assert "Local channel coherence" in text
    assert "Five-level DAS Analysis roadmap" in text
    assert "hcz-das-qc" in text
    assert "Level 4 traditional signal enhancement" in text
    assert "Common-mode removal" in text
    assert "Despike and median filtering" in text
    assert "Channel balancing" in text
    assert "local normalization" in text.lower()
    assert "robust clipping" in text.lower()
    assert "Denoise workflow reports" in text
    assert "hcz-das-denoise" in text
    assert "Level 5 wavefield assisted analysis" in text
    assert "FK directional energy" in text
    assert "Apparent slope attribute" in text
    assert "Apparent velocity attribute" in text
    assert "Local moveout coherence" in text
    assert "Moveout summary report" in text
    assert "hcz-das-moveout" in text


def test_tutorial_notebook_avoids_local_paths_and_development_content():
    text = NOTEBOOK.read_text(encoding="utf-8")

    assert "E:\\HczDocument" not in text
    assert "development log" not in text.lower()
    assert "commit" not in text.lower()
    assert "pytest" not in text.lower()
