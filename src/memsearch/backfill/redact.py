from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

REDACTION = "[REDACTED]"
REDACTOR_VERSION = "2026-06-05.1"
SIGNED_URL_MARKERS = {
    "x-amz-signature",
    "x-goog-signature",
    "signature",
    "token",
    "expires",
    "expiresin",
    "x-amz-expires",
    "x-goog-expires",
}

@dataclass(frozen=True)
class SecretHit:
    path: str
    pattern: str
    line: int


SECRET_PATTERNS = [
    ("signed_url", re.compile(r"https?://[^\s)>\]\"']+")),
    ("computer_session_link", re.compile(r"computer:///sessions/[^\s)]+")),
    ("service_account_key_file", re.compile(r"\b[\w.-]*service-account-key\.json\b", re.IGNORECASE)),
    ("gcp_service_account_json", re.compile(r"\{[^{}]*\"type\"\s*:\s*\"service_account\"[^{}]*\"private_key\"[^{}]*\}", re.DOTALL)),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)),
    ("authorization_bearer", re.compile(r"(?i)(Authorization:\s*Bearer\s+)[^\s]+")),
    ("bearer_token", re.compile(r"(?i)(Bearer\s+)[^\s]+")),
    ("x_api_key_header", re.compile(r"(?i)(x-api-key:\s*)[^\s]+")),
    ("cookie_header", re.compile(r"(?i)(Cookie:\s*)[^\n\r]+")),
    (
        "env_secret",
        re.compile(
            r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|APPLICATION[_-]?PASSWORD)[A-Z0-9_]*\s*=\s*)['\"]?[^'\"\s]+['\"]?"
        ),
    ),
    ("openai_anthropic_key", re.compile(r"\b(?:sk-proj-|sk-|sk-ant-)[A-Za-z0-9._-]{8,}\b")),
    ("github_or_slack_token", re.compile(r"\b(?:xox[baprs]-|gh[pousr]_|eyJ)[A-Za-z0-9._-]{12,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key_value", re.compile(r"(?i)(aws_secret_access_key\s*[=:]\s*)['\"]?[A-Za-z0-9/+=]{20,}['\"]?")),
    ("private_key_header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

SCAN_PATTERNS = [
    ("signed_url_query", re.compile(r"https?://[^\s)>\]\"']*[?&](?:X-Amz-Signature|X-Goog-Signature|Signature|token|X-Amz-Expires|X-Goog-Expires)=", re.IGNORECASE)),
    ("computer_session_link", re.compile(r"computer:///sessions/[^\s)]+")),
    ("service_account_key_file", re.compile(r"\b[\w.-]*service-account-key\.json\b", re.IGNORECASE)),
    ("gcp_service_account_json", re.compile(r"\"type\"\s*:\s*\"service_account\".*?\"private_key\"", re.DOTALL)),
    ("authorization_bearer", re.compile(r"(?i)(Authorization:\s*Bearer\s+)(?!\[REDACTED\])[A-Za-z0-9._-]{12,}")),
    ("bearer_token", re.compile(r"(?i)(Bearer\s+)(?!\[REDACTED\])[A-Za-z0-9._-]{12,}")),
    ("x_api_key_header", re.compile(r"(?i)(x-api-key:\s*)(?!\[REDACTED\])[A-Za-z0-9._-]{12,}")),
    ("cookie_header", re.compile(r"(?i)(Cookie:\s*)(?!\[REDACTED\])[^\n\r]+")),
    (
        "env_secret",
        re.compile(
            r"\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|APPLICATION[_-]?PASSWORD)[A-Z0-9_]*\s*=\s*)['\"]?(?!\[REDACTED\])[^'\"\s]{8,}"
        ),
    ),
    ("openai_anthropic_key", re.compile(r"\b(?:sk-proj-|sk-|sk-ant-)[A-Za-z0-9._-]{8,}\b")),
    ("github_or_slack_token", re.compile(r"\b(?:xox[baprs]-|gh[pousr]_|eyJ)[A-Za-z0-9._-]{12,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key_value", re.compile(r"(?i)(aws_secret_access_key\s*[=:]\s*)['\"]?(?!\[REDACTED\])[A-Za-z0-9/+=]{20,}['\"]?")),
    ("private_key_header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for name, pattern in SECRET_PATTERNS:
        replacement = _redact_url if name == "signed_url" else _replacement
        redacted = pattern.sub(replacement, redacted)
    return redacted


def secret_severity(pattern: str) -> str:
    if pattern in {
        "gcp_service_account_json",
        "private_key_block",
        "private_key_header",
        "openai_anthropic_key",
        "aws_access_key",
        "aws_secret_key_value",
        "authorization_bearer",
        "bearer_token",
    }:
        return "high"
    if pattern in {"signed_url_query", "service_account_key_file", "x_api_key_header", "cookie_header", "env_secret"}:
        return "medium"
    return "low"


def scan_text_for_secrets(text: str, *, path: str = "") -> list[SecretHit]:
    hits: list[SecretHit] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in SCAN_PATTERNS:
            for match in pattern.finditer(line):
                if REDACTION in match.group(0):
                    continue
                hits.append(SecretHit(path=path, pattern=name, line=line_no))
    return hits


def scan_path_for_secrets(root: Path) -> list[SecretHit]:
    paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    hits: list[SecretHit] = []
    for path in paths:
        if path.suffix.lower() not in {".md", ".json", ".txt", ".csv", ".env"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits.extend(scan_text_for_secrets(text, path=str(path)))
    return hits


def secret_hits_to_json(hits: list[SecretHit]) -> str:
    return json.dumps([hit.__dict__ for hit in hits], indent=2, sort_keys=True)


def _replacement(match: re.Match[str]) -> str:
    if match.groups():
        return f"{match.group(1)}{REDACTION}"
    return REDACTION


def _redact_url(match: re.Match[str]) -> str:
    raw_url = match.group(0)
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return "[redacted malformed URL]"
    query_names = {name.lower() for name, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if not query_names.intersection(SIGNED_URL_MARKERS):
        return raw_url
    safe_path = redact_secrets(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")))
    if REDACTION in safe_path:
        return "[redacted signed URL]"
    return safe_path
