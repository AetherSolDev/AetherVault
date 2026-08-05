# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
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
        temp_db.save_credential(CredentialEntry(title="Existing", username="admin", password="vault_pass"))

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
        temp_db.save_credential(CredentialEntry(title="Existing", username="admin", password="vault_pass"))

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

    def test_import_from_csv_updates_existing(self, temp_db, tmp_path):
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
        assert loaded[0].title == "Updated"
        assert loaded[0].password == "new_pass"
        assert len(loaded) == 1

    def test_import_from_csv_missing_title_returns_zero(self, temp_db, tmp_path):
        import csv
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "username"])
            w.writerow(["https://x.com", "user"])

        n = temp_db.import_from_csv(str(csv_path))
        assert n == 0

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
