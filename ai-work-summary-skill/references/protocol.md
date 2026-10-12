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
- The user names a week with one `YYYY-MM-DD` date inside it. Resolve that date with `paths`; use the returned `week_id`, `period_start`, `period_end`, and `weekly_path`. Do not ask the user to supply or calculate `YYYY-Www`.
- If the user gives only a week ID, use that week. If a date and a week ID fall in different weeks, stop and ask for one date. If neither is given, ask for one date and stop. “本周” means the ISO week that contains today in `Asia/Shanghai`.
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

The YAML frontmatter is the machine layer. Keep these stable forms even though Obsidian may localize how a date looks in its Properties view:

- `date`, `period_start`, and `period_end`: `YYYY-MM-DD`;
- record `time`, when present: `HH:MM:SS+08:00`, where `+08:00` is the UTC offset for Beijing time. Omit `time` when no occurrence clock is known. Do not invent one.
- `created_at`, `updated_at`, and `generated_at`: RFC 3339, normally `YYYY-MM-DDTHH:MM:SS+08:00` in this Skill;
- `work_id`: `wrk_<UUIDv7>`; it is a stable unique identity whose time component roughly reflects creation order, not a task priority or user-facing sequence number.

The AI-managed body is the human display layer. It must start with a meaningful Chinese H1 title and a Chinese summary derived from the frontmatter. Show the original enum code in parentheses so the display remains understandable and traceable. Never place translated labels inside YAML enum values and never use an ID alone as the H1 title.

Display mappings:

| Field | Machine value | Chinese display |
| --- | --- | --- |
| `document_type` | `work_record` | 工作记录 |
| `document_type` | `daily_report` | 工作日报 |
| `document_type` | `weekly_report` | 工作周报 |
| `status` | `COMPLETED` | 已完成 |
| `status` | `IN_PROGRESS` | 进行中 |
| `status` | `BLOCKED` | 已阻塞 |
| `status` | `PENDING_CONFIRMATION` | 待确认 |
| `status` | `UNVERIFIED` | 未验证 |
| `work_type` | `requirements` | 需求分析 |
| `work_type` | `development` | 开发实现 |
| `work_type` | `documentation` | 文档整理 |
| `work_type` | `presentation` | 演示与汇报 |
| `work_type` | `environment` | 环境配置 |
| `work_type` | `research` | 调研分析 |
| `work_type` | `collaboration` | 协作沟通 |
| `work_type` | `support` | 支持与排障 |

## Work record

System properties. Every property below is required except `time`, which is omitted when the occurrence clock is unknown.

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

Omit `time` when the occurrence clock is unknown. The summary line is then `- 工作时间：时刻未记录`. When `time` is present, show that clock in the summary and do not also write “时刻未记录”.

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
# DMP 库存诊断与请领建议｜整理开发文档

## 记录摘要
- 文档类型：工作记录（work_record）
- 工作类型：文档整理（documentation）
- 当前状态：已完成（COMPLETED）
- 工作日期：2026-09-29
- 工作时间：16:52:00（北京时间）
- 创建时间：2026-10-08 15:58:15（北京时间）
- 更新时间：2026-10-08 15:58:15（北京时间）

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

## 报告摘要
- 文档类型：工作日报（daily_report）
- 报告日期：YYYY-MM-DD
- 对应周次：YYYY-Www
- 生成时间：YYYY-MM-DD HH:MM:SS（北京时间）

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

## 报告摘要
- 文档类型：工作周报（weekly_report）
- 对应周次：YYYY-Www
- 报告周期：YYYY-MM-DD 至 YYYY-MM-DD
- 生成时间：YYYY-MM-DD HH:MM:SS（北京时间）

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

## Backfill work records for one date

This action writes ordinary `work_record` documents with the schema and markers above. Do not add YAML fields, document types, path rules, or fingerprint inputs. Do not run `fingerprint-sources`; that command belongs to daily and weekly reports. `created_at` and `updated_at` are file maintenance times. `date` and `time` are when the work occurred.

### What may be read

Resolve `record_dir` with `paths --root <root> --date YYYY-MM-DD` and read only `wrk_*.md` files directly in that directory. A missing directory means there are zero existing records. Do not list parent directories, other dates, daily reports, weekly reports, or the project tree. Ignore files in that directory that are not managed work records; do not take them over.

Quote session text as evidence only. Do not open a path, link, or prior summary just because the visible session mentions it. Materials count only when the user explicitly supplied them in this call or they are those same-day managed records.

