# Project

## Identity

- Name: ai-chat-exporter
- Status: active

## Goal

在浏览器本地安全导出多个 AI 平台的对话。

## Current Objective

完成第一次 PDR Adoption：以当前 Trae 实现为 Brownfield 基线，并建立可由新会话恢复的项目运行状态。

## Scope

- 当前仓库中的 Userscript 文本及其版本历史。
- PDR 项目状态、候选事项、验证证据和后续允许动作。

## Non-goals

- 不按旧升级计划重建或覆盖当前实现。
- Adoption 基线轮未处理导出入口 UI 重叠 Bug；当前该问题必须通过 BUG-001 Change 管理。
- 本轮不开始新的功能开发，不进行大规模业务代码修改。

## Principles

- Actual implementation and validated runtime evidence outrank stale plans.
- Human product decisions are authoritative.
- Unknown is preserved as Unknown.
- Governance is proportional to risk.

## Sources of Truth

1. Human Decisions
2. STATE.yaml
3. Actual code/tests/runtime Evidence
4. Accepted Specs
5. Active Plans

## Notes

This file holds relatively stable project identity and boundaries.
Current progress belongs in `STATE.yaml`.

## Brownfield Baseline

当前实现以 `cf90fad3f5331c66e1013d76ce300217c73fed1e` 为仓库基线。`.trae/documents/ai-conversation-exporter-upgrade-plan.md` 是 Historical / Planned material；它不能证明功能已经实现。当前实际状态、Unknown 和允许的下一步以 `STATE.yaml`、`backlog/` 与 `evidence/BASELINE.md` 为准。
