# Work summary file protocol

Read this reference before any write. It defines the managed Markdown contract; do not silently invent alternative paths, statuses, or markers.

## Root and paths

`work_summary_root` is the directory explicitly supplied by the user. If none is supplied, it is `<current-project-root>/work-summary`.

```text
<work_summary_root>/
├── 工作记录/YYYY/MM/DD/wrk_<UUIDv7>.md
├── 日报/YYYY/MM/YYYY-MM-DD 工作日报.md
└── 周报/YYYY/MM/YYYY-Www（MM月DD日-MM月DD日）工作周报.md
```

- Interpret dates in `Asia/Shanghai`.
- A week is Monday through Sunday and uses its ISO week ID.
- Store a weekly report under the year and month containing the week's Monday.
- A cross-month week has one report whose filename shows both boundary dates.
- An explicitly supplied root does not receive another `work-summary` suffix.

Use `scripts/work_summary_io.py paths` rather than recalculating these paths manually.

## Stable identity

- Generate a new ID once with `scripts/work_summary_io.py new-id`.
- Format: `wrk_<UUIDv7>`.
- Never derive or regenerate it from content, title, project, or path.
- Preserve it when updating a record.
- Stop if two files contain the same ID with different content or sources.

## Managed document shape

Every file created by the skill has system-managed YAML plus exactly one AI region and one human region:

```markdown
---
schema_version: 1
document_type: work_record
...
---

<!-- AI-MANAGED:START -->
AI-generated content
<!-- AI-MANAGED:END -->

<!-- HUMAN:START -->
Human additions
<!-- HUMAN:END -->
```

All frontmatter fields are system-managed. Do not put human notes in frontmatter or in the AI region. `write-document` stops rather than deleting an unknown frontmatter field or unmanaged body text.

Quote every free-text value, path, and timestamp in frontmatter. Leave only documented identifiers, dates, enums, and list `work_id` values unquoted. Timestamps must be valid RFC 3339 values with a timezone, and record times must be valid clock values in `HH:MM:SS+08:00` form.

## Work record

Required system properties:

```yaml
schema_version: 1
document_type: work_record
work_id: wrk_<UUIDv7>
date: YYYY-MM-DD
time: "HH:MM:SS+08:00"
project: "Project name"
work_type: development
source_ai: codex
source_ref: "current-task or supplied artifact"
status: UNVERIFIED
created_at: "RFC 3339 timestamp"
updated_at: "RFC 3339 timestamp"
```

`work_type` is one of:

```text
requirements
development
documentation
presentation
environment
research
collaboration
support
```

AI-managed headings:

```markdown
# 工作记录标题

## 工作目标
## 实际结果
## 产出物
## 关键决定
## 验证结果
## 风险与阻断
## 后续动作
## 证据
```

Keep `created_at` unchanged during an update. Update `updated_at` only when content changes.

## Daily report

Required system properties:

```yaml
schema_version: 1
document_type: daily_report
date: YYYY-MM-DD
week_id: YYYY-Www
weekly_report: "周报/YYYY/MM/YYYY-Www（MM月DD日-MM月DD日）工作周报.md"
source_work_ids:
  - wrk_<UUIDv7>
source_fingerprint: "sha256:<64 lowercase hex characters>"
generated_at: "RFC 3339 timestamp"
```

AI-managed headings:

```markdown
# YYYY-MM-DD 工作日报

## 今日结论
## 按目标汇总的工作
## 关键决定
## 产出物与验证
## 风险、阻断与待确认事项
## 后续动作
## 来源与对应周报
```

Each reported goal must identify its source `work_id` values. Regenerate the whole AI region when managed sources change; preserve the human region exactly.

`weekly_report` must exactly equal the normalized relative weekly path returned by `paths` for the report date.

## Weekly report

Required system properties:

```yaml
schema_version: 1
document_type: weekly_report
week_id: YYYY-Www
period_start: YYYY-MM-DD
period_end: YYYY-MM-DD
source_daily:
  - "日报/YYYY/MM/YYYY-MM-DD 工作日报.md"
source_work_ids:
  - wrk_<UUIDv7>
source_fingerprint: "sha256:<64 lowercase hex characters>"
generated_at: "RFC 3339 timestamp"
```

AI-managed headings:

```markdown
# YYYY-Www 工作周报

## 本周结论
## 按目标汇总的重点工作
## 产出物与验证
## 关键决定
## 能力与环境建设
## 结转事项、风险与阻断
## 下周计划
## 来源
```

Do not concatenate daily reports mechanically. Resolve the narrative against original records and preserve missing or conflicting evidence explicitly.

Every `source_daily` value must use the normalized relative form `日报/YYYY/MM/YYYY-MM-DD 工作日报.md`; its directory must match its date, and that date must fall within `period_start` through `period_end`.

## Update and stop rules

- Before generating a daily or weekly report, run `fingerprint-sources` over every authorized managed source file. It validates managed documents and rejects conflicting duplicate `work_id` values. Pass ordinary supplemental files explicitly authorized by the user with repeated `--supplement-file` arguments. For supplemental text supplied directly in the current task, write normalized text to a temporary file and pass it as a supplement.
- The stable `source_fingerprint` combines managed source identities and contents with supplement contents. Supplement paths are not part of the fingerprint, so identical normalized content remains stable when a different temporary path is used. Supplement bytes are hashed, not parsed or executed.
- Pass the same complete managed and supplemental input sets to `write-document` using the same flags. The helper recomputes the fingerprint and rejects mismatches involving `source_fingerprint`, `source_work_ids`, or `source_daily`.
- Same `source_fingerprint` and the same system properties other than `generated_at`: do not regenerate or write; preserve the existing `generated_at`. If another system property changed, update the report normally.
- New `work_id`: include it once.
- Existing changed record: regenerate the relevant AI region.
- Existing unchanged record: do not duplicate it.
- Missing evidence: use `UNVERIFIED` or another truthful non-complete status.
- Ambiguous goal merge: keep items separate or ask.
- Broken, missing, duplicated, nested, or reversed markers: stop.
- Unknown YAML property or non-whitespace body text outside the two regions: stop.
- Source read failure: name the path and do not treat it as empty content.
- Never upload, send, delete, or migrate as part of these actions.

## Helper commands

Run from the skill directory or use the script's absolute path.

```text
python scripts/work_summary_io.py new-id
python scripts/work_summary_io.py paths --root <root> --date YYYY-MM-DD [--work-id wrk_<UUIDv7>]
python scripts/work_summary_io.py fingerprint-sources --root <root> --source-file <source.md> [--source-file <source.md> ...] [--supplement-file <supplement> ...]
python scripts/work_summary_io.py write-document --root <root> --path <target.md> --frontmatter-file <yaml-body.txt> --managed-file <managed.md> [--source-file <source.md> ...] [--supplement-file <supplement> ...]
```

The helper accepts only the documented frontmatter subset and exact per-document schemas; malformed YAML, missing or undeclared properties, invalid values, paths outside the canonical root, and paths inconsistent with the document identity are rejected. Work-record writes do not use report source or supplement flags. Daily reports require their exact work-record sources; weekly reports require their exact daily-report sources and every original work record named by those daily reports. Supplements may be outside `work_summary_root` only when the current call explicitly authorizes those exact files; they never authorize directory traversal or discovery. `write-document` creates missing parent directories only for the resolved target, preserves a valid existing human region, prints `created`, `updated`, or `unchanged`, and fails without writing when safety checks fail.
