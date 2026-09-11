# Active

## Current Objective

第一次 PDR Adoption：完成当前实现的 Brownfield Baseline Reconstruction，并留下可恢复的状态、分类、证据和 Next Allowed。

## Active Change

`CHG-0001` — Separate overlapping ChatGPT export entry points (`REVIEW`)

## Current Work

The generic button position was adjusted; static validation is complete and evidence is recorded. Real-site verification is unavailable offline.

## Stop Condition

CHG-0001 的静态 Acceptance Criteria 有 Evidence，真实 ChatGPT 页面行为保持 Unknown；不得伪造实站 PASS。

## Blocked

None.

## Next Allowed

- 先阅读 `PROJECT.md`、`STATE.yaml`、本文件和 `evidence/BASELINE.md`。
- 完成 CHG-0001 的 Review；若需要真实页面验证，等待可用运行环境或记录为未验证。
- 可对通用版与 ChatGPT 专用版开展 UX Discovery；未形成 Spec 前不得开始实现。
- 可独立开展 source / license provenance 核验；公开发布前必须保留证据并经过 Human Gate。
