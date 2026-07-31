# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
# Path: tests/test_credential_entry.py
# Purpose: Unit tests for the CredentialEntry data model.

"""Unit tests for the CredentialEntry data model."""

from aethervault.core_logic import CredentialEntry


class TestCredentialEntry:
    def test_creates_from_kwargs(self, sample_entry):
        assert sample_entry.title == "Test Site"
        assert sample_entry.url == "https://example.com"
        assert sample_entry.username == "john"
        assert sample_entry.password == "MyP@ssw0rd!"

    def test_to_dict_roundtrip(self, sample_entry):
        d = sample_entry.to_dict()
        restored = CredentialEntry(**d)
        assert restored.title == sample_entry.title
        assert restored.password == sample_entry.password
        assert restored.time_last_used == sample_entry.time_last_used
        assert restored.time_password_changed == sample_entry.time_password_changed
        assert restored.db_id == sample_entry.db_id
        assert restored.created_at == sample_entry.created_at

    def test_defaults_for_missing_fields(self):
        e = CredentialEntry(title="Minimal", password="pass")
        assert e.url == ""
        assert e.username == ""
        assert e.tags == ""
        assert e.custom_fields == ""
        assert e.parent_id == 0
        assert e.time_last_used == ""
        assert e.time_password_changed == ""
        assert e.db_id is None

    def test_to_dict_contains_all_fields(self, sample_entry):
        d = sample_entry.to_dict()
        expected_keys = {
            "db_id", "title", "url", "username", "email", "password",
            "phone", "address", "category", "notes", "tags", "custom_fields",
            "parent_id", "created_at", "modified_at",
            "time_last_used", "time_password_changed",
        }
        assert set(d.keys()) == expected_keys

    def test_empty_password_in_roundtrip(self):
        e = CredentialEntry(title="NoPass", password="")
        d = e.to_dict()
        assert d["password"] == ""
