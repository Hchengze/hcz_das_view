import json
import sys

import pytest

from das_view.cli import extensions


def test_extensions_cli_module_import_and_help(capsys):
    assert callable(extensions.main)
    assert callable(extensions.build_parser)

    with pytest.raises(SystemExit) as excinfo:
        extensions.main(["--help"])

    assert excinfo.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_extensions_cli_list_outputs_builtin_table(capsys):
    assert extensions.main(["--list"]) == 0

    output = capsys.readouterr().out
    assert "zd_hdf5" in output
    assert "statistics" in output
    assert "json" in output


def test_extensions_cli_filters_by_kind(capsys):
    assert extensions.main(["--kind", "reader"]) == 0

    output = capsys.readouterr().out
    assert "zd_hdf5" in output
    assert "puniu_dat" in output
    assert "statistics" not in output


def test_extensions_cli_json_output_is_valid(capsys):
    assert extensions.main(["--kind", "export", "--json"]) == 0

    rows = json.loads(capsys.readouterr().out)
    assert {row["name"] for row in rows} == {"csv", "json"}
    assert all(row["kind"] == "export" for row in rows)


def test_extensions_cli_does_not_start_gui_or_read_data(capsys):
    sys.modules.pop("PyQt5", None)

    assert extensions.main(["--kind", "analysis"]) == 0

    assert "PyQt5" not in sys.modules
    assert "event_candidates" in capsys.readouterr().out
