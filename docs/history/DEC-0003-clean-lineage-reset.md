# DEC-0003 — Clean-Lineage Reset / 代码血统重置

Date: 2026-09-20
Status: Human Accepted / Published

## 中文

### 决策

旧 GitHub/PDR 路线中由 DEC-0002 确立的 donor-based `Core + Platform Adapters` 实现血统，不再作为当前 ChatHarbor 的 authoritative code lineage。

当前实现重新建立在固定的 `huhusmang/ChatGPT-Exporter` 上游基线上，并以保存的 clean-lineage Gate / Release 工件作为版本恢复证据。

此前的 Conservative v0.1-v0.5、`wanda1416/ai-chat-exporter` 参考、Pilot/Core 实验、PDR Changes / Decisions / Evidence 均保留为 Historical Exploration、Product Requirement Evidence、Behavioral Reference 与 Regression Oracle，但不是当前主线代码祖先。

### 原因

旧路线成功澄清了需求、状态语义、恢复行为、UI 与工程边界；但继续从多个 donor 重组能力，会不断增加 provenance、兼容性与 Authority 复杂度。

选择一个单一、明确、可审计的上游祖先，可以让历史能力只在当前需求与新证据支持时重新引入，而不是默认继承全部历史实现。

### Supersession 边界

本 Decision 只 supersede DEC-0002 关于“当前实现代码血统”的 Authority；它不否定 DEC-0002 当时作为 Human Decision 的历史有效性，也不删除在该路线下形成的工程成果。

## English

### Decision

The donor-based `Core + Platform Adapters` implementation lineage established by legacy DEC-0002 is no longer the authoritative code lineage for the current ChatHarbor implementation.

The current implementation re-establishes a clean lineage from a fixed `huhusmang/ChatGPT-Exporter` upstream baseline, with preserved clean-lineage Gate / Release artifacts serving as reconstruction evidence.

Earlier Conservative v0.1-v0.5 work, the `wanda1416/ai-chat-exporter` reference, Pilot/Core experiments, and PDR Changes / Decisions / Evidence remain preserved as Historical Exploration, Product Requirement Evidence, Behavioral Reference, and Regression Oracle, but are not code ancestors of the current mainline.

### Reason

The earlier route successfully clarified product requirements, state semantics, recovery behavior, UX, and engineering boundaries. Continued multi-donor recomposition, however, increasingly coupled implementation work to provenance, compatibility, and authority complexity.

A single explicit, auditable upstream ancestry allows historical capabilities to be reintroduced only when current requirements and current evidence justify them, rather than inheriting all historical implementation by default.

### Supersession boundary

This Decision supersedes DEC-0002 only with respect to the authority of the **current implementation lineage**. It does not invalidate DEC-0002 as a historical Human Decision and does not erase the engineering work produced under that architecture.
