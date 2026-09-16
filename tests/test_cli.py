# Created: 2026-09-16
# Last Edited: 2026-09-16 14:11 CT (America/Chicago)
# Path: tests/test_cli.py
# Purpose: Tests for the headless command-line interface (aethervault.cli).

"""Tests for the headless command-line interface."""

import json
import subprocess
import sys

import pytest

from aethervault.cli import MASTER_PASSWORD_ENV, main
from aethervault.core import engine
from aethervault.shared import database

MASTER_PW = "cli-master-password-123"


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(MASTER_PASSWORD_ENV, MASTER_PW)
    assert main(["--vault-dir", str(tmp_path), "init"]) == 0
    return tmp_path


def run(vault_dir, *argv):
    return main(["--vault-dir", str(vault_dir), *argv])


class TestInitAndVersion:
    def test_version(self, capsys):
        assert main(["--version"]) == 0
        assert "CLI" in capsys.readouterr().out

    def test_no_command_prints_help(self, capsys):
        assert main([]) == 2
        assert "COMMAND" in capsys.readouterr().out

    def test_init_creates_vault_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv(MASTER_PASSWORD_ENV, MASTER_PW)
        assert main(["--vault-dir", str(tmp_path), "init"]) == 0
        assert (tmp_path / "aethervault.db").exists()
        assert (tmp_path / ".master.key").exists()

    def test_init_twice_fails(self, vault_dir, capsys):
        assert run(vault_dir, "init") == 1
        assert "already exists" in capsys.readouterr().err


class TestReadCommands:
    def test_list_empty_json(self, vault_dir, capsys):
        assert run(vault_dir, "list", "--json") == 0
        assert json.loads(capsys.readouterr().out) == []

    def test_add_then_list_json(self, vault_dir, capsys):
        assert run(vault_dir, "add", "--title", "GitHub", "--username", "octocat",
                   "--password", "s3cret", "--json") == 0
        capsys.readouterr()
        assert run(vault_dir, "list", "--json") == 0
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 1
        assert data[0]["title"] == "GitHub"
        assert data[0]["password"] == "*" * 8

    def test_list_show_password(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "s3cret")
        capsys.readouterr()
        assert run(vault_dir, "list", "--json", "--show-password") == 0
        assert json.loads(capsys.readouterr().out)[0]["password"] == "s3cret"

    def test_search(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "a")
        run(vault_dir, "add", "--title", "Bank", "--password", "b")
        capsys.readouterr()
        assert run(vault_dir, "search", "git", "--json") == 0
        assert [e["title"] for e in json.loads(capsys.readouterr().out)] == ["GitHub"]

    def test_filter_by_category_and_tag(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "A", "--password", "a",
            "--category", "Work", "--tags", "dev")
        run(vault_dir, "add", "--title", "B", "--password", "b", "--category", "Home")
        capsys.readouterr()
        assert run(vault_dir, "list", "--json", "--category", "work") == 0
        assert [e["title"] for e in json.loads(capsys.readouterr().out)] == ["A"]
        assert run(vault_dir, "list", "--json", "--tag", "dev") == 0
        assert [e["title"] for e in json.loads(capsys.readouterr().out)] == ["A"]

    def test_show_field_password(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "s3cret", "--json")
        entry_id = json.loads(capsys.readouterr().out)["db_id"]
        assert run(vault_dir, "show", str(entry_id), "--field", "password") == 0
        assert capsys.readouterr().out.strip() == "s3cret"

    def test_show_unknown_field(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "x")
        capsys.readouterr()
        assert run(vault_dir, "show", "1", "--field", "bogus") == 1
        assert "Unknown field" in capsys.readouterr().err

    def test_show_missing_entry(self, vault_dir, capsys):
        assert run(vault_dir, "show", "999", "--json") == 1
        assert "error" in capsys.readouterr().err


class TestWriteCommands:
    def test_generate_password(self, vault_dir, capsys):
        assert run(vault_dir, "add", "--title", "Gen", "--generate", "24", "--json") == 0
        entry_id = json.loads(capsys.readouterr().out)["db_id"]
        assert run(vault_dir, "show", str(entry_id), "--field", "password") == 0
        assert len(capsys.readouterr().out.strip()) == 24

    def test_add_requires_title(self, vault_dir, capsys):
        assert run(vault_dir, "add", "--password", "x") == 1
        assert "title" in capsys.readouterr().err

    def test_update(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "Old", "--password", "x", "--json")
        entry_id = json.loads(capsys.readouterr().out)["db_id"]
        assert run(vault_dir, "update", str(entry_id), "--title", "New", "--json") == 0
        capsys.readouterr()
        assert run(vault_dir, "show", str(entry_id), "--field", "title") == 0
        assert capsys.readouterr().out.strip() == "New"

    def test_update_requires_a_field(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "X", "--password", "x")
        capsys.readouterr()
        assert run(vault_dir, "update", "1") == 1
        assert "No fields" in capsys.readouterr().err

    def test_delete_without_yes_noninteractive(self, vault_dir, capsys, monkeypatch):
        run(vault_dir, "add", "--title", "X", "--password", "x")
        capsys.readouterr()

        class _FakeStdin:
            def isatty(self):
                return False

        monkeypatch.setattr(sys, "stdin", _FakeStdin())
        assert run(vault_dir, "delete", "1") == 1
        assert "Refusing" in capsys.readouterr().err

    def test_delete_with_yes(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "X", "--password", "x")
        capsys.readouterr()
        assert run(vault_dir, "delete", "1", "--yes") == 0
        capsys.readouterr()
        assert run(vault_dir, "list", "--json") == 0
        assert json.loads(capsys.readouterr().out) == []


class TestTotp:
    SECRET = "JBSWY3DPEHPK3PXP"

    def test_add_totp_and_generate_code(self, vault_dir, capsys):
        assert run(vault_dir, "add", "--title", "GitHub", "--password", "p",
                   "--totp-secret", self.SECRET, "--json") == 0
        entry_id = json.loads(capsys.readouterr().out)["db_id"]
        assert run(vault_dir, "totp", str(entry_id)) == 0
        code = capsys.readouterr().out.strip().split()[0]
        assert code.isdigit() and len(code) == 6

    def test_totp_json(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "p",
            "--totp-secret", self.SECRET, "--json")
        entry_id = json.loads(capsys.readouterr().out)["db_id"]
        assert run(vault_dir, "totp", str(entry_id), "--json") == 0
        data = json.loads(capsys.readouterr().out)
        assert data["code"].isdigit() and len(data["code"]) == 6
        assert 0 < data["remaining"] <= 30

    def test_totp_missing_secret_errors(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "p")
        capsys.readouterr()
        assert run(vault_dir, "totp", "1") == 1
        assert "no TOTP" in capsys.readouterr().err

    def test_list_masks_totp_secret(self, vault_dir, capsys):
        run(vault_dir, "add", "--title", "GitHub", "--password", "p",
            "--totp-secret", self.SECRET)
        capsys.readouterr()
        assert run(vault_dir, "list", "--json") == 0
        assert json.loads(capsys.readouterr().out)[0]["totp_secret"] == "*" * 8


class TestMaintenance:
    def test_export_import_round_trip(self, vault_dir, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(engine, "DB_PATH", str(vault_dir / "aethervault.db"))
        monkeypatch.setattr(engine, "DATA_DIR", str(vault_dir))
        monkeypatch.setattr(database, "load_settings", lambda: {"remote_backup_dir": ""})
        run(vault_dir, "add", "--title", "GitHub", "--password", "s3cret")
        capsys.readouterr()
        csv_path = str(tmp_path / "out.csv")
        assert run(vault_dir, "export", csv_path) == 0

        other = tmp_path / "other"
        other.mkdir()
        assert main(["--vault-dir", str(other), "init"]) == 0
        assert main(["--vault-dir", str(other), "import", csv_path]) == 0
        capsys.readouterr()
        assert main(["--vault-dir", str(other), "list", "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 1
        assert data[0]["title"] == "GitHub"

    def test_backup(self, vault_dir, capsys, monkeypatch):
        monkeypatch.setattr(engine, "DB_PATH", str(vault_dir / "aethervault.db"))
        monkeypatch.setattr(engine, "DATA_DIR", str(vault_dir))
        monkeypatch.setattr(database, "load_settings", lambda: {"remote_backup_dir": ""})
        run(vault_dir, "add", "--title", "GitHub", "--password", "x")
        capsys.readouterr()
        assert run(vault_dir, "backup") == 0
        assert "Backup written" in capsys.readouterr().out


class TestHeadless:
    def test_cli_does_not_import_pyside6(self):
        code = "import sys, aethervault.cli; assert 'PySide6' not in sys.modules; print('ok')"
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "ok"
