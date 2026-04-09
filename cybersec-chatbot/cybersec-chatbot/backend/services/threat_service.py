"""
threat_service.py — Two-stage threat analysis.

Stage 1 — deterministic keyword/regex scan (fast, zero API cost).
Stage 2 — GPT analysis when Stage 1 confidence is low or ambiguous.

The two stages are intentionally decoupled so you can swap or tune each
independently without touching the other.
"""

from typing import Optional
from openai import AsyncOpenAI

from ..config import get_settings
from ..models.threat_models import ThreatResponse
from ..utils.phishing_keywords import compute_keyword_score

# Threshold below which we escalate to AI analysis
_AI_ESCALATION_THRESHOLD = 0.4


def _classify_level(score: float, patterns: list[str], text: str = "") -> tuple[str, str]:
    """Map score + patterns to threat level and type. Returns (level, threat_type)."""
    patterns_text = " ".join(patterns).lower() + text.lower()
    
    # Map threat types to their criticality
    threat_type_scores = {
        "zero_day": 0.95,
        "ransomware": 0.9,
        "sql_injection": 0.85,
        "xss": 0.85,
        "ddos": 0.8,
        "malware": 0.8,
        "brute_force": 0.75,
        "mitm": 0.75,
        "social_engineering": 0.7,
        "phishing": 0.7,
        "evasion": 0.8,
    }
    
    # Detect threat type from patterns
    threat_type = "unknown"
    max_threat_score = 0.0
    
    for threat in threat_type_scores:
        if threat in patterns_text:
            if threat_type_scores[threat] > max_threat_score:
                threat_type = threat
                max_threat_score = threat_type_scores[threat]
    
    # Determine threat level based on score
    if score >= 0.7:
        return "critical", threat_type if threat_type != "unknown" else "phishing"
    elif score >= 0.4:
        return "suspicious", threat_type if threat_type != "unknown" else "suspicious_activity"
    return "safe", "none"


def _build_advice(level: str, threat_type: str, patterns: list[str]) -> str:
    """Return actionable advice based on threat level and type."""
    advice_map = {
        ("safe", "none"): "This message appears safe. Always stay vigilant and avoid sharing personal information.",
        
        ("suspicious", "phishing"): (
            "⚠️ This message shows signs of a phishing attack. "
            "Do NOT click links or share personal information. "
            "Verify the sender through official channels before responding."
        ),
        ("suspicious", "malware"): (
            "⚠️ This message may contain malware. "
            "Do NOT download or execute files from unknown sources. "
            "Verify the source before opening attachments."
        ),
        ("suspicious", "social_engineering"): (
            "⚠️ This appears to be social engineering. "
            "Be cautious of requests that seem unusual or create pressure. "
            "Verify directly with the organization before complying."
        ),
        ("suspicious", "suspicious_activity"): (
            "⚠️ This message contains suspicious patterns. "
            "Do NOT share any personal information. "
            "Verify the sender through official channels."
        ),
        
        ("critical", "zero_day"): (
            "🚨 CRITICAL — Zero-day vulnerability detected. "
            "This represents an unknown security flaw. "
            "Update your software immediately and contact your security team."
        ),
        ("critical", "ransomware"): (
            "🚨 CRITICAL — Ransomware detected. "
            "Do NOT open files or click links. "
            "Isolate your device and contact your IT security team immediately. "
            "Back up critical data from other devices."
        ),
        ("critical", "sql_injection"): (
            "🚨 CRITICAL — SQL Injection attack detected. "
            "This could compromise your database. "
            "Contact your IT/development team immediately. "
            "Review access logs and implement input validation."
        ),
        ("critical", "xss"): (
            "🚨 CRITICAL — Cross-Site Scripting (XSS) attack detected. "
            "This could steal your session data or credentials. "
            "Clear your browser cache and cookies. "
            "Report this to the website administrator immediately."
        ),
        ("critical", "ddos"): (
            "🚨 CRITICAL — DDoS attack detected. "
            "Service is being overwhelmed by excessive requests. "
            "The system may be unavailable. Contact your ISP/hosting provider. "
            "Implement DDoS protection services."
        ),
        ("critical", "malware"): (
            "🚨 CRITICAL — Malware detected. "
            "Do NOT download or execute any files from this source. "
            "Scan your device with updated antivirus software immediately. "
            "Contact your IT security team."
        ),
        ("critical", "brute_force"): (
            "🚨 CRITICAL — Brute force attack detected. "
            "Someone is attempting to guess passwords. "
            "Enable 2FA, use strong unique passwords, and review access logs. "
            "Contact your security team if this is your account."
        ),
        ("critical", "mitm"): (
            "🚨 CRITICAL — Man-in-the-Middle (MITM) attack suspected. "
            "Your data may be intercepted. "
            "Only use HTTPS connections and trusted networks. "
            "Verify SSL certificates before entering sensitive information."
        ),
        ("critical", "social_engineering"): (
            "🚨 CRITICAL — Sophisticated social engineering attempt detected. "
            "Do NOT comply with requests or share information. "
            "Verify through official channels before taking action. "
            "Report to your security team."
        ),
        ("critical", "phishing"): (
            "🚨 CRITICAL — Phishing attack detected. "
            "Do NOT click links, share passwords, OTPs, or financial details. "
            "Report to your IT/security team immediately. "
            "If you've shared information, change your passwords now."
        ),
    }
    
    base = advice_map.get((level, threat_type), advice_map.get((level, "suspicious_activity"), 
                                                                  advice_map[("safe", "none")]))
    
    if "otp" in " ".join(patterns).lower() or "sensitive_data" in " ".join(patterns).lower():
        base += " ⛔ Legitimate organizations NEVER ask for passwords, OTPs, or sensitive data via messages."
    return base


