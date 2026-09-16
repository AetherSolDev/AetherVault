# Created: 2026-09-16
# Last Edited: 2026-09-16 15:08 CT (America/Chicago)
# Path: tests/test_totp.py
# Purpose: Tests for RFC 6238 TOTP generation/verification and otpauth parsing.

"""Tests for aethervault.core.totp."""

import base64

import pytest

from aethervault.core.totp import (
    generate_code,
    generate_secret,
    parse_otpauth,
    resolve_config,
    verify_code,
)


def _b32(text: str) -> str:
    return base64.b32encode(text.encode("utf-8")).decode("ascii")


# RFC 6238 Appendix B test secrets (ASCII) encoded as base32.
SECRET_SHA1 = _b32("12345678901234567890")
SECRET_SHA256 = _b32("12345678901234567890123456789012")
SECRET_SHA512 = _b32(
    "1234567890123456789012345678901234567890123456789012345678901234"
)

# (timestamp, 8-digit SHA1 code) from RFC 6238 Appendix B.
RFC6238_SHA1 = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


class TestRfc6238Vectors:
    @pytest.mark.parametrize("timestamp,expected", RFC6238_SHA1)
    def test_sha1_8_digit(self, timestamp, expected):
        assert generate_code(SECRET_SHA1, timestamp, digits=8) == expected

    @pytest.mark.parametrize("timestamp,expected", RFC6238_SHA1)
    def test_sha1_6_digit_is_last_six(self, timestamp, expected):
        assert generate_code(SECRET_SHA1, timestamp) == expected[-6:]

    @pytest.mark.parametrize("timestamp,expected", [(59, "46119246"),
                                                    (2000000000, "90698825")])
    def test_sha256_8_digit(self, timestamp, expected):
        assert generate_code(SECRET_SHA256, timestamp, digits=8,
                             algorithm="sha256") == expected

    @pytest.mark.parametrize("timestamp,expected", [(59, "90693936"),
                                                    (2000000000, "38618901")])
    def test_sha512_8_digit(self, timestamp, expected):
        assert generate_code(SECRET_SHA512, timestamp, digits=8,
                             algorithm="SHA512") == expected


class TestSecretDecoding:
    def test_accepts_lowercase_spaces_and_missing_padding(self):
        expected = generate_code(SECRET_SHA1, 59, digits=8)
        messy = SECRET_SHA1.lower()
        spaced = " ".join(messy[i:i + 4] for i in range(0, len(messy), 4))
        assert generate_code(spaced, 59, digits=8) == expected

    def test_empty_secret_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_code("")

    def test_invalid_base32_raises(self):
        with pytest.raises(ValueError, match="base32"):
            generate_code("not!valid!base32")

    def test_bad_digits_raises(self):
        with pytest.raises(ValueError, match="digits"):
            generate_code(SECRET_SHA1, 59, digits=4)

    def test_bad_period_raises(self):
        with pytest.raises(ValueError, match="period"):
            generate_code(SECRET_SHA1, 59, period=0)

    def test_bad_algorithm_raises(self):
        with pytest.raises(ValueError, match="algorithm"):
            generate_code(SECRET_SHA1, 59, algorithm="md5")


class TestVerifyCode:
    def test_current_code_verifies(self):
        now = 1234567890
        assert verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now), timestamp=now)

    def test_skew_accepts_adjacent_steps(self):
        now = 1234567890
        assert verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now - 30), timestamp=now)
        assert verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now + 30), timestamp=now)

    def test_skew_rejects_far_off(self):
        now = 1234567890
        assert not verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now - 90), timestamp=now)

    def test_zero_skew_exact_only(self):
        now = 1234567890
        assert verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now),
                           timestamp=now, skew=0)
        assert not verify_code(SECRET_SHA1, generate_code(SECRET_SHA1, now - 30),
                               timestamp=now, skew=0)

    def test_wrong_code_rejected(self):
        assert not verify_code(SECRET_SHA1, "000000", timestamp=1234567890)

    def test_empty_code_rejected(self):
        assert not verify_code(SECRET_SHA1, "", timestamp=1234567890)


