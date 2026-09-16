# Created: 2026-09-16
# Last Edited: 2026-09-16 17:53 CT (America/Chicago)
# Path: aethervault/core/sync.py
# Purpose: Offline-first sync core — encrypted payloads and per-entry LWW merge.

"""Sync core: encrypted payloads and per-entry last-writer-wins merge.

Design (zero-knowledge): a client builds a payload of its entries, **encrypts it with a key
derived from the master password hash**, and hands the ciphertext to a sync server. The
server only ever stores ciphertext. Merging happens client-side after decrypt.

Entries are matched by their stable ``entry_uuid`` (not ``db_id``, which is per-vault) and
resolved last-writer-wins on ``modified_at``. Deletions are tombstones (``deleted=1``) so a
removal on one device is not resurrected by an older copy on another.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from aethervault.core.engine import decrypt_data, encrypt_data

__all__ = [
    "SYNC_FIELDS",
    "SYNC_PAYLOAD_VERSION",
    "SyncClient",
    "SyncError",
    "build_payload",
    "decrypt_payload",
    "derive_sync_key",
    "encrypt_payload",
    "entry_to_record",
    "merge_records",
    "payload_from_records",
]

#: Distinct KDF salt so the sync key differs from the local encryption key.
SYNC_SALT = b"aethervault_sync_key_salt_v1"
SYNC_KDF_ITERATIONS = 480000
SYNC_PAYLOAD_VERSION = 1

#: Entry fields carried in a sync payload (``db_id`` is deliberately excluded — it is
#: per-vault; ``entry_uuid`` is the stable cross-device identifier).
SYNC_FIELDS = (
    "entry_uuid", "title", "url", "username", "email", "password", "phone",
    "address", "category", "notes", "tags", "custom_fields",
    "totp_secret", "recovery_codes", "parent_id",
    "created_at", "modified_at", "time_last_used", "time_password_changed",
    "deleted",
)


def derive_sync_key(master_password: str) -> bytes:
    """Derive a Fernet key for sync payloads from the master password.

    Uses a distinct KDF salt (deliberately **not** the per-vault stored hash, which is salted
    randomly), so every device sharing the same master password derives the same sync key and
    can decrypt each other's payloads — while the server, which never sees the password,
    cannot.
    """
    if not master_password:
        raise ValueError("Master password cannot be empty for sync key derivation.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SYNC_SALT,
        iterations=SYNC_KDF_ITERATIONS,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def entry_to_record(entry) -> Dict:
    """Convert a CredentialEntry into a plain sync record."""
    data = entry.to_dict()
    return {field: data.get(field) for field in SYNC_FIELDS}


def build_payload(entries) -> Dict:
    """Build a sync payload dict from a list of CredentialEntry objects."""
    return payload_from_records([entry_to_record(e) for e in entries])


def payload_from_records(records) -> Dict:
    """Wrap a list of sync records into a payload dict."""
    return {
        "version": SYNC_PAYLOAD_VERSION,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "entries": list(records),
    }


def encrypt_payload(payload: Dict, key: bytes) -> str:
    """Encrypt a sync payload dict to an opaque ciphertext token."""
    return encrypt_data(json.dumps(payload, separators=(",", ":"), sort_keys=True), key)


def decrypt_payload(token: str, key: bytes) -> Dict:
    """Decrypt a sync payload token back to a dict, raising ValueError on bad input."""
    text = decrypt_data(token, key)
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError("Invalid sync payload (wrong key or corrupt data).") from e
    if not isinstance(payload, dict) or "entries" not in payload:
        raise ValueError("Malformed sync payload.")
    return payload


def _wins(a: Dict, b: Dict) -> bool:
    """Return True if record ``a`` should win over ``b`` (LWW on modified_at)."""
    ta, tb = str(a.get("modified_at") or ""), str(b.get("modified_at") or "")
    if ta != tb:
        return ta > tb
    # Tie-break: a tombstone wins over a concurrent edit so entries are not resurrected.
    return bool(a.get("deleted")) and not bool(b.get("deleted"))


def merge_records(local: List[Dict], remote: List[Dict]) -> List[Dict]:
    """Merge two lists of sync records by ``entry_uuid``, last-writer-wins.

    Records without an ``entry_uuid`` are skipped (cannot be merged safely).
    """
    by_uuid: Dict[str, Dict] = {}
    for record in list(local) + list(remote):
        uuid = record.get("entry_uuid")
        if not uuid:
            continue
        current = by_uuid.get(uuid)
        if current is None or _wins(record, current):
            by_uuid[uuid] = record
    return list(by_uuid.values())


class SyncError(Exception):
    """Raised for sync transport or authentication failures."""


class SyncClient:
    """Minimal HTTP client for the AetherVault sync server."""

    def __init__(self, base_url: str, token: str = "", timeout: int = 15):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.timeout = timeout

    def _request(self, method: str, path: str,
                 body: Optional[dict] = None) -> Tuple[int, dict]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b"{}")
            except (json.JSONDecodeError, ValueError):
                payload = {}
            return e.code, payload
        except (urllib.error.URLError, OSError) as e:
            raise SyncError(f"Cannot reach sync server at {self.base_url}: {e}") from e

    def pull(self) -> Tuple[int, Optional[str]]:
        """Return ``(version, ciphertext_or_None)`` from the server."""
        status, body = self._request("GET", "/vault")
        if status != 200:
            raise SyncError(f"Pull failed (HTTP {status}): {body.get('error', 'unknown')}")
        return int(body.get("version", 0)), body.get("payload")

    def push(self, base_version: int, payload: str,
             device_id: str = "") -> Tuple[bool, int, Optional[str]]:
        """Push ciphertext. Returns ``(ok, version, current_payload_on_conflict)``."""
        status, body = self._request("POST", "/vault", {
            "base_version": base_version, "payload": payload, "device_id": device_id,
        })
        if status == 200:
            return True, int(body.get("version", 0)), payload
        if status == 409:
            return False, int(body.get("version", 0)), body.get("payload")
        raise SyncError(f"Push failed (HTTP {status}): {body.get('error', 'unknown')}")
