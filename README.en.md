# AI Multi-Source Work Summary Skill

[中文说明](README.md)

This is an explicitly invoked Codex Skill that records the current task as traceable Markdown and generates or safely updates daily and weekly reports from user-authorized sources.

It is designed for users who want structured work summaries without allowing an agent to scan private chat history, overwrite human notes, or send reports automatically.

## What It Does

- Creates work records with stable UUIDv7-based `work_id` values
- Builds daily reports from managed work records and explicit supplemental input
- Builds ISO-week reports from managed daily reports and explicit supplemental input
- Separates facts, inferences, recommendations, and unresolved items
- Uses stable source fingerprints for traceable, idempotent updates
- Preserves human-authored content outside the AI-managed region

## Safety and Authorization Boundaries

- Runs only when explicitly invoked
- Reads only the current visible task context, files explicitly named by the user, and managed files required for the requested action
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
Use $ai-work-summary-skill to generate today's daily report from the work records I explicitly provide.
```

```text
Use $ai-work-summary-skill to generate an ISO-week report from this week's managed daily reports.
```

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

The current version has completed contract review, read-only review, and isolated behavioral validation. The validation history explicitly distinguishes structural checks from behavioral evidence.

## License

[MIT](LICENSE)
