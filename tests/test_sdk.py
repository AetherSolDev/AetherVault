# Created: 2026-09-16
# Last Edited: 2026-09-16 14:13 CT (America/Chicago)
# Path: tests/test_sdk.py
# Purpose: Tests for the GUI-free Vault client SDK (aethervault.sdk).

"""Tests for the GUI-free Vault client SDK."""

import os
import sqlite3

import pytest

from aethervault.core import engine
from aethervault.shared import database
from aethervault.sdk import (
    AuthenticationError,
    EntryNotFoundError,
    Vault,
    VaultError,
    VaultLockedError,
    VaultNotFoundError,
)

MASTER_PW = "correct-horse-battery-staple"


@pytest.fixture
def vault_paths(tmp_path):
    return str(tmp_path / "aethervault.db"), str(tmp_path / ".master.key")


@pytest.fixture
def vault(vault_paths):
    db_path, key_file = vault_paths
    v = Vault.create(MASTER_PW, db_path, key_file)
    yield v
    v.lock()


@pytest.fixture
def isolated_backups(tmp_path, vault_paths, monkeypatch):
    """Keep backup rotation out of the real data dir and disable remote mirroring."""
    monkeypatch.setattr(engine, "DB_PATH", vault_paths[0])
    monkeypatch.setattr(engine, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(database, "load_settings", lambda: {"remote_backup_dir": ""})
    return tmp_path


class TestLifecycle:
    def test_create_unlocks_vault(self, vault):
        assert not vault.is_locked
        assert vault.list_entries() == []

    def test_create_rejects_short_password(self, vault_paths):
        db_path, key_file = vault_paths
        with pytest.raises(VaultError, match="at least 8"):
            Vault.create("short", db_path, key_file)

    def test_create_rejects_existing_key(self, vault, vault_paths):
        with pytest.raises(VaultError, match="already exists"):
            Vault.create(MASTER_PW, vault_paths[0], vault_paths[1])

    def test_unlock_wrong_password(self, vault, vault_paths):
        db_path, key_file = vault_paths
        vault.lock()
        with pytest.raises(AuthenticationError):
            Vault(db_path, key_file).unlock("wrong-password")

    def test_unlock_missing_key_file(self, vault_paths):
        db_path, key_file = vault_paths
        with pytest.raises(VaultNotFoundError):
            Vault(db_path, key_file).unlock(MASTER_PW)

    def test_operations_require_unlock(self, vault, vault_paths):
        db_path, key_file = vault_paths
        vault.lock()
        locked = Vault(db_path, key_file)
        with pytest.raises(VaultLockedError):
            locked.list_entries()
        with pytest.raises(VaultLockedError):
            locked.add(title="Nope", password="x")

    def test_context_manager_locks_on_exit(self, vault_paths):
        db_path, key_file = vault_paths
        Vault.create(MASTER_PW, db_path, key_file).lock()
        with Vault(db_path, key_file).unlock(MASTER_PW) as vault:
            assert not vault.is_locked
        assert vault.is_locked

    def test_lock_then_unlock_again(self, vault, vault_paths):
        db_path, key_file = vault_paths
        vault.lock()
        assert vault.is_locked
        vault.unlock(MASTER_PW)
        assert not vault.is_locked


class TestCrud:
    def test_add_list_get(self, vault):
        new_id = vault.add(title="GitHub", username="octocat", password="s3cret")
        entries = vault.list_entries()
        assert len(entries) == 1
        assert entries[0].db_id == new_id
        assert vault.get(new_id).password == "s3cret"

    def test_add_requires_title(self, vault):
        with pytest.raises(VaultError, match="title"):
            vault.add(password="s3cret")

    def test_add_rejects_unknown_field(self, vault):
        with pytest.raises(VaultError, match="Unknown credential field"):
            vault.add(title="X", password="y", not_a_field="z")

    def test_password_is_encrypted_at_rest(self, vault, vault_paths):
        vault.add(title="GitHub", password="plaintext-secret")
        conn = sqlite3.connect(vault_paths[0])
        try:
            stored = conn.execute("SELECT password FROM credentials").fetchone()[0]
        finally:
            conn.close()
        assert stored != "plaintext-secret"
        assert "plaintext-secret" not in stored

    def test_update_field_persists(self, vault):
        new_id = vault.add(title="GitHub", password="old")
        vault.update(new_id, password="new", category="Dev")
        reloaded = vault.get(new_id)
        assert reloaded.password == "new"
        assert reloaded.category == "Dev"

    def test_update_unknown_field(self, vault):
        new_id = vault.add(title="GitHub", password="old")
        with pytest.raises(VaultError, match="Unknown credential field"):
            vault.update(new_id, bogus="x")

    def test_update_missing_entry(self, vault):
        with pytest.raises(EntryNotFoundError):
            vault.update(999, password="x")

    def test_delete_entry(self, vault):
        new_id = vault.add(title="GitHub", password="x")
        vault.delete(new_id)
        assert vault.list_entries() == []

    def test_delete_missing_entry(self, vault):
        with pytest.raises(EntryNotFoundError):
            vault.delete(999)

    def test_search_matches_multiple_fields(self, vault):
        vault.add(title="GitHub", username="octocat", password="x")
        vault.add(title="GitLab", category="dev", password="y")
        vault.add(title="Bank", password="z")
        assert {e.title for e in vault.search("git")} == {"GitHub", "GitLab"}
        assert {e.title for e in vault.search("octocat")} == {"GitHub"}
        assert {e.title for e in vault.search("dev")} == {"GitLab"}

    def test_search_empty_returns_all(self, vault):
        vault.add(title="A", password="x")
        vault.add(title="B", password="y")
        assert len(vault.search("")) == 2

    def test_find_by_title_and_username(self, vault):
        vault.add(title="GitHub", username="octocat", password="x")
        assert vault.find(title="github").username == "octocat"
        assert vault.find(username="OCTOCAT").title == "GitHub"
        assert vault.find(title="missing") is None

    def test_find_requires_a_criterion(self, vault):
        with pytest.raises(VaultError, match="requires"):
            vault.find()


class TestMaintenance:
    def test_export_import_round_trip(self, vault, vault_paths, tmp_path,
                                      isolated_backups):
        vault.add(title="GitHub", username="octocat", password="s3cret")
        csv_path = str(tmp_path / "export.csv")
        assert vault.export_csv(csv_path) == 1

        other = Vault.create(
            "another-master-pw", str(tmp_path / "other.db"), str(tmp_path / ".other.key")
        )
        try:
            assert other.import_csv(csv_path) == 1
            imported = other.list_entries()
            assert len(imported) == 1
            assert imported[0].password == "s3cret"
        finally:
            other.lock()

    def test_backup_creates_timestamped_copy(self, vault, isolated_backups):
        vault.add(title="GitHub", password="x")
        backup_path = vault.backup()
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert os.path.dirname(backup_path) == str(isolated_backups)
        assert os.path.basename(backup_path).startswith("aethervault_")

    def test_backup_lands_beside_custom_vault(self, vault_paths, monkeypatch):
        """F20: a non-default vault backs up next to itself, not the app data dir."""
        monkeypatch.setattr(database, "load_settings", lambda: {"remote_backup_dir": ""})
        db_path, key_file = vault_paths
        vault = Vault.create(MASTER_PW, db_path, key_file)
        try:
            vault.add(title="GitHub", password="x")
            backup_path = vault.backup()
        finally:
            vault.lock()
        assert backup_path is not None
        assert os.path.dirname(backup_path) == os.path.dirname(db_path)


class TestSecurity:
    def test_wrong_password_leaves_vault_intact(self, vault, vault_paths):
        db_path, key_file = vault_paths
        vault.add(title="GitHub", password="x")
        vault.lock()
        with pytest.raises(AuthenticationError):
            Vault(db_path, key_file).unlock("definitely-not-the-password")
        assert os.path.exists(db_path)
        assert os.path.exists(key_file)
        assert len(Vault(db_path, key_file).unlock(MASTER_PW).list_entries()) == 1

    def test_duress_password_is_not_honoured(self, vault, vault_paths, tmp_path):
        db_path, key_file = vault_paths
        vault.add(title="GitHub", password="x")
        vault.lock()
        duress_key = str(tmp_path / "duress.key")
        with open(duress_key, "w", encoding="utf-8") as f:
            f.write(engine.hash_password("duress-password"))
        with pytest.raises(AuthenticationError):
            Vault(db_path, key_file).unlock("duress-password")
        assert os.path.exists(db_path)
