# Created: 2026-07-27
# Last Edited: 2026-07-27 13:47 CT (America/Chicago)
# Path: tests/test_db_manager.py
# Purpose: Integration tests for DatabaseManager CRUD operations.

"""Integration tests for DatabaseManager CRUD operations."""

import pytest

from aethervault.core_logic import CredentialEntry


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
