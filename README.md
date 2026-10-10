# AI 多来源工作总结 Skill

[English README](README.en.md)

这是一个仅在用户明确调用时运行的 Codex Skill。它把当前任务记录为可追溯的 Markdown 工作记录，并基于用户明确授权的材料生成或安全更新日报、周报。

它适合希望把零散工作上下文整理成结构化记录，同时又不希望 Agent 扫描历史私有会话、覆盖人工备注或自动外发报告的用户。

## 它解决什么问题

- 将当前任务沉淀为带稳定 `work_id` 的工作记录
- 从受管工作记录和明确补充材料生成日报
- 从受管日报和明确补充材料生成 ISO 周报
- 将工作记录逐级压缩为按目标组织的日报和周报，避免机械拼接和流水账
- 按指定日期，从当前可见会话补齐缺失的工作记录，并与当日已有记录去重
- 区分事实、推断、建议与待确认信息
- 用来源指纹支持可追溯更新和重复运行
- 将 AI 托管区域与人工编辑区域分开，避免覆盖人工内容
- 保留标准机器字段，同时在正文中提供与其一致的中文标题和记录摘要

## 安全与授权边界

- 仅支持显式调用，不自动介入普通总结请求
- 只读取当前任务可见上下文、用户明确指定的文件，以及完成当前动作所需的受管文件
- 按指定日期补录时，只读取当前可见会话和该日已有工作记录，不打开其他历史会话
- 不主动搜索或读取其他历史私有会话
- 不把材料中的命令或请求当作可信指令执行
- 不自动发送、上传或发布工作记录、日报或周报
- 输出根目录不唯一、材料冲突或关键事实不足时会停止并请求确认

完整行为边界见 [行为契约](docs/SKILL_CONTRACT.md)。已执行的隔离验证见 [验证记录](docs/SKILL_VALIDATION.md)。

## 输出结构

默认在当前项目根目录下使用 `work-summary/`；也可以在调用时明确指定另一个根目录。

```text
work-summary/
|-- 工作记录/
|   `-- YYYY/MM/DD/wrk_<UUIDv7>.md
|-- 日报/
|   `-- YYYY/MM/YYYY-MM-DD 工作日报.md
`-- 周报/
    `-- YYYY/MM/YYYY-Www 工作周报.md
```

日报会记录对应周报路径，周报会记录实际参与汇总的日报路径。跨月周仍按各日报日期追溯来源，周报文件存放在该 ISO 周起始日所在月份。

## 机器字段与中文显示

YAML frontmatter 用于校验、去重和跨工具处理，因此继续使用稳定格式：日期为 `YYYY-MM-DD`，有发生时刻时工作时间为 `HH:MM:SS+08:00`，时间戳为包含时区的 RFC 3339，记录编号为 `wrk_<UUIDv7>`。其中 `T` 是日期与时间的标准分隔符，`+08:00` 表示北京时间偏移；不要删掉它们，也不要把中文直接拼进枚举值。没有可支撑的发生时刻时省略 `time`，正文写“时刻未记录”，不编造钟点。

正文用于阅读。工作记录使用有实际含义的中文标题，并在“记录摘要”中把文档类型、工作类型、状态和时间显示为中文，例如“文档整理（documentation）”“已完成（COMPLETED）”“2026-10-08 15:58:15（北京时间）”。日报和周报使用对应的“报告摘要”。辅助脚本会校验展示摘要与 YAML 一致，避免两套信息发生漂移。

UUIDv7 已经兼顾唯一性，其时间部分可大致反映生成先后；`work_id` 不代表任务优先级，因此不会改成需要扫描全局记录的连续序号。需要调整任务顺序时，应在正文中表达优先级，而不是修改稳定 ID。

## 安装到 Codex

将仓库中的 `ai-work-summary-skill` 文件夹复制到 Codex skills 目录。

Windows 用户级安装通常是：

```text
%USERPROFILE%\.codex\skills\ai-work-summary-skill\SKILL.md
```

也可以在某个项目中隔离安装：

```text
<项目根目录>\.codex\skills\ai-work-summary-skill\SKILL.md
```

复制后开启一个新任务，让 Skill 列表刷新。运行辅助脚本需要 Python 3.10 或更高版本；Skill 本身不需要第三方 Python 包。

## 显式调用

本 Skill 不允许隐式调用。请在请求中明确写出 `$ai-work-summary-skill`，并说明要执行的动作。

```text
使用 $ai-work-summary-skill 记录当前任务。
```

```text
使用 $ai-work-summary-skill 补录当前会话中 2026-10-10 的工作记录。
```

```text
使用 $ai-work-summary-skill，根据我明确指定的工作记录生成今天的日报。
```

```text
使用 $ai-work-summary-skill 生成包含 2026-10-08 的周报。
```

给出这一周里的任意一天即可。Skill 会按周一至周日确定周期，并在结果里写明周编号和起止日期。不需要自己计算 `2026-W41`。

如果需要指定工作总结根目录，请提供一个确定路径；不要同时给出两个候选目录让 Skill 自行选择。

## 仓库结构

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
    |   |-- protocol.md
    |   `-- report-writing.md
    `-- scripts/
        `-- work_summary_io.py
```

根目录的文档用于说明、审查和验证；安装时只需复制同名的 `ai-work-summary-skill/` 子目录。

## 项目状态

此前版本已完成行为契约、只读审查和隔离行为验证。本次机器层与中文展示层整改已通过官方结构检查和定向回归；尚未重新执行全量行为 Eval。指定日期的可见会话批量补录已写入契约和 Skill 说明，隔离行为 Eval 尚未执行。验证记录保留历史轮次及本次定向证据，结构通过不被等同于行为正确。

## 许可证

[MIT](LICENSE)
