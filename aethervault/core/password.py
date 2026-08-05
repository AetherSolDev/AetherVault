# Created: 2026-08-05
# Last Edited: 2026-08-05 15:35 CT (America/Chicago)
# Path: aethervault/core/password.py
# Purpose: Password strength scoring and secure password generation.

"""Password strength scoring and secure password generation."""

import random
import re
import string


def score_password(password: str) -> int:
    """Score a password 0-100 based on length and character diversity."""
    if not password:
        return 0
    score = 0
    if len(password) >= 8:
        score += 15
    if len(password) >= 12:
        score += 15
    if len(password) >= 16:
        score += 10
    if re.search(r"[a-z]", password):
        score += 10
    if re.search(r"[A-Z]", password):
        score += 15
    if re.search(r"\d", password):
        score += 15
    if re.search(r"[^a-zA-Z0-9]", password):
        score += 20
    return min(score, 100)


def generate_strong_password(
    length: int = 18, use_lower=True, use_upper=True, use_digit=True, use_symbol=True
) -> str:
    """Generate a cryptographically random password with configurable character sets."""
    if length < 1:
        length = 1
    char_sets = []
    if use_lower:
        char_sets.append(string.ascii_lowercase)
    if use_upper:
        char_sets.append(string.ascii_uppercase)
    if use_digit:
        char_sets.append(string.digits)
    if use_symbol:
        char_sets.append(string.punctuation)
    if not char_sets:
        char_sets.append(string.ascii_letters)
    all_chars = "".join(char_sets)
    if not all_chars:
        return ""
    password = []
    if use_lower:
        password.append(random.choice(string.ascii_lowercase))
    if use_upper:
        password.append(random.choice(string.ascii_uppercase))
    if use_digit:
        password.append(random.choice(string.digits))
    if use_symbol:
        password.append(random.choice(string.punctuation))
    while len(password) < length:
        password.append(random.choice(all_chars))
    random.shuffle(password)
    return "".join(password[:length])
