# ChatHarbor 历史与代码血统

[中文](HISTORY.md) · [English](HISTORY.en.md)

本文记录 ChatHarbor 为什么出现、为什么几次换路线，以及“历史探索”和“当前代码祖先”之间的区别。

## 1. 起点：先解决自己的 ChatGPT 历史保存问题

ChatGPT 长期是维护者的主力 AI 工作环境。由于官方完整数据导出链接长期未能及时取得，实际需求首先是：**把自己的长期会话可靠地保存下来。**

现有 ChatGPT 专用导出工具可以解决“拿到数据”的一部分问题，但维护者担心大批量、频繁请求会造成不必要的服务器压力，并可能触发平台限流或风控误判。因此，第一阶段的目标不是开发一个新产品，而是让个人导出过程更慢、更可控、更可恢复。

这里的“可能触发风控”是当时的风险判断和设计动机，不是对 ChatGPT 封禁机制的确定性结论。

## 2. Conservative Lineage：在现有 ChatGPT 专用工具上直接扩展

最初版本直接基于 OwlCt 的 ChatGPT 专用导出工具修改。代码被复制到 Tampermonkey / Violentmonkey 中直接运行，并逐步增加：

- 多档速度与随机抖动；
- 单批数量限制；
- 批次间长暂停；
- 本地去重；
- pending / exported 两阶段状态；
- 中断恢复；
- retry / cancellation；
- 缓存与增量发现；
- ZIP / 历史恢复；
- 面向个人实际操作的 UI。

这条路线一直发展到 Conservative v0.5。

### 历史 metadata 说明

这些版本最初是个人自用脚本。维护者当时并不熟悉 Userscript metadata、代码 provenance 和开源发布规范，因此直到 Conservative v0.5，脚本头部大体沿用了上游信息，没有随着功能修改同步完成规范化更新。

因此，旧脚本里的 `@author` / `@source` 可以证明其上游来源，但**不能单独用来判断其中是否存在维护者后续增加的大量功能代码**。历史代码血统应结合源代码比较、保存工件和仓库记录判断。

同时，这些版本仍然是 OwlCt 代码的派生作品，并不是从零原创；这一点同样应保持清楚。

## 3. Generalization：从“好用的专用工具”向统一架构探索

随着专用版功能越来越成熟，项目开始探索能否把这些能力推广到其他 AI 平台。

`wanda1416/ai-chat-exporter` 提供了另一条独立路线：不同平台各自拥有 API / 认证 / 分页 / 解析逻辑，同时通过 Adapter 与统一导出管线衔接。

在此基础上，项目曾选择 **Option C — Extract & Recompose**：

- 保留成熟的 ChatGPT 专用行为；
- 吸收通用 Adapter 架构；
- 建立独立 `Core + Platform Adapters`；
- 通过 PDR、Change、Decision、Evidence 和 Browser Verification 管理实现。

这一阶段形成了大量真实价值：stable identity、Unknown 边界、version-aware state、selection、cache/index、retry/cancel、progress、项目/归档语义以及工作台 UX 都在这里得到系统化讨论和验证。

旧 GitHub/PDR 路线现完整保留在 `legacy/pre-clean-lineage`。

## 4. Lineage Reset：为什么没有继续沿 Option C 代码实现

Option C 并不是“失败”。它成功澄清了大量需求和工程边界。但继续从多个 donor 抽取、适配、合并能力，也产生了越来越高的：

- provenance 复杂度；
- 历史兼容负担；
- 当前实现与旧计划的 Authority 冲突；
- UI / Core / donor 之间的状态同步成本；
- “哪些结论现在仍然有效”的恢复成本。

项目因此决定重新建立一个**单一、明确、可审计的代码祖先**，而不是继续让历史 donor 逐层侵入当前 Core。

这就是 clean-lineage reset。

旧 Conservative / Generic / Pilot 工作没有被删除。它们的角色从“代码 donor”转为：

- Product Requirement Evidence；
- Historical Exploration；
- Behavioral Reference；
- Regression Oracle。

## 5. Current clean lineage

当前主线直接建立在固定的：

- repository: `huhusmang/ChatGPT-Exporter`
- pinned commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- pinned userscript Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`

之上。

然后逐步建立：

- 直接目录写入与 Manifest；
- version-aware selective sync；
- 保守请求策略；
- Desktop workspace；
- streaming transaction；
- Archive Layout v2；
- Remote Index / project truth；
- attachment incremental/backfill；
- commit-accurate state；
- auditable reports；
- attachment provenance 与 failure explainability。

### Git 重建说明

clean-lineage 的早期开发主要以保存的 ZIP / source bundles 作为 durable artifacts。2026-09-16 根据这些原始工件、内部 checksum 和历史记录重建了 Git commits / tags。

因此：

- 保存的历史发布包是原始证据；
- 重建的 Git commit/tag 用于恢复版本演进；
- 不应把重建出来的 commit hash 说成当时原始存在的 Git hash。

详见 `docs/history/RECONSTRUCTION.md` 与 `docs/history/INVENTORY_2026-09-16.md`。

## 6. 从“同步器”进一步收敛为“归档与完整性审计”

在 0.0.14.x 阶段，附件失败问题一度让项目怀疑公开发布是否值得。

随后通过真实归档审计发现，未成功归档并不是单一问题：平台当前可能返回 403、404、415、500，也可能只留下已失效的临时下载 URL；不同来源附件还呈现不同失败分布。

这使产品定位发生了最后一次重要收敛：

> **ChatHarbor 不承诺平台无法保证的“100% 完整”。它尽可能保存当前可取得的数据，并把已知缺口变成可解释、可追溯、可回到原会话核查的证据。**

因此 v0.0.14.5 的产品定位是：

**Local-first ChatGPT Archive & Integrity Audit**

而不是一个声称“全部下载完成”的普通 exporter。

## 7. 当前历史边界

```text
现实需求：官方完整导出不可及时取得
        ↓
OwlCt ChatGPT 专用导出器
        ↓
Conservative Lineage v0.1 → v0.5
        ↓
        ├── + wanda1416 通用 Adapter 路线参考
        ↓
Option C / Core + Platform Adapters / PDR 探索
        ↓
Lineage Reset
        ↓
huhusmang fixed upstream
        ↓
ChatHarbor clean lineage 0.0.x
        ↓
v0.0.14.5
Local archive + integrity audit + transparent diagnostics
```

历史探索被保留；当前 Authority 与当前代码祖先保持单一、明确。
