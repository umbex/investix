from pathlib import Path

from app.importing import cli
from app.importing.stocks26 import ImportPreview


def test_cli_previews_without_finalizing(monkeypatch, capsys, tmp_path: Path) -> None:
    source = tmp_path / "movimenti.csv"
    source.write_text("placeholder")
    preview = ImportPreview("abc123", [], [])
    monkeypatch.setattr(cli, "preview_movimenti", lambda _: preview)

    assert cli.main([str(source)]) == 0

    output = capsys.readouterr().out
    assert "Righe valide: 0" in output
    assert "Preview completata" in output


def test_cli_refuses_finalize_when_preview_has_errors(monkeypatch, capsys, tmp_path: Path) -> None:
    source = tmp_path / "movimenti.csv"
    source.write_text("placeholder")
    preview = ImportPreview("abc123", [], ["Riga 5: tipo non mappato"])
    monkeypatch.setattr(cli, "preview_movimenti", lambda _: preview)

    assert cli.main(["--finalize", str(source)]) == 2
    assert "Riga 5" in capsys.readouterr().out


def test_cli_requires_a_reconciliation_report_to_finalize(monkeypatch, capsys, tmp_path: Path) -> None:
    source = tmp_path / "movimenti.csv"
    source.write_text("placeholder")
    monkeypatch.setattr(cli, "preview_movimenti", lambda _: ImportPreview("abc123", [], []))

    assert cli.main(["--finalize", str(source)]) == 3
    assert "report" in capsys.readouterr().out.lower()


def test_reconcile_cli_can_write_a_json_report(monkeypatch, capsys, tmp_path: Path) -> None:
    from app.importing import reconcile_cli
    from app.importing.ledger_reconciliation import LedgerReconciliation

    source = tmp_path / "movimenti.csv"
    report_path = tmp_path / "report.json"
    source.write_text("placeholder")
    monkeypatch.setattr(reconcile_cli, "preview_movimenti", lambda _: ImportPreview("abc", [], []))
    monkeypatch.setattr(reconcile_cli, "reconcile_preview_with_ledger", lambda *_: LedgerReconciliation({}, {}, "matched"))
    monkeypatch.setattr(reconcile_cli, "create_session_factory", lambda: lambda: _SessionContext(LedgerReconciliation({}, {}, "matched")))

    assert reconcile_cli.main([str(source), "--report", str(report_path)]) == 0
    assert '"quantity_status": "matched"' in report_path.read_text()


class _SessionContext:
    def __init__(self, report):
        self.report = report

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False
