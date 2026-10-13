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
