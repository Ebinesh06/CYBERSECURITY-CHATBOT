"""
phishing_keywords.py — Curated threat detection data.

Provides keyword lists, regex patterns, and a scoring function used by
ThreatService to perform fast, deterministic (non-AI) first-pass analysis.
This catches obvious threats without burning API tokens.
"""

import re

# ---------------------------------------------------------------------------
# Keyword banks  (tuples: keyword, weight 0-1, category)
# ---------------------------------------------------------------------------

PHISHING_KEYWORDS: list[tuple[str, float, str]] = [
    # Urgency triggers
    ("urgent", 0.6, "urgency"),
    ("immediately", 0.5, "urgency"),
    ("act now", 0.7, "urgency"),
    ("limited time", 0.5, "urgency"),
    ("expires today", 0.7, "urgency"),
    ("account suspended", 0.8, "urgency"),
    ("verify now", 0.7, "urgency"),
    ("last warning", 0.8, "urgency"),

    # Sensitive data requests
    ("otp", 0.85, "sensitive_data"),
    ("one-time password", 0.85, "sensitive_data"),
    ("share your password", 0.95, "sensitive_data"),
    ("send your pin", 0.95, "sensitive_data"),
    ("cvv", 0.8, "sensitive_data"),
    ("social security", 0.85, "sensitive_data"),
    ("bank account number", 0.85, "sensitive_data"),
    ("credit card number", 0.85, "sensitive_data"),
    ("mother's maiden name", 0.75, "sensitive_data"),
    ("date of birth", 0.4, "sensitive_data"),

    # Financial lures
    ("you have won", 0.8, "financial_lure"),
    ("claim your prize", 0.8, "financial_lure"),
    ("free gift", 0.6, "financial_lure"),
    ("wire transfer", 0.65, "financial_lure"),
    ("western union", 0.7, "financial_lure"),
    ("bitcoin payment", 0.65, "financial_lure"),
    ("lottery", 0.7, "financial_lure"),
    ("inheritance", 0.6, "financial_lure"),
    ("million dollars", 0.75, "financial_lure"),

    # Authority impersonation
    ("irs", 0.6, "impersonation"),
    ("microsoft support", 0.75, "impersonation"),
    ("apple id suspended", 0.85, "impersonation"),
    ("paypal account", 0.5, "impersonation"),
    ("amazon security", 0.55, "impersonation"),

    # Technical threats
    ("your device is infected", 0.85, "malware"),
    ("virus detected", 0.8, "malware"),
    ("download and run", 0.7, "malware"),
    ("click the link below", 0.5, "phishing_link"),
    ("update your payment", 0.7, "financial_lure"),
    ("confirm your details", 0.6, "sensitive_data"),
]

MALWARE_KEYWORDS: list[tuple[str, float, str]] = [
    ("execute", 0.4, "execution"),
    ("powershell", 0.5, "execution"),
    ("cmd.exe", 0.7, "execution"),
    ("disable antivirus", 0.9, "evasion"),
    ("turn off firewall", 0.9, "evasion"),
    ("ransomware", 0.85, "ransomware"),
    ("encrypt your files", 0.85, "ransomware"),
    ("locked files", 0.75, "ransomware"),
    ("recovery key needed", 0.8, "ransomware"),
    ("pay to unlock", 0.9, "ransomware"),
    ("remote access", 0.5, "rat"),
    ("keylogger", 0.8, "spyware"),
    ("trojan", 0.8, "malware"),
    ("worm", 0.75, "malware"),
]

RANSOMWARE_KEYWORDS: list[tuple[str, float, str]] = [
    ("ransomware detected", 0.95, "ransomware"),
    ("your files are encrypted", 0.95, "ransomware"),
    ("pay the attacker", 0.95, "ransomware"),
    ("bitcoin ransom", 0.9, "ransomware"),
    ("recovery impossible", 0.85, "ransomware"),
    ("system locked", 0.75, "ransomware"),
    ("decrypt for payment", 0.95, "ransomware"),
    ("data hostage", 0.9, "ransomware"),
]

MITM_KEYWORDS: list[tuple[str, float, str]] = [
    ("unencrypted connection", 0.8, "mitm"),
    ("insecure wifi", 0.75, "mitm"),
    ("ssl certificate invalid", 0.85, "mitm"),
    ("man-in-the-middle", 0.95, "mitm"),
    ("intercepting data", 0.9, "mitm"),
    ("public wifi", 0.4, "mitm"),
    ("no https", 0.5, "mitm"),
    ("network sniffer", 0.85, "mitm"),
]

DDOS_KEYWORDS: list[tuple[str, float, str]] = [
    ("ddos attack", 0.95, "ddos"),
    ("distributed denial", 0.95, "ddos"),
    ("server overwhelmed", 0.85, "ddos"),
    ("service unavailable", 0.4, "ddos"),
    ("request flood", 0.9, "ddos"),
    ("botnet attack", 0.9, "ddos"),
    ("traffic spike", 0.5, "ddos"),
]