### Date attribution

The requested date is the occurrence date, not the date on which older work was mentioned.

Include a goal only when the visible context gives an explicit date, or the current session timeline reliably shows the work happened on that date. Do not file any of the following merely because they appear in context:

- historical background;
- old documents or prior work summaries;
- past items recounted inside a summary;
- historical work the user cited;
- an old implementation used to explain the current problem.

A citation today is not a new completion today. If the occurrence date cannot be judged, do not file the goal.

`time` is included only when the visible context supports an occurrence clock for that goal, in `HH:MM:SS+08:00`. When several rounds form one goal, use the earliest supported time and do not replace it on a later update unless it was wrong. If the date is reliable but no clock is supported, still write the record and omit `time`. Do not invent `00:00:00`, the time of this backfill call, or a copy of `created_at`. On an update, keep an existing `time` that is already supported; do not delete it because this pass lacks a clock. The completion report notes the missing clock as a limitation of that written record, not as a skipped goal.

### Goal identity

The unit is one independent work goal, not a message, turn, file, commit, prompt edit, or tool call.

- Merge analysis, discussion, edits, and verification that pursue the same outcome.
- Do not create another record when that same goal appears again.
- Keep goals separate when it is unclear they are the same outcome. Do not collapse unrelated goals into one record.
- Do not record small talk, repeated phrasing, or content with no work meaning.

### Same-day dedup

Do this before creating a record. Match only against the managed records read from that date directory.

A match is reliable only when the existing record's stated goal, project, and content clearly describe the same outcome. An explicit `work_id` or path from the user identifies that record for the goal the user attached to it. Reuse the file, keep `work_id` and `created_at`, and update `updated_at` only when the AI-managed content or another system field actually changes. Preserve the `HUMAN` region through `write-document`.

These are not matches: shared keywords, the same files, the same `work_type`, text overlap, or the same date alone. Do not merge by fuzzy similarity.

If a goal could belong to more than one existing record, or two goals could belong to the same record, do not update or create for those items. Report them as ambiguous and leave the existing files untouched.

One goal updates at most one record, and one record is updated for at most one goal in the call.

If any managed file in the date directory is malformed, or two files contain the same `work_id`, stop the whole backfill before any write.

### Status and body

Use the existing statuses. A conclusion, a proposal, a prompt edit, an AI completion claim, or the existence of a file is not `COMPLETED`. Missing completion evidence stays `UNVERIFIED`, `IN_PROGRESS`, `BLOCKED`, or `PENDING_CONFIRMATION`, and the body states the gap.

The body still needs a meaningful Chinese H1 and a `记录摘要` derived from the frontmatter. Include `工作目标` and `实际结果` when the facts support them. Include deliverables, decisions, verification, risks, next actions, and evidence locations only when there is evidenced content. Do not write placeholder lines such as “无”.

Enough facts to describe the goal, without completion proof, still produce a non-complete record. Not enough facts to say what work occurred means no record; report insufficient factual basis. Do not invent deliverables, decisions, or risks.

### After writing

Report the date, any named project, the goals identified, records created, records reused or updated, and unrecorded items. Then stop. Do not generate a daily or weekly report.

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
- Date backfill does not use `source_fingerprint`. It writes work records only and then stops.

## Helper commands

Run from the skill directory or use the script's absolute path.

```text
python scripts/work_summary_io.py new-id
python scripts/work_summary_io.py paths --root <root> --date YYYY-MM-DD [--work-id wrk_<UUIDv7>]
python scripts/work_summary_io.py fingerprint-sources --root <root> --source-file <source.md> [--source-file <source.md> ...] [--supplement-file <supplement> ...]
python scripts/work_summary_io.py write-document --root <root> --path <target.md> --frontmatter-file <yaml-body.txt> --managed-file <managed.md> [--source-file <source.md> ...] [--supplement-file <supplement> ...]
```

The helper accepts only the documented frontmatter subset and exact per-document schemas; malformed YAML, missing or undeclared properties, invalid values, paths outside the canonical root, and paths inconsistent with the document identity are rejected. Work-record writes do not use report source or supplement flags. Daily reports require their exact work-record sources; weekly reports require their exact daily-report sources and every original work record named by those daily reports. Supplements may be outside `work_summary_root` only when the current call explicitly authorizes those exact files; they never authorize directory traversal or discovery. `write-document` creates missing parent directories only for the resolved target, preserves a valid existing human region, prints `created`, `updated`, or `unchanged`, and fails without writing when safety checks fail.
