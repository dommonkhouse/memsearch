from __future__ import annotations

import json
from pathlib import Path

import pytest

from memsearch.backfill.manus_api import (
    ManusApiClient,
    ManusAttachmentDownload,
    ManusPromotionError,
    export_manus_run,
    generate_manus_memsearch_cards,
    promote_manus_run,
    verify_manus_run,
)
from memsearch.backfill.redact import scan_path_for_secrets

FIXTURES = Path(__file__).parent / "fixtures" / "manus_api"


def load_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_client_paginates_tasks_with_get_only() -> None:
    calls: list[tuple[str, str, dict[str, str]]] = []

    def transport(method: str, url: str, headers: dict[str, str]) -> bytes:
        calls.append((method, url, headers))
        if "cursor=cursor-2" in url:
            return load_fixture("tasks_page_2.json")
        return load_fixture("tasks_page_1.json")

    client = ManusApiClient(api_key="test-key", transport=transport)

    tasks = client.iter_tasks(page_limit=1)

    assert [task["id"] for task in tasks] == ["task-alpha", "task-beta"]
    assert {method for method, _, _ in calls} == {"GET"}
    assert all(headers["x-manus-api-key"] == "test-key" for _, _, headers in calls)


def test_export_writes_staged_task_manifest_transcript_and_deduped_attachments(tmp_path: Path) -> None:
    class FakeClient:
        def iter_tasks(self, max_tasks: int | None = None) -> list[dict]:
            page = json.loads(load_fixture("tasks_page_1.json"))
            return page["data"][:max_tasks]

        def iter_messages(self, task_id: str) -> list[dict]:
            assert task_id == "task-alpha"
            return json.loads(load_fixture("messages_task_alpha.json"))["messages"]

        def download_attachment(self, url: str, destination: Path) -> ManusAttachmentDownload:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f"downloaded from {url}", encoding="utf-8")
            payload = destination.read_bytes()
            import hashlib

            return ManusAttachmentDownload(
                filename=destination.name,
                content_type="text/markdown",
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                status="downloaded",
                error="",
                local_path=str(destination),
                message_timestamp="",
                side="",
            )

    summary = export_manus_run(FakeClient(), tmp_path, machine="Test Mac", limit=1, run_id="run-1")
    run_dir = tmp_path / "run-1"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    transcript = next((run_dir / "tasks").glob("*/transcript.md")).read_text(encoding="utf-8")
    raw_messages = next((run_dir / "tasks").glob("*/raw/messages.json")).read_text(encoding="utf-8")

    assert summary["tasks_converted"] == 1
    assert manifest["tasks"][0]["attachments_total"] == 3
    assert [a["filename"] for a in manifest["tasks"][0]["attachments"]] == ["notes.md", "notes-2.md", "NOTES-3.md"]
    assert "backfill-agent:manus_api task:task-alpha source:manus_api" in transcript
    assert "https://download.manus.im" not in transcript
    assert "https://download.manus.im" not in json.dumps(manifest)
    assert "[signed-url-omitted]" in raw_messages
    assert verify_manus_run(run_dir) == []


def test_export_resume_retries_failed_tasks_without_reprocessing_successes(tmp_path: Path) -> None:
    class FlakyClient:
        def __init__(self) -> None:
            self.fail_beta = True
            self.message_calls: list[str] = []

        def iter_tasks(self, max_tasks: int | None = None) -> list[dict]:
            return [
                {"id": "task-alpha", "title": "Alpha task", "created_at": "1780390415", "updated_at": "1780390534"},
                {"id": "task-beta", "title": "Beta task", "created_at": "1780390593", "updated_at": "1780390633"},
            ][:max_tasks]

        def iter_messages(self, task_id: str) -> list[dict]:
            self.message_calls.append(task_id)
            if task_id == "task-beta" and self.fail_beta:
                raise RuntimeError("temporary Manus API failure")
            return json.loads(load_fixture("messages_task_alpha.json"))["messages"][:1]

        def download_attachment(self, url: str, destination: Path) -> ManusAttachmentDownload:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("safe attachment", encoding="utf-8")
            payload = destination.read_bytes()
            import hashlib

            return ManusAttachmentDownload(
                filename=destination.name,
                content_type="text/markdown",
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                status="downloaded",
                error="",
                local_path=str(destination),
                message_timestamp="",
                side="",
            )

    client = FlakyClient()
    first = export_manus_run(client, tmp_path, machine="Test Mac", run_id="run-resume")
    client.fail_beta = False
    client.message_calls.clear()
    second = export_manus_run(client, tmp_path, machine="Test Mac", run_id="run-resume", resume=True)

    assert first["tasks_converted"] == 1
    assert first["errors"] == 1
    assert client.message_calls == ["task-beta"]
    assert second["tasks_converted"] == 2
    assert second["errors"] == 0