SOCIAL_ENGINEERING_KEYWORDS: list[tuple[str, float, str]] = [
    ("social engineering", 0.95, "social_engineering"),
    ("pretend to be", 0.7, "social_engineering"),
    ("trick you into", 0.75, "social_engineering"),
    ("impersonate", 0.8, "social_engineering"),
    ("trust exploitation", 0.85, "social_engineering"),
    ("psychological manipulation", 0.9, "social_engineering"),
    ("convince you to", 0.6, "social_engineering"),
]

SQL_INJECTION_KEYWORDS: list[tuple[str, float, str]] = [
    ("sql injection", 0.95, "sql_injection"),
    ("sql query ", 0.5, "sql_injection"),
    ("drop table", 0.95, "sql_injection"),
    ("database hack", 0.85, "sql_injection"),
    ("union select", 0.9, "sql_injection"),
    ("where 1=1", 0.95, "sql_injection"),
    ("sql command", 0.6, "sql_injection"),
]

XSS_KEYWORDS: list[tuple[str, float, str]] = [
    ("xss attack", 0.95, "xss"),
    ("script injection", 0.9, "xss"),
    ("javascript payload", 0.9, "xss"),
    ("<script>", 0.95, "xss"),
    ("dom-based xss", 0.95, "xss"),
    ("reflected xss", 0.95, "xss"),
    ("stored xss", 0.95, "xss"),
    ("cross-site script", 0.95, "xss"),
]

BRUTE_FORCE_KEYWORDS: list[tuple[str, float, str]] = [
    ("brute force", 0.9, "brute_force"),
    ("password guessing", 0.85, "brute_force"),
    ("crack password", 0.9, "brute_force"),
    ("dictionary attack", 0.9, "brute_force"),
    ("exhaustive login", 0.85, "brute_force"),
    ("rapid login attempts", 0.8, "brute_force"),
    ("password spraying", 0.85, "brute_force"),
]

ZERO_DAY_KEYWORDS: list[tuple[str, float, str]] = [
    ("zero-day", 0.95, "zero_day"),
    ("0-day", 0.95, "zero_day"),
    ("unknown vulnerability", 0.85, "zero_day"),
    ("unpatched exploit", 0.9, "zero_day"),
    ("zero day vulnerability", 0.95, "zero_day"),
    ("exploit unexpected bug", 0.8, "zero_day"),
]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

SUSPICIOUS_URL_PATTERNS: list[re.Pattern] = [
    re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", re.I),   # bare IP URLs
    re.compile(r"bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly", re.I),           # URL shorteners
    re.compile(r"[a-z0-9-]{15,}\.(tk|ml|ga|cf|gq|xyz|top|click)", re.I), # sketchy TLDs
    re.compile(r"paypal[^.]*\.(net|org|info|biz)", re.I),                 # brand spoofing
    re.compile(r"amazon[^.]*\.(net|org|info|biz)", re.I),
    re.compile(r"apple[^.]*\.(net|org|info|biz)", re.I),
    re.compile(r"secure[^.]*login\.", re.I),                              # fake secure login
]

SENSITIVE_DATA_PATTERN = re.compile(
    r"\b(\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4})"   # card number
    r"|\b(\d{3}-\d{2}-\d{4})\b"                   # SSN
    r"|\b([0-9]{6,8})\b",                           # OTP-like numeric codes
    re.I,
)


def compute_keyword_score(text: str) -> tuple[float, list[str]]:
    """
    Scan *text* against all keyword banks and return:
      - total_score  (clamped 0.0 – 1.0)
      - detected     list of human-readable pattern descriptions

    Score is the max of any single hit, boosted by 0.1 per additional hit
    (so multiple weak signals compound into a stronger warning).
    """
    lower = text.lower()
    hits: list[tuple[float, str]] = []

    # Check all threat keyword lists
    all_keywords = (
        PHISHING_KEYWORDS + MALWARE_KEYWORDS + RANSOMWARE_KEYWORDS +
        MITM_KEYWORDS + DDOS_KEYWORDS + SOCIAL_ENGINEERING_KEYWORDS +
        SQL_INJECTION_KEYWORDS + XSS_KEYWORDS + BRUTE_FORCE_KEYWORDS +
        ZERO_DAY_KEYWORDS
    )

    for keyword, weight, category in all_keywords:
        if keyword in lower:
            label = f"{category}: '{keyword}'"
            hits.append((weight, label))

    for pattern in SUSPICIOUS_URL_PATTERNS:
        if pattern.search(text):
            hits.append((0.75, f"suspicious URL pattern"));

    if SENSITIVE_DATA_PATTERN.search(text):
        hits.append((0.7, "potential sensitive data (card/SSN/OTP) detected"))

    if not hits:
        return 0.0, []

    hits.sort(key=lambda h: h[0], reverse=True)
    base = hits[0][0]
    boost = min(0.2, 0.05 * (len(hits) - 1))
    score = min(1.0, base + boost)
    return round(score, 3), [h[1] for h in hits]
