# Created: 2026-07-27
# Last Edited: 2026-07-27 13:47 CT (America/Chicago)
# Path: tests/test_score_password.py
# Purpose: Unit tests for the score_password function.

"""Unit tests for the score_password function."""

from src.core_logic import score_password


class TestScorePassword:
    def test_empty_password_returns_zero(self):
        assert score_password("") == 0

    def test_very_short_password_scores_low(self):
        assert score_password("ab") < 30

    def test_password_meets_length_requirements(self):
        assert score_password("abcdefgh") >= 15

    def test_password_with_all_char_types_scores_high(self):
        assert score_password("MyP@ssw0rd!sS3cur3!") == 100

    def test_password_with_lowercase_only(self):
        s = score_password("abcdefghijklmnop")
        after_length = s
        s2 = score_password("abcdefghijklmnopq")
        assert s2 >= after_length

    def test_password_with_uppercase_gets_bonus(self):
        lower_only = score_password("abcdefghijklmnop")
        with_upper = score_password("Abcdefghijklmnop")
        assert with_upper > lower_only

    def test_password_with_digits_gets_bonus(self):
        no_digits = score_password("Abcdefghijklmnop")
        with_digits = score_password("Abcdefghijklmnop1")
        assert with_digits > no_digits

    def test_password_with_special_chars_gets_bonus(self):
        no_special = score_password("Abcdefghijklmnop1")
        with_special = score_password("Abcdefghijklmnop1!")
        assert with_special > no_special

    def test_score_never_exceeds_one_hundred(self):
        assert score_password("a" * 100 + "A1!") <= 100
        assert score_password("!" * 100) <= 100

    def test_score_is_deterministic(self):
        assert score_password("TestPass123!") == score_password("TestPass123!")
