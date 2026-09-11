# Active

## Current Objective

第一次 PDR Adoption：完成当前实现的 Brownfield Baseline Reconstruction，并留下可恢复的状态、分类、证据和 Next Allowed。

## Active Change

`CHG-0002` — Redesign ChatHarbor conversation export workflow (`VERIFYING`)

## Current Work

The generic exporter first implementation slice is complete; static validation is being recorded. ChatGPT v0.4 parity and live acceptance remain open.

## Stop Condition

CHG-0002 当前 Stop Condition：所有可由工程环境验证的实现标准有 Evidence，PDR validate PASS；未验证的实站行为保持 Unknown。

## Blocked

None.

## Next Allowed

- 先阅读 `PROJECT.md`、`STATE.yaml`、本文件和 `evidence/BASELINE.md`。
- 继续实现下一垂直切片，并保持每步可回退、可验证。
- 在实站验证前不得标记 ACCEPTED 或 CLOSED。
- 可对通用版与 ChatGPT 专用版开展 UX Discovery；未形成 Spec 前不得开始实现。
- 可独立开展 source / license provenance 核验；公开发布前必须保留证据并经过 Human Gate。
