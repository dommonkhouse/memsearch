from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
USER_PATH_RE = re.compile(r"/Users/[^/\s]+/[^\s]+")
WHITESPACE_RE = re.compile(r"\s+")

MACHINE_NAME_ALIASES = {
    "Dominics-Mac-mini": "Dominic's Mac Mini",
    "Dominics-Macbook": "Dominic's MacBook",
    "dominics-mac-mini": "Dominic's Mac Mini",
    "dominics-macbook": "Dominic's MacBook",
}


def normalise_machine_name(machine: str) -> str:
    return MACHINE_NAME_ALIASES.get(machine, machine)


def machine_slug(machine: str) -> str:
    normalised = normalise_machine_name(machine)
    cleaned = normalised.replace("'", "").lower()
    return re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return f"sha256:{h.hexdigest()}"


@dataclass(frozen=True)
class SourceFile:
    path: Path
    product: str
    machine: str
    source_kind: str = "local"
    is_fallback: bool = False
    status: str = "pending"
    file_size: int = 0
    mtime: float = 0.0
    content_hash: str = ""

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        product: str,
        machine: str,
        source_kind: str = "local",
        is_fallback: bool = False,
        status: str = "pending",
    ) -> SourceFile:
        resolved = path.expanduser()
        stat = resolved.stat()
        return cls(
            path=resolved,
            product=product,
            machine=normalise_machine_name(machine),
            source_kind=source_kind,
            is_fallback=is_fallback,
            status=status,
            file_size=stat.st_size,
            mtime=stat.st_mtime,
            content_hash=file_sha256(resolved),
        )

    def to_manifest_entry(self, *, conversation_key: str = "", status: str | None = None) -> BackfillManifestEntry:
        return BackfillManifestEntry.from_source_file(self, conversation_key=conversation_key, status=status or self.status)


@dataclass(frozen=True)
class Turn:
    role: str
    text: str
    timestamp: str = ""

    def normalised_for_fingerprint(self) -> str:
        role = self.role.strip().lower()
        text = UUID_RE.sub("", self.text)
        text = USER_PATH_RE.sub("[PATH]", text)
        text = WHITESPACE_RE.sub(" ", text).strip()
        return f"{role}: {text}"


@dataclass(frozen=True)
class Conversation:
    source: SourceFile
    product: str
    machine: str
    turns: list[Turn]
    platform_id: str = ""
    title: str = ""
    started_at: str = ""
    ended_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def conversation_key(self) -> str:
        if self.platform_id:
            return f"platform:{self.platform_id}"
        if self.source.path:
            return f"source:{self.product}:{machine_slug(self.machine)}:{self.source.path}"
        return f"fingerprint:{self.transcript_fingerprint()}"

    def fingerprint_turns(self) -> list[Turn]:
        return [turn for turn in self.turns if turn.role.strip().lower() in {"user", "assistant"}][:20]

    def normalised_fingerprint_text(self) -> str:
        return "\n".join(turn.normalised_for_fingerprint() for turn in self.fingerprint_turns())

    def transcript_fingerprint(self) -> str:
        return "sha256:" + hashlib.sha256(self.normalised_fingerprint_text().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BackfillManifestEntry:
    product: str
    machine: str
    source_path: str
    file_size: int
    mtime: float
    content_hash: str
    status: str
    generated_output_path: str = ""
    last_error: str = ""
    conversation_key: str = ""
    transcript_fingerprint: str = ""

    @classmethod
    def from_source_file(
        cls,
        source: SourceFile,
        *,
        conversation_key: str = "",
        status: str = "pending",
        generated_output_path: str = "",
        last_error: str = "",
        transcript_fingerprint: str = "",
    ) -> BackfillManifestEntry:
        return cls(
            product=source.product,
            machine=normalise_machine_name(source.machine),
            source_path=str(source.path),
            file_size=source.file_size,
            mtime=source.mtime,
            content_hash=source.content_hash,
            status=status,
            generated_output_path=generated_output_path,
            last_error=last_error,
            conversation_key=conversation_key,
            transcript_fingerprint=transcript_fingerprint,
        )

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BackfillManifestEntry:
        allowed = cls.__dataclass_fields__.keys()
        values = {k: data.get(k, "") for k in allowed}
        values["file_size"] = int(values["file_size"] or 0)
        values["mtime"] = float(values["mtime"] or 0.0)
        values["machine"] = normalise_machine_name(str(values["machine"]))
        return cls(**values)


@dataclass(frozen=True)
class HistoricalSourceAnchor:
    product: str
    session_id: str
    transcript_path: str
    machine: str
    fingerprint: str | None = None


@dataclass(frozen=True)
class HistoricalSourceIndex:
    by_source_path: dict[str, HistoricalSourceAnchor] = field(default_factory=dict)
    by_transcript_path: dict[str, HistoricalSourceAnchor] = field(default_factory=dict)
    by_session_id: dict[str, HistoricalSourceAnchor] = field(default_factory=dict)
    by_fingerprint: dict[str, HistoricalSourceAnchor] = field(default_factory=dict)


@dataclass(frozen=True)
class BackfillRunSummary:
    scanned: int = 0
    converted: int = 0
    already_imported: int = 0
    skipped: int = 0
    errors: int = 0


def loose_jsonl_conversation(path: Path, *, product: str, machine: str) -> Conversation:
    turns: list[Turn] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = str(row.get("type") or row.get("role") or row.get("author") or "")
            text = _extract_text(row.get("message", row.get("content", row.get("text", ""))))
            if role and text:
                turns.append(Turn(role=role, text=text))
    source = SourceFile.from_path(path, product=product, machine=machine)
    return Conversation(source=source, product=product, machine=machine, turns=turns)


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_extract_text(item) for item in value if _extract_text(item)).strip()
    if isinstance(value, dict):
        if "text" in value:
            return _extract_text(value["text"])
        if "content" in value:
            return _extract_text(value["content"])
    return ""
