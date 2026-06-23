import json
from pathlib import Path


README = Path("README.md")
HANDOFF = Path("docs/08_project_handoff.md")
NOTEBOOK = Path("docs/09_tutorial_user_manual.ipynb")


def _notebook_text() -> str:
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in payload["cells"])


def test_readme_contains_release_candidate_checklist_and_validation_package():
    text = README.read_text(encoding="utf-8")

    assert "Release candidate readiness checklist" in text
    assert "git status clean" in text
    assert "full pytest" in text
    assert "real-world validation package" in text
    assert "python examples/real_world_validation_package.py" in text


def test_handoff_contains_release_notes_and_known_limitations():
    text = HANDOFF.read_text(encoding="utf-8")

    assert "Release notes draft" in text
    assert "Known limitations" in text
    assert "Core file readers" in text
    assert "GPU optional compute backend" in text
    assert "Windows exe unsigned" in text


def test_tutorial_contains_cli_inventory_limitations_and_acceptance_workflow():
    text = _notebook_text()

    assert "CLI inventory" in text
    assert "hcz-das-gpu" in text
    assert "Examples inventory" in text
    assert "real-world validation package" in text
    assert "Known limitations" in text
    assert "User acceptance workflow" in text


def test_docs_avoid_private_paths_and_forbidden_interpretation_claims():
    text = README.read_text(encoding="utf-8") + "\n" + HANDOFF.read_text(encoding="utf-8") + "\n" + _notebook_text()
    lowered = text.lower()

    assert "E:\\HczDocument" not in text
    assert "true subsurface velocity" not in lowered
    assert "real strata velocity" not in lowered
    assert "event candidates are localization" not in lowered
    assert "event candidate localization" not in lowered
