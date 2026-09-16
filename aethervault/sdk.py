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
import uuid
from typing import Any, Dict, List, Optional, Tuple

from aethervault.core.engine import (
    DB_PATH,
    MASTER_KEY_FILE,
    hash_password,
    load_master_password,
    verify_password,
    wipe_vault_files,
)
from aethervault.core.sync import (
    HLC,
    KDF_ITERATIONS,
    RelayClient,
    RelayError,
    SyncConfig,
    derive_kek,
    encrypt_record,
    entry_to_payload,
    new_data_key,
    new_kdf_salt,
    record_to_apply,
    unwrap_data_key,
    wrap_data_key,
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
        self._master_password: str = ""
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
        self._master_password = password

    def unlock(self, password: str, allow_duress_wipe: bool = False) -> "Vault":
        """Verify ``password`` and open the vault. Returns ``self`` for chaining.

        With ``allow_duress_wipe=True`` (used by the CLI), entering the duress password
        destroys **only this vault's local files** and raises ``AuthenticationError`` — the
        same error as a wrong password. Nothing is pushed to sync, so the hub and every other
        device are unaffected.
        """
        if not os.path.exists(self.key_file):
            raise VaultNotFoundError(f"No master key file at {self.key_file}.")
        if allow_duress_wipe:
            duress_file = os.path.join(os.path.dirname(self.key_file), ".duress.key")
            duress_hash = load_master_password(duress_file)
            if duress_hash and verify_password(password, duress_hash):
                wipe_vault_files(self.db_path, self.key_file)
                raise AuthenticationError("Invalid master password.")
        stored = load_master_password(self.key_file)
        if not stored or not verify_password(password, stored):
            raise AuthenticationError("Invalid master password.")
        self._open_with(stored)
        self._master_password = password
        return self

    def lock(self) -> None:
        """Close the database connection and drop the derived encryption key."""
        if self._db is not None:
            self._db.__exit__(None, None, None)
        self._db = None
        self._master_password = ""

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

    def sync(self, server_url: str = "", token: str = "", device_id: str = "",
             max_retries: int = 5) -> Dict[str, int]:
        """Pull remote changes, merge, and push local changes to the relay.

        Requires the vault to have been set up (:meth:`setup_sync`) or enrolled
        (:meth:`enroll_sync`). Returns ``{"pulled", "pushed", "server_rev"}``.
        """
        db = self._require_unlocked()
        if not self._master_password:
            raise VaultError("The master password is required to sync.")
        config = self._sync_config()
        cfg = config.load()
        if not cfg:
            raise VaultError("This vault is not configured for sync.")
        client = RelayClient(cfg["relay_url"], cfg.get("token", ""))
        data_key = self._unwrap_data_key(client)
        hlc = HLC(cfg["device_id"], cfg.get("hlc_last", ""))
        db.rev_provider = hlc.next

        records, server_rev = client.pull(int(cfg.get("last_server_rev", 0)))
        local_revs = {e.entry_uuid: e.sync_rev
                      for e in db.load_all_credentials(include_deleted=True)}
        to_apply = []
        for rec in records:
            hlc.observe(rec.get("rev", ""))
            if str(rec.get("rev", "")) > str(local_revs.get(rec["uuid"], "")):
                to_apply.append(record_to_apply(rec, data_key))
        if to_apply:
            db.apply_sync_records(to_apply)

        pushed = self._build_records(db, data_key, hlc, cfg["vault_id"], cfg["device_id"])
        applied, push_rev = client.push(pushed)
        cfg.update({"last_server_rev": max(server_rev, push_rev), "hlc_last": hlc.last_rev})
        config.save(cfg)
        return {"pulled": len(to_apply), "pushed": applied,
                "server_rev": cfg["last_server_rev"]}

    def setup_sync(self, relay_url: str, enroll_secret: str,
                   device_name: str = "") -> Dict[str, Any]:
        """Create the vault on the relay and enroll THIS device (first device)."""
        db = self._require_unlocked()
        if not self._master_password:
            raise VaultError("The master password is required to set up sync.")
        config = self._sync_config()
        if config.load():
            raise VaultError("This vault is already configured for sync.")
        data_key = new_data_key()
        kdf_salt = new_kdf_salt()
        wrapped = wrap_data_key(data_key, derive_kek(self._master_password, kdf_salt))
        vault_id = str(uuid.uuid4())
        client = RelayClient(relay_url)
        client.create_vault(vault_id, kdf_salt, wrapped, enroll_secret)
        enrolled = client.enroll(device_name, enroll_secret)
        device_id, token = enrolled["device_id"], enrolled["token"]
        client = RelayClient(relay_url, token)
        hlc = HLC(device_id)
        db.rev_provider = hlc.next
        records = self._build_records(db, data_key, hlc, vault_id, device_id)
        _applied, server_rev = client.push(records)
        config.save({"relay_url": relay_url, "vault_id": vault_id, "device_id": device_id,
                     "token": token, "last_server_rev": server_rev, "hlc_last": hlc.last_rev})
        return {"vault_id": vault_id, "device_id": device_id, "pushed": len(records)}

    def enroll_sync(self, relay_url: str, enroll_secret: str,
                    device_name: str = "") -> Dict[str, Any]:
        """Enroll THIS device into an existing relay vault, then pull and push."""
        db = self._require_unlocked()
        if not self._master_password:
            raise VaultError("The master password is required to enroll.")
        config = self._sync_config()
        if config.load():
            raise VaultError("This vault is already configured for sync.")
        client = RelayClient(relay_url)
        enrolled = client.enroll(device_name, enroll_secret)
        device_id, token = enrolled["device_id"], enrolled["token"]
        client = RelayClient(relay_url, token)
        data_key = self._unwrap_data_key(client)
        hlc = HLC(device_id)
        db.rev_provider = hlc.next

        records, server_rev = client.pull(0)
        applied = [record_to_apply(r, data_key) for r in records]
        for rec in records:
            hlc.observe(rec.get("rev", ""))
        if applied:
            db.apply_sync_records(applied)

        vault_id = enrolled.get("vault_id", "")
        pushed = self._build_records(db, data_key, hlc, vault_id, device_id)
        applied_push, push_rev = client.push(pushed)
        config.save({"relay_url": relay_url, "vault_id": vault_id, "device_id": device_id,
                     "token": token, "last_server_rev": max(server_rev, push_rev),
                     "hlc_last": hlc.last_rev})
        return {"device_id": device_id, "pulled": len(applied), "pushed": applied_push}

    def sync_devices(self) -> List[Dict[str, Any]]:
        """List devices enrolled on the relay."""
        cfg = self._sync_config().load()
        if not cfg:
            raise VaultError("This vault is not configured for sync.")
        return RelayClient(cfg["relay_url"], cfg.get("token", "")).devices()

    def sync_revoke(self, device_id: str) -> None:
        """Revoke another enrolled device on the relay."""
        cfg = self._sync_config().load()
        if not cfg:
            raise VaultError("This vault is not configured for sync.")
        RelayClient(cfg["relay_url"], cfg.get("token", "")).revoke(device_id)

    def _sync_config(self) -> SyncConfig:
        return SyncConfig(self.db_path)

    def _unwrap_data_key(self, client: RelayClient) -> bytes:
        meta = client.vault_meta()
        kek = derive_kek(self._master_password, meta["kdf_salt"],
                         int(meta.get("kdf_iterations", KDF_ITERATIONS)))
        return unwrap_data_key(meta["wrapped_master"], kek)

    def _build_records(self, db, data_key, hlc, vault_id, device_id) -> List[Dict]:
        records = []
        for entry in db.load_all_credentials(include_deleted=True):
            rev = entry.sync_rev or hlc.next()
            if not entry.sync_rev:
                db.set_sync_rev(entry.db_id, rev)
            records.append({
                "uuid": entry.entry_uuid,
                "vault_id": vault_id,
                "device_id": device_id,
                "rev": rev,
                "deleted": bool(int(entry.deleted or 0)),
                "deleted_at": "",
                "updated_at": entry.modified_at or "",
                "payload": encrypt_record(entry_to_payload(entry), data_key),
            })
        return records