class TestGenerateSecret:
    def test_default_is_32_base32_chars(self):
        secret = generate_secret()
        assert len(secret) == 32
        assert set(secret) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")

    def test_generated_secret_produces_codes(self):
        assert len(generate_code(generate_secret())) == 6

    def test_unique(self):
        assert len({generate_secret() for _ in range(50)}) == 50

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="at least"):
            generate_secret(num_bytes=4)


class TestParseOtpauth:
    def test_full_uri(self):
        uri = (f"otpauth://totp/GitHub:octocat?secret={SECRET_SHA1}"
               "&issuer=GitHub&algorithm=SHA1&digits=6&period=30")
        parsed = parse_otpauth(uri)
        assert parsed["secret"] == SECRET_SHA1
        assert parsed["issuer"] == "GitHub"
        assert parsed["account"] == "octocat"
        assert parsed["period"] == 30
        assert parsed["digits"] == 6
        assert parsed["algorithm"] == "SHA1"

    def test_minimal_uri_defaults(self):
        parsed = parse_otpauth(f"otpauth://totp/acct?secret={SECRET_SHA1}")
        assert parsed["period"] == 30
        assert parsed["digits"] == 6
        assert parsed["algorithm"] == "SHA1"
        assert parsed["account"] == "acct"
        assert parsed["issuer"] == ""

    def test_issuer_from_label_when_query_missing(self):
        parsed = parse_otpauth(f"otpauth://totp/Acme:joe?secret={SECRET_SHA1}")
        assert parsed["issuer"] == "Acme"
        assert parsed["account"] == "joe"

    def test_percent_encoded_label(self):
        parsed = parse_otpauth(
            f"otpauth://totp/My%20Site:joe%40x.com?secret={SECRET_SHA1}"
        )
        assert parsed["issuer"] == "My Site"
        assert parsed["account"] == "joe@x.com"

    def test_custom_params(self):
        parsed = parse_otpauth(
            f"otpauth://totp/x?secret={SECRET_SHA1}&digits=8&period=60&algorithm=SHA256"
        )
        assert parsed["digits"] == 8
        assert parsed["period"] == 60
        assert parsed["algorithm"] == "SHA256"

    def test_non_otpauth_scheme(self):
        with pytest.raises(ValueError, match="otpauth"):
            parse_otpauth("https://example.com")

    def test_non_totp_type(self):
        with pytest.raises(ValueError, match="Unsupported otpauth type"):
            parse_otpauth(f"otpauth://hotp/x?secret={SECRET_SHA1}")

    def test_missing_secret(self):
        with pytest.raises(ValueError, match="secret"):
            parse_otpauth("otpauth://totp/x")

    def test_invalid_secret(self):
        with pytest.raises(ValueError, match="base32"):
            parse_otpauth("otpauth://totp/x?secret=@@@@")

    def test_bad_digits(self):
        with pytest.raises(ValueError, match="digits"):
            parse_otpauth(f"otpauth://totp/x?secret={SECRET_SHA1}&digits=abc")

    def test_bad_algorithm(self):
        with pytest.raises(ValueError, match="algorithm"):
            parse_otpauth(f"otpauth://totp/x?secret={SECRET_SHA1}&algorithm=md5")


class TestResolveConfig:
    def test_bare_secret_uses_defaults(self):
        parsed = resolve_config(SECRET_SHA1)
        assert parsed["secret"] == SECRET_SHA1
        assert parsed["digits"] == 6
        assert parsed["period"] == 30
        assert parsed["algorithm"] == "SHA1"

    def test_otpauth_uri_is_parsed(self):
        parsed = resolve_config(
            f"otpauth://totp/Acme:joe?secret={SECRET_SHA1}&digits=8&period=60"
        )
        assert parsed["account"] == "joe"
        assert parsed["digits"] == 8
        assert parsed["period"] == 60

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            resolve_config("")
