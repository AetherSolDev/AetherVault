# Created: 2025-12-04
# Last Edited: 2026-08-01 02:00 CT (America/Chicago)
# Path: aethervault/core_logic.py
# Purpose: Encryption, hashing, data model, and settings management for AetherVault.

"""Encryption, hashing, credential data model, and application settings management for AetherVault."""

import base64
import hashlib
import json
import logging
import re
import os
import random
import string
import time
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from aethervault import PROJECT_ROOT

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "aethervault.db")
MASTER_KEY_FILE = os.path.join(DATA_DIR, ".master.key")
DB_BACKUP_PATH = f"{DB_PATH}.bak"
JOURNAL_FILE = os.path.join(PROJECT_ROOT, "journal.md")
APP_SETTINGS_FILE = os.path.join(DATA_DIR, ".app_settings.json")

APPLICATION_SALT = b"password_manager_salt_value_12345"
backend = default_backend()
DEFAULT_LOCKOUT_MINUTES = 3
logger = logging.getLogger(__name__)


def derive_encryption_key(master_password_hash: str) -> bytes:
    """Derive an AES-256 Fernet key from the master password hash via PBKDF2."""
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
    """Return a backup file path with a human-readable timestamp."""
    timestamp = time.strftime("%Y.%m.%d_%H%M%S")
    db_dir = os.path.dirname(DB_PATH)
    return os.path.join(db_dir, f"aethervault_{timestamp}.db.bak")


def encrypt_data(data: str, key: bytes) -> str:
    """Encrypt a plaintext string using Fernet symmetric encryption."""
    if not data:
        return ""
    try:
        f = Fernet(key)
        encrypted_bytes = f.encrypt(data.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except (TypeError, ValueError) as e:
        logger.error("Encryption failed: %s", e)
        return data


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext."""
    if not encrypted_data:
        return ""
    try:
        f = Fernet(key)
        decrypted_bytes = f.decrypt(encrypted_data.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, TypeError, ValueError):
        return encrypted_data


def generate_strong_password(
    length: int = 18, use_lower=True, use_upper=True, use_digit=True, use_symbol=True
) -> str:
    """Generate a cryptographically random password with configurable character sets."""
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
    """Hash a password with a random salt using PBKDF2-SHA256 and return a Base64 string."""
    salt = os.urandom(16)
    hashed_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return base64.b64encode(salt + hashed_bytes).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored PBKDF2-SHA256 hash."""
    try:
        decoded_hash = base64.b64decode(stored_hash)
        salt = decoded_hash[:16]
        stored_hash_part = decoded_hash[16:]
        new_hash_part = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 600000
        )
        return new_hash_part == stored_hash_part
    except (ValueError, TypeError):
        return False


def score_password(password: str) -> int:
    """Score a password 0-100 based on length and character diversity."""
    if not password:
        return 0
    score = 0
    if len(password) >= 8:
        score += 15
    if len(password) >= 12:
        score += 15
    if len(password) >= 16:
        score += 10
    if re.search(r"[a-z]", password):
        score += 10
    if re.search(r"[A-Z]", password):
        score += 15
    if re.search(r"\d", password):
        score += 15
    if re.search(r"[^a-zA-Z0-9]", password):
        score += 20
    return min(score, 100)


def load_master_password(file_path: str) -> Optional[str]:
    """Read the stored master password hash from disk, or return None."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except OSError:
            return None
    return None


def store_master_password(password: str) -> bool:
    """Hash and persist the master password to the master key file."""
    hashed_pass = hash_password(password)
    try:
        with open(MASTER_KEY_FILE, "w") as f:
            f.write(hashed_pass)
        return True
    except OSError:
        return False


def load_settings() -> dict:
    """Load application settings from the JSON settings file, falling back to defaults."""
    try:
        with open(APP_SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"lockout_minutes": DEFAULT_LOCKOUT_MINUTES, "theme": "dark"}


def save_settings(settings: dict):
    """Persist application settings to the JSON settings file."""
    try:
        with open(APP_SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        logger.error("Error saving settings: %s", e)


class CredentialEntry:
    """Data class representing a single credential entry with all metadata fields."""
    def __init__(self, **kwargs):
        """Initialize a CredentialEntry from keyword arguments, defaulting missing fields."""
        self.db_id = kwargs.get("db_id")
        self.title = kwargs.get("title", "")
        self.url = kwargs.get("url", "")
        self.username = kwargs.get("username", "")
        self.email = kwargs.get("email", "")
        self.password = kwargs.get("password", "")
        self.phone = kwargs.get("phone", "")
        self.address = kwargs.get("address", "")
        self.category = kwargs.get("category", "")
        self.notes = kwargs.get("notes", "")
        self.tags = kwargs.get("tags", "")
        self.custom_fields = kwargs.get("custom_fields", "")
        self.parent_id = kwargs.get("parent_id", 0)
        self.created_at = kwargs.get("created_at")
        self.modified_at = kwargs.get("modified_at")
        self.time_last_used = kwargs.get("time_last_used", "")
        self.time_password_changed = kwargs.get("time_password_changed", "")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this credential entry to a plain dictionary."""
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
            "time_last_used": self.time_last_used,
            "time_password_changed": self.time_password_changed,
        }
