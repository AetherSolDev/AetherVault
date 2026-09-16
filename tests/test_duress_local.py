# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tests/test_duress_local.py
# Purpose: Tests for local-only duress wipe on custom vault paths (SDK/CLI).

"""Duress on a synced client: wipe local files only, never push, leave the dir otherwise."""

import pytest

from aethervault.core.engine import hash_password
from aethervault.sdk import AuthenticationError, Vault

MASTER_PW = "correct-horse-battery"
DURESS_PW = "duress-trigger-123"


def _make_vault(tmp_path):
    db_path = tmp_path / "aethervault.db"
    key_file = tmp_path / ".master.key"
    vault = Vault.create(MASTER_PW, str(db_path), str(key_file))
    vault.add(title="GitHub", password="p")
    vault.lock()
    (tmp_path / ".duress.key").write_text(hash_password(DURESS_PW), encoding="utf-8")
    return db_path, key_file


class TestSdkDuressWipe:
    def test_duress_wipes_local_only(self, tmp_path):
        db_path, key_file = _make_vault(tmp_path)
        (tmp_path / "keep.txt").write_text("unrelated", encoding="utf-8")

        with pytest.raises(AuthenticationError):
            Vault(str(db_path), str(key_file)).unlock(
                DURESS_PW, allow_duress_wipe=True
            )

        assert not db_path.exists()
        assert not key_file.exists()
        assert not (tmp_path / ".duress.key").exists()
        assert (tmp_path / "keep.txt").exists()  # targeted wipe spares other files

    def test_no_wipe_when_not_allowed(self, tmp_path):
        db_path, key_file = _make_vault(tmp_path)
        with pytest.raises(AuthenticationError):
            Vault(str(db_path), str(key_file)).unlock(DURESS_PW)  # allow_duress_wipe=False
        assert db_path.exists()
        assert key_file.exists()


class TestCliDuressWipe:
    def test_cli_duress_wipe_looks_like_a_bad_password(self, tmp_path, monkeypatch, capsys):
        from aethervault.cli import MASTER_PASSWORD_ENV, main

        _make_vault(tmp_path)
        monkeypatch.setenv(MASTER_PASSWORD_ENV, DURESS_PW)

        rc = main(["--vault-dir", str(tmp_path), "list"])
        assert rc == 1
        assert "Invalid master password" in capsys.readouterr().err
        assert not (tmp_path / "aethervault.db").exists()

    def test_cli_no_duress_keeps_vault(self, tmp_path, monkeypatch, capsys):
        from aethervault.cli import MASTER_PASSWORD_ENV, main

        _make_vault(tmp_path)
        monkeypatch.setenv(MASTER_PASSWORD_ENV, DURESS_PW)

        rc = main(["--vault-dir", str(tmp_path), "--no-duress", "list"])
        assert rc == 1
        assert (tmp_path / "aethervault.db").exists()
