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


def test_redact_computer_session_file_links() -> None:
    text = "Here you go: [key](computer:///sessions/name/mnt/outputs/service-account-key.json)"

    redacted = redact_secrets(text)

    assert "computer:///sessions" not in redacted
    assert "service-account-key.json" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_service_account_key_filenames() -> None:
    text = "ga4-service-account-key.json i need it"

    redacted = redact_secrets(text)

    assert "service-account-key.json" not in redacted
    assert "[REDACTED]" in redacted