class ThreatService:
    """Orchestrates keyword scanning and optional AI threat analysis."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)

    async def analyze(self, text: str) -> ThreatResponse:
        """Run full two-stage threat analysis on *text*."""
        # ── Stage 1: fast keyword scan ────────────────────────────────────
        score, patterns = compute_keyword_score(text)
        level, threat_type = _classify_level(score, patterns, text)
        advice = _build_advice(level, threat_type, patterns)
        ai_analysis: Optional[str] = None

        # ── Stage 2: AI escalation when uncertain ─────────────────────────
        if score < _AI_ESCALATION_THRESHOLD:
            ai_result = await self._ai_classify(text)
            if ai_result:  # Only process if AI analysis succeeded
                ai_analysis = ai_result
                # Parse AI verdict to possibly upgrade the threat level
                lower_ai = ai_analysis.lower()
                if "zero-day" in lower_ai or "0-day" in lower_ai:
                    level = "critical"
                    threat_type = "zero_day"
                    score = max(score, 0.95)
                elif "ransomware" in lower_ai:
                    level = "critical"
                    threat_type = "ransomware"
                    score = max(score, 0.9)
                elif "sql injection" in lower_ai:
                    level = "critical"
                    threat_type = "sql_injection"
                    score = max(score, 0.85)
                elif "xss" in lower_ai or "cross-site" in lower_ai:
                    level = "critical"
                    threat_type = "xss"
                    score = max(score, 0.85)
                elif "ddos" in lower_ai:
                    level = "critical"
                    threat_type = "ddos"
                    score = max(score, 0.8)
                elif "phishing" in lower_ai:
                    level = "critical"
                    threat_type = "phishing"
                    score = max(score, 0.75)
                elif "malware" in lower_ai or "malicious" in lower_ai:
                    level = "critical"
                    threat_type = "malware"
                    score = max(score, 0.85)
                elif "brute force" in lower_ai:
                    level = "critical"
                    threat_type = "brute_force"
                    score = max(score, 0.75)
                elif "social engineering" in lower_ai:
                    level = "suspicious"
                    threat_type = "social_engineering"
                    score = max(score, 0.7)
                elif "suspicious" in lower_ai:
                    level = "suspicious"
                    threat_type = "suspicious_activity"
                    score = max(score, 0.5)
                
                advice = _build_advice(level, threat_type, patterns)

        return ThreatResponse(
            threat_level=level,
            threat_type=threat_type,
            confidence=round(score, 3),
            detected_patterns=patterns,
            advice=advice,
            ai_analysis=ai_analysis,
        )

    async def _ai_classify(self, text: str) -> str:
        """Ask GPT to classify the text and explain its reasoning."""
        try:
            prompt = (
                "You are a cybersecurity threat analyst. Classify the following message "
                "as one of: 'safe', 'suspicious', 'phishing', or 'malware'. "
                "Explain your reasoning in 2-3 sentences, citing specific red flags. "
                "Start your response with the classification word.\n\n"
                f"Message:\n{text[:1500]}"  # truncate to avoid token waste
            )
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1,  # low temperature for consistent classification
            )
            return response.choices[0].message.content or "Unable to classify."
        except Exception as exc:
            # Gracefully handle API errors - return None to skip AI analysis
            # The keyword-based detection is sufficient for demo purposes
            return None
