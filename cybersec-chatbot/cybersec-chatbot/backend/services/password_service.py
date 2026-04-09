"""
password_service.py — Password strength evaluation service.
"""
from ..models.threat_models import PasswordResponse
from ..utils.password_utils import (
    calculate_entropy, check_common_patterns,
    score_password, STRENGTH_SUGGESTIONS,
)


class PasswordService:
    """Stateless service — safe to instantiate once and reuse."""

    def evaluate(self, password: str) -> PasswordResponse:
        entropy = calculate_entropy(password)
        issues = check_common_patterns(password)
        score, strength = score_password(password)
        suggestions = STRENGTH_SUGGESTIONS.get(strength, [])
        return PasswordResponse(
            strength=strength,
            score=score,
            entropy_bits=entropy,
            issues=issues,
            suggestions=suggestions,
        )
