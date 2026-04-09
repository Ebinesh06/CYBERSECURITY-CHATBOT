"""
test_password.py — Unit tests for password strength evaluation.
"""

import pytest
from backend.utils.password_utils import calculate_entropy, check_common_patterns, score_password
from backend.services.password_service import PasswordService


# ── Entropy calculation ───────────────────────────────────────────────────

def test_entropy_increases_with_length():
    short = calculate_entropy("abc")
    long_ = calculate_entropy("abcdefghij")
    assert long_ > short


def test_entropy_increases_with_charset():
    lower_only = calculate_entropy("abcdefgh")
    mixed = calculate_entropy("aB3!efgh")  # same length, larger charset
    assert mixed > lower_only


def test_entropy_single_char():
    e = calculate_entropy("a")
    assert e > 0


# ── Pattern checks ────────────────────────────────────────────────────────

def test_common_password_flagged():
    issues = check_common_patterns("password")
    assert any("commonly used" in i.lower() for i in issues)


def test_short_password_flagged():
    issues = check_common_patterns("abc")
    assert any("short" in i.lower() or "8" in i for i in issues)


def test_no_uppercase_flagged():
    issues = check_common_patterns("alllower1!")
    assert any("uppercase" in i.lower() for i in issues)


def test_repeated_chars_flagged():
    issues = check_common_patterns("aaabbb123!")
    assert any("repeated" in i.lower() for i in issues)


def test_sequential_flagged():
    issues = check_common_patterns("abcdefgh!")
    assert any("sequential" in i.lower() for i in issues)


def test_strong_password_no_issues():
    issues = check_common_patterns("Tr0ub4dor&3-XkP!")
    assert len(issues) == 0


# ── Score and strength labels ─────────────────────────────────────────────

@pytest.mark.parametrize("pw,expected", [
    ("abc",              "very_weak"),
    ("password1",        "weak"),
    ("Summer2024!",      "moderate"),
    ("Kj8#mP2@nQ5!",    "strong"),
    ("Xk9#mP2@nQ5!vLw3", "very_strong"),
])
def test_strength_labels(pw, expected):
    _, label = score_password(pw)
    assert label == expected


# ── PasswordService end-to-end ────────────────────────────────────────────

def test_service_returns_all_fields():
    svc = PasswordService()
    result = svc.evaluate("Hello123!")
    assert result.strength in ("very_weak", "weak", "moderate", "strong", "very_strong")
    assert 0 <= result.score <= 100
    assert result.entropy_bits > 0
    assert isinstance(result.issues, list)
    assert isinstance(result.suggestions, list)
    assert len(result.suggestions) > 0


def test_very_strong_password():
    svc = PasswordService()
    result = svc.evaluate("!Kx9@mN3#pL7$vQ2%wR8")
    assert result.strength in ("strong", "very_strong")
    assert result.score >= 70
    assert result.entropy_bits > 80
