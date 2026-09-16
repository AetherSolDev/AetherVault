# Created: 2026-09-16
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: aethervault/sdk.py
# Purpose: Programmatic client SDK to unlock and manage a vault without the GUI.

"""Programmatic client SDK for AetherVault.

Unlock a vault with the master password and read/write credential entries from a
script or another application — no PySide6/GUI dependency::

    from aethervault.sdk import Vault

    with Vault().unlock("master-password") as vault:
        for entry in vault.search("github"):
            print(entry.title, entry.username)

The SDK operates on the same on-disk vault as the desktop app
(``data/aethervault.db`` + ``data/.master.key``), so a vault created in the app
opens here and vice-versa. Reuse is deliberate: encryption, migrations, backups,
and CSV import/export all go through the existing ``DatabaseManager`` and
``aethervault.core.engine`` — no logic is duplicated.

Security notes:
    - The master password is verified against the stored PBKDF2 hash; the Fernet
      key is derived from that stored hash, exactly as the GUI does.
    - The duress password is intentionally *not* honoured here: a duress password
      raises :class:`AuthenticationError` instead of wiping the vault, so
      automation can never destroy a vault by accident.
    - Plaintext passwords are only ever held in memory for the lifetime of an
      unlocked :class:`Vault`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Tuple

from aethervault.core.engine import (
    DB_PATH,
    MASTER_KEY_FILE,
    hash_password,
    load_master_password,
    verify_password,
)
from aethervault.core.totp import generate_code, resolve_config
from aethervault.shared.database import DatabaseManager
from aethervault.shared.models import CredentialEntry

__all__ = [
    "Vault",
    "VaultError",
    "VaultNotFoundError",
    "VaultLockedError",
    "AuthenticationError",
    "EntryNotFoundError",
]

logger = logging.getLogger(__name__)

#: Error titles the DatabaseManager raises that are informational during internal
#: recovery flows and must not abort an SDK operation.
_NON_FATAL_ERRORS = frozenset({"Integrity Check", "Export Warning"})

#: Fields searched by :meth:`Vault.search` (case-insensitive substring match).
_SEARCHABLE_FIELDS = ("title", "url", "username", "email", "category", "tags", "notes")


class VaultError(Exception):
    """Base class for every SDK error."""


class VaultNotFoundError(VaultError):
    """Raised when the vault's master key file does not exist."""


class VaultLockedError(VaultError):
    """Raised when an operation requires an unlocked vault."""


class AuthenticationError(VaultError):
    """Raised when the master password is missing or incorrect."""


class EntryNotFoundError(VaultError):
    """Raised when a requested credential entry does not exist."""


