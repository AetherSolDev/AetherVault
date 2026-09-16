# Created: 2026-09-16
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: aethervault/core/totp.py
# Purpose: RFC 6238 TOTP generation/verification and otpauth:// parsing (pure stdlib).
"""RFC 6238 TOTP (time-based one-time passwords) and ``otpauth://`` parsing.

Pure standard library (``hmac``/``hashlib``/``base64``/``struct``/``secrets``) — no
new dependencies. This is the business-logic layer for AetherVault's built-in
authenticator feature; it has no UI imports and is fully testable headlessly.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

__all__ = [
    "generate_code",
    "generate_secret",
    "parse_otpauth",
    "resolve_config",
    "verify_code",
]

_ALGORITHMS = {
    "SHA1": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA512": hashlib.sha512,
}

DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30
DEFAULT_ALGORITHM = "SHA1"
DEFAULT_SECRET_BYTES = 20  # 160 bits -> 32 base32 characters


def _decode_secret(secret: str) -> bytes:
    """Decode a base32 TOTP secret, tolerating spaces, lowercase, and missing padding."""
    normalized = (secret or "").strip().replace(" ", "").upper()
    if not normalized:
        raise ValueError("TOTP secret cannot be empty.")
    padded = normalized + "=" * (-len(normalized) % 8)
    try:
        return base64.b32decode(padded, casefold=True)
    except ValueError as e:  # binascii.Error subclasses ValueError
        raise ValueError("Invalid base32 TOTP secret.") from e


def _hotp(key: bytes, counter: int, digits: int, algorithm: str) -> str:
    """Compute an HOTP value (RFC 4226) for the given counter."""
    mac = hmac.new(key, struct.pack(">Q", counter), _ALGORITHMS[algorithm]).digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def _validate(digits: int, period: int, algorithm: str) -> str:
    """Validate TOTP parameters, returning the normalized (upper-case) algorithm."""
    if not 6 <= digits <= 10:
        raise ValueError("TOTP 'digits' must be between 6 and 10.")
    if period <= 0:
        raise ValueError("TOTP 'period' must be a positive number of seconds.")
    algo = (algorithm or DEFAULT_ALGORITHM).upper()
    if algo not in _ALGORITHMS:
        raise ValueError(f"Unsupported TOTP algorithm: {algorithm!r}.")
    return algo


def generate_code(
    secret: str,
    timestamp: Optional[float] = None,
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_PERIOD,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """Return the TOTP code for ``secret`` at ``timestamp`` (defaults to now)."""
    algo = _validate(digits, period, algorithm)
    key = _decode_secret(secret)
    ts = time.time() if timestamp is None else timestamp
    return _hotp(key, int(ts) // period, digits, algo)


def verify_code(
    secret: str,
    code: str,
    timestamp: Optional[float] = None,
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_PERIOD,
    algorithm: str = DEFAULT_ALGORITHM,
    skew: int = 1,
) -> bool:
    """Return True if ``code`` matches the current (or ±``skew`` step) TOTP code."""
    candidate = str(code).strip()
    if not candidate:
        return False
    ts = time.time() if timestamp is None else timestamp
    for step in range(-skew, skew + 1):
        expected = generate_code(secret, ts + step * period, digits, period, algorithm)
        if hmac.compare_digest(expected, candidate):
            return True
    return False


def generate_secret(num_bytes: int = DEFAULT_SECRET_BYTES) -> str:
    """Generate a cryptographically random, unpadded base32 TOTP secret."""
    if num_bytes < 10:
        raise ValueError("A TOTP secret should be at least 10 bytes (80 bits).")
    return base64.b32encode(secrets.token_bytes(num_bytes)).decode("ascii").rstrip("=")


def parse_otpauth(uri: str) -> dict:
    """Parse an ``otpauth://totp/...`` URI into a settings dict.

    Returns ``{secret, issuer, account, label, period, digits, algorithm}``.
    Raises ``ValueError`` for non-otpauth schemes, non-TOTP types, missing/invalid
    secrets, or unsupported parameters.
    """
    parsed = urlparse((uri or "").strip())
    if parsed.scheme.lower() != "otpauth":
        raise ValueError("Not an otpauth:// URI.")
    if parsed.netloc.lower() != "totp":
        raise ValueError(f"Unsupported otpauth type {parsed.netloc!r} (only 'totp').")

    params = {k.lower(): v[0] for k, v in parse_qs(parsed.query).items() if v}
    secret = params.get("secret", "")
    if not secret:
        raise ValueError("otpauth URI is missing the 'secret' parameter.")
    _decode_secret(secret)  # validate base32 up front

    label = unquote(parsed.path.lstrip("/"))
    issuer = params.get("issuer", "").strip()
    account = label
    if ":" in label:
        prefix, _, rest = label.partition(":")
        if not issuer:
            issuer = prefix.strip()
        account = rest.strip()

    try:
        period = int(params.get("period", DEFAULT_PERIOD))
        digits = int(params.get("digits", DEFAULT_DIGITS))
    except ValueError as e:
        raise ValueError("otpauth 'period' and 'digits' must be integers.") from e
    algorithm = _validate(digits, period, params.get("algorithm", DEFAULT_ALGORITHM))

    return {
        "secret": secret,
        "issuer": issuer,
        "account": account,
        "label": label,
        "period": period,
        "digits": digits,
        "algorithm": algorithm,
    }


def resolve_config(value: str) -> dict:
    """Return TOTP settings from either a bare base32 secret or an ``otpauth://`` URI.

    Vault entries store whichever form the user supplied; this normalizes both to the
    same dict shape as :func:`parse_otpauth`.
    """
    text = (value or "").strip()
    if text.lower().startswith("otpauth://"):
        return parse_otpauth(text)
    _decode_secret(text)  # validate base32
    return {
        "secret": text,
        "issuer": "",
        "account": "",
        "label": "",
        "period": DEFAULT_PERIOD,
        "digits": DEFAULT_DIGITS,
        "algorithm": DEFAULT_ALGORITHM,
    }
