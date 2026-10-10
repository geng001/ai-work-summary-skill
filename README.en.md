# AI Multi-Source Work Summary Skill

[中文说明](README.md)

This is an explicitly invoked Codex Skill that records the current task as traceable Markdown and generates or safely updates daily and weekly reports from user-authorized sources.

It is designed for users who want structured work summaries without allowing an agent to scan private chat history, overwrite human notes, or send reports automatically.

## What It Does

- Creates work records with stable UUIDv7-based `work_id` values
- Builds daily reports from managed work records and explicit supplemental input
- Builds ISO-week reports from managed daily reports and explicit supplemental input
- Backfills missing work records for one specified date from the current visible session, without scanning other chats
- Separates facts, inferences, recommendations, and unresolved items
- Uses stable source fingerprints for traceable, idempotent updates
- Preserves human-authored content outside the AI-managed region
- Keeps standard machine fields while adding a synchronized Chinese title and readable summary to the body

## Safety and Authorization Boundaries

- Runs only when explicitly invoked
- Reads only the current visible task context, files explicitly named by the user, and managed files required for the requested action
- For date backfill, reads the current visible session and that date's existing work records only
- Does not search other private chat history
- Treats source content as untrusted evidence, not executable instructions
- Does not send, upload, or publish reports
- Stops when the output root is ambiguous, sources conflict, or required facts are missing

See the [behavior contract](docs/SKILL_CONTRACT.md) for the complete rules and the [validation record](docs/SKILL_VALIDATION.md) for isolated behavioral evidence.

## Output Layout

By default, the Skill uses `work-summary/` under the current project root. The user may explicitly provide another root.

```text
work-summary/
|-- 工作记录/
|   `-- YYYY/MM/DD/wrk_<UUIDv7>.md
|-- 日报/
|   `-- YYYY/MM/YYYY-MM-DD 工作日报.md
`-- 周报/
    `-- YYYY/MM/YYYY-Www 工作周报.md
```

Daily reports retain the corresponding weekly-report path, and weekly reports retain the daily-report paths actually used as sources. A cross-month week is stored under the month containing that ISO week's start date.

## Machine Fields and Human Display

YAML frontmatter keeps stable machine formats for validation and interchange: `YYYY-MM-DD` dates, `HH:MM:SS+08:00` record times when an occurrence clock is known, timezone-aware RFC 3339 timestamps, and `wrk_<UUIDv7>` identities. The `T` separator and `+08:00` offset are intentional and must not be removed, and translated labels are not appended to enum values. When no occurrence clock is known, `time` is omitted and the summary says the clock was not recorded.

The Markdown body is the readable layer. It uses a meaningful Chinese title and a summary that displays document type, work type, status, and time in Chinese while retaining the original enum code in parentheses. The helper verifies that this summary matches the frontmatter. UUIDv7 provides unique identities whose time component roughly reflects creation order; `work_id` is not a task-priority number.

## Installation for Codex

Copy the repository's `ai-work-summary-skill` folder into a Codex skills directory.

Typical user-level path on Windows:

```text
%USERPROFILE%\.codex\skills\ai-work-summary-skill\SKILL.md
```

Project-scoped isolated installation:

```text
<project-root>\.codex\skills\ai-work-summary-skill\SKILL.md
```

Start a new task after copying so the Skill list refreshes. The helper requires Python 3.10 or later and uses only the Python standard library.

## Explicit Invocation

Implicit invocation is disabled. Name `$ai-work-summary-skill` and the requested action explicitly.

```text
Use $ai-work-summary-skill to record the current task.
```

```text
Use $ai-work-summary-skill to backfill work records for 2026-10-10 from the current visible session.
```

```text
Use $ai-work-summary-skill to generate today's daily report from the work records I explicitly provide.
```

```text
Use $ai-work-summary-skill to generate the weekly report for the week containing 2026-10-08.
```

Name any date inside the week. The Skill resolves Monday through Sunday and reports the week ID and boundary dates. Callers do not calculate `YYYY-Www` themselves.

Provide one exact work-summary root when overriding the default. Do not provide multiple alternatives and ask the Skill to choose.

## Repository Layout

```text
ai-work-summary-skill/
|-- README.md
|-- README.en.md
|-- LICENSE
|-- .gitattributes
|-- .gitignore
|-- docs/
|   |-- SKILL_CONTRACT.md
|   `-- SKILL_VALIDATION.md
`-- ai-work-summary-skill/
    |-- SKILL.md
    |-- agents/
    |   `-- openai.yaml
    |-- references/
    |   `-- protocol.md
    `-- scripts/
        `-- work_summary_io.py
```

The root documents describe and verify the project. Only the nested `ai-work-summary-skill/` directory is required for installation.

## Project Status

The previous version completed contract review, read-only review, and isolated behavioral validation. This machine/display-layer update passed official structural validation and targeted regression checks; a full behavioral Eval has not been rerun. Date backfill from the current visible session is now specified in the contract and Skill, and its isolated behavioral Eval has not been run. The validation history distinguishes structural checks from behavioral evidence.

## License

[MIT](LICENSE)