class Vault:
    """A programmatic client for a single AetherVault vault.

    Call :meth:`unlock` (or :meth:`create`) before any read/write method. The
    instance is also a context manager and locks itself on exit.
    """

    def __init__(self, db_path: Optional[str] = None, key_file: Optional[str] = None):
        """Point the client at a vault; defaults to the standard app data dir."""
        self.db_path = db_path or DB_PATH
        self.key_file = key_file or MASTER_KEY_FILE
        self._db: Optional[DatabaseManager] = None
        self.last_error: Optional[Tuple[str, str]] = None

    # --- lifecycle ---

    def _handle_error(self, title: str, message: str) -> None:
        """DatabaseManager error callback: log, record, and raise (except recovery)."""
        logger.error("%s: %s", title, message)
        self.last_error = (title, message)
        if title not in _NON_FATAL_ERRORS:
            raise VaultError(f"{title}: {message}")

    @property
    def is_locked(self) -> bool:
        """True when no usable database connection is open."""
        return self._db is None or self._db.conn is None

    def _require_unlocked(self) -> DatabaseManager:
        if self.is_locked:
            raise VaultLockedError("Vault is locked. Call unlock() first.")
        return self._db

    def _open_with(self, stored_hash: str) -> None:
        """Open the database and derive the encryption key from the stored hash."""
        self._db = DatabaseManager(self.db_path, self._handle_error)
        if self._db.conn is None:
            raise VaultError(f"Could not open vault database at {self.db_path}.")
        self._db.set_encryption_key(stored_hash)

    @classmethod
    def create(
        cls,
        password: str,
        db_path: Optional[str] = None,
        key_file: Optional[str] = None,
    ) -> "Vault":
        """Create a new, empty vault protected by ``password`` and return it unlocked."""
        vault = cls(db_path, key_file)
        vault._create(password)
        return vault

    def _create(self, password: str) -> None:
        if not password or len(password) < 8:
            raise VaultError("Master password must be at least 8 characters.")
        if os.path.exists(self.key_file):
            raise VaultError(f"A master key already exists at {self.key_file}.")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.key_file)), exist_ok=True)
            with open(self.key_file, "w", encoding="utf-8") as f:
                f.write(hash_password(password))
        except OSError as e:
            raise VaultError(f"Could not write master key file: {e}") from e
        self._open_with(load_master_password(self.key_file))

    def unlock(self, password: str) -> "Vault":
        """Verify ``password`` and open the vault. Returns ``self`` for chaining."""
        if not os.path.exists(self.key_file):
            raise VaultNotFoundError(f"No master key file at {self.key_file}.")
        stored = load_master_password(self.key_file)
        if not stored or not verify_password(password, stored):
            raise AuthenticationError("Invalid master password.")
        self._open_with(stored)
        return self

    def lock(self) -> None:
        """Close the database connection and drop the derived encryption key."""
        if self._db is not None:
            self._db.__exit__(None, None, None)
        self._db = None

    def __enter__(self) -> "Vault":
        self._require_unlocked()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.lock()

    # --- reads ---

    def list_entries(self) -> List[CredentialEntry]:
        """Return every credential, sorted by title (case-insensitive)."""
        return self._require_unlocked().load_all_credentials()

    def search(self, query: str) -> List[CredentialEntry]:
        """Return entries whose title/url/username/email/category/tags/notes match.

        Matching is a case-insensitive substring test. An empty query returns all
        entries (equivalent to :meth:`list_entries`).
        """
        needle = (query or "").strip().lower()
        if not needle:
            return self.list_entries()
        return [
            entry
            for entry in self.list_entries()
            if any(needle in str(getattr(entry, field, "")).lower()
                   for field in _SEARCHABLE_FIELDS)
        ]

    def get(self, db_id: int) -> CredentialEntry:
        """Return the entry with ``db_id`` or raise :class:`EntryNotFoundError`."""
        for entry in self.list_entries():
            if entry.db_id == db_id:
                return entry
        raise EntryNotFoundError(f"No credential with db_id={db_id}.")

    def find(
        self, title: Optional[str] = None, username: Optional[str] = None
    ) -> Optional[CredentialEntry]:
        """Return the first entry matching ``title`` and/or ``username`` exactly.

        Matching is case-insensitive. Returns None when nothing matches; raises
        :class:`VaultError` when neither argument is supplied.
        """
        wanted_title = (title or "").strip().lower()
        wanted_user = (username or "").strip().lower()
        if not wanted_title and not wanted_user:
            raise VaultError("find() requires a title and/or username.")
        for entry in self.list_entries():
            if wanted_title and entry.title.strip().lower() != wanted_title:
                continue
            if wanted_user and entry.username.strip().lower() != wanted_user:
                continue
            return entry
        return None

    # --- writes ---

    def add(self, **fields: Any) -> int:
        """Create a credential from ``fields`` and return its new ``db_id``.

        ``title`` is required; every other :class:`CredentialEntry` field is
        optional. ``password`` defaults to an empty string.
        """
        db = self._require_unlocked()
        if not str(fields.get("title", "")).strip():
            raise VaultError("A credential requires a non-empty 'title'.")
        entry = CredentialEntry()
        for key in fields:
            if not hasattr(entry, key):
                raise VaultError(f"Unknown credential field: {key}")
        new_id = db.save_credential(CredentialEntry(**fields))
        if new_id is None:
            raise VaultError("Failed to save credential.")
        return new_id

    def update(self, db_id: int, **fields: Any) -> CredentialEntry:
        """Apply ``fields`` to an existing entry and return the updated entry."""
        db = self._require_unlocked()
        entry = self.get(db_id)
        for key, value in fields.items():
            if not hasattr(entry, key):
                raise VaultError(f"Unknown credential field: {key}")
            setattr(entry, key, value)
        db.update_credential(entry)
        return entry

    def delete(self, db_id: int) -> None:
        """Delete the entry with ``db_id``, or raise :class:`EntryNotFoundError`."""
        self._require_unlocked()
        self.get(db_id)
        self._db.delete_credential(db_id)

    def totp_code(self, db_id: int) -> str:
        """Return the current TOTP code for ``db_id`` (RFC 6238).

        Raises :class:`VaultError` when the entry has no TOTP secret configured.
        """
        entry = self.get(db_id)
        if not entry.totp_secret:
            raise VaultError(f"Entry {db_id} has no TOTP secret.")
        config = resolve_config(entry.totp_secret)
        return generate_code(
            config["secret"], digits=config["digits"],
            period=config["period"], algorithm=config["algorithm"],
        )

    # --- maintenance ---

    def backup(self) -> Optional[str]:
        """Create a timestamped vault backup and return its path (or None)."""
        return self._require_unlocked().create_pre_op_backup("SDK backup")

    def export_csv(self, file_path: str) -> int:
        """Write all entries to ``file_path`` as CSV; returns the row count."""
        return self._require_unlocked().export_to_csv(file_path, self.list_entries())

    def import_csv(self, file_path: str) -> int:
        """Import entries from a CSV file; returns the count inserted."""
        return self._require_unlocked().import_from_csv(file_path)
