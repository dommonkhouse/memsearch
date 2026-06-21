from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from .parsers.manus import parse_manus_task, parse_staged_manus_task
from .redact import REDACTOR_VERSION, redact_secrets, scan_path_for_secrets, secret_severity
from .render import output_path_for_conversation, render_conversation

API_BASE_URL = "https://api.manus.ai/v2"
TRUSTED_ATTACHMENT_HOSTS = ("manus.ai", "manus.im")


class ManusApiError(RuntimeError):
    pass


class ManusPromotionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManusAttachmentDownload:
    filename: str
    content_type: str
    bytes: int
    sha256: str
    status: str
    error: str
    local_path: str
    message_timestamp: str
    side: str


class ManusApiClient:
    def __init__(self, api_key: str | None = None, *, base_url: str = API_BASE_URL, transport: Any | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("MANUS_API_KEY", "")
        if not self.api_key:
            raise ManusApiError("MANUS_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self._transport = transport

    def list_tasks_page(self, *, limit: int = 100, cursor: str = "", order: str = "desc", scope: str = "all") -> dict[str, Any]:
        return self._get_json("task.list", {"limit": limit, "cursor": cursor, "order": order, "scope": scope})

    def iter_tasks(self, *, page_limit: int = 100, order: str = "desc", scope: str = "all", max_tasks: int | None = None) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        cursor = ""
        while True:
            page = self.list_tasks_page(limit=page_limit, cursor=cursor, order=order, scope=scope)
            for task in page.get("data") or page.get("tasks") or []:
                tasks.append(task)
                if max_tasks is not None and len(tasks) >= max_tasks:
                    return tasks
            if not page.get("has_more"):
                return tasks
            cursor = str(page.get("next_cursor") or "")
            if not cursor:
                return tasks

    def list_messages_page(
        self,
        task_id: str,
        *,
        limit: int = 200,
        cursor: str = "",
        order: str = "asc",
        verbose: bool = True,
        slides_format: str = "pptx",
    ) -> dict[str, Any]:
        return self._get_json(
            "task.listMessages",
            {
                "task_id": task_id,
                "limit": limit,
                "cursor": cursor,
                "order": order,
                "verbose": "true" if verbose else "false",
                "slides_format": slides_format,
            },
        )

    def iter_messages(self, task_id: str, *, page_limit: int = 200) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        cursor = ""
        while True:
            page = self.list_messages_page(task_id, limit=page_limit, cursor=cursor)
            messages.extend(page.get("messages") or page.get("data") or [])
            if not page.get("has_more"):
                return messages
            cursor = str(page.get("next_cursor") or "")
            if not cursor:
                return messages

    def download_attachment(self, url: str, destination: Path) -> ManusAttachmentDownload:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            body, content_type = self._download(url, include_auth=False)
        except ManusApiError as first_error:
            if not _trusted_attachment_url(url):
                return _failed_download(destination, str(first_error))
            try:
                body, content_type = self._download(url, include_auth=True)
            except ManusApiError as second_error:
                return _failed_download(destination, str(second_error))
        destination.write_bytes(body)
        return ManusAttachmentDownload(
            filename=destination.name,
            content_type=content_type,
            bytes=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            status="downloaded",
            error="",
            local_path=str(destination),
            message_timestamp="",
            side="",
        )

    def _get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        query = urlencode({k: v for k, v in params.items() if v not in {"", None}})
        full_url = f"{url}?{query}" if query else url
        payload = self._request("GET", full_url, include_auth=True)
        data = json.loads(payload.decode("utf-8"))
        if data.get("ok") is False:
            raise ManusApiError("Manus API returned ok=false")
        return data

    def _download(self, url: str, *, include_auth: bool) -> tuple[bytes, str]:
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                response = client.get(url, headers=self._headers(include_auth=include_auth))
            if response.status_code >= 400:
                raise ManusApiError(f"attachment download failed with HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "application/octet-stream")
            return response.content, content_type
        except (httpx.HTTPError, ValueError) as exc:
            raise ManusApiError("attachment download failed") from exc

    def _request(self, method: str, url: str, *, include_auth: bool) -> bytes:
        if method != "GET":
            raise ManusApiError("Manus export client is read-only")
        if self._transport is not None:
            return self._transport(method, url, self._headers(include_auth=include_auth))
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60, follow_redirects=True) as client:
                    response = client.get(url, headers=self._headers(include_auth=include_auth))
                if response.status_code in {401, 403}:
                    raise ManusApiError(f"Manus API auth/scope error: HTTP {response.status_code}")
                if response.status_code not in {408, 429, 500, 502, 503, 504} and response.status_code >= 400:
                    raise ManusApiError(f"Manus API request failed: HTTP {response.status_code}")
                if response.status_code < 400:
                    return response.content
                last_error = ManusApiError(f"Manus API request failed: HTTP {response.status_code}")
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.5 * (attempt + 1))
        raise ManusApiError("Manus API request failed after retries") from last_error

    def _headers(self, *, include_auth: bool) -> dict[str, str]:
        headers = {"accept": "application/json", "user-agent": "memsearch-chat-backfill/0.1"}
        if include_auth:
            headers["x-manus-api-key"] = self.api_key
        return headers


def export_manus_run(
    client: ManusApiClient,
    output_root: Path,
    *,
    machine: str,
    limit: int | None = None,
    run_id: str | None = None,
    resume: bool = False,
    task_ids: list[str] | None = None,
) -> dict[str, Any]:
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / run_id
    tasks_dir = run_dir / "tasks"
    memory_dir = run_dir / "memory"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    existing_manifest = _read_json(run_dir / "manifest.json") if resume and (run_dir / "manifest.json").is_file() else {}
    manifest_tasks_by_id = {str(task.get("id") or ""): task for task in existing_manifest.get("tasks", [])}
    errors_by_task = {str(error.get("task_id") or ""): error for error in existing_manifest.get("errors", [])}
    tasks = client.iter_tasks(max_tasks=limit)
    if task_ids is not None:
        wanted = set(task_ids)
        tasks = [task for task in tasks if str(task.get("id") or "") in wanted]

    for task in tasks:
        task_id = str(task.get("id") or "")
        if not task_id:
            continue
        if resume and task_id in manifest_tasks_by_id:
            continue
        task_dir = tasks_dir / f"{_slug(task.get('title') or task_id)}-{task_id}"
        raw_dir = task_dir / "raw"
        attachment_dir = task_dir / "attachments"
        raw_dir.mkdir(parents=True, exist_ok=True)
        try:
            messages = client.iter_messages(task_id)
            attachments = _download_task_attachments(client, messages, attachment_dir)
            _write_json(raw_dir / "task.json", task)
            _write_json(raw_dir / "messages.json", _messages_without_urls(messages))
            conversation = parse_manus_task(
                task=task,
                messages=messages,
                source_path=raw_dir / "messages.json",
                machine=machine,
                artifacts=[attachment.__dict__ for attachment in attachments],
            )
            transcript_path = task_dir / "transcript.md"
            transcript_path.write_text(render_conversation(conversation), encoding="utf-8")
            output_path = output_path_for_conversation(memory_dir, conversation)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            existing = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
            output_path.write_text(existing + render_conversation(conversation), encoding="utf-8")
            manifest_tasks_by_id[task_id] = {
                "id": task_id,
                "title": redact_secrets(str(task.get("title") or "")),
                "status": task.get("status", ""),
                "created_at": task.get("created_at", ""),
                "updated_at": task.get("updated_at", ""),
                "task_type": task.get("task_type", ""),
                "task_url": task.get("task_url", ""),
                "task_dir": str(task_dir),
                "transcript_path": str(transcript_path),
                "memory_path": str(output_path),
                "message_events": len(messages),
                "attachments_total": len(attachments),
                "attachments_downloaded": sum(1 for attachment in attachments if attachment.status == "downloaded"),
                "attachments": [attachment.__dict__ for attachment in attachments],
                "transcript_fingerprint": conversation.transcript_fingerprint(),
            }
            errors_by_task.pop(task_id, None)
        except Exception as exc:
            errors_by_task[task_id] = {"task_id": task_id, "error": str(exc)}

    manifest_tasks = list(manifest_tasks_by_id.values())
    errors = list(errors_by_task.values())
    total_messages = sum(int(task.get("message_events") or 0) for task in manifest_tasks)
    total_attachments = sum(int(task.get("attachments_total") or 0) for task in manifest_tasks)
    downloaded_attachments = sum(int(task.get("attachments_downloaded") or 0) for task in manifest_tasks)

    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_manus_api_export",
        "resumed": resume,
        "task_limit": limit,
        "tasks_returned": len(tasks),
        "tasks_converted": len(manifest_tasks),
        "message_events": total_messages,
        "attachments_total": total_attachments,
        "attachments_downloaded": downloaded_attachments,
        "tasks": manifest_tasks,
        "errors": errors,
    }
    _write_json(run_dir / "manifest.json", manifest)
    summary = {
        "run_id": run_id,
        "output_dir": str(run_dir),
        "manifest_path": str(run_dir / "manifest.json"),
        "tasks_returned": len(tasks),
        "tasks_converted": len(manifest_tasks),
        "errors": len(errors),
        "message_events": total_messages,
        "attachments_total": total_attachments,
        "attachments_downloaded": downloaded_attachments,
    }
    _write_json(run_dir / "summary.json", summary)
    return summary


