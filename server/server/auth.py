# Created: 2026-09-16
# Last Edited: 2026-09-16 12:36 CT (America/Chicago)
# Path: server/auth.py
# Purpose: Token and enrollment-secret helpers for the sync relay.

"""Token and enrollment-secret helpers for the relay.

Device tokens are random and only ever stored as SHA-256 hashes, so a relay DB
leak does not expose usable tokens. The enrollment secret is compared in constant
time.
"""

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    """Return a new random device token (URL-safe)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the hex SHA-256 of a token, for at-rest storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def secret_matches(provided: str, expected: str) -> bool:
    """Constant-time comparison of the enrollment secret."""
    if not expected:
        return False
    return hmac.compare_digest(
        (provided or "").encode("utf-8"), expected.encode("utf-8")
    )
