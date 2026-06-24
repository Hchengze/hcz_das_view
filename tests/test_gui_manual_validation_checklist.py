import pytest

from examples import gui_manual_validation_checklist as checklist


def test_gui_manual_validation_checklist_import_and_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        checklist.main(["--help"])
    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_gui_manual_validation_checklist_markdown_output():
    text = checklist.format_checklist(markdown=True)

    assert "GUI manual validation checklist" in text
    assert "QC report" in text
    assert "Denoise report" in text
    assert "Moveout summary" in text
    assert "PyQtGraph experimental backend" in text
    assert "E:\\HczDocument" not in text


def test_gui_manual_validation_checklist_plain_output():
    text = checklist.format_checklist()

    assert "启动 GUI" in text
    assert "JSON export" in text
    assert "CSV export" in text
    assert "E:\\HczDocument" not in text
