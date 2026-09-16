# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: tests/test_sync.py
# Purpose: Tests for the sync core (payloads, encryption, LWW merge) and sync schema.

"""Tests for aethervault.core.sync and the sync-related schema."""

import sqlite3

import pytest

from aethervault.core.sync import (
    SYNC_FIELDS,
    build_payload,
    decrypt_payload,
    derive_sync_key,
    encrypt_payload,
    merge_records,
)
from aethervault.shared.database import DatabaseManager
from aethervault.shared.models import CredentialEntry


def rec(uuid, modified, deleted=0, title=""):
    record = {field: "" for field in SYNC_FIELDS}
    record.update({
        "entry_uuid": uuid,
        "modified_at": modified,
        "deleted": deleted,
        "title": title,
    })
    return record


class TestDeriveSyncKey:
    def test_deterministic(self):
        assert derive_sync_key("hash") == derive_sync_key("hash")

    def test_differs_from_encryption_key(self):
        from aethervault.core.engine import derive_encryption_key
        assert derive_sync_key("hash") != derive_encryption_key("hash")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            derive_sync_key("")


class TestPayloadEncryption:
    def test_round_trip_and_opaque(self):
        key = derive_sync_key("hash")
        payload = build_payload([CredentialEntry(
            title="GitHub", password="p", entry_uuid="u1",
            modified_at="2026-01-01 00:00:00",
        )])
        token = encrypt_payload(payload, key)
        assert isinstance(token, str)
        assert "GitHub" not in token
        assert decrypt_payload(token, key)["entries"][0]["title"] == "GitHub"

    def test_wrong_key_raises(self):
        token = encrypt_payload({"version": 1, "entries": []}, derive_sync_key("a"))
        with pytest.raises(ValueError):
            decrypt_payload(token, derive_sync_key("b"))

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            decrypt_payload("not-a-token", derive_sync_key("a"))


class TestMerge:
    def test_newest_wins(self):
        merged = merge_records(
            [rec("u1", "2026-01-02 00:00:00", title="new")],
            [rec("u1", "2026-01-01 00:00:00", title="old")],
        )
        assert len(merged) == 1
        assert merged[0]["title"] == "new"

    def test_union_of_distinct(self):
        merged = merge_records([rec("u1", "2026-01-01")], [rec("u2", "2026-01-01")])
        assert {m["entry_uuid"] for m in merged} == {"u1", "u2"}

    def test_tombstone_wins_tie(self):
        merged = merge_records(
            [rec("u1", "2026-01-01 00:00:00", deleted=1)],
            [rec("u1", "2026-01-01 00:00:00", deleted=0)],
        )
        assert bool(merged[0]["deleted"]) is True

    def test_edit_after_delete_wins(self):
        merged = merge_records(
            [rec("u1", "2026-01-02 00:00:00", deleted=0, title="resurrected")],
            [rec("u1", "2026-01-01 00:00:00", deleted=1)],
        )
        assert bool(merged[0]["deleted"]) is False

    def test_missing_uuid_skipped(self):
        merged = merge_records([{"entry_uuid": "", "modified_at": "x"}], [rec("u1", "y")])
        assert len(merged) == 1


class TestSyncSchema:
    def test_uuid_assigned_on_save(self, temp_db):
        temp_db.save_credential(CredentialEntry(title="A", password="p"))
        assert temp_db.load_all_credentials()[0].entry_uuid

    def test_delete_is_a_tombstone(self, temp_db):
        entry_id = temp_db.save_credential(CredentialEntry(title="A", password="p"))
        temp_db.delete_credential(entry_id)
        assert temp_db.load_all_credentials() == []
        tombstoned = temp_db.load_all_credentials(include_deleted=True)
        assert len(tombstoned) == 1
        assert int(tombstoned[0].deleted) == 1

    def test_migration_backfills_entry_uuid(self, tmp_path):
        db_path = str(tmp_path / "legacy.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE credentials (
                db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, url TEXT, username TEXT, email TEXT,
                password TEXT NOT NULL, phone TEXT, address TEXT, category TEXT,
                notes TEXT, tags TEXT DEFAULT '', custom_fields TEXT DEFAULT '',
                parent_id INTEGER DEFAULT 0, created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL, time_last_used TEXT DEFAULT '',
                time_password_changed TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            "INSERT INTO credentials (title, password, created_at, modified_at) "
            "VALUES ('Legacy', 'cipher', '2026-01-01', '2026-01-01')"
        )
        conn.commit()
        conn.close()

        dm = DatabaseManager(db_path, lambda t, m: None)
        dm.set_encryption_key("test-key")
        loaded = dm.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].entry_uuid  # backfilled
        assert int(loaded[0].deleted) == 0
        dm.conn.close()

    def test_apply_sync_records_insert_update_tombstone(self, temp_db):
        temp_db.apply_sync_records([{
            "entry_uuid": "u1", "title": "GitHub", "password": "p",
            "modified_at": "2026-01-01 00:00:00",
        }])
        entries = temp_db.load_all_credentials()
        assert len(entries) == 1 and entries[0].entry_uuid == "u1"

        temp_db.apply_sync_records([{
            "entry_uuid": "u1", "title": "GitHub2", "password": "p",
            "modified_at": "2026-01-02 00:00:00",
        }])
        assert temp_db.load_all_credentials()[0].title == "GitHub2"

        temp_db.apply_sync_records([{
            "entry_uuid": "u1", "title": "GitHub2", "password": "p",
            "deleted": 1, "modified_at": "2026-01-03 00:00:00",
        }])
        assert temp_db.load_all_credentials() == []
        assert int(temp_db.load_all_credentials(include_deleted=True)[0].deleted) == 1
