# Created: 2026-07-27
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: tests/test_db_manager.py
# Purpose: Integration tests for DatabaseManager CRUD operations.

"""Integration tests for DatabaseManager CRUD operations."""

import os

import pytest

from aethervault.shared.database import DatabaseManager
from aethervault.shared.models import CredentialEntry


class TestDatabaseManager:
    def test_save_and_load_credential(self, temp_db, sample_entry):
        saved_id = temp_db.save_credential(sample_entry)
        assert saved_id is not None
        assert saved_id > 0

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].title == "Test Site"
        assert loaded[0].password == "MyP@ssw0rd!"

    def test_update_credential(self, temp_db, sample_entry):
        saved_id = temp_db.save_credential(sample_entry)
        sample_entry.db_id = saved_id
        sample_entry.password = "NewP@ss1!"
        temp_db.update_credential(sample_entry)

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].password == "NewP@ss1!"

    def test_delete_credential(self, temp_db, sample_entry):
        saved_id = temp_db.save_credential(sample_entry)
        temp_db.delete_credential(saved_id)

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 0

    def test_multiple_credentials(self, temp_db):
        e1 = CredentialEntry(title="Site A", password="pass1")
        e2 = CredentialEntry(title="Site B", password="pass2")
        temp_db.save_credential(e1)
        temp_db.save_credential(e2)

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 2

    def test_preview_import_no_conflicts(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "url", "username", "password"])
            w.writerow(["New Site", "https://new.com", "user1", "pass123"])

        preview = temp_db.preview_import(str(csv_path))
        assert preview["total_rows"] == 1
        assert preview["non_conflict_count"] == 1
        assert len(preview["conflicts"]) == 0

    def test_execute_import_keep_vault(self, temp_db, tmp_path):
        import csv
        temp_db.save_credential(
            CredentialEntry(title="Existing", username="admin", password="vault_pass")
        )

        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "url", "username", "password"])
            w.writerow(["Existing", "https://ex.com", "admin", "import_pass"])

        decisions = {("existing", "admin"): "keep_vault"}
        n = temp_db.execute_import(str(csv_path), decisions)
        assert n == 0  # skipped conflict

        loaded = temp_db.load_all_credentials()
        assert loaded[0].password == "vault_pass"

    def test_execute_import_replace(self, temp_db, tmp_path):
        import csv
        temp_db.save_credential(
            CredentialEntry(title="Existing", username="admin", password="vault_pass")
        )

        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "url", "username", "password"])
            w.writerow(["Existing", "https://ex.com", "admin", "import_pass"])

        decisions = {("existing", "admin"): "replace"}
        n = temp_db.execute_import(str(csv_path), decisions)
        assert n == 1  # replaced

        loaded = temp_db.load_all_credentials()
        assert loaded[0].password == "import_pass"

    # --- import_from_csv ---

    def test_import_from_csv_inserts_new(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "url", "username", "password"])
            w.writerow(["NewSite", "https://new.com", "user1", "pass123"])
            w.writerow(["Site2", "https://two.com", "user2", "pass456"])

        n = temp_db.import_from_csv(str(csv_path))
        assert n == 2
        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 2

    def test_import_from_csv_ignores_db_id_column(self, temp_db, tmp_path):
        import csv
        saved_id = temp_db.save_credential(CredentialEntry(title="Old", password="old_pass"))
        assert saved_id is not None

        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["db_id", "name", "password"])
            w.writerow([str(saved_id), "Updated", "new_pass"])

        n = temp_db.import_from_csv(str(csv_path))
        assert n == 1
        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 2
        imported = [e for e in loaded if e.title == "Updated"]
        assert len(imported) == 1
        assert imported[0].password == "new_pass"
        assert imported[0].db_id != saved_id

    def test_import_export_roundtrip_into_other_vault_preserves_all(self, tmp_path):
        """Importing an export from vault A into vault B must insert every row
        as new, never overwrite B's rows or drop rows by a foreign db_id."""
        import csv

        db_a = str(tmp_path / "vault_a.db")
        db_b = str(tmp_path / "vault_b.db")
        err = lambda t, m: None
        dm_a = DatabaseManager(db_a, err)
        dm_a.set_encryption_key("test_key_placeholder_12345678901234567890")
        for title, user in [("Alpha", "a"), ("Beta", "b"), ("Gamma", "c")]:
            dm_a.save_credential(CredentialEntry(title=title, username=user, password=f"pw_{title.lower()}"))
        exported = dm_a.load_all_credentials()
        csv_path = str(tmp_path / "export.csv")
        dm_a.export_to_csv(csv_path, exported)
        dm_a.conn.close()

        dm_b = DatabaseManager(db_b, err)
        dm_b.set_encryption_key("test_key_placeholder_12345678901234567890")
        dm_b.save_credential(CredentialEntry(title="ExistingOne", username="e1", password="orig1"))
        dm_b.save_credential(CredentialEntry(title="ExistingTwo", username="e2", password="orig2"))

        n = dm_b.import_from_csv(csv_path)
        assert n == 3

        after = dm_b.load_all_credentials()
        by_title = {e.title: e for e in after}
        assert len(after) == 5
        assert by_title["Alpha"].password == "pw_alpha"
        assert by_title["Beta"].password == "pw_beta"
        assert by_title["Gamma"].password == "pw_gamma"
        assert by_title["ExistingOne"].password == "orig1"
        assert by_title["ExistingTwo"].password == "orig2"
        dm_b.conn.close()

    def test_import_from_csv_missing_title_returns_zero(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username"])
            w.writerow(["https://x.com", "user"])

        n = temp_db.import_from_csv(str(csv_path))
        assert n == 0

    def test_import_from_csv_derives_title_from_url(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username", "password"])
            w.writerow(["https://www.example.com/login", "user1", "pass123"])

        n = temp_db.import_from_csv(str(csv_path))
        assert n == 1
        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].title == "example.com"
        assert loaded[0].url == "https://www.example.com/login"
        assert loaded[0].password == "pass123"

    def test_preview_import_derives_title_from_url(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username", "password"])
            w.writerow(["http://10.0.0.130:8080", "bmunoz", "Houston1"])

        preview = temp_db.preview_import(str(csv_path))
        assert preview["total_rows"] == 1
        assert preview["non_conflict_count"] == 1
        assert len(preview["conflicts"]) == 0

    def test_execute_import_derives_title_from_url(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username", "password"])
            w.writerow(["https://watch.plex.tv", "user1", "Houston1"])

        n = temp_db.execute_import(str(csv_path), {})
        assert n == 1
        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].title == "watch.plex.tv"

    def test_import_from_csv_file_not_found(self, temp_db):
        with pytest.raises(FileNotFoundError):
            temp_db.import_from_csv("/nonexistent/file.csv")

    def test_import_from_csv_raises_without_key(self, temp_db_no_key, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "password"])
            w.writerow(["X", "pass"])

        with pytest.raises(RuntimeError, match="Encryption key not set"):
            temp_db_no_key.import_from_csv(str(csv_path))

    def test_preview_import_raises_without_key(self, temp_db_no_key, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "password"])
            w.writerow(["X", "pass"])

        with pytest.raises(RuntimeError, match="Encryption key not set"):
            temp_db_no_key.preview_import(str(csv_path))

    def test_execute_import_raises_without_key(self, temp_db_no_key, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "password"])
            w.writerow(["X", "pass"])

        with pytest.raises(RuntimeError, match="Encryption key not set"):
            temp_db_no_key.execute_import(str(csv_path), {})

    def test_save_credential_without_key_returns_none(self, temp_db_no_key):
        entry = CredentialEntry(title="NoKey", password="test")
        result = temp_db_no_key.save_credential(entry)
        assert result is None

    def test_update_credential_without_key_does_not_crash(self, temp_db_no_key):
        entry = CredentialEntry(title="NoKey", password="test", db_id=1)
        temp_db_no_key.update_credential(entry)

    # --- export_to_csv ---

    def test_export_to_csv(self, temp_db, sample_entry, tmp_path):
        temp_db.save_credential(sample_entry)
        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1

        csv_path = tmp_path / "export.csv"
        n = temp_db.export_to_csv(str(csv_path), loaded)
        assert n == 1

        import csv
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["title"] == "Test Site"
        assert rows[0]["password"] == "MyP@ssw0rd!"

    def test_export_to_csv_empty_list(self, temp_db, tmp_path):
        csv_path = tmp_path / "empty.csv"
        n = temp_db.export_to_csv(str(csv_path), [])
        assert n == 0

    # --- find_and_remove_duplicates ---

    def test_find_and_remove_duplicates(self, temp_db):
        temp_db.save_credential(CredentialEntry(title="Dup", username="a", password="pass1"))
        temp_db.save_credential(CredentialEntry(title="Dup", username="a", password="pass2"))
        temp_db.save_credential(CredentialEntry(title="Unique", username="b", password="pass3"))

        deleted = temp_db.find_and_remove_duplicates()
        assert deleted == 1

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 2

    def test_find_and_remove_duplicates_no_dupes(self, temp_db):
        temp_db.save_credential(CredentialEntry(title="A", username="a", password="p1"))
        temp_db.save_credential(CredentialEntry(title="B", username="b", password="p2"))

        deleted = temp_db.find_and_remove_duplicates()
        assert deleted == 0
        assert len(temp_db.load_all_credentials()) == 2

    def test_find_and_remove_duplicates_keeps_oldest(self, temp_db):
        id1 = temp_db.save_credential(CredentialEntry(title="Dup", username="a", password="first"))
        id2 = temp_db.save_credential(CredentialEntry(title="Dup", username="a", password="second"))
        assert id1 is not None and id2 is not None

        temp_db.find_and_remove_duplicates()

        loaded = temp_db.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].password == "first"

    # --- create_pre_op_backup ---

    def test_create_pre_op_backup_creates_file(self, temp_db, tmp_path):
        import shutil
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        backup_path = str(backup_dir / "test_backup.db.bak")

        original_db = temp_db.db_path
        shutil.copyfile(original_db, backup_path)

        result = temp_db.create_pre_op_backup("TestOp")
        assert result is not None
        assert os.path.exists(result)

    def test_manual_restore_from_backup(self, temp_db):
        """Copying a backup over the live DB (the Restore flow) preserves data."""
        import shutil

        from aethervault.shared.database import DatabaseManager

        temp_db.save_credential(CredentialEntry(title="GitHub", password="s3cret"))
        backup = temp_db.create_pre_op_backup("Verify")
        assert backup and os.path.exists(backup)

        temp_db.conn.close()
        shutil.copyfile(backup, temp_db.db_path)

        restored = DatabaseManager(temp_db.db_path, lambda t, m: None)
        restored.set_encryption_key("test_key_placeholder_12345678901234567890")
        loaded = restored.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].password == "s3cret"
        restored.conn.close()

    # --- integrity check & recovery (F14) ---

    def test_integrity_check_passes_on_valid_db(self, temp_db):
        assert temp_db.conn is not None
        result = temp_db.cursor.execute("PRAGMA integrity_check").fetchone()
        assert result[0] == "ok"

    def test_recover_from_backup_when_corrupt(self, tmp_path, monkeypatch):
        """A corrupt DB is recovered from the latest backup on connect."""
        import shutil
        from aethervault.core.engine import DB_BACKUP_PATH, DATA_DIR
        from aethervault.shared.database import DatabaseManager

        db_path = str(tmp_path / "aethervault.db")
        monkeypatch.setattr("aethervault.core.engine.DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "aethervault.core.engine.DB_BACKUP_PATH", str(tmp_path / "aethervault.db.bak")
        )

        # create valid db with a credential
        dm = DatabaseManager(db_path, lambda t, m: None)
        dm.set_encryption_key("test-key")
        dm.save_credential(CredentialEntry(title="T", password="secret"))
        dm.conn.close()

        # back it up, then corrupt the live db
        backup = tmp_path / "aethervault_2026.08.05_120000.db.bak"
        shutil.copyfile(db_path, backup)
        with open(db_path, "w") as f:
            f.write("NOT A VALID SQLITE DATABASE" * 10)

        messages = []
        dm2 = DatabaseManager(db_path, lambda t, m: messages.append(f"{t}: {m}"))
        assert dm2.conn is not None
        dm2.set_encryption_key("test-key")
        loaded = dm2.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].password == "secret"
        assert any("recovered" in m.lower() for m in messages)
        dm2.conn.close()

    def test_no_backup_fails_safely(self, tmp_path, monkeypatch):
        """A corrupt DB with no backup leaves conn=None instead of crashing."""
        from aethervault.shared.database import DatabaseManager

        db_path = str(tmp_path / "aethervault.db")
        monkeypatch.setattr("aethervault.core.engine.DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "aethervault.core.engine.DB_BACKUP_PATH", str(tmp_path / "aethervault.db.bak")
        )
        with open(db_path, "w") as f:
            f.write("NOT A VALID SQLITE DATABASE" * 10)

        dm = DatabaseManager(db_path, lambda t, m: None)
        assert dm.conn is None


