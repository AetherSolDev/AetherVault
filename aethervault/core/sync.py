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
from typing import Dict, List

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from aethervault.core.engine import decrypt_data, encrypt_data

__all__ = [
    "SYNC_FIELDS",
    "SYNC_PAYLOAD_VERSION",
    "build_payload",
    "decrypt_payload",
    "derive_sync_key",
    "encrypt_payload",
    "entry_to_record",
    "merge_records",
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


def derive_sync_key(master_password_hash: str) -> bytes:
    """Derive a Fernet key for sync payloads (separate from the local encryption key)."""
    if not master_password_hash:
        raise ValueError("Master password hash cannot be empty for sync key derivation.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SYNC_SALT,
        iterations=SYNC_KDF_ITERATIONS,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password_hash.encode("utf-8")))


def entry_to_record(entry) -> Dict:
    """Convert a CredentialEntry into a plain sync record."""
    data = entry.to_dict()
    return {field: data.get(field) for field in SYNC_FIELDS}


def build_payload(entries) -> Dict:
    """Build a sync payload dict from a list of CredentialEntry objects."""
    return {
        "version": SYNC_PAYLOAD_VERSION,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "entries": [entry_to_record(e) for e in entries],
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
