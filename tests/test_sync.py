# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: tests/test_sync.py
# Purpose: Tests for the relay-aligned sync core and sync schema.

"""Tests for aethervault.core.sync (key wrapping, records, HLC, merge) and the schema."""

import sqlite3

import pytest

from aethervault.core.sync import (
    HLC,
    SyncConfig,
    decrypt_record,
    derive_kek,
    encrypt_record,
    entry_to_payload,
    merge_records,
    new_data_key,
    new_kdf_salt,
    record_to_apply,
    unwrap_data_key,
    wrap_data_key,
)
from aethervault.shared.database import DatabaseManager
from aethervault.shared.models import CredentialEntry


class TestKeyWrapping:
    def test_wrap_unwrap_round_trip(self):
        data_key = new_data_key()
        kek = derive_kek("pw", new_kdf_salt())
        assert unwrap_data_key(wrap_data_key(data_key, kek), kek) == data_key

    def test_wrong_password_fails(self):
        data_key = new_data_key()
        salt = new_kdf_salt()
        wrapped = wrap_data_key(data_key, derive_kek("pw", salt))
        with pytest.raises(ValueError):
            unwrap_data_key(wrapped, derive_kek("other", salt))

    def test_kek_is_deterministic(self):
        salt = new_kdf_salt()
        assert derive_kek("pw", salt) == derive_kek("pw", salt)


class TestRecordCrypto:
    def test_round_trip_and_opaque(self):
        data_key = new_data_key()
        payload = {"title": "GitHub", "password": "p"}
        token = encrypt_record(payload, data_key)
        assert "GitHub" not in token
        assert decrypt_record(token, data_key) == payload

    def test_wrong_key_raises(self):
        token = encrypt_record({"title": "x"}, new_data_key())
        with pytest.raises(ValueError):
            decrypt_record(token, new_data_key())


class TestEntryToPayload:
    def test_carries_fields_but_not_record_ids(self):
        payload = entry_to_payload(CredentialEntry(
            title="GitHub", password="p", totp_secret="SECRET",
        ))
        assert payload["title"] == "GitHub"
        assert payload["totp_secret"] == "SECRET"
        assert "entry_uuid" not in payload
        assert "deleted" not in payload


class TestRecordToApply:
    def test_live_record(self):
        data_key = new_data_key()
        record = {
            "uuid": "u1", "rev": "1", "deleted": False, "updated_at": "2026-01-01",
            "payload": encrypt_record({"title": "GitHub", "password": "p"}, data_key),
        }
        applied = record_to_apply(record, data_key)
        assert applied["entry_uuid"] == "u1"
        assert applied["title"] == "GitHub"
        assert applied["deleted"] == 0

    def test_deleted_record(self):
        applied = record_to_apply(
            {"uuid": "u1", "rev": "2", "deleted": True, "updated_at": "2026-01-02",
             "payload": ""},
            new_data_key(),
        )
        assert applied["entry_uuid"] == "u1"
        assert applied["deleted"] == 1


class TestHLC:
    def test_monotonic_and_sortable(self):
        clock = HLC("dev")
        revs = [clock.next() for _ in range(5)]
        assert revs == sorted(revs)
        assert len(set(revs)) == 5

    def test_observe_advances_past_remote(self):
        clock = HLC("dev")
        clock.observe("9999999999999999:000005:other")
        assert clock.next() > "9999999999999999:000005:other"

    def test_rev_format(self):
        parts = HLC("dev").next().split(":")
        assert len(parts) == 3 and parts[2] == "dev"


class TestMerge:
    def test_higher_rev_wins(self):
        merged = merge_records(
            [{"uuid": "u1", "rev": "2", "payload": "b"}],
            [{"uuid": "u1", "rev": "1", "payload": "a"}],
        )
        assert merged[0]["payload"] == "b"

    def test_union_of_distinct(self):
        merged = merge_records([{"uuid": "u1", "rev": "1"}], [{"uuid": "u2", "rev": "1"}])
        assert {m["uuid"] for m in merged} == {"u1", "u2"}

    def test_missing_uuid_skipped(self):
        assert len(merge_records([{"rev": "1"}], [{"uuid": "u1", "rev": "1"}])) == 1


class TestSyncConfig:
    def test_save_load_delete(self, tmp_path):
        config = SyncConfig(str(tmp_path / "vault.db"))
        assert config.load() is None
        config.save({"relay_url": "http://x", "device_id": "d", "token": "t",
                     "last_server_rev": 3})
        assert config.load()["last_server_rev"] == 3
        config.delete()
        assert config.load() is None


class TestSyncSchema:
    def test_uuid_assigned_on_save(self, temp_db):
        temp_db.save_credential(CredentialEntry(title="A", password="p"))
        assert temp_db.load_all_credentials()[0].entry_uuid

    def test_delete_is_a_tombstone(self, temp_db):
        entry_id = temp_db.save_credential(CredentialEntry(title="A", password="p"))
        temp_db.delete_credential(entry_id)
        assert temp_db.load_all_credentials() == []
        tombstoned = temp_db.load_all_credentials(include_deleted=True)
        assert len(tombstoned) == 1 and int(tombstoned[0].deleted) == 1

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
        assert len(loaded) == 1 and loaded[0].entry_uuid
        assert int(loaded[0].deleted) == 0
        dm.conn.close()

    def test_apply_sync_records_insert_update_tombstone(self, temp_db):
        temp_db.apply_sync_records([{
            "entry_uuid": "u1", "title": "GitHub", "password": "p",
            "modified_at": "2026-01-01 00:00:00",
        }])
        assert temp_db.load_all_credentials()[0].entry_uuid == "u1"

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
