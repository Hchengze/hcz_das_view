import json
from pathlib import Path

from tools import check_artifacts, check_cli_help, check_notebook_safety


def test_artifact_checker_imports_and_current_repo_passes():
    assert callable(check_artifacts.main)
    assert check_artifacts.find_forbidden(check_artifacts.tracked_files(Path("."))) == []


def test_artifact_checker_finds_forbidden_files():
    violations = check_artifacts.find_forbidden(
        [
            "src/module.py",
            "sample.h5",
            "dist/package.whl",
            "validation_outputs/preview.png",
            "report.json",
        ]
    )

    assert "sample.h5" in violations
    assert "dist/package.whl" in violations
    assert "validation_outputs/preview.png" in violations
    assert "report.json" in violations


def test_notebook_safety_checker_imports_and_current_notebook_passes():
    text = check_notebook_safety.notebook_text(Path("docs/09_tutorial_user_manual.ipynb"))

    assert check_notebook_safety.find_forbidden_text(text) == []


def test_notebook_safety_checker_finds_private_path_and_process_terms(tmp_path):
    notebook = tmp_path / "unsafe.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": ["E:\\HczDocument private path and test session starts output"],
                    }
                ],
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    text = check_notebook_safety.notebook_text(notebook)
    violations = check_notebook_safety.find_forbidden_text(text)

    assert "E:\\HczDocument" in violations
    assert "test session starts" in violations


def test_cli_help_checker_runs_all_module_help_smokes():
    assert check_cli_help.main([]) == 0
