from __future__ import annotations

from memsearch.backfill.redact import redact_secrets


def test_redact_obvious_tokens() -> None:
    text = "Authorization: Bearer sk-test\nOPENAI_API_KEY=abc123"

    redacted = redact_secrets(text)

    assert "sk-test" not in redacted
    assert "abc123" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_cookie_and_application_password_values() -> None:
    text = "Cookie: sessionid=secret-cookie\nWP_APPLICATION_PASSWORD='wp-secret'"

    redacted = redact_secrets(text)

    assert "secret-cookie" not in redacted
    assert "wp-secret" not in redacted
    assert redacted.count("[REDACTED]") >= 2

