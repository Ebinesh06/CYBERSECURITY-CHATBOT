"""
password_utils.py — Password entropy and strength helpers.

Uses information-theory entropy (bits) rather than simple length/character
class checks, giving a more accurate picture of actual password strength.
"""

import math
import re


def _character_pool_size(password: str) -> int:
    """Return the alphabet size for Shannon entropy estimation."""
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"\d", password):
        pool += 10
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        pool += 32
    if re.search(r"[^\x00-\x7F]", password):  # unicode / emoji
        pool += 64
    return max(pool, 1)


def calculate_entropy(password: str) -> float:
    """Shannon entropy in bits: len * log2(pool_size)."""
    return round(len(password) * math.log2(_character_pool_size(password)), 2)


def check_common_patterns(password: str) -> list[str]:
    """Return a list of weaknesses found in the password."""
    issues = []
    lower = password.lower()

    # Common weak passwords
    common = {"password", "123456", "qwerty", "letmein", "welcome",
              "admin", "login", "passw0rd", "abc123", "iloveyou"}
    if lower in common:
        issues.append("This is one of the most commonly used passwords.")

    if len(password) < 8:
        issues.append("Too short — use at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        issues.append("Add at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        issues.append("Add at least one lowercase letter.")
    if not re.search(r"\d", password):
        issues.append("Add at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        issues.append("Add at least one special character (!@#$ etc.).")

    # Repeated characters: e.g. "aaa" or "111"
    if re.search(r"(.)\1{2,}", password):
        issues.append("Avoid repeated characters (e.g. aaa, 111).")

    # Sequential patterns
    for seq in ("abcdef", "qwerty", "12345678", "abcdefgh"):
        if seq in lower:
            issues.append(f"Avoid sequential patterns (found '{seq}').")
            break

    return issues


def score_password(password: str) -> tuple[int, str]:
    """
    Return (score 0-100, strength label).

    Score bands:
      0-20  → very_weak
      21-40 → weak
      41-60 → moderate
      61-80 → strong
      81-100 → very_strong
    """
    entropy = calculate_entropy(password)

    # Base score from entropy (80 bits = perfect)
    base = min(80, int((entropy / 80) * 80))

    # Bonuses
    if len(password) >= 12:
        base += 10
    if len(password) >= 16:
        base += 10

    score = min(100, base)

    if score <= 20:
        return score, "very_weak"
    elif score <= 40:
        return score, "weak"
    elif score <= 60:
        return score, "moderate"
    elif score <= 80:
        return score, "strong"
    else:
        return score, "very_strong"


STRENGTH_SUGGESTIONS: dict[str, list[str]] = {
    "very_weak": [
        "Use a passphrase of 4+ random words (e.g. 'horse-battery-staple-lamp').",
        "Never reuse passwords across sites.",
        "Consider a password manager.",
    ],
    "weak": [
        "Increase length to at least 12 characters.",
        "Mix uppercase, lowercase, digits, and symbols.",
        "Avoid dictionary words or names.",
    ],
    "moderate": [
        "Add more length or special characters to reach 'strong'.",
        "Store in a password manager rather than memory.",
    ],
    "strong": [
        "Great password! Enable two-factor authentication for extra security.",
    ],
    "very_strong": [
        "Excellent! Remember to store it in a password manager.",
        "Enable 2FA on your account for defence-in-depth.",
    ],
}
