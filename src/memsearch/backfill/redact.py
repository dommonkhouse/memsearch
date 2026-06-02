from __future__ import annotations

import re

REDACTION = "[REDACTED]"

SECRET_PATTERNS = [
    re.compile(r"(?i)(Authorization:\s*Bearer\s+)[^\s]+"),
    re.compile(r"(?i)(Bearer\s+)sk-[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(Cookie:\s*)[^\n\r]+"),
    re.compile(r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|APPLICATION[_-]?PASSWORD)[A-Z0-9_]*\s*=\s*)['\"]?[^'\"\s]+['\"]?"),
    re.compile(r"\bsk-[A-Za-z0-9._-]+\b"),
    re.compile(r"\b(?:xox[baprs]-|gh[pousr]_|eyJ)[A-Za-z0-9._-]{12,}\b"),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_replacement, redacted)
    return redacted


def _replacement(match: re.Match[str]) -> str:
    if match.groups():
        return f"{match.group(1)}{REDACTION}"
    return REDACTION
