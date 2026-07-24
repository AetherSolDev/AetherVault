# Created: 2025-12-04
# Last Edited: 2026-07-24 00:37 CT (America/Chicago)
# Path: src/core_logic.py
# Purpose: Encryption, hashing, data model, and settings management.

import base64
import hashlib
import json
import os
import random
import string
import sys
import time
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src import PROJECT_ROOT

DB_PATH = os.path.join(PROJECT_ROOT, "password_manager.db")
MASTER_KEY_FILE = os.path.join(PROJECT_ROOT, ".master.key")
DB_BACKUP_PATH = f"{DB_PATH}.bak"
JOURNAL_FILE = os.path.join(PROJECT_ROOT, "journal.md")
APP_SETTINGS_FILE = os.path.join(PROJECT_ROOT, ".app_settings.json")

APPLICATION_SALT = b"password_manager_salt_value_12345"
backend = default_backend()
DEFAULT_LOCKOUT_MINUTES = 3


def derive_encryption_key(master_password_hash: str) -> bytes:
    if not master_password_hash:
        raise ValueError("Master password hash cannot be empty for key derivation.")
    password_bytes = master_password_hash.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=APPLICATION_SALT,
        iterations=480000,
        backend=backend,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
    return key


def get_timestamped_backup_path() -> str:
    timestamp = time.strftime("%Y.%m.%d_%H%M%S")
    db_dir = os.path.dirname(DB_PATH)
    return os.path.join(db_dir, f"kiss_vault_{timestamp}.db.bak")


def encrypt_data(data: str, key: bytes) -> str:
    if not data:
        return ""
    try:
        f = Fernet(key)
        encrypted_bytes = f.encrypt(data.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"Encryption failed: {e}")
        return data


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    if not encrypted_data:
        return ""
    try:
        f = Fernet(key)
        decrypted_bytes = f.decrypt(encrypted_data.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        return encrypted_data


def generate_strong_password(
    length: int = 18, use_lower=True, use_upper=True, use_digit=True, use_symbol=True
) -> str:
    if length < 1:
        length = 1
    char_sets = []
    if use_lower:
        char_sets.append(string.ascii_lowercase)
    if use_upper:
        char_sets.append(string.ascii_uppercase)
    if use_digit:
        char_sets.append(string.digits)
    if use_symbol:
        char_sets.append(string.punctuation)
    if not char_sets:
        char_sets.append(string.ascii_letters)
    all_chars = "".join(char_sets)
    if not all_chars:
        return ""
    password = []
    if use_lower:
        password.append(random.choice(string.ascii_lowercase))
    if use_upper:
        password.append(random.choice(string.ascii_uppercase))
    if use_digit:
        password.append(random.choice(string.digits))
    if use_symbol:
        password.append(random.choice(string.punctuation))
    while len(password) < length:
        password.append(random.choice(all_chars))
    random.shuffle(password)
    return "".join(password[:length])


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return base64.b64encode(salt + hashed_bytes).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        decoded_hash = base64.b64decode(stored_hash)
        salt = decoded_hash[:16]
        stored_hash_part = decoded_hash[16:]
        new_hash_part = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 600000
        )
        return new_hash_part == stored_hash_part
    except Exception:
        return False


def load_master_password(file_path: str) -> Optional[str]:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except Exception:
            return None
    return None


def store_master_password(password: str) -> bool:
    hashed_pass = hash_password(password)
    try:
        with open(MASTER_KEY_FILE, "w") as f:
            f.write(hashed_pass)
        return True
    except Exception:
        return False


def load_settings() -> dict:
    try:
        with open(APP_SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"lockout_minutes": DEFAULT_LOCKOUT_MINUTES, "theme": "dark"}


def save_settings(settings: dict):
    try:
        with open(APP_SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Error saving settings: {e}")


class CredentialEntry:
    def __init__(self, **kwargs):
        self.db_id = kwargs.get("db_id")
        self.title = kwargs.get("title")
        self.url = kwargs.get("url")
        self.username = kwargs.get("username")
        self.email = kwargs.get("email")
        self.password = kwargs.get("password")
        self.phone = kwargs.get("phone")
        self.address = kwargs.get("address")
        self.category = kwargs.get("category")
        self.notes = kwargs.get("notes")
        self.tags = kwargs.get("tags", "")
        self.custom_fields = kwargs.get("custom_fields", "")
        self.parent_id = kwargs.get("parent_id", 0)
        self.created_at = kwargs.get("created_at")
        self.modified_at = kwargs.get("modified_at")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "db_id": self.db_id,
            "title": self.title,
            "url": self.url,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "phone": self.phone,
            "address": self.address,
            "category": self.category,
            "notes": self.notes,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }
