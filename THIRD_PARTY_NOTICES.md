# Third-Party Notices / 第三方来源说明

[中文](#中文) · [English](#english)

## 中文

ChatHarbor 当前主线与历史探索涉及多条不同的代码来源。为避免把“历史参考”和“当前代码祖先”混在一起，说明如下。

### 1. 当前 clean-lineage 的直接上游

当前 ChatHarbor clean-lineage 的保存工件记录以下固定上游身份：

- Repository: `huhusmang/ChatGPT-Exporter`
- Historical URL: `https://github.com/huhusmang/ChatGPT-Exporter`
- Pinned commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- Pinned userscript Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- License recorded in inherited userscript metadata: MIT

ChatHarbor v0.0.x 在该固定基线上增加并修改了本地归档、Manifest、增量同步、事务写入、保守请求策略、Remote Index、附件治理、完整性审计与 UI 等能力。

### 2. Historical Conservative Lineage

在 clean-lineage 之前，维护者曾直接修改 OwlCt 的 ChatGPT 专用导出脚本，形成 Conservative v0.1 → v0.5 的个人使用路线。

- Historical source: `https://github.com/OwlCt/ChatGPT-Export`
- License recorded in the preserved userscript metadata: MIT

这些历史版本包含大量维护者后续增加的保守导出、批次、暂停、去重、恢复、retry/cancel 与 UI 代码，但它们仍然是上游代码的派生作品，并不是从零原创。

直到 Conservative v0.5，这些脚本主要直接复制到 Tampermonkey / Violentmonkey 使用，旧 metadata 头部没有随着功能演进同步规范化。因此旧 `@author` / `@source` 字段只应作为 provenance 证据的一部分，而不能单独代表全部贡献关系。

这条 Conservative Lineage **不是当前 clean-lineage 的代码祖先**，但保留为产品需求证据、行为参考和回归 oracle。

### 3. Historical Generic / Adapter Reference

项目曾参考 `wanda1416/ai-chat-exporter` 的多平台 Adapter 思路，探索 `Core + Platform Adapters` 的重组路线。

- Historical source: `https://github.com/wanda1416/ai-chat-exporter`
- License recorded in the preserved userscript metadata: MIT

该路线保留在旧 GitHub/PDR 历史中，但**不是当前 clean-lineage 的代码祖先**。

### 4. JSZip

Userscript 通过 cdnjs 加载 JSZip：

- Project: JSZip
- URL: `https://stuk.github.io/jszip/`
- Runtime CDN: `https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js`

JSZip 适用其自身许可证。

### 5. 历史分支

旧 GitHub/PDR 实现完整保留在：

`legacy/pre-clean-lineage`

当前主线历史说明见 `HISTORY.md` 与 `docs/history/RECONSTRUCTION.md`。

---

## English

ChatHarbor has interacted with several distinct source lineages. The following notes intentionally separate **historical references** from the **current code ancestor**.

### 1. Direct upstream of the current clean lineage

Preserved ChatHarbor clean-lineage artifacts record the following fixed upstream identity:

- Repository: `huhusmang/ChatGPT-Exporter`
- Historical URL: `https://github.com/huhusmang/ChatGPT-Exporter`
- Pinned commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- Pinned userscript Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- License recorded in inherited userscript metadata: MIT

ChatHarbor v0.0.x adds and modifies local archive/Manifest handling, incremental sync, transactional writes, conservative request policy, Remote Index behavior, attachment governance, integrity auditing, and UI behavior on top of that fixed baseline.

### 2. Historical Conservative Lineage

Before the clean-lineage reset, the maintainer directly modified an OwlCt ChatGPT-specific exporter and evolved a personal-use Conservative v0.1 → v0.5 line.

- Historical source: `https://github.com/OwlCt/ChatGPT-Export`
- License recorded in preserved userscript metadata: MIT

Those historical variants contain substantial downstream additions for conservative pacing, batching, pauses, deduplication, recovery, retry/cancel, and UI behavior. They nevertheless remain derivative works of their upstream code and were not written from scratch.

Through Conservative v0.5, the scripts were mainly pasted directly into Tampermonkey / Violentmonkey, so the old metadata header was not consistently updated as functionality evolved. Historical `@author` / `@source` fields therefore represent only part of the provenance evidence.

The Conservative Lineage is **not a code ancestor of the current clean-lineage mainline**. It is preserved as product-requirement evidence, behavioral reference, and regression oracle.

### 3. Historical Generic / Adapter reference

The project also referenced `wanda1416/ai-chat-exporter` while exploring a multi-platform `Core + Platform Adapters` recomposition route.

- Historical source: `https://github.com/wanda1416/ai-chat-exporter`
- License recorded in preserved userscript metadata: MIT

That exploration remains in the old GitHub/PDR history but is **not a code ancestor of the current clean lineage**.

### 4. JSZip

The userscript loads JSZip through cdnjs:

- Project: JSZip
- URL: `https://stuk.github.io/jszip/`
- Runtime CDN: `https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js`

JSZip remains subject to its own license.

### 5. Historical branch

The earlier GitHub/PDR implementation is preserved at:

`legacy/pre-clean-lineage`

See `HISTORY.en.md` and `docs/history/RECONSTRUCTION.md` for the current lineage boundary.
