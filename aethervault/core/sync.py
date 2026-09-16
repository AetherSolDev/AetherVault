# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: aethervault/core/sync.py
# Purpose: Relay-aligned sync core — key wrapping, HLC revisions, record payloads, merge.

"""Relay-aligned sync core.

The relay (`server/`) is a zero-knowledge, **record-level** delta service:

* it stores the vault's *wrapped* data key + KDF params (so a new device can bootstrap),
  opaque per-record ``payload`` ciphertext, and hashed device tokens;
* record merge is last-write-wins by the client's HLC ``rev`` (compared as a string);
* clients pull deltas with ``GET /v1/changes?since=N`` and push with ``POST /v1/changes``.

Key model: a random 32-byte **data key** encrypts record payloads. It is wrapped with a KEK
derived from the master password (PBKDF2 + a stored salt) and kept on the relay, so changing
the password only re-wraps the key. A new device enrolls (enrollment secret), fetches
``/v1/vault/meta``, derives the KEK from the password, and unwraps the data key.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from aethervault.core.engine import decrypt_data, encrypt_data

__all__ = [
    "HLC",
    "KDF_ALGORITHM",
    "KDF_ITERATIONS",
    "RelayClient",
    "RelayError",
    "SyncConfig",
    "decrypt_record",
    "derive_kek",
    "encrypt_record",
    "entry_to_payload",
    "merge_records",
    "new_data_key",
    "new_kdf_salt",
    "record_to_apply",
    "unwrap_data_key",
    "wrap_data_key",
]

SYNC_FORMAT_VERSION = 1
KDF_ALGORITHM = "pbkdf2-sha256"
KDF_ITERATIONS = 480000

#: Entry fields carried inside an encrypted record payload (record-level uuid/rev/deleted
#: live on the record itself, not in the payload).
PAYLOAD_FIELDS = (
    "title", "url", "username", "email", "password", "phone", "address",
    "category", "notes", "tags", "custom_fields", "totp_secret", "recovery_codes",
    "parent_id", "created_at", "time_last_used", "time_password_changed",
)


# --------------------------------------------------------------------------- #
# Key wrapping
# --------------------------------------------------------------------------- #

def new_data_key() -> bytes:
    """Generate a new random Fernet data key for record payloads."""
    return Fernet.generate_key()


def new_kdf_salt() -> str:
    """Generate a fresh base64 KDF salt."""
    return base64.b64encode(os.urandom(16)).decode("ascii")


def derive_kek(password: str, kdf_salt: str, iterations: int = KDF_ITERATIONS) -> bytes:
    """Derive a key-encryption key from the master password and the relay's KDF salt."""
    if not password:
        raise ValueError("Master password cannot be empty.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=base64.b64decode(kdf_salt),
        iterations=iterations,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def wrap_data_key(data_key: bytes, kek: bytes) -> str:
    """Encrypt the data key with the KEK, returning an opaque string."""
    return Fernet(kek).encrypt(data_key).decode("ascii")


def unwrap_data_key(wrapped: str, kek: bytes) -> bytes:
    """Recover the data key from its wrapped form, raising ValueError on a bad KEK."""
    try:
        return Fernet(kek).decrypt(wrapped.encode("ascii"))
    except (InvalidToken, ValueError, TypeError) as e:
        raise ValueError("Could not unwrap the data key (wrong password?).") from e


# --------------------------------------------------------------------------- #
# Record payloads
# --------------------------------------------------------------------------- #

def entry_to_payload(entry) -> Dict:
    """Return the plaintext payload dict for a CredentialEntry."""
    data = entry.to_dict()
    return {field: data.get(field) for field in PAYLOAD_FIELDS}


def encrypt_record(payload: Dict, data_key: bytes) -> str:
    """Encrypt a payload dict to an opaque ciphertext string."""
    return encrypt_data(json.dumps(payload, separators=(",", ":"), sort_keys=True), data_key)


def decrypt_record(payload: str, data_key: bytes) -> Dict:
    """Decrypt a record payload string back to a dict."""
    text = decrypt_data(payload, data_key)
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError("Invalid record payload (wrong key or corrupt data).") from e
    if not isinstance(result, dict):
        raise ValueError("Malformed record payload.")
    return result


def record_to_apply(record: Dict, data_key: bytes) -> Dict:
    """Convert a relay record into a dict for ``DatabaseManager.apply_sync_records``."""
    fields = {field: "" for field in PAYLOAD_FIELDS}
    if not record.get("deleted"):
        fields.update(decrypt_record(record["payload"], data_key))
    return {
        **fields,
        "entry_uuid": record["uuid"],
        "deleted": 1 if record.get("deleted") else 0,
        "sync_rev": record.get("rev", ""),
        "modified_at": record.get("updated_at") or "",
    }


def merge_records(local: List[Dict], remote: List[Dict]) -> List[Dict]:
    """Merge relay records by ``uuid``, keeping the highest ``rev`` (string compare)."""
    by_uuid: Dict[str, Dict] = {}
    for record in list(local) + list(remote):
        uuid = record.get("uuid")
        if not uuid:
            continue
        current = by_uuid.get(uuid)
        if current is None or str(record.get("rev", "")) > str(current.get("rev", "")):
            by_uuid[uuid] = record
    return list(by_uuid.values())


# --------------------------------------------------------------------------- #
# Hybrid logical clock
# --------------------------------------------------------------------------- #

class HLC:
    """A monotonic, string-sortable revision clock: ``<millis:016d>:<counter:06d>:<device>``."""

    def __init__(self, device_id: str, last_rev: str = ""):
        self.device_id = device_id or "device"
        self.last_millis = 0
        self.counter = 0
        self.last_rev = last_rev
        if last_rev:
            self.observe(last_rev)

    def observe(self, rev: str) -> None:
        """Advance the clock past a remote ``rev`` (standard HLC receive)."""
        try:
            millis_s, counter_s, _ = rev.split(":", 2)
            millis, counter = int(millis_s), int(counter_s)
        except (ValueError, AttributeError):
            return
        if millis > self.last_millis:
            self.last_millis = millis
            self.counter = counter
        elif millis == self.last_millis and counter > self.counter:
            self.counter = counter

    def next(self) -> str:
        """Return a new revision string greater than any previously issued one."""
        now = int(time.time() * 1000)
        if now > self.last_millis:
            self.last_millis = now
            self.counter = 0
        else:
            self.counter += 1
        self.last_rev = f"{self.last_millis:016d}:{self.counter:06d}:{self.device_id}"
        return self.last_rev


# --------------------------------------------------------------------------- #
# Relay client
# --------------------------------------------------------------------------- #

class RelayError(Exception):
    """Raised for relay transport or authentication failures."""


class RelayClient:
    """HTTP client for the AetherVault sync relay."""

    def __init__(self, base_url: str, token: str = "", timeout: int = 20):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Optional[dict] = None,
                 enroll_secret: str = "") -> Tuple[int, dict]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if enroll_secret:
            req.add_header("X-Enroll-Secret", enroll_secret)
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
            raise RelayError(f"Cannot reach the sync relay at {self.base_url}: {e}") from e

    def _ok(self, method: str, path: str, body: Optional[dict] = None,
            enroll_secret: str = "") -> dict:
        status, payload = self._request(method, path, body, enroll_secret)
        if status >= 400:
            raise RelayError(f"{method} {path} failed (HTTP {status}): "
                             f"{payload.get('detail', payload.get('error', 'unknown'))}")
        return payload

    def health(self) -> bool:
        status, _ = self._request("GET", "/healthz")
        return status == 200

    def create_vault(self, vault_id: str, kdf_salt: str, wrapped_master: str,
                     enroll_secret: str, iterations: int = KDF_ITERATIONS) -> dict:
        return self._ok("POST", "/v1/vault", {
            "vault_id": vault_id,
            "format_version": SYNC_FORMAT_VERSION,
            "kdf_algorithm": KDF_ALGORITHM,
            "kdf_iterations": iterations,
            "kdf_salt": kdf_salt,
            "wrapped_master": wrapped_master,
        }, enroll_secret=enroll_secret)

    def enroll(self, device_name: str, enroll_secret: str) -> dict:
        return self._ok("POST", "/v1/enroll", {"device_name": device_name},
                        enroll_secret=enroll_secret)

    def vault_meta(self) -> dict:
        return self._ok("GET", "/v1/vault/meta")

    def pull(self, since: int = 0) -> Tuple[List[dict], int]:
        payload = self._ok("GET", f"/v1/changes?since={int(since)}")
        return payload.get("records", []), int(payload.get("server_rev", 0))

    def push(self, records: List[dict]) -> Tuple[int, int]:
        payload = self._ok("POST", "/v1/changes", {"records": records})
        return int(payload.get("applied", 0)), int(payload.get("server_rev", 0))

    def devices(self) -> List[dict]:
        return self._ok("GET", "/v1/devices").get("devices", [])

    def revoke(self, device_id: str) -> None:
        self._ok("DELETE", f"/v1/devices/{device_id}")


# --------------------------------------------------------------------------- #
# Local sync config (sync.json beside the vault)
# --------------------------------------------------------------------------- #

class SyncConfig:
    """Persisted per-device sync state, stored as ``<db_path>.sync.json``.

    Duress wipes this file (``engine.wipe_vault_files`` deletes it), which detaches the device
    without touching the relay or other devices. It is keyed on the vault's database path so
    multiple vaults in one directory do not collide.
    """

    def __init__(self, db_path: str):
        self.path = f"{db_path}.sync.json"

    def load(self) -> Optional[dict]:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def save(self, config: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def delete(self) -> None:
        try:
            os.remove(self.path)
        except OSError:
            pass
