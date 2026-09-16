# Created: 2026-08-05
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: aethervault/core/engine.py
# Purpose: Encryption, hashing, key derivation, backup/wipe, and settings management.

"""Encryption, hashing, key derivation, backup/wipe, and settings management."""

import base64
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from aethervault import PROJECT_ROOT

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "aethervault.db")
MASTER_KEY_FILE = os.path.join(DATA_DIR, ".master.key")
DURESS_KEY_FILE = os.path.join(DATA_DIR, ".duress.key")
DB_BACKUP_PATH = f"{DB_PATH}.bak"
BACKUP_MAX_FILES = 5
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


def get_timestamped_backup_path(db_path: Optional[str] = None) -> str:
    """Return a timestamped backup path beside ``db_path`` (default: the app vault)."""
    timestamp = time.strftime("%Y.%m.%d_%H%M%S")
    db_dir = os.path.dirname(db_path or DB_PATH)
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


def load_master_password(file_path: str) -> Optional[str]:
    """Read the stored master password hash from disk, or return None."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return None
    return None


def store_master_password(password: str) -> bool:
    """Hash and persist the master password to the master key file."""
    hashed_pass = hash_password(password)
    try:
        with open(MASTER_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(hashed_pass)
        return True
    except OSError:
        return False


def load_duress_password() -> Optional[str]:
    """Read the stored duress password hash from disk, or return None."""
    return load_master_password(DURESS_KEY_FILE)


def store_duress_password(password: str) -> bool:
    """Hash and persist the duress password to the duress key file."""
    hashed_pass = hash_password(password)
    try:
        with open(DURESS_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(hashed_pass)
        return True
    except OSError:
        return False


def clear_duress_password() -> bool:
    """Delete the duress key file. Returns True if removed (or absent)."""
    try:
        if os.path.exists(DURESS_KEY_FILE):
            os.remove(DURESS_KEY_FILE)
        return True
    except OSError:
        return False


def rotate_backups(
    max_files: int = BACKUP_MAX_FILES, data_dir: Optional[str] = None
) -> int:
    """Prune timestamped .bak files, keeping the max_files most recent.
    Returns the number of files removed. ``data_dir`` defaults to the app data dir."""
    if max_files <= 0:
        return 0
    directory = data_dir or DATA_DIR
    backups = sorted(
        f for f in os.listdir(directory)
        if f.startswith("aethervault_") and f.endswith(".db.bak")
    )
    stale = backups[:-max_files]
    for f in stale:
        try:
            os.remove(os.path.join(directory, f))
        except OSError:
            pass
    return len(stale)


def checkpoint_database(db_path: str) -> bool:
    """Checkpoint a WAL-mode SQLite database so its data is fully in the main file.

    A running vault in WAL mode keeps recent writes in the -wal file; copying only
    the .db would produce a backup missing those writes. Opening a temporary read-only
    connection and running wal_checkpoint(TRUNCATE) forces all WAL content into the
    main database file before it is copied."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        return True
    except sqlite3.Error:
        conn.close()
        return False


def mirror_backup(
    backup_path: str,
    remote_dir: str,
    max_files: int = BACKUP_MAX_FILES,
) -> Optional[str]:
    """Copy a timestamped backup to a remote directory, rotating old copies.

    The remote copy keeps the same timestamped filename as the local backup so it can
    be restored from AetherVault's Restore dialog. The remote directory must exist and
    be writable; a missing/unwritable remote is a non-fatal mirror failure (the local
    backup still succeeded). Returns the remote path on success, None on failure."""
    if not remote_dir:
        return None
    try:
        os.makedirs(remote_dir, exist_ok=True)
        remote_path = os.path.join(remote_dir, os.path.basename(backup_path))
        shutil.copy2(backup_path, remote_path)
        backups = sorted(
            f for f in os.listdir(remote_dir)
            if f.startswith("aethervault_") and f.endswith(".db.bak")
        )
        for stale in backups[:-max_files] if max_files > 0 else []:
            try:
                os.remove(os.path.join(remote_dir, stale))
            except OSError:
                pass
        return remote_path
    except (OSError, shutil.Error):
        return None


def _overwrite_and_remove(path: str):
    """Overwrite a file with random bytes then delete it (defense-in-depth wipe)."""
    try:
        size = os.path.getsize(path)
        if size > 0:
            with open(path, "r+b") as f:
                remaining = size
                chunk = 65536
                while remaining > 0:
                    n = min(chunk, remaining)
                    f.write(os.urandom(n))
                    remaining -= n
                f.flush()
                os.fsync(f.fileno())
        os.remove(path)
    except OSError:
        pass


def wipe_vault() -> bool:
    """Destroy the vault and all backups, making the data unrecoverable.

    Order matters: the master/duress key files are deleted FIRST so the AES
    ciphertext becomes cryptographically unrecoverable even if a later step
    is interrupted. Remaining files are then overwritten with random data
    and removed as defense-in-depth."""
    for key_file in (MASTER_KEY_FILE, DURESS_KEY_FILE):
        _overwrite_and_remove(key_file)
    for name in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, name)
        if not os.path.isfile(path):
            continue
        if name == ".portable":
            continue
        _overwrite_and_remove(path)
    return True


def wipe_vault_files(db_path: str, key_file: str) -> bool:
    """Destroy only the vault's own files at a custom path (SDK/CLI duress).

    Unlike :func:`wipe_vault` (which clears the whole dedicated data directory), this leaves
    unrelated files in the directory alone — important when ``--vault-dir`` points at a
    shared/synced folder. Keys are removed first (crypto erasure), then the database, its
    WAL/SHM sidecars, backups, and settings."""
    directory = os.path.dirname(os.path.abspath(db_path))
    key_dir = os.path.dirname(os.path.abspath(key_file))
    for key in (key_file, os.path.join(key_dir, ".duress.key")):
        _overwrite_and_remove(key)
    targets = [
        db_path, f"{db_path}-wal", f"{db_path}-shm", f"{db_path}.bak",
        f"{db_path}.sync.json",
        os.path.join(directory, ".app_settings.json"),
        os.path.join(directory, "sync.json"),
    ]
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.startswith("aethervault_") and name.endswith(".db.bak"):
                targets.append(os.path.join(directory, name))
            if name.endswith(".sync.json"):
                targets.append(os.path.join(directory, name))
    for path in targets:
        _overwrite_and_remove(path)
    return True


def load_settings() -> dict:
    """Load application settings from the JSON settings file, falling back to defaults."""
    try:
        with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "lockout_minutes": DEFAULT_LOCKOUT_MINUTES,
            "theme": "dark",
            "remote_backup_dir": "",
        }


def save_settings(settings: dict):
    """Persist application settings to the JSON settings file."""
    try:
        with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        logger.error("Error saving settings: %s", e)