class TestTotpColumns:
    """A21 — totp_secret / recovery_codes persistence, encryption, and migration."""

    def test_totp_fields_round_trip_and_encrypted_at_rest(self, temp_db):
        entry = CredentialEntry(
            title="GitHub", password="p",
            totp_secret="JBSWY3DPEHPK3PXP", recovery_codes="code1\ncode2",
        )
        entry_id = temp_db.save_credential(entry)
        raw = temp_db.cursor.execute(
            "SELECT totp_secret, recovery_codes FROM credentials WHERE db_id = ?",
            (entry_id,),
        ).fetchone()
        assert raw[0] != "JBSWY3DPEHPK3PXP"
        assert raw[1] != "code1\ncode2"

        loaded = temp_db.load_all_credentials()[0]
        assert loaded.totp_secret == "JBSWY3DPEHPK3PXP"
        assert loaded.recovery_codes == "code1\ncode2"

    def test_update_persists_totp(self, temp_db):
        temp_db.save_credential(CredentialEntry(title="GitHub", password="p"))
        entry = temp_db.load_all_credentials()[0]
        entry.totp_secret = "JBSWY3DPEHPK3PXP"
        temp_db.update_credential(entry)
        assert temp_db.load_all_credentials()[0].totp_secret == "JBSWY3DPEHPK3PXP"

    def test_export_csv_excludes_totp(self, temp_db, tmp_path):
        temp_db.save_credential(CredentialEntry(
            title="GitHub", password="p", totp_secret="JBSWY3DPEHPK3PXP",
        ))
        out = str(tmp_path / "export.csv")
        temp_db.export_to_csv(out, temp_db.load_all_credentials())
        with open(out, encoding="utf-8") as f:
            content = f.read()
        assert "totp_secret" not in content
        assert "JBSWY3DPEHPK3PXP" not in content

    def test_migration_adds_totp_columns_to_existing_db(self, tmp_path):
        import sqlite3

        from aethervault.shared.database import DatabaseManager

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
            "VALUES (?, ?, ?, ?)",
            ("Legacy", "ciphertext", "2026-01-01", "2026-01-01"),
        )
        conn.commit()
        conn.close()

        dm = DatabaseManager(db_path, lambda t, m: None)
        dm.set_encryption_key("test-key")
        columns = {
            row[1] for row in dm.cursor.execute("PRAGMA table_info(credentials)").fetchall()
        }
        assert {"totp_secret", "recovery_codes"} <= columns

        loaded = dm.load_all_credentials()
        assert len(loaded) == 1
        assert loaded[0].title == "Legacy"
        assert loaded[0].totp_secret == ""
        assert loaded[0].recovery_codes == ""
        dm.conn.close()
