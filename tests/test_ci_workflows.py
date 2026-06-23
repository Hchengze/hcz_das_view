from pathlib import Path


CI = Path(".github/workflows/ci.yml")
RELEASE = Path(".github/workflows/release-smoke.yml")


def test_ci_workflow_exists_and_has_expected_jobs():
    text = CI.read_text(encoding="utf-8")

    assert "test-ubuntu:" in text
    assert "test-windows:" in text
    assert "packaging-smoke:" in text
    assert "artifact-safety:" in text
    assert "ubuntu-latest" in text
    assert "windows-latest" in text
    assert 'python-version: "3.11"' in text


def test_ci_workflow_runs_tests_and_cli_help_smoke():
    text = CI.read_text(encoding="utf-8")

    assert "python -B -m pytest -p no:cacheprovider" in text
    assert "python tools/check_cli_help.py" in text
    assert "python tools/check_notebook_safety.py" in text
    assert "python tools/check_artifacts.py" in text
    assert "python -m das_view.cli.gpu --info" in text
    assert "python -m build" in text
    assert "dist/*.whl" in text


def test_ci_windows_uses_repository_local_pytest_temp():
    text = CI.read_text(encoding="utf-8")

    assert ".tmp_pytest" in text
    assert "--basetemp .tmp_pytest\\ci_basetemp" in text


def test_ci_does_not_publish_or_use_pypi_secrets():
    combined = CI.read_text(encoding="utf-8") + "\n" + RELEASE.read_text(encoding="utf-8")
    lowered = combined.lower()

    assert "pypi" not in lowered
    assert "twine" not in lowered
    assert "gh-release" not in lowered
    assert "secrets." not in combined


def test_release_smoke_has_manual_and_tag_triggers():
    text = RELEASE.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "tags:" in text
    assert '"v*"' in text
    assert "python -B -m pytest -p no:cacheprovider" in text
    assert "python tools/check_cli_help.py" in text
    assert "python tools/check_notebook_safety.py" in text
    assert "python tools/check_artifacts.py" in text
    assert "python -m das_view.cli.gpu --info" in text
    assert "python -m build" in text
