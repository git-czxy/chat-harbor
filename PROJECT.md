# Project

## Identity

- Name: ai-chat-exporter
- Status: active

## Goal

在浏览器本地安全导出多个 AI 平台的对话。

## Origin / Problem Statement

ChatHarbor 源于用户长期受到 AI 长期记忆、项目记忆和上下文污染影响，需要取得自己的原始会话历史进行事实提取和重新核验。由于官方全量历史导出长期未能取得，项目转向自行构建安全可靠的对话导出工具。现有普通插件/脚本虽可单条或全量导出，但在完整性、增量、去重、恢复、批量请求压力和风控误判等方面不能满足需求。

## Project Goal

安全、准确、可恢复地保存用户自己的 AI 会话历史，并识别同一会话的持续变化，而不是只完成一次性下载。

## Future Intent

在满足真实个人需求并稳定运行后，为有类似需求的其他用户提供工具、方法和参考。Future Intent 不自动扩大当前 Scope。

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
- Safety over speed.
- Fidelity over convenience.
- Recoverability over one-shot export.
- Stable Identity, Versioned Artifact.
- Raw/source fidelity must not be silently discarded; Markdown/TXT are representations, not the sole fact source.

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
