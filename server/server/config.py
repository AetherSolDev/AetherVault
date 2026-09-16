# Created: 2026-09-16
# Last Edited: 2026-09-16 12:36 CT (America/Chicago)
# Path: server/config.py
# Purpose: Environment-driven configuration for the AetherVault sync relay.

"""Configuration for the AetherVault sync relay.

Everything is environment-driven so the same image runs anywhere. The only
secret the relay holds is the enrollment secret (never the vault key or master
password — the relay is zero-knowledge).
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    data_dir: str
    db_path: str
    enroll_secret: str
    host: str
    port: int
    max_payload_bytes: int
    max_records_per_push: int

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = os.environ.get("AETHERVAULT_DATA_DIR", "/data")
        return cls(
            data_dir=data_dir,
            db_path=os.environ.get(
                "AETHERVAULT_DB_PATH", os.path.join(data_dir, "relay.db")
            ),
            enroll_secret=os.environ.get("AETHERVAULT_ENROLL_SECRET", ""),
            host=os.environ.get("AETHERVAULT_HOST", "127.0.0.1"),
            port=int(os.environ.get("AETHERVAULT_PORT", "8787")),
            max_payload_bytes=int(
                os.environ.get("AETHERVAULT_MAX_PAYLOAD_BYTES", str(256 * 1024))
            ),
            max_records_per_push=int(
                os.environ.get("AETHERVAULT_MAX_RECORDS_PER_PUSH", "1000")
            ),
        )

    @property
    def enrollment_enabled(self) -> bool:
        return bool(self.enroll_secret)