def estimate_manus_export(client: ManusApiClient) -> dict[str, Any]:
    tasks = client.iter_tasks()
    statuses: dict[str, int] = {}
    attachments_available = 0
    for task in tasks:
        status = str(task.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        if task.get("attachments"):
            attachments_available += len(task.get("attachments") or [])
    return {
        "tasks": len(tasks),
        "statuses": statuses,
        "attachments_visible_in_task_list": attachments_available,
        "estimated_minutes": max(30, round(len(tasks) * 0.2)),
    }


def verify_manus_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return [f"missing manifest: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for task in manifest.get("tasks", []):
        errors.extend(
            f"task missing {key}: {task.get('id', '<unknown>')}"
            for key in ["id", "transcript_path", "task_dir"]
            if not task.get(key)
        )
        transcript = Path(task.get("transcript_path", ""))
        if not transcript.is_file():
            errors.append(f"missing transcript: {transcript}")
        for attachment in task.get("attachments", []):
            if attachment.get("status") != "downloaded":
                continue
            path = Path(attachment.get("local_path", ""))
            if not path.is_file():
                errors.append(f"missing attachment: {path}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != attachment.get("sha256"):
                errors.append(f"checksum mismatch: {path}")
    return errors


def promote_manus_run(run_dir: Path, output_dir: Path, *, force: bool = False, file_soft_cap: int = 500_000) -> dict[str, Any]:
    run_dir = run_dir.expanduser()
    output_dir = output_dir.expanduser()
    if not run_dir.is_dir():
        raise ManusPromotionError(f"missing Manus run: {run_dir}")
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise ManusPromotionError(f"refusing to overwrite non-empty output: {output_dir}")
    if force and output_dir.exists():
        _empty_directory(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_errors = verify_manus_run(run_dir)
    if validation_errors:
        raise ManusPromotionError("Manus run verification failed: " + "; ".join(validation_errors[:5]))

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    run_id = str(manifest.get("run_id") or run_dir.name)
    raw_hits = scan_path_for_secrets(run_dir)
    hit_records = _excluded_secret_records(raw_hits, run_dir, manifest)
    hit_attachment_paths = {
        record["_source_path"]
        for record in hit_records
        if record.get("source_kind") == "attachment" and record.get("_source_path")
    }
    public_hit_records = [{key: value for key, value in record.items() if not key.startswith("_")} for record in hit_records]

    sections_by_month: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    source_task_map: dict[str, dict[str, Any]] = {}
    rendered_task_count = 0
    excluded_attachment_count = 0
    rendered_attachment_metadata_count = 0

    for task in sorted(manifest.get("tasks", []), key=lambda item: str(item.get("created_at") or "")):
        task_id = str(task.get("id") or "")
        task_dir = Path(str(task.get("task_dir") or ""))
        if not task_id or not task_dir.is_dir():
            continue
        conversation = parse_staged_manus_task(task_dir, machine="manus_cloud")
        safe_artifacts: list[dict[str, Any]] = []
        excluded_artifacts: list[dict[str, Any]] = []
        for artifact in conversation.artifacts:
            raw_path = str(artifact.get("local_path") or "")
            safe_artifact = _redact_mapping(artifact)
            if raw_path in hit_attachment_paths:
                safe_artifact["status"] = "excluded_secret"
                excluded_artifacts.append(safe_artifact)
                excluded_attachment_count += 1
                continue
            safe_artifacts.append(safe_artifact)
            rendered_attachment_metadata_count += 1

        safe_conversation = conversation.__class__(
            source=conversation.source,
            product=conversation.product,
            machine="manus_cloud",
            turns=conversation.turns,
            platform_id=conversation.platform_id,
            title=redact_secrets(conversation.title),
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            metadata=_redact_mapping(conversation.metadata),
            artifacts=safe_artifacts,
        )
        section = render_conversation(safe_conversation)
        section += _render_excluded_artifacts(excluded_artifacts)
        month = _month_from_timestamp(safe_conversation.started_at)
        sections_by_month[month].append((task_id, section, redact_secrets(_relative_or_name(task_dir, run_dir))))
        rendered_task_count += 1

    markdown_files, source_task_map = _write_promoted_markdown(output_dir, sections_by_month, file_soft_cap=file_soft_cap)

    promotion_manifest = {
        "run_id": run_id,
        "source_run_path": str(run_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "redactor_version": REDACTOR_VERSION,
        "task_count": len(manifest.get("tasks", [])),
        "rendered_task_count": rendered_task_count,
        "excluded_task_count": 0,
        "attachment_count": sum(int(task.get("attachments_total") or 0) for task in manifest.get("tasks", [])),
        "rendered_attachment_metadata_count": rendered_attachment_metadata_count,
        "excluded_attachment_count": excluded_attachment_count,
        "markdown_files": markdown_files,
        "source_task_map": source_task_map,
        "failed_validation": False,
    }
    rotation_report = _rotation_report(public_hit_records, run_id)
    summary = {
        "run_id": run_id,
        "source_run_path": str(run_dir),
        "output_dir": str(output_dir),
        "raw_secret_hits": len(public_hit_records),
        "markdown_files": len(markdown_files),
        "rendered_task_count": rendered_task_count,
        "excluded_attachment_count": excluded_attachment_count,
        "rotation_ack_required": bool(hit_records),
    }

    _write_json(output_dir / "promotion-manifest.json", promotion_manifest)
    _write_json(output_dir / "excluded-secrets.json", public_hit_records)
    _write_json(output_dir / "rotation-report.json", rotation_report)
    (output_dir / "rotation-report.md").write_text(_render_rotation_report_markdown(rotation_report), encoding="utf-8")
    _write_json(output_dir / "summary.json", summary)
    return summary


def generate_manus_memsearch_cards(promoted_dir: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    promoted_dir = promoted_dir.expanduser()
    output_dir = output_dir.expanduser()
    if not promoted_dir.is_dir():
        raise ManusPromotionError(f"missing promoted Manus run: {promoted_dir}")
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise ManusPromotionError(f"refusing to overwrite non-empty output: {output_dir}")
    if force and output_dir.exists():
        _empty_directory(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_root = promoted_dir / "memory" / "manus_cloud" / "manus_api"
    if not source_root.is_dir():
        raise ManusPromotionError(f"missing promoted Manus markdown root: {source_root}")
    output_root = output_dir / "memory" / "manus_cloud" / "manus_api"
    output_root.mkdir(parents=True, exist_ok=True)

    markdown_files: list[dict[str, Any]] = []
    task_ids: set[str] = set()
    card_count = 0

    for source_file in sorted(source_root.glob("*.md")):
        cards: list[str] = []
        for title, body in _split_manus_sessions(source_file.read_text(encoding="utf-8")):
            card = _render_manus_memsearch_card(title, body, source_file.resolve())
            cards.append(card)
            card_count += 1
            task_id = _extract_line_value(card, "Manus task ID")
            if task_id:
                task_ids.add(task_id)
        output_file = output_root / source_file.name
        text = "\n".join(cards).rstrip() + ("\n" if cards else "")
        output_file.write_text(text, encoding="utf-8")
        markdown_files.append(
            {
                "path": str(output_file),
                "byte_size": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )

    summary = {
        "source_promoted_path": str(promoted_dir),
        "output_dir": str(output_dir),
        "markdown_files": len(markdown_files),
        "task_cards": card_count,
        "unique_task_ids": len(task_ids),
        "card_format": "manus_session_card_v1",
    }
    _write_json(
        output_dir / "card-manifest.json",
        {
            **summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "redactor_version": REDACTOR_VERSION,
            "files": markdown_files,
            "task_ids": sorted(task_ids),
        },
    )
    _write_json(output_dir / "summary.json", summary)
    return summary


def mark_manus_run_not_indexed(run_dir: Path, *, reason: str) -> Path:
    note_path = run_dir / "WHY-NOT-INDEXED.md"
    note_path.write_text(
        "\n".join(
            [
                "# Why this Manus run is not indexed",
                "",
                f"- Run: `{run_dir.name}`",
                f"- Marked at: `{datetime.now(timezone.utc).isoformat()}`",
                f"- Reason: {redact_secrets(reason)}",
                "",
                "This raw export is retained for evidence only. It must not be passed to MemSearch indexing.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return note_path


def _split_manus_sessions(text: str) -> list[tuple[str, str]]:
    sessions: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## Manus Api session "):
            if current_title:
                sessions.append((current_title, "\n".join(current_lines)))
            current_title = line.removeprefix("## ").strip()
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)
    if current_title:
        sessions.append((current_title, "\n".join(current_lines)))
    return sessions


def _render_manus_memsearch_card(title: str, body: str, full_transcript_path: Path) -> str:
    preamble, events = _split_manus_events(body)
    users: list[str] = []
    assistants: list[str] = []
    notes: list[str] = []
    tools: list[tuple[str, str]] = []
    for kind, event_body in events:
        if kind == "User":
            users.append(event_body.strip())
        elif kind == "Assistant":
            assistants.append(event_body.strip())
        elif kind in {"Explanation", "Plan_Update", "New_Plan_Step", "Status"}:
            text = _event_json_to_text(event_body)
            if text:
                notes.append(text)
        elif kind == "Tool_Used":
            tools.append(_tool_event_bits(event_body))

    tool_counts = Counter(tool for tool, _ in tools)
    tool_hints = _unique_non_empty(hint for _, hint in tools)
    lines = [
        f"## {redact_secrets(title)}",
        f"- Full cleaned transcript: `{redact_secrets(str(full_transcript_path))}`",
    ]
    for label in [
        "Manus task ID",
        "Manus task URL",
        "Time range",
        "Manus status",
        "Manus message events",
        "Manus artefacts",
    ]:
        value = _extract_line_value(preamble, label)
        if value:
            display_label = "Message events" if label == "Manus message events" else "Artefacts" if label == "Manus artefacts" else label
            lines.append(f"- {display_label}: {redact_secrets(value)}")
    if tool_counts:
        lines.append("- Tools used: " + ", ".join(f"{redact_secrets(tool)} ({count})" for tool, count in tool_counts.most_common(10)))
    lines.append("")

    if users:
        lines.append("User requests:")
        lines.extend(_bullet_items(users, per_item_limit=1000, max_items=4))
        if len(users) > 4:
            lines.append(f"- Additional user messages: {len(users) - 4}")
        lines.append("")
    if assistants:
        lines.append("Assistant outcomes:")
        lines.extend(_bullet_items(assistants[-3:], per_item_limit=900, max_items=3))
        if len(assistants) > 3:
            lines.append(f"- Earlier assistant messages: {len(assistants) - 3}")
        lines.append("")
    if notes:
        lines.append("Progress notes:")
        lines.extend(_bullet_items(notes, per_item_limit=450, max_items=5))
        lines.append("")
    if tool_hints:
        lines.append("Tool/action hints:")
        lines.extend(_bullet_items(tool_hints, per_item_limit=220, max_items=8))
        lines.append("")
    lines.append("---")
    return "\n".join(lines)


def _split_manus_events(body: str) -> tuple[str, list[tuple[str, str]]]:
    event_re = re.compile(r"^### (User|Assistant|Explanation|Plan_Update|New_Plan_Step|Status|Tool_Used) \d+\s*$")
    preamble: list[str] = []
    events: list[tuple[str, str]] = []
    current_kind = ""
    current_lines: list[str] = []
    for line in body.splitlines():
        match = event_re.match(line)
        if match:
            if current_kind:
                events.append((current_kind, "\n".join(current_lines)))
            else:
                preamble.extend(current_lines)
            current_kind = match.group(1)
            current_lines = []
            continue
        current_lines.append(line)
    if current_kind:
        events.append((current_kind, "\n".join(current_lines)))
    else:
        preamble.extend(current_lines)
    return "\n".join(preamble).strip(), events


def _event_json_to_text(body: str) -> str:
    text = body.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(data, dict):
        if "content" in data:
            return str(data.get("content") or "")
        if "title" in data:
            return str(data.get("title") or "")
        if "steps" in data:
            return "; ".join(
                f"{step.get('status', '')}: {step.get('title', '')}"
                for step in data.get("steps", [])
                if isinstance(step, dict)
            )
    return _squash(text)


def _tool_event_bits(body: str) -> tuple[str, str]:
    try:
        data = json.loads(body.strip()) if body.strip() else {}
    except json.JSONDecodeError:
        return ("tool", "")
    if not isinstance(data, dict):
        return ("tool", "")
    message = data.get("message") if isinstance(data.get("message"), dict) else {}
    tool = str(data.get("tool") or message.get("tool") or data.get("action") or "tool")
    brief = str(data.get("brief") or "")
    description = str(data.get("description") or "")
    hint = brief if brief and brief != "No brief" else description
    return (_squash(tool), _squash(hint))


def _extract_line_value(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}: (.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _bullet_items(items: list[str], *, per_item_limit: int, max_items: int) -> list[str]:
    bullets: list[str] = []
    for item in items[:max_items]:
        clean = redact_secrets(_truncate(item.strip(), per_item_limit))
        if clean:
            bullets.append("- " + clean.replace("\n", "\n  "))
    return bullets


def _unique_non_empty(items: Any) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = str(item or "").strip()
        if clean and clean not in seen:
            values.append(clean)
            seen.add(clean)
    return values


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _empty_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _empty_directory(child)
            child.rmdir()
        else:
            child.unlink()


def _excluded_secret_records(hits: list[Any], run_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    attachment_by_path: dict[str, dict[str, Any]] = {}
    task_dirs: list[tuple[str, Path]] = []
    for task in manifest.get("tasks", []):
        task_id = str(task.get("id") or "")
        task_dir = Path(str(task.get("task_dir") or ""))
        if task_id and task_dir:
            task_dirs.append((task_id, task_dir))
        for attachment in task.get("attachments", []):
            local_path = str(attachment.get("local_path") or "")
            if local_path:
                attachment_by_path[local_path] = {"task_id": task_id, "sha256": attachment.get("sha256", "")}

    records: list[dict[str, Any]] = []
    for hit in hits:
        hit_path = Path(hit.path)
        source_task_id = ""
        source_kind = "run"
        source_checksum = ""
        if str(hit_path) in attachment_by_path:
            source_kind = "attachment"
            source_task_id = str(attachment_by_path[str(hit_path)]["task_id"])
            source_checksum = str(attachment_by_path[str(hit_path)]["sha256"])
        else:
            for task_id, task_dir in task_dirs:
                with _suppress_value_error():
                    hit_path.relative_to(task_dir)
                    source_task_id = task_id
                    source_kind = "task"
                    break
        records.append(
            {
                "detector": hit.pattern,
                "severity": secret_severity(hit.pattern),
                "source_task_id": source_task_id,
                "source_kind": source_kind,
                "source_artefact_checksum": source_checksum,
                "_source_path": str(hit_path),
                "redacted_relative_path": redact_secrets(_relative_or_name(hit_path, run_dir)),
                "line": hit.line,
                "classification_status": "unreviewed",
                "reason": "raw Manus export secret scan hit",
            }
        )
    return records


def _write_promoted_markdown(
    output_dir: Path,
    sections_by_month: dict[str, list[tuple[str, str, str]]],
    *,
    file_soft_cap: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    markdown_root = output_dir / "memory" / "manus_cloud" / "manus_api"
    markdown_root.mkdir(parents=True, exist_ok=True)
    markdown_files: list[dict[str, Any]] = []
    source_task_map: dict[str, dict[str, Any]] = {}

    for month, sections in sorted(sections_by_month.items()):
        part = 1
        current: list[tuple[str, str, str]] = []
        current_bytes = 0
        for task_id, section, raw_pointer in sections:
            section_bytes = len(section.encode("utf-8"))
            if current and current_bytes + section_bytes > file_soft_cap:
                _write_markdown_part(markdown_root, month, part, current, markdown_files, source_task_map)
                part += 1
                current = []
                current_bytes = 0
            current.append((task_id, section, raw_pointer))
            current_bytes += section_bytes
        if current:
            _write_markdown_part(markdown_root, month, part, current, markdown_files, source_task_map)
    return markdown_files, source_task_map


def _write_markdown_part(
    markdown_root: Path,
    month: str,
    part: int,
    sections: list[tuple[str, str, str]],
    markdown_files: list[dict[str, Any]],
    source_task_map: dict[str, dict[str, Any]],
) -> None:
    path = markdown_root / f"{month}-part{part}.md"
    lines: list[str] = []
    task_ids: list[str] = []
    for task_id, section, raw_pointer in sections:
        line_start = len(lines) + 1
        section_lines = section.rstrip().splitlines()
        lines.extend(section_lines)
        lines.append("")
        line_end = len(lines)
        task_ids.append(task_id)
        source_task_map[task_id] = {
            "markdown_file": str(path),
            "line_start": line_start,
            "line_end": line_end,
            "raw_archive_pointer": raw_pointer,
        }
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    markdown_files.append(
        {
            "path": str(path),
            "byte_size": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "task_ids": task_ids,
        }
    )


def _redact_mapping(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_redact_mapping(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_mapping(item) for key, item in value.items()}
    return value


def _render_excluded_artifacts(artifacts: list[dict[str, Any]]) -> str:
    if not artifacts:
        return ""
    lines = ["", "## Excluded artefacts", ""]
    for artifact in artifacts:
        filename = redact_secrets(str(artifact.get("filename") or "attachment"))
        sha256 = redact_secrets(str(artifact.get("sha256") or ""))
        lines.append(f"- {filename} (excluded_secret, sha256:{sha256})")
    return "\n".join(lines).rstrip() + "\n"


def _rotation_report(records: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[_credential_type(str(record.get("detector") or ""))].append(
            {
                "task_id": record.get("source_task_id", ""),
                "first_seen": "",
                "redacted_source_path": record.get("redacted_relative_path", ""),
                "detector": record.get("detector", ""),
                "severity": record.get("severity", ""),
                "classification_status": record.get("classification_status", "unreviewed"),
            }
        )
    return {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acknowledgement_required": bool(records),
        "acknowledgement_phrase": f"ROTATE-ACK {run_id}",
        "groups": dict(sorted(groups.items())),
    }


def _render_rotation_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Manus credential rotation report",
        "",
        f"- Run ID: `{report.get('run_id', '')}`",
        f"- Acknowledgement required: `{report.get('acknowledgement_required', False)}`",
        f"- Acknowledgement phrase: `{report.get('acknowledgement_phrase', '')}`",
        "",
    ]
    for group, records in report.get("groups", {}).items():
        lines.extend([f"## {group}", ""])
        lines.extend(
            (
                "- "
                + f"task `{record.get('task_id', '')}`; "
                + f"{record.get('detector', '')}; "
                + f"{record.get('severity', '')}; "
                + f"{record.get('redacted_source_path', '')}"
            )
            for record in records
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _credential_type(detector: str) -> str:
    if detector in {"gcp_service_account_json", "service_account_key_file"}:
        return "GCP service account"
    if detector == "openai_anthropic_key":
        return "OpenAI/API key"
    if detector in {"aws_access_key", "aws_secret_key_value"}:
        return "AWS credential"
    if detector in {"authorization_bearer", "bearer_token"}:
        return "generic bearer token"
    if detector in {"private_key_block", "private_key_header"}:
        return "PEM/private key"
    if detector == "signed_url_query":
        return "signed URL"
    return "other"


def _relative_or_name(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _month_from_timestamp(timestamp: str) -> str:
    if len(timestamp) >= 7 and timestamp[4] == "-":
        return timestamp[:7]
    return "unknown"


class _suppress_value_error:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return exc_type is ValueError


def _download_task_attachments(
    client: ManusApiClient,
    messages: list[dict[str, Any]],
    attachment_dir: Path,
) -> list[ManusAttachmentDownload]:
    attachments: list[ManusAttachmentDownload] = []
    used_names: set[str] = set()
    for message in messages:
        timestamp = str(message.get("timestamp") or "")
        for side in ("user_message", "assistant_message"):
            payload = message.get(side) or {}
            for attachment in payload.get("attachments") or []:
                filename = _safe_filename(str(attachment.get("filename") or "attachment"))
                filename = _dedupe_filename(filename, used_names)
                used_names.add(filename)
                url = str(attachment.get("url") or "")
                if not url:
                    attachments.append(
                        ManusAttachmentDownload(
                            filename=filename,
                            content_type=str(attachment.get("content_type") or ""),
                            bytes=0,
                            sha256="",
                            status="missing_url",
                            error="missing_url",
                            local_path="",
                            message_timestamp=timestamp,
                            side=side,
                        )
                    )
                    continue
                downloaded = client.download_attachment(url, attachment_dir / filename)
                attachments.append(
                    ManusAttachmentDownload(
                        filename=filename,
                        content_type=str(attachment.get("content_type") or downloaded.content_type),
                        bytes=downloaded.bytes,
                        sha256=downloaded.sha256,
                        status=downloaded.status,
                        error=downloaded.error,
                        local_path=downloaded.local_path,
                        message_timestamp=timestamp,
                        side=side,
                    )
                )
    return attachments


def _messages_without_urls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = json.loads(json.dumps(messages))
    for message in sanitized:
        for side in ("user_message", "assistant_message"):
            for attachment in (message.get(side) or {}).get("attachments") or []:
                if "url" in attachment:
                    attachment["url"] = "[signed-url-omitted]"
    return sanitized


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _trusted_attachment_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    return any(host == trusted or host.endswith(f".{trusted}") for trusted in TRUSTED_ATTACHMENT_HOSTS)


def _failed_download(destination: Path, error: str) -> ManusAttachmentDownload:
    return ManusAttachmentDownload(
        filename=destination.name,
        content_type="",
        bytes=0,
        sha256="",
        status="failed",
        error=error,
        local_path="",
        message_timestamp="",
        side="",
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or "task"


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(value).name).strip(".-")
    return name or "attachment"


def _dedupe_filename(filename: str, used_names: set[str]) -> str:
    normalised_names = {name.casefold() for name in used_names}
    if filename.casefold() not in normalised_names:
        return filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 2
    while True:
        candidate = f"{stem}-{index}{suffix}"
        if candidate.casefold() not in normalised_names:
            return candidate
        index += 1


def _iso_from_seconds(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""
