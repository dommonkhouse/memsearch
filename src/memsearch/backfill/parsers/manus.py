from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import BackfillManifestEntry, Conversation, SourceFile, Turn


def classify_manus_source(path: str | Path) -> str:
    path_obj = Path(path)
    text = str(path_obj)
    if "indexeddb.leveldb" in text.lower() or "IndexedDB" in path_obj.parts:
        return "indexeddb_probe_only"
    if "Cache" in path_obj.parts or "Cache_Data" in path_obj.parts or "GPUCache" in path_obj.parts:
        return "cache_probe_only"
    return "unknown_format"


def probe_manus_source(source: SourceFile) -> BackfillManifestEntry:
    reason = classify_manus_source(source.path)
    return BackfillManifestEntry.from_source_file(source, status="skipped", last_error=reason)


def dedupe_manus_probe_entries(entries: list[BackfillManifestEntry]) -> list[BackfillManifestEntry]:
    seen: set[str] = set()
    deduped: list[BackfillManifestEntry] = []
    for entry in entries:
        if entry.conversation_key and entry.conversation_key in seen:
            deduped.append(
                BackfillManifestEntry(
                    product=entry.product,
                    machine=entry.machine,
                    source_path=entry.source_path,
                    file_size=entry.file_size,
                    mtime=entry.mtime,
                    content_hash=entry.content_hash,
                    status="duplicate_conversation",
                    generated_output_path=entry.generated_output_path,
                    last_error="duplicate_conversation",
                    conversation_key=entry.conversation_key,
                    transcript_fingerprint=entry.transcript_fingerprint,
                )
            )
            continue
        if entry.conversation_key:
            seen.add(entry.conversation_key)
        deduped.append(entry)
    return deduped


def parse_manus_task(
    *,
    task: dict[str, Any],
    messages: list[dict[str, Any]],
    source_path: Path,
    machine: str,
    artifacts: list[dict[str, Any]] | None = None,
) -> Conversation:
    task_id = str(task.get("id") or "")
    source = SourceFile.from_path(source_path, product="manus_api", machine=machine, source_kind="api")
    turns = [_turn_from_message(message) for message in messages]
    turns = [turn for turn in turns if turn.text.strip()]
    return Conversation(
        source=source,
        product="manus_api",
        machine=machine,
        turns=turns,
        platform_id=task_id,
        title=str(task.get("title") or task_id),
        started_at=_iso_from_seconds(task.get("created_at")),
        ended_at=_iso_from_seconds(task.get("updated_at")),
        metadata={
            "task_id": task_id,
            "task_url": str(task.get("task_url") or f"https://manus.im/app/{task_id}"),
            "status": str(task.get("status") or ""),
            "task_type": str(task.get("task_type") or ""),
            "message_count": len(messages),
            "artifact_count": len(artifacts or []),
            "source": "manus_api",
            "exported_by_machine": machine,
        },
        artifacts=artifacts or [],
    )


def parse_staged_manus_task(task_dir: Path, *, machine: str) -> Conversation:
    task = json.loads((task_dir / "raw" / "task.json").read_text(encoding="utf-8"))
    messages_path = task_dir / "raw" / "messages.json"
    messages = json.loads(messages_path.read_text(encoding="utf-8"))
    manifest_path = task_dir.parent.parent / "manifest.json"
    artifacts: list[dict[str, Any]] = []
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("tasks", []):
            if entry.get("id") == task.get("id"):
                artifacts = entry.get("attachments", [])
                break
    return parse_manus_task(
        task=task, messages=messages, source_path=messages_path, machine=machine, artifacts=artifacts
    )


def _turn_from_message(message: dict[str, Any]) -> Turn:
    timestamp = str(message.get("timestamp") or "")
    event_type = str(message.get("type") or "")
    for role, key in [("user", "user_message"), ("assistant", "assistant_message"), ("error", "error_message")]:
        payload = message.get(key)
        if payload:
            text = _payload_text(payload)
            return Turn(role=role, text=text, timestamp=timestamp)
    if event_type == "status_update" and message.get("status_update"):
        return Turn(role="status", text=json.dumps(message["status_update"], sort_keys=True), timestamp=timestamp)
    if event_type in {
        "tool_used",
        "plan_update",
        "new_plan_step",
        "explanation",
        "structured_output_result",
        "user_stop",
    }:
        payload = message.get(event_type, {})
        return Turn(role=event_type, text=json.dumps(payload, sort_keys=True), timestamp=timestamp)
    return Turn(role=event_type or "event", text=json.dumps(message, sort_keys=True), timestamp=timestamp)


def _payload_text(payload: dict[str, Any]) -> str:
    if "content" in payload:
        return str(payload.get("content") or "")
    return json.dumps(payload, sort_keys=True)


def _iso_from_seconds(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""