def test_export_records_invalid_attachment_url_without_failing_task(tmp_path: Path) -> None:
    class BadAttachmentClient:
        def iter_tasks(self, max_tasks: int | None = None) -> list[dict]:
            return [{"id": "task-bad-url", "title": "Bad URL", "created_at": "1780390415", "updated_at": "1780390534"}]

        def iter_messages(self, task_id: str) -> list[dict]:
            return [
                {
                    "timestamp": "1780390415452",
                    "type": "message",
                    "user_message": {
                        "content": "bad attachment",
                        "attachments": [{"filename": "bad.txt", "content_type": "text/plain", "url": "https://[bad"}],
                    },
                }
            ]

        def download_attachment(self, url: str, destination: Path) -> ManusAttachmentDownload:
            return ManusApiClient(api_key="test-key", transport=lambda method, request_url, headers: b"{}").download_attachment(
                url,
                destination,
            )

    summary = export_manus_run(BadAttachmentClient(), tmp_path, machine="Test Mac", run_id="run-bad-url")
    manifest = json.loads((tmp_path / "run-bad-url" / "manifest.json").read_text(encoding="utf-8"))

    assert summary["tasks_converted"] == 1
    assert summary["errors"] == 0
    assert manifest["tasks"][0]["attachments"][0]["status"] == "failed"


def test_promote_creates_sanitised_indexable_layer_and_reports_exclusions(tmp_path: Path) -> None:
    class FakeClient:
        def iter_tasks(self, max_tasks: int | None = None) -> list[dict]:
            page = json.loads(load_fixture("tasks_page_1.json"))
            task = dict(page["data"][0])
            task["title"] = "Alpha sk-proj-abcdefghijklmnop"
            return [task]

        def iter_messages(self, task_id: str) -> list[dict]:
            messages = json.loads(load_fixture("messages_task_alpha.json"))["messages"]
            messages[0]["user_message"]["content"] = "Use Authorization: Bearer secretbearertoken123"
            return messages

        def download_attachment(self, url: str, destination: Path) -> ManusAttachmentDownload:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if url.endswith("signed-alpha"):
                destination.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----", encoding="utf-8")
            else:
                destination.write_text(f"downloaded from {url}", encoding="utf-8")
            payload = destination.read_bytes()
            import hashlib

            return ManusAttachmentDownload(
                filename=destination.name,
                content_type="text/markdown",
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                status="downloaded",
                error="",
                local_path=str(destination),
                message_timestamp="",
                side="",
            )

    export_manus_run(FakeClient(), tmp_path / "raw", machine="Test Mac", limit=1, run_id="run-secret")
    run_dir = tmp_path / "raw" / "run-secret"
    output = tmp_path / "indexable" / "run-secret"

    summary = promote_manus_run(run_dir, output)
    markdown = next((output / "memory" / "manus_cloud" / "manus_api").glob("*.md")).read_text(encoding="utf-8")
    excluded = json.loads((output / "excluded-secrets.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "promotion-manifest.json").read_text(encoding="utf-8"))
    rotation = json.loads((output / "rotation-report.json").read_text(encoding="utf-8"))

    assert summary["raw_secret_hits"] > 0
    assert "backfill-agent:manus_api task:task-alpha source:manus_api" in markdown
    assert "secretbearertoken123" not in markdown
    assert "sk-proj-" not in markdown
    assert "PRIVATE KEY" not in markdown
    assert "excluded_secret" in markdown
    assert "memory/manus_cloud/manus_api" in manifest["markdown_files"][0]["path"]
    assert manifest["source_task_map"]["task-alpha"]["raw_archive_pointer"]
    assert all("source_path" not in record for record in excluded)
    assert "secretbearertoken123" not in json.dumps(excluded)
    assert rotation["acknowledgement_phrase"] == "ROTATE-ACK run-secret"
    assert scan_path_for_secrets(output) == []

    with pytest.raises(ManusPromotionError):
        promote_manus_run(run_dir, output)

    card_output = tmp_path / "cards" / "run-secret"
    card_summary = generate_manus_memsearch_cards(output, card_output)
    card_markdown = next((card_output / "memory" / "manus_cloud" / "manus_api").glob("*.md")).read_text(encoding="utf-8")
    card_manifest = json.loads((card_output / "card-manifest.json").read_text(encoding="utf-8"))

    assert card_summary["task_cards"] == 1
    assert card_summary["unique_task_ids"] == 1
    assert card_manifest["task_ids"] == ["task-alpha"]
    assert card_markdown.count("## Manus Api session") == 1
    assert card_markdown.count("Manus task ID: task-alpha") == 1
    assert "Full cleaned transcript:" in card_markdown
    assert str(next((output / "memory" / "manus_cloud" / "manus_api").glob("*.md")).resolve()) in card_markdown
    assert "secretbearertoken123" not in card_markdown
    assert "sk-proj-" not in card_markdown
