from __future__ import annotations

from memsearch.backfill.redact import redact_secrets, scan_path_for_secrets


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


def test_scan_path_checks_markdown_and_json(tmp_path) -> None:
    (tmp_path / "safe.md").write_text("hello", encoding="utf-8")
    (tmp_path / "manifest.json").write_text('{"token": "GITHUB_TOKEN=ghp_abcdefghijklmnop"}', encoding="utf-8")

    hits = scan_path_for_secrets(tmp_path)

    assert hits
    assert {hit.path for hit in hits} == {str(tmp_path / "manifest.json")}


def test_redact_signed_urls_strips_secret_query() -> None:
    text = "Download https://storage.example.com/report.pdf?X-Amz-Signature=secret&X-Amz-Expires=60"

    redacted = redact_secrets(text)

    assert "X-Amz-Signature" not in redacted
    assert "secret" not in redacted
    assert "https://storage.example.com/report.pdf" in redacted


def test_redact_malformed_url_like_text_does_not_raise() -> None:
    text = "Broken link https://[bad"

    redacted = redact_secrets(text)

    assert "[redacted malformed URL]" in redacted


def test_redact_private_key_block_and_service_account_json() -> None:
    text = """
{"type":"service_account","private_key":"-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"}
"""

    redacted = redact_secrets(text)

    assert "service_account" not in redacted
    assert "PRIVATE KEY" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_common_cloud_key_patterns() -> None:
    text = "sk-proj-abcdefghijklmnop AKIAABCDEFGHIJKLMNOP aws_secret_access_key=abcdabcdabcdabcdabcdabcd"

    redacted = redact_secrets(text)

    assert "sk-proj-" not in redacted
    assert "AKIAABCDEFGHIJKLMNOP" not in redacted
    assert "abcdabcdabcdabcdabcdabcd" not in redacted
