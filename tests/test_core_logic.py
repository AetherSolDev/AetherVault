# Created: 2026-07-27
# Last Edited: 2026-07-30 22:31 CT (America/Chicago)
# Path: tests/test_core_logic.py
# Purpose: Unit tests for encryption, hashing, password generation, and settings.

"""Unit tests for encryption, hashing, password generation, and settings."""

import json
import os
import tempfile

import pytest

from aethervault.core.engine import (
    decrypt_data,
    derive_encryption_key,
    encrypt_data,
    hash_password,
    load_master_password,
    load_settings,
    save_settings,
    store_master_password,
    verify_password,
)
from aethervault.core.password import generate_strong_password
from aethervault.shared.models import CredentialEntry


class TestDeriveEncryptionKey:
    def test_derives_deterministic_key(self):
        key1 = derive_encryption_key("same_hash")
        key2 = derive_encryption_key("same_hash")
        assert key1 == key2
        assert isinstance(key1, bytes)
        assert len(key1) > 0

    def test_different_hashes_produce_different_keys(self):
        key1 = derive_encryption_key("hash_a")
        key2 = derive_encryption_key("hash_b")
        assert key1 != key2

    def test_empty_hash_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            derive_encryption_key("")


class TestEncryptDecrypt:
    def test_roundtrip(self):
        key = derive_encryption_key("test_hash_for_encrypt")
        original = "MyS3cretP@ss!"
        encrypted = encrypt_data(original, key)
        assert encrypted != original
        decrypted = decrypt_data(encrypted, key)
        assert decrypted == original

    def test_empty_string_returns_empty(self):
        key = derive_encryption_key("any_hash")
        assert encrypt_data("", key) == ""
        assert decrypt_data("", key) == ""

    def test_different_key_fails_to_decrypt(self):
        key1 = derive_encryption_key("hash_1")
        key2 = derive_encryption_key("hash_2")
        encrypted = encrypt_data("secret", key1)
        decrypted = decrypt_data(encrypted, key2)
        assert decrypted != "secret"

    def test_encrypt_twice_different_ciphertext(self):
        key = derive_encryption_key("hash")
        data = "same data"
        e1 = encrypt_data(data, key)
        e2 = encrypt_data(data, key)
        assert e1 != e2

    def test_decrypt_garbage_returns_original(self):
        key = derive_encryption_key("hash")
        result = decrypt_data("not-valid-encrypted-data", key)
        assert result == "not-valid-encrypted-data"


class TestPasswordHashing:
    def test_roundtrip(self):
        password = "MyC0mpl3xP@ss!"
        stored = hash_password(password)
        assert stored != password
        assert verify_password(password, stored)

    def test_wrong_password_fails(self):
        stored = hash_password("correct_password")
        assert not verify_password("wrong_password", stored)

    def test_empty_password_fails(self):
        stored = hash_password("anything")
        assert not verify_password("", stored)

    def test_different_salts(self):
        h1 = hash_password("same_pass")
        h2 = hash_password("same_pass")
        assert h1 != h2

    def test_invalid_stored_hash_returns_false(self):
        assert not verify_password("test", "not-a-base64-hash")


class TestGenerateStrongPassword:
    def test_default_length(self):
        pw = generate_strong_password()
        assert len(pw) == 18

    def test_custom_length(self):
        pw = generate_strong_password(length=32)
        assert len(pw) == 32

    def test_min_length_one(self):
        pw = generate_strong_password(length=1)
        assert len(pw) == 1

    def test_contains_each_chosen_set(self):
        pw = generate_strong_password(length=50, use_lower=True, use_upper=True, use_digit=True, use_symbol=True)
        assert any(c.islower() for c in pw)
        assert any(c.isupper() for c in pw)
        assert any(c.isdigit() for c in pw)
        assert any(not c.isalnum() for c in pw)

    def test_only_lowercase(self):
        pw = generate_strong_password(length=20, use_lower=True, use_upper=False, use_digit=False, use_symbol=False)
        assert all(c.islower() for c in pw)

    def test_unique_generations(self):
        pws = {generate_strong_password() for _ in range(100)}
        assert len(pws) > 90


class TestMasterPasswordPersistence:
    def test_store_and_load(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, ".master.key")
            monkeypatch.setattr("aethervault.core.engine.MASTER_KEY_FILE", key_path)
            assert store_master_password("MyM@sterP@ss!")
            loaded = load_master_password(key_path)
            assert loaded is not None
            assert loaded != "MyM@sterP@ss!"

    def test_load_missing_file(self):
        result = load_master_password("/nonexistent/path/.master.key")
        assert result is None


class TestSettingsPersistence:
    def test_save_and_load(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, ".app_settings.json")
            monkeypatch.setattr("aethervault.core.engine.APP_SETTINGS_FILE", settings_path)
            settings = {"lockout_minutes": 5, "theme": "light"}
            save_settings(settings)
            loaded = load_settings()
            assert loaded == settings

    def test_missing_file_returns_defaults(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, ".nonexistent.json")
            monkeypatch.setattr("aethervault.core.engine.APP_SETTINGS_FILE", settings_path)
            loaded = load_settings()
            assert loaded == {"lockout_minutes": 3, "theme": "dark"}

    def test_invalid_json_returns_defaults(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "bad.json")
            monkeypatch.setattr("aethervault.core.engine.APP_SETTINGS_FILE", settings_path)
            with open(settings_path, "w") as f:
                f.write("not json")
            loaded = load_settings()
            assert loaded == {"lockout_minutes": 3, "theme": "dark"}
