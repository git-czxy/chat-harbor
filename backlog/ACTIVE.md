# Active

## Current Objective

第一次 PDR Adoption：完成当前实现的 Brownfield Baseline Reconstruction，并留下可恢复的状态、分类、证据和 Next Allowed。

## Active Change

`CHG-0002` — Redesign ChatHarbor conversation export workflow (`VERIFYING`)

## Current Work

The ChatHarbor main entry and workspace information architecture have been corrected; v0.4 is Legacy / Reference and will not be migrated.

## Stop Condition

CHG-0002 当前 Stop Condition：主入口接管和视觉/文案修复完成并有 Evidence；真实页面行为仍需 Human Acceptance。

## Blocked

None.

## Next Allowed

- 先阅读 `PROJECT.md`、`STATE.yaml`、本文件和 `evidence/BASELINE.md`。
- 完成静态验证后回到 VERIFYING。
- 进行最小实站检查：入口打开新工作区，不再打开旧 Range 弹窗。
- 在实站验证前不得标记 ACCEPTED 或 CLOSED。
- 可对通用版与 ChatGPT 专用版开展 UX Discovery；未形成 Spec 前不得开始实现。
- 可独立开展 source / license provenance 核验；公开发布前必须保留证据并经过 Human Gate。
