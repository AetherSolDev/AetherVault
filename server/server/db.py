# Created: 2026-09-16
# Last Edited: 2026-09-16 12:36 CT (America/Chicago)
# Path: server/db.py
# Purpose: SQLite schema and data access for the zero-knowledge sync relay.

"""SQLite storage for the AetherVault sync relay.

The relay is single-vault and zero-knowledge: it stores the vault's *wrapped*
key + KDF parameters (so a new device can bootstrap), opaque record payloads, and
device token hashes. It can never decrypt a record.

Design notes:
- One writer at a time (a process-level lock in the app) + WAL; this is a
  personal relay, not a multi-tenant service.
- ``server_seq`` is a per-vault monotonic counter that gives clients a cheap
  incremental-pull cursor (``since``).
- Record merge is last-write-wins by the client's HLC ``rev`` (string compare).
"""

import sqlite3
import uuid as uuid_module
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vaults (
    vault_id       TEXT PRIMARY KEY,
    format_version INTEGER NOT NULL,
    kdf_algorithm  TEXT NOT NULL,
    kdf_iterations INTEGER NOT NULL,
    kdf_salt       TEXT NOT NULL,
    wrapped_master TEXT NOT NULL,
    server_seq     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    device_id  TEXT PRIMARY KEY,
    vault_id   TEXT NOT NULL,
    name       TEXT NOT NULL DEFAULT '',
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_seen  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS records (
    vault_id   TEXT NOT NULL,
    uuid       TEXT NOT NULL,
    server_rev INTEGER NOT NULL,
    rev        TEXT NOT NULL,
    device_id  TEXT NOT NULL DEFAULT '',
    deleted    INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    payload    TEXT NOT NULL,
    PRIMARY KEY (vault_id, uuid)
);

CREATE INDEX IF NOT EXISTS idx_records_cursor ON records (vault_id, server_rev);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    """Open a WAL-mode connection with named-column access."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str) -> None:
    """Create the relay tables if they do not exist."""
    conn = connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# --- Vault ---

def get_vault(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM vaults LIMIT 1").fetchone()


def create_vault(
    conn: sqlite3.Connection,
    vault_id: str,
    format_version: int,
    kdf_algorithm: str,
    kdf_iterations: int,
    kdf_salt: str,
    wrapped_master: str,
) -> None:
    conn.execute(
        """
        INSERT INTO vaults
            (vault_id, format_version, kdf_algorithm, kdf_iterations, kdf_salt,
             wrapped_master, server_seq, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (vault_id, format_version, kdf_algorithm, kdf_iterations, kdf_salt,
         wrapped_master, utcnow()),
    )
    conn.commit()


# --- Devices ---

def create_device(
    conn: sqlite3.Connection, vault_id: str, name: str, token_hash: str
) -> str:
    device_id = str(uuid_module.uuid4())
    conn.execute(
        """
        INSERT INTO devices (device_id, vault_id, name, token_hash, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?, '')
        """,
        (device_id, vault_id, name, token_hash, utcnow()),
    )
    conn.commit()
    return device_id


def get_device_by_token(conn: sqlite3.Connection, token_hash: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM devices WHERE token_hash = ?", (token_hash,)
    ).fetchone()


def touch_device(conn: sqlite3.Connection, device_id: str) -> None:
    conn.execute("UPDATE devices SET last_seen = ? WHERE device_id = ?", (utcnow(), device_id))
    conn.commit()


def list_devices(conn: sqlite3.Connection, vault_id: str) -> List[Dict[str, object]]:
    rows = conn.execute(
        "SELECT device_id, name, created_at, last_seen FROM devices WHERE vault_id = ?"
        " ORDER BY created_at",
        (vault_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def delete_device(conn: sqlite3.Connection, vault_id: str, device_id: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM devices WHERE vault_id = ? AND device_id = ?", (vault_id, device_id)
    )
    conn.commit()
    return cursor.rowcount > 0


# --- Records ---

def pull_records(
    conn: sqlite3.Connection, vault_id: str, since: int
) -> Tuple[List[Dict[str, object]], int]:
    """Return records changed after ``since`` plus the current server sequence."""
    seq = conn.execute(
        "SELECT server_seq FROM vaults WHERE vault_id = ?", (vault_id,)
    ).fetchone()
    server_rev = int(seq["server_seq"]) if seq else 0
    rows = conn.execute(
        """
        SELECT uuid, vault_id, device_id, rev, deleted, deleted_at, updated_at, payload
        FROM records
        WHERE vault_id = ? AND server_rev > ?
        ORDER BY server_rev ASC
        """,
        (vault_id, since),
    ).fetchall()
    records = [
        {
            "uuid": row["uuid"],
            "vault_id": row["vault_id"],
            "device_id": row["device_id"],
            "rev": row["rev"],
            "deleted": bool(row["deleted"]),
            "deleted_at": row["deleted_at"],
            "updated_at": row["updated_at"],
            "payload": row["payload"],
        }
        for row in rows
    ]
    return records, server_rev


def push_records(
    conn: sqlite3.Connection, vault_id: str, records: List[Dict[str, object]]
) -> Tuple[int, int]:
    """Apply records with last-write-wins by ``rev``. Returns (applied, server_rev)."""
    row = conn.execute(
        "SELECT server_seq FROM vaults WHERE vault_id = ?", (vault_id,)
    ).fetchone()
    seq = int(row["server_seq"]) if row else 0
    applied = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for record in records:
            existing = conn.execute(
                "SELECT rev FROM records WHERE vault_id = ? AND uuid = ?",
                (vault_id, record["uuid"]),
            ).fetchone()
            if existing is not None and not (record["rev"] > existing["rev"]):
                continue
            seq += 1
            applied += 1
            conn.execute(
                """
                INSERT OR REPLACE INTO records
                    (vault_id, uuid, server_rev, rev, device_id, deleted,
                     deleted_at, updated_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vault_id,
                    record["uuid"],
                    seq,
                    record["rev"],
                    record.get("device_id", ""),
                    int(bool(record.get("deleted", False))),
                    record.get("deleted_at", ""),
                    record.get("updated_at", ""),
                    record["payload"],
                ),
            )
        if applied:
            conn.execute(
                "UPDATE vaults SET server_seq = ? WHERE vault_id = ?", (seq, vault_id)
            )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    return applied, seq
