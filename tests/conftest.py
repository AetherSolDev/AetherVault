# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
# Path: tests/conftest.py
# Purpose: Shared test fixtures for AetherVault test suite.

"""Shared test fixtures for AetherVault test suite."""

import tempfile

import pytest

from aethervault.core_logic import CredentialEntry
from aethervault.db_manager import DatabaseManager


@pytest.fixture
def temp_db():
    db_path = tempfile.mktemp(suffix=".db")
    err = lambda t, m: None
    dm = DatabaseManager(db_path, err)
    dm.set_encryption_key("test_key_placeholder_12345678901234567890")
    yield dm
    dm.conn.close()
    import os
    os.unlink(db_path)


@pytest.fixture
def temp_db_no_key():
    db_path = tempfile.mktemp(suffix=".db")
    err = lambda t, m: None
    dm = DatabaseManager(db_path, err)
    yield dm
    dm.conn.close()
    import os
    os.unlink(db_path)


@pytest.fixture
def sample_entry():
    return CredentialEntry(
        title="Test Site",
        url="https://example.com",
        username="john",
        email="john@example.com",
        password="MyP@ssw0rd!",
        phone="555-0100",
        address="123 Main St",
        category="Work",
        notes="Test note",
        tags="web,important",
        time_last_used="2026-06-01",
        time_password_changed="2026-05-15",
    )
