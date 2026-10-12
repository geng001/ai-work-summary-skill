#!/usr/bin/env python3
"""Deterministic IDs, paths, source checks, and safe managed Markdown writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import tempfile
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath


AI_START = "<!-- AI-MANAGED:START -->"
AI_END = "<!-- AI-MANAGED:END -->"
HUMAN_START = "<!-- HUMAN:START -->"
HUMAN_END = "<!-- HUMAN:END -->"
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))$")
LIST_ITEM_RE = re.compile(r"^  -(?:\s+(.*))?$")
WORK_ID_RE = re.compile(r"^wrk_([0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\+08:00$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PLAIN_SCALAR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+@-]*$")
DAILY_REPORT_PATH_RE = re.compile(
    r"^日报/(\d{4})/(\d{2})/(\d{4}-\d{2}-\d{2}) 工作日报\.md$"
)

STATUSES = {"COMPLETED", "IN_PROGRESS", "BLOCKED", "PENDING_CONFIRMATION", "UNVERIFIED"}
WORK_TYPES = {
    "requirements", "development", "documentation", "presentation",
    "environment", "research", "collaboration", "support",
}
DOCUMENT_TYPE_LABELS = {
    "work_record": "工作记录",
    "daily_report": "工作日报",
    "weekly_report": "工作周报",
}
STATUS_LABELS = {
    "COMPLETED": "已完成",
    "IN_PROGRESS": "进行中",
    "BLOCKED": "已阻塞",
    "PENDING_CONFIRMATION": "待确认",
    "UNVERIFIED": "未验证",
}
WORK_TYPE_LABELS = {
    "requirements": "需求分析",
    "development": "开发实现",
    "documentation": "文档整理",
    "presentation": "演示与汇报",
    "environment": "环境配置",
    "research": "调研分析",
    "collaboration": "协作沟通",
    "support": "支持与排障",
}
SCHEMAS = {
    "work_record": {
        "schema_version", "document_type", "work_id", "date", "project",
        "work_type", "source_ai", "source_ref", "status", "created_at", "updated_at",
    },
    "daily_report": {
        "schema_version", "document_type", "date", "week_id", "weekly_report",
        "source_work_ids", "source_fingerprint", "generated_at",
    },
    "weekly_report": {
        "schema_version", "document_type", "week_id", "period_start", "period_end",
        "source_daily", "source_work_ids", "source_fingerprint", "generated_at",
    },
}
OPTIONAL_FIELDS = {
    "work_record": {"time"},
}
LIST_FIELDS = {"source_work_ids", "source_daily"}
PLAIN_SCALAR_FIELDS = {
    "schema_version", "document_type", "work_id", "date", "work_type",
    "source_ai", "status", "week_id", "period_start", "period_end",
    "source_work_ids",
}


class SafetyError(ValueError):
    """Raised when an existing document cannot be updated safely."""


def make_uuid7(timestamp_ms: int | None = None) -> str:
    """Return an RFC 9562 UUIDv7 with a work-record prefix."""
    if timestamp_ms is None:
        timestamp_ms = time.time_ns() // 1_000_000
    if not 0 <= timestamp_ms < 1 << 48:
        raise ValueError("timestamp milliseconds must fit in 48 bits")

    value = timestamp_ms << 80
    value |= 0x7 << 76
    value |= secrets.randbits(12) << 64
    value |= 0b10 << 62
    value |= secrets.randbits(62)
    return f"wrk_{uuid.UUID(int=value)}"


def validate_work_id(value: str) -> str:
    match = WORK_ID_RE.fullmatch(value)
    if not match:
        raise SafetyError("work_id must be wrk_<UUIDv7>")
    parsed = uuid.UUID(match.group(1))
    if parsed.version != 7 or parsed.variant != uuid.RFC_4122:
        raise SafetyError("work_id must contain an RFC 9562 UUIDv7")
    return value


def canonical(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def require_within(root: Path, candidate: Path, label: str) -> Path:
    resolved_root = canonical(root)
    resolved_candidate = canonical(candidate)
    try:
        common = Path(os.path.commonpath((resolved_root, resolved_candidate)))
    except ValueError as exc:
        raise SafetyError(f"{label} is outside work_summary_root") from exc
    if os.path.normcase(str(common)) != os.path.normcase(str(resolved_root)):
        raise SafetyError(f"{label} is outside work_summary_root")
    return resolved_candidate


def report_paths(root: Path, target_date: date, work_id: str | None) -> dict[str, str | None]:
    root = canonical(root)
    if work_id is not None:
        validate_work_id(work_id)
    iso_year, iso_week, _ = target_date.isocalendar()
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)
    week_id = f"{iso_year}-W{iso_week:02d}"
    weekly_name = (
        f"{week_id}（{week_start:%m月%d日}-{week_end:%m月%d日}）工作周报.md"
    )

    record_dir = root / "工作记录" / f"{target_date:%Y}" / f"{target_date:%m}" / f"{target_date:%d}"
    daily_path = root / "日报" / f"{target_date:%Y}" / f"{target_date:%m}" / f"{target_date:%Y-%m-%d} 工作日报.md"
    weekly_path = root / "周报" / f"{week_start:%Y}" / f"{week_start:%m}" / weekly_name

    return {
        "work_summary_root": str(root),
        "record_dir": str(record_dir),
        "record_path": str(record_dir / f"{work_id}.md") if work_id else None,
        "daily_path": str(daily_path),
        "week_id": week_id,
        "period_start": week_start.isoformat(),
        "period_end": week_end.isoformat(),
        "weekly_path": str(weekly_path),
    }


def parse_scalar(raw: str, key: str) -> str | int:
    if not raw:
        raise SafetyError(f"YAML property {key} requires a scalar value")
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SafetyError(f"invalid quoted YAML scalar for {key}") from exc
        if not isinstance(value, str):
            raise SafetyError(f"YAML property {key} must be a string")
        return value
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            raise SafetyError(f"invalid quoted YAML scalar for {key}")
        inner = raw[1:-1]
        if "'" in inner.replace("''", ""):
            raise SafetyError(f"invalid quoted YAML scalar for {key}")
        return inner.replace("''", "'")
    if raw == "1" and key == "schema_version":
        return 1
    if key not in PLAIN_SCALAR_FIELDS:
        raise SafetyError(f"YAML property {key} must use a quoted string")
    if not PLAIN_SCALAR_RE.fullmatch(raw) or raw.lower() in {"null", "true", "false", "yes", "no", "on", "off"}:
        raise SafetyError(f"unsupported unquoted YAML scalar for {key}")
    return raw


def parse_frontmatter(frontmatter: str) -> dict[str, object]:
    """Parse the deliberately small, dependency-free YAML subset used by this Skill."""
    data: dict[str, object] = {}
    active_list: str | None = None
    for number, line in enumerate(frontmatter.splitlines(), 1):
        if not line.strip():
            continue
        if line.startswith("\t") or line.rstrip() != line:
            raise SafetyError(f"unsupported YAML whitespace on line {number}")
        list_match = LIST_ITEM_RE.fullmatch(line)
        if list_match:
            if active_list is None:
                raise SafetyError(f"unexpected YAML list item on line {number}")
            item = parse_scalar(list_match.group(1) or "", active_list)
            assert isinstance(data[active_list], list)
            data[active_list].append(item)
            continue
        if line.startswith(" "):
            raise SafetyError(f"unsupported nested YAML on line {number}")
        match = KEY_RE.fullmatch(line)
        if not match:
            raise SafetyError(f"invalid YAML on line {number}")
        key, raw = match.groups()
        if key in data:
            raise SafetyError(f"duplicate top-level YAML key: {key}")
        if key in LIST_FIELDS:
            if raw:
                raise SafetyError(f"YAML list {key} must use indented list items")
            data[key] = []
            active_list = key
        else:
            data[key] = parse_scalar(raw, key)
            active_list = None
    if not data:
        raise SafetyError("frontmatter is empty")
    validate_frontmatter(data)
    return data


def require_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise SafetyError(f"YAML property {key} must be a non-empty string")
    return value


def parse_date_value(value: str, key: str) -> date:
    if not DATE_RE.fullmatch(value):
        raise SafetyError(f"YAML property {key} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SafetyError(f"YAML property {key} is not a valid date") from exc


def validate_timestamp(value: str, key: str) -> None:
    if not RFC3339_RE.fullmatch(value):
        raise SafetyError(f"YAML property {key} must be an RFC 3339 timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SafetyError(f"YAML property {key} must be an RFC 3339 timestamp") from exc
    if parsed.utcoffset() is None:
        raise SafetyError(f"YAML property {key} must include a timezone")


def display_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    beijing = parsed.astimezone(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y-%m-%d %H:%M:%S（北京时间）")


def display_record_time(value: str) -> str:
    parsed = datetime.strptime(value, "%H:%M:%S%z")
    return parsed.strftime("%H:%M:%S（北京时间）")


def summary_block(managed: str, heading: str) -> list[str]:
    lines = [line.strip() for line in managed.splitlines()]
    if lines.count(heading) != 1:
        raise SafetyError(f"AI-managed content must contain exactly one {heading}")
    start = lines.index(heading) + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")), len(lines))
    return [line for line in lines[start:end] if line]


def validate_readable_managed_content(data: dict[str, object], managed: str) -> None:
    """Keep the Chinese display layer synchronized with machine frontmatter."""
    lines = [line.strip() for line in managed.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("# ") or lines[0].startswith("## "):
        raise SafetyError("AI-managed content must start with one human-readable H1 title")
    title = lines[0][2:].strip()
    if not title:
        raise SafetyError("AI-managed H1 title must not be empty")

    document_type = str(data["document_type"])
    if title in {str(data.get("work_id", "")), "工作记录标题"}:
        raise SafetyError("work record H1 title must describe the work instead of repeating an ID or placeholder")

    if document_type == "work_record":
        block = summary_block(managed, "## 记录摘要")
        if "time" in data:
            time_line = f"- 工作时间：{display_record_time(str(data['time']))}"
        else:
            time_line = "- 工作时间：时刻未记录"
        time_lines = [line for line in block if line.startswith("- 工作时间：")]
        if time_lines != [time_line]:
            raise SafetyError("AI-managed summary time does not match frontmatter")
        required = {
            f"- 文档类型：{DOCUMENT_TYPE_LABELS[document_type]}（{document_type}）",
            f"- 工作类型：{WORK_TYPE_LABELS[str(data['work_type'])]}（{data['work_type']}）",
            f"- 当前状态：{STATUS_LABELS[str(data['status'])]}（{data['status']}）",
            f"- 工作日期：{data['date']}",
            time_line,
            f"- 创建时间：{display_timestamp(str(data['created_at']))}",
            f"- 更新时间：{display_timestamp(str(data['updated_at']))}",
        }
    elif document_type == "daily_report":
        block = summary_block(managed, "## 报告摘要")
        required = {
            f"- 文档类型：{DOCUMENT_TYPE_LABELS[document_type]}（{document_type}）",
            f"- 报告日期：{data['date']}",
            f"- 对应周次：{data['week_id']}",
            f"- 生成时间：{display_timestamp(str(data['generated_at']))}",
        }
    else:
        block = summary_block(managed, "## 报告摘要")
        required = {
            f"- 文档类型：{DOCUMENT_TYPE_LABELS[document_type]}（{document_type}）",
            f"- 对应周次：{data['week_id']}",
            f"- 报告周期：{data['period_start']} 至 {data['period_end']}",
            f"- 生成时间：{display_timestamp(str(data['generated_at']))}",
        }

    missing = sorted(required - set(block))
    if missing:
        raise SafetyError("AI-managed summary is missing or inconsistent: " + "; ".join(missing))


def validate_string_list(data: dict[str, object], key: str, item_validator=None) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise SafetyError(f"YAML property {key} must be a non-empty string list")
    result = list(value)
    if len(result) != len(set(result)):
        raise SafetyError(f"YAML property {key} contains duplicate values")
    if item_validator:
        for item in result:
            item_validator(item)
    return result


def validate_frontmatter(data: dict[str, object]) -> None:
    if data.get("schema_version") != 1:
        raise SafetyError("schema_version must be 1")
    document_type = require_string(data, "document_type")
    expected = SCHEMAS.get(document_type)
    if expected is None:
        raise SafetyError(f"unsupported document_type: {document_type}")
    actual = set(data)
    allowed = expected | OPTIONAL_FIELDS.get(document_type, set())
    missing = sorted(expected - actual)
    unknown = sorted(actual - allowed)
    if missing:
        raise SafetyError("missing required YAML properties: " + ", ".join(missing))
    if unknown:
        raise SafetyError("undeclared YAML properties: " + ", ".join(unknown))

    if document_type == "work_record":
        validate_work_id(require_string(data, "work_id"))
        parse_date_value(require_string(data, "date"), "date")
        if "time" in data:
            time_value = require_string(data, "time")
            if not TIME_RE.fullmatch(time_value):
                raise SafetyError("time must use HH:MM:SS+08:00")
            try:
                datetime.strptime(time_value, "%H:%M:%S%z")
            except ValueError as exc:
                raise SafetyError("time must contain a valid clock time") from exc
        if require_string(data, "work_type") not in WORK_TYPES:
            raise SafetyError("work_type is not allowed")
        if require_string(data, "status") not in STATUSES:
            raise SafetyError("status is not allowed")
        for key in ("project", "source_ai", "source_ref"):
            require_string(data, key)
        for key in ("created_at", "updated_at"):
            validate_timestamp(require_string(data, key), key)
    elif document_type == "daily_report":
        target_date = parse_date_value(require_string(data, "date"), "date")
        expected_week = f"{target_date.isocalendar().year}-W{target_date.isocalendar().week:02d}"
        if require_string(data, "week_id") != expected_week:
            raise SafetyError("week_id does not match date")
        require_string(data, "weekly_report")
        validate_string_list(data, "source_work_ids", validate_work_id)
        if not FINGERPRINT_RE.fullmatch(require_string(data, "source_fingerprint")):
            raise SafetyError("source_fingerprint must use sha256:<64 lowercase hex characters>")
        validate_timestamp(require_string(data, "generated_at"), "generated_at")
    else:
        period_start = parse_date_value(require_string(data, "period_start"), "period_start")
        period_end = parse_date_value(require_string(data, "period_end"), "period_end")
        if period_end != period_start + timedelta(days=6) or period_start.weekday() != 0:
            raise SafetyError("weekly period must run Monday through Sunday")
        expected_week = f"{period_start.isocalendar().year}-W{period_start.isocalendar().week:02d}"
        if require_string(data, "week_id") != expected_week:
            raise SafetyError("week_id does not match period_start")
        validate_string_list(data, "source_daily")
        validate_string_list(data, "source_work_ids", validate_work_id)
        if not FINGERPRINT_RE.fullmatch(require_string(data, "source_fingerprint")):
            raise SafetyError("source_fingerprint must use sha256:<64 lowercase hex characters>")
        validate_timestamp(require_string(data, "generated_at"), "generated_at")


def parse_managed_document(text: str) -> tuple[dict[str, object], str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SafetyError("file has missing or invalid YAML frontmatter")
    data = parse_frontmatter(match.group(1))
    for marker in (AI_START, AI_END, HUMAN_START, HUMAN_END):
        if text.count(marker) != 1:
            raise SafetyError(f"file must contain exactly one {marker}")
    ai_start = text.index(AI_START, match.end())
    ai_end = text.index(AI_END, ai_start + len(AI_START))
    human_start = text.index(HUMAN_START, ai_end + len(AI_END))
    human_end = text.index(HUMAN_END, human_start + len(HUMAN_START))
    if not (match.end() <= ai_start < ai_end < human_start < human_end):
        raise SafetyError("managed and human markers are reversed or nested")
    if text[match.end():ai_start].strip():
        raise SafetyError("unmanaged content exists before the AI-managed region")
    if text[ai_end + len(AI_END):human_start].strip():
        raise SafetyError("unmanaged content exists between managed and human regions")
    if text[human_end + len(HUMAN_END):].strip():
        raise SafetyError("unmanaged content exists after the human region")
    managed_inner = text[ai_start + len(AI_START):ai_end]
    human_inner = text[human_start + len(HUMAN_START):human_end]
    return data, managed_inner, human_inner


def expected_target(root: Path, data: dict[str, object]) -> Path:
    document_type = str(data["document_type"])
    if document_type == "work_record":
        target_date = date.fromisoformat(str(data["date"]))
        expected = report_paths(root, target_date, str(data["work_id"]))["record_path"]
    elif document_type == "daily_report":
        target_date = date.fromisoformat(str(data["date"]))
        expected = report_paths(root, target_date, None)["daily_path"]
    else:
        target_date = date.fromisoformat(str(data["period_start"]))
        expected = report_paths(root, target_date, None)["weekly_path"]
    assert expected is not None
    return canonical(Path(expected))


def validate_relationship_paths(root: Path, data: dict[str, object]) -> None:
    document_type = str(data["document_type"])
    if document_type == "daily_report":
        target_date = date.fromisoformat(str(data["date"]))
        weekly_path = report_paths(root, target_date, None)["weekly_path"]
        assert weekly_path is not None
        expected = canonical(Path(weekly_path)).relative_to(canonical(root)).as_posix()
        if data["weekly_report"] != expected:
            raise SafetyError("weekly_report does not match the report path for date")
        return
    if document_type != "weekly_report":
        return

    period_start = date.fromisoformat(str(data["period_start"]))
    period_end = date.fromisoformat(str(data["period_end"]))
    for source in data["source_daily"]:
        assert isinstance(source, str)
        match = DAILY_REPORT_PATH_RE.fullmatch(source)
        if not match:
            raise SafetyError("source_daily must use 日报/YYYY/MM/YYYY-MM-DD 工作日报.md")
        source_date = parse_date_value(match.group(3), "source_daily date")
        if match.group(1) != f"{source_date:%Y}" or match.group(2) != f"{source_date:%m}":
            raise SafetyError("source_daily directory does not match its report date")
        if not period_start <= source_date <= period_end:
            raise SafetyError("source_daily date is outside the weekly period")
        relative = PurePosixPath(source)
        require_within(root, canonical(root).joinpath(*relative.parts), "source_daily path")


def build_document(frontmatter: str, managed: str, human_inner: str) -> str:
    frontmatter = frontmatter.strip("\r\n")
    managed = managed.strip("\r\n")
    return (
        f"---\n{frontmatter}\n---\n\n"
        f"{AI_START}\n{managed}\n{AI_END}\n\n"
        f"{HUMAN_START}{human_inner}{HUMAN_END}\n"
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def read_utf8_exact(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def fingerprint_sources(
    root: Path, sources: list[Path], supplement_files: list[Path] | None = None
) -> dict[str, object]:
    root = canonical(root)
    if not sources:
        raise SafetyError("at least one source file is required")
    entries: list[tuple[str, bytes]] = []
    supplement_entries: list[bytes] = []
    supplement_paths: set[str] = set()
    work_ids: dict[str, tuple[Path, str, str]] = {}
    for source in sources:
        resolved = require_within(root, source, "source file")
        if not resolved.is_file():
            raise SafetyError(f"source file does not exist: {source}")
        raw = resolved.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafetyError(f"source file is not valid UTF-8: {source}") from exc
        data, _, _ = parse_managed_document(text)
        validate_relationship_paths(root, data)
        if data["document_type"] == "work_record":
            work_id = str(data["work_id"])
            content_hash = hashlib.sha256(raw).hexdigest()
            source_ref = str(data["source_ref"])
            previous = work_ids.get(work_id)
            if previous and (previous[1] != content_hash or previous[2] != source_ref):
                raise SafetyError(f"conflicting duplicate work_id {work_id}: {previous[0]} and {resolved}")
            work_ids[work_id] = (resolved, content_hash, source_ref)
        relative = resolved.relative_to(root).as_posix()
        entries.append((relative, raw))
    for supplement in supplement_files or []:
        resolved = canonical(supplement)
        key = os.path.normcase(str(resolved))
        if key in supplement_paths:
            raise SafetyError(f"duplicate supplement file: {supplement}")
        supplement_paths.add(key)
        if not resolved.is_file():
            raise SafetyError(f"supplement file does not exist: {supplement}")
        supplement_entries.append(hashlib.sha256(resolved.read_bytes()).digest())
    sorted_entries = sorted(entries, key=lambda entry: entry[0].casefold())
    sorted_supplements = sorted(supplement_entries)
    digest = hashlib.sha256()
    for relative, raw in sorted_entries:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).digest())
        digest.update(b"\0")
    for supplement_hash in sorted_supplements:
        digest.update(b"supplement\0")
        digest.update(supplement_hash)
        digest.update(b"\0")
    return {
        "source_fingerprint": "sha256:" + digest.hexdigest(),
        "source_files": [relative for relative, _ in sorted_entries],
        "work_ids": sorted(work_ids),
        "supplement_fingerprints": ["sha256:" + value.hex() for value in sorted_supplements],
    }


def validate_report_source_binding(
    root: Path,
    data: dict[str, object],
    sources: list[Path],
    supplement_files: list[Path],
) -> None:
    """Bind report provenance fields to the exact managed sources used for its fingerprint."""
    document_type = str(data["document_type"])
    if document_type == "work_record":
        if sources or supplement_files:
            raise SafetyError("work records do not accept report source or supplement files")
        return
    if not sources:
        raise SafetyError("daily and weekly reports require the exact source files used")

    root = canonical(root)
    resolved_sources: list[Path] = []
    source_keys: set[str] = set()
    source_work_ids: set[str] = set()
    source_daily: set[str] = set()
    daily_work_ids: set[str] = set()
    target_date = date.fromisoformat(str(data["date"])) if document_type == "daily_report" else None
    period_start = (
        date.fromisoformat(str(data["period_start"])) if document_type == "weekly_report" else None
    )
    period_end = (
        date.fromisoformat(str(data["period_end"])) if document_type == "weekly_report" else None
    )

    for source in sources:
        resolved = require_within(root, source, "source file")
        key = os.path.normcase(str(resolved))
        if key in source_keys:
            raise SafetyError(f"duplicate source file: {source}")
        source_keys.add(key)
        if not resolved.is_file():
            raise SafetyError(f"source file does not exist: {source}")
        source_text = read_utf8_exact(resolved)
        source_data, _, _ = parse_managed_document(source_text)
        validate_relationship_paths(root, source_data)
        expected_source = expected_target(root, source_data)
        if os.path.normcase(str(resolved)) != os.path.normcase(str(expected_source)):
            raise SafetyError("source file path does not match its managed document identity")

        source_type = str(source_data["document_type"])
        source_date = date.fromisoformat(str(source_data["date"])) if source_type != "weekly_report" else None
        if document_type == "daily_report":
            if source_type != "work_record":
                raise SafetyError("daily reports accept only work records as source files")
            if source_date != target_date:
                raise SafetyError("daily report source work record date does not match report date")
            source_work_ids.add(str(source_data["work_id"]))
        else:
            assert period_start is not None and period_end is not None
            if source_type == "work_record":
                if source_date is None or not period_start <= source_date <= period_end:
                    raise SafetyError("weekly report source work record date is outside the weekly period")
                source_work_ids.add(str(source_data["work_id"]))
            elif source_type == "daily_report":
                if source_date is None or not period_start <= source_date <= period_end:
                    raise SafetyError("weekly report source daily date is outside the weekly period")
                source_daily.add(resolved.relative_to(root).as_posix())
                daily_work_ids.update(str(item) for item in source_data["source_work_ids"])
            else:
                raise SafetyError("weekly reports accept only daily reports and work records as source files")
        resolved_sources.append(resolved)

    declared_work_ids = set(data["source_work_ids"])
    if source_work_ids != declared_work_ids:
        raise SafetyError("source_work_ids do not match the actual source work records")
    if document_type == "weekly_report":
        if not source_daily:
            raise SafetyError("weekly reports require at least one source daily report")
        if not source_work_ids:
            raise SafetyError("weekly reports require at least one source work record")
        if daily_work_ids != source_work_ids:
            raise SafetyError(
                "source work records do not match the work IDs declared by the source daily reports"
            )
        if source_daily != set(data["source_daily"]):
            raise SafetyError("source_daily does not match the actual source daily reports")

    calculated = fingerprint_sources(root, resolved_sources, supplement_files)["source_fingerprint"]
    if data["source_fingerprint"] != calculated:
        raise SafetyError("source_fingerprint does not match the actual source files")


def write_document(
    root: Path,
    path: Path,
    frontmatter_file: Path,
    managed_file: Path,
    source_files: list[Path] | None = None,
    supplement_files: list[Path] | None = None,
) -> str:
    root = canonical(root)
    path = require_within(root, path, "target path")
    frontmatter = read_utf8_exact(frontmatter_file)
    managed = read_utf8_exact(managed_file)
    new_data = parse_frontmatter(frontmatter.strip("\r\n"))
    validate_readable_managed_content(new_data, managed)
    validate_relationship_paths(root, new_data)
    validate_report_source_binding(
        root,
        new_data,
        source_files or [],
        supplement_files or [],
    )
    expected = expected_target(root, new_data)
    if os.path.normcase(str(path)) != os.path.normcase(str(expected)):
        raise SafetyError(f"target path does not match the managed path for {new_data['document_type']}")

    if path.exists():
        old_text = read_utf8_exact(path)
        old_data, _, human_inner = parse_managed_document(old_text)
        if old_data["document_type"] != new_data["document_type"]:
            raise SafetyError("document_type cannot change during update")
        if new_data["document_type"] == "work_record":
            if old_data["work_id"] != new_data["work_id"]:
                raise SafetyError("work_id cannot change during update")
            if old_data["created_at"] != new_data["created_at"]:
                raise SafetyError("created_at cannot change during update")
        elif old_data["source_fingerprint"] == new_data["source_fingerprint"]:
            old_stable = {key: value for key, value in old_data.items() if key != "generated_at"}
            new_stable = {key: value for key, value in new_data.items() if key != "generated_at"}
            if old_stable == new_stable:
                return "unchanged"
        action_if_changed = "updated"
    else:
        old_text = None
        human_inner = "\n"
        action_if_changed = "created"

    new_text = build_document(frontmatter, managed, human_inner)
    if old_text == new_text:
        return "unchanged"

    atomic_write(path, new_text)
    return action_if_changed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_id = subparsers.add_parser("new-id", help="generate a wrk_-prefixed UUIDv7")
    new_id.add_argument("--timestamp-ms", type=int, help=argparse.SUPPRESS)

    paths = subparsers.add_parser("paths", help="calculate record, daily, and weekly paths")
    paths.add_argument("--root", required=True, type=Path)
    paths.add_argument("--date", required=True, type=date.fromisoformat)
    paths.add_argument("--work-id")

    fingerprint = subparsers.add_parser(
        "fingerprint-sources", help="validate sources and calculate a stable fingerprint"
    )
    fingerprint.add_argument("--root", required=True, type=Path)
    fingerprint.add_argument("--source-file", required=True, action="append", type=Path)
    fingerprint.add_argument("--supplement-file", action="append", type=Path)

    write = subparsers.add_parser("write-document", help="safely create or update a managed Markdown document")
    write.add_argument("--root", required=True, type=Path)
    write.add_argument("--path", required=True, type=Path)
    write.add_argument("--frontmatter-file", required=True, type=Path)
    write.add_argument("--managed-file", required=True, type=Path)
    write.add_argument("--source-file", action="append", type=Path)
    write.add_argument("--supplement-file", action="append", type=Path)

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        if args.command == "new-id":
            print(make_uuid7(args.timestamp_ms))
        elif args.command == "paths":
            print(json.dumps(report_paths(args.root, args.date, args.work_id), ensure_ascii=False, indent=2))
        elif args.command == "fingerprint-sources":
            print(
                json.dumps(
                    fingerprint_sources(
                        args.root,
                        args.source_file,
                        args.supplement_file,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "write-document":
            print(
                write_document(
                    args.root,
                    args.path,
                    args.frontmatter_file,
                    args.managed_file,
                    args.source_file,
                    args.supplement_file,
                )
            )
        else:
            raise AssertionError(f"unhandled command: {args.command}")
    except (OSError, ValueError, SafetyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
