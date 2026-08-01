# Created: 2026-08-01
# Last Edited: 2026-08-01 02:23 CT (America/Chicago)
# Path: tests/test_duress.py
# Purpose: Unit tests for duress password, vault wipe, and backup rotation.

"""Unit tests for duress password, vault wipe, and backup rotation."""

import os

import pytest

import aethervault.core_logic as core


@pytest.fixture
def fake_data_dir(tmp_path, monkeypatch):
    """Point core_logic's DATA_DIR-dependent paths at an isolated temp dir."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(core, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(core, "DB_PATH", str(data_dir / "aethervault.db"))
    monkeypatch.setattr(core, "MASTER_KEY_FILE", str(data_dir / ".master.key"))
    monkeypatch.setattr(core, "DURESS_KEY_FILE", str(data_dir / ".duress.key"))
    monkeypatch.setattr(core, "APP_SETTINGS_FILE", str(data_dir / ".app_settings.json"))
    return data_dir


def _seed_vault(data_dir, n_backups=3):
    """Create a vault DB, master/duress keys, settings, and timestamped backups."""
    for f in ("aethervault.db", "aethervault.db-wal", "aethervault.db-shm",
              "aethervault.db.bak", ".master.key", ".duress.key",
              ".app_settings.json"):
        (data_dir / f).write_bytes(b"x" * 1024)
    for i in range(n_backups):
        (data_dir / f"aethervault_2026.08.01_{1000 + i}.db.bak").write_bytes(
            b"y" * 1024
        )
    (data_dir / ".portable").write_text("portable\n")


class TestDuressPassword:
    def test_store_and_verify_roundtrip(self, fake_data_dir):
        assert core.store_duress_password("panictrigger123")
        loaded = core.load_duress_password()
        assert loaded is not None
        assert core.verify_password("panictrigger123", loaded)
        assert not core.verify_password("wrongpass", loaded)

    def test_clear_removes_file(self, fake_data_dir):
        core.store_duress_password("panictrigger123")
        assert (fake_data_dir / ".duress.key").exists()
        assert core.clear_duress_password()
        assert core.load_duress_password() is None

    def test_load_returns_none_when_absent(self, fake_data_dir):
        assert core.load_duress_password() is None


class TestRotateBackups:
    def test_keeps_most_recent(self, fake_data_dir):
        _seed_vault(fake_data_dir, n_backups=4)
        removed = core.rotate_backups(max_files=2)
        assert removed == 2
        remaining = sorted(f.name for f in fake_data_dir.iterdir()
                           if f.name.startswith("aethervault_"))
        assert len(remaining) == 2
        assert remaining == ["aethervault_2026.08.01_1002.db.bak",
                             "aethervault_2026.08.01_1003.db.bak"]

    def test_no_rotation_when_under_limit(self, fake_data_dir):
        _seed_vault(fake_data_dir, n_backups=2)
        assert core.rotate_backups(max_files=5) == 0
        assert len(list(fake_data_dir.glob("aethervault_*.db.bak"))) == 2


class TestWipeVault:
    def test_wipe_destroys_everything(self, fake_data_dir):
        _seed_vault(fake_data_dir, n_backups=3)
        assert core.wipe_vault()
        leftovers = [f.name for f in fake_data_dir.iterdir()
                     if f.name != ".portable"]
        assert leftovers == []
        assert list(fake_data_dir.iterdir()) == [
            fake_data_dir / ".portable"
        ]

    def test_wipe_removes_master_and_duress_keys(self, fake_data_dir):
        _seed_vault(fake_data_dir)
        core.wipe_vault()
        assert not (fake_data_dir / ".master.key").exists()
        assert not (fake_data_dir / ".duress.key").exists()

    def test_wipe_idempotent_on_clean_dir(self, fake_data_dir):
        assert core.wipe_vault()
        assert core.wipe_vault()
