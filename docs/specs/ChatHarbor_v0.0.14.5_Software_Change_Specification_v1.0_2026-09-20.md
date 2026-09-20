# ChatHarbor v0.0.14.5 软件变更规格说明书
**Software Change Specification（SCS）**

**主题：Attachment Provenance, Failure Explainability & Conversation-centric Recovery**
**文档版本：v1.0**
**日期：2026-09-20**
**状态：Design Baseline / Ready for Implementation**
**Authority：本文件作为 ChatHarbor v0.0.14.5 的实现基线；后续实现如与本文件冲突，应先回到本文件确认，不得在开发过程中静默扩大范围。**

---

## 0. 文档目的

本文件整合并固化 ChatHarbor v0.0.14.4 已验证的可审计报告机制，以及 v0.0.14.5 新增的附件来源治理、失败可解释性、会话级完整性提示和人工核查导航设计。

v0.0.14.5 的目标不是继续扩大下载或同步能力，而是让用户能够清楚知道：

1. 哪些对话和附件已经成功归档；
2. 哪些附件当前未成功归档；
3. 未成功归档的附件来自哪里；
4. 平台在什么阶段返回了什么错误；
5. 用户可以回到哪个原会话进一步核查；
6. 如果是用户上传文件，用户还可以自行到本地、NAS、网盘或 Everything 等工具中搜索原件。

核心产品原则：

> **ChatHarbor 尽可能获取当前能够获取的对话资料和状态；无法获取的内容不隐藏、不伪装成功，而是保留足够证据，让用户知道缺口并决定是否进一步处理。**

---

# 1. 当前基线：v0.0.14.4

v0.0.14.4 已通过真实 Browser Smoke，并完成以下能力：

- 报告生成日期时间；
- `SYNC_COMPLETION` / `LOCAL_PREFLIGHT` 报告类型区分；
- 报告阶段与状态来源；
- 附件策略记录；
- 本轮附件结果；
- 本轮附件失败原因汇总；
- 本轮失败逐条明细；
- 历史累计附件状态；
- 本轮失败与历史累计严格区分；
- 不修改 Manifest schema；
- 不改变附件 retry 规则；
- 不改变 Remote Index、项目判断、同步分类或事务逻辑。

这些能力在 v0.0.14.5 中属于：

> **Inherited Validated Baseline / 不可退化基线**

任何 v0.0.14.5 实现不得删除、弱化或模糊这些已经验证通过的能力。

---

# 2. v0.0.14.5 版本目标

v0.0.14.5 需要进一步回答：

1. 某个未成功归档附件是用户上传，还是 ChatGPT 生成？
2. 它通过 `file` 还是 `sandbox` 引用？
3. 它失败在哪个阶段？
4. 原始错误是什么？
5. 所在会话是什么？
6. 用户能否直接打开原会话自行核查？
7. 历史失败中，不同来源和不同错误的分布是什么？
8. 用户能否在不被大量技术信息淹没的情况下逐层查看证据？

v0.0.14.5 的产品定位：

> **Local-first, user-triggered, incremental ChatGPT archive with transparent diagnostics.**

---

# 3. 相比 v0.0.14.4 的主要改进

| 能力 | v0.0.14.4 | v0.0.14.5 |
|---|---|---|
| 报告日期时间 | 有 | 继承并固化 |
| 报告类型/阶段 | 有 | 继承并固化 |
| 附件策略 | 有 | 继承并固化 |
| 本轮附件失败原因 | 有 | 保留 |
| 本轮失败逐条明细 | 有 | 保留 |
| 历史失败总数 | 有 | 有 |
| `file / sandbox` 分类 | 明细可见 | 正式纳入分类 |
| 用户上传 / ChatGPT生成来源 | 不完整 | 正式建立 provenance |
| 历史来源补全 | 无 | 本地 JSON 重建 |
| 按来源统计失败 | 无 | 有 |
| 来源 × 错误交叉统计 | 无 | 有 |
| 会话列表显示附件缺口 | 无 | 有 |
| 会话详情显示未成功归档附件 | 无 | 有 |
| HTTP / 平台错误解释 | 原始字符串 | tooltip / popover |
| 打开原 ChatGPT 会话 | 无 | 有 |
| 用户后续核查引导 | 无 | 有 |
| 自动修复失败附件 | 无 | 仍然无 |
| 第五种主状态 | 无 | 仍然无 |

---

# 4. 产品语义

## 4.1 不使用“附件丢失”

统一采用：

> **未成功归档附件**

原因：

`403 / 404 / 415 / 500 / download_url missing or expired` 只证明：

> ChatHarbor 当次没有成功取得该资源。

不能据此证明：

> 文件已经永久删除或永久不可恢复。

## 4.2 四主状态保持不变

继续保持：

- 已同步
- 待同步
- 需确认
- 异常

附件完整性属于独立维度，不增加第五主状态。

允许：

> 已同步 · 附件 3 未归档

禁止新增主状态：

> 附件失败

---

# 5. Attachment Provenance 数据模型

## 5.1 来源分类

新增标准字段：

```text
source_category
```

允许值：

```text
user_upload
assistant_generated_deliverable
generated_media
assistant_asset
unknown
```

| 值 | 含义 |
|---|---|
| `user_upload` | 用户主动上传到 ChatGPT 会话中的文件 |
| `assistant_generated_deliverable` | ChatGPT 生成供用户下载的交付文件 |
| `generated_media` | 明确由生成工具产生的图片/媒体 |
| `assistant_asset` | Assistant/Tool 相关，但不能进一步确定为以上类别 |
| `unknown` | 证据不足，不推断 |

## 5.2 `file / sandbox` 与来源类别分离

`file / sandbox` 是 **reference kind / transport kind**，回答 ChatGPT 用什么资源引用机制表示该资源。

`source_category` 回答这个资源来自哪里。

禁止：

```text
file = 用户上传
```

因为部分 ChatGPT 生成资源同样可能使用 `file`。

## 5.3 Provenance 判定规则

采用保守规则：

```text
user role + message.metadata.attachments
→ user_upload

assistant role + sandbox
→ assistant_generated_deliverable

tool role + explicit dalle / generation metadata
→ generated_media

assistant/tool + file + 不满足以上强证据
→ assistant_asset

证据不足
→ unknown
```

不得为了减少 `unknown` 而猜测。

---

# 6. 新数据持久化要求

对于 v0.0.14.5 以后新发现的附件和新产生的 failure evidence，增加可选 provenance 字段：

```text
owner_role
source_category
```

必要时补：

```text
reference_kind
```

前提是当前结构中没有稳定等价字段。

要求：

- 新字段向后兼容；
- 旧 Manifest 缺字段仍正常读取；
- 不因为缺字段触发 migration error；
- provenance 不参与同步状态判定；
- provenance 不决定是否 PENDING；
- provenance 只用于解释、统计和导航；
- failure 原始错误必须保留。

---

# 7. 历史 Provenance Backfill

历史补全不得进入日常同步 Core，应继续作为独立 **Attachment Provenance Backfill / Migration Tool**。

## 7.1 Phase 1 — Local Dry Run

输入：

```text
Manifest + 本地 conversation JSON
```

行为：

```text
不联网
不下载附件
不重试失败附件
不修改 Manifest
```

利用 `conversation_id / message_id / file_id / sandbox_path / owner role / message metadata` 重建历史 provenance。

## 7.2 Phase 2 — Audit

输出：

- 成功附件 provenance 分布；
- 历史失败总数；
- 按 `source_category` 分类；
- 按 `file / sandbox` 分类；
- 按 failure stage 分类；
- 按原始 error 分类；
- `source_category × error` 交叉统计；
- 本地识别成功数量；
- Unknown 数量；
- 涉及 Unknown 的会话数量。

当前真实 Dry Run 已证明：280 条历史失败可全部从本地 JSON 重建来源，Unknown = 0。

## 7.3 Phase 3 — Optional Online Complement

只在 `local reconstruction = unknown` 时允许。

规则：

- 只读取 unresolved failure 所在 conversation detail；
- 不全量抓所有会话；
- 不下载附件；
- 不重试失败资源；
- 不修改 Core 状态；
- 429 时停止；
- 在线仍无法判断则保留 `unknown`。

如果 `Unknown = 0`，则无需执行在线补查。

## 7.4 Phase 4 — Optional Apply

Dry Run 与 Audit 完成后，才允许人工选择 Apply Provenance Backfill。

只补 provenance 字段，不得：

- 修改 `attachment_state`；
- 修改失败原因；
- 删除 failure evidence；
- 改写成功/失败事实；
- 自动重试附件。

---

# 8. 会话列表 UI

## 8.1 会话是一级对象

不建立“全局失败附件列表”作为主要用户入口。

原因：文件可能重名、名称相似，且脱离会话后难理解；ChatGPT 本身以会话组织信息。

## 8.2 会话列表显示附件完整性提示

存在未成功归档附件时，显示次级标记，例如：

```text
已同步    附件 3 未归档
```

要求：

- 不抢占主状态视觉层级；
- 没有问题时不增加视觉噪声；
- 数量必须对应真实未成功归档附件数量；
- 不改变主状态。

## 8.3 附件维度二级筛选

允许增加：

```text
附件：全部 | 完整 | 有未成功归档
```

这是附件维度筛选，不是主状态筛选。

---

# 9. 会话详情 UI

顶部结构：

```text
会话：ChatHarbor｜……
附件归档：成功 12 · 未成功 3                [打开原会话]
```

## 9.1 打开原会话

整个会话详情只放一次，不得每个附件重复按钮。

目标：用户发现重要附件未归档时，可以直接回到 ChatGPT 原始上下文自行确认。

实现优先：

```text
conversation_id → 原 ChatGPT conversation URL
```

必须 Browser Smoke 验证普通会话与项目内会话。如果无法可靠构建 URL，不得猜测错误地址。

---

# 10. 未成功归档附件列表

默认采用紧凑列表，禁止“一条附件一个大卡片”。

推荐：

```text
未成功归档附件
────────────────────────────────────────────
report.user.js   ChatGPT生成   415 ⓘ      binary        ›
source.pdf       用户上传      404 ⓘ      metadata      ›
analysis.zip     ChatGPT生成   URL失效 ⓘ   download_url  ›
────────────────────────────────────────────
```

每项默认一行，最多两行。

默认只显示：文件名、来源、原始错误简写、失败阶段、展开控制。

---

# 11. 文件名展示规则

文件名是视觉主项。长文件名采用截断，悬浮时显示完整名称。

不能让错误码比文件名更突出。用户首先关心的是：哪个文件没有保存下来？

---

# 12. 单条按需展开

点击 `›` 后原地展开，不跳转新页。

示例：

```text
report.user.js   ChatGPT生成   415 ⓘ   binary   ˅

  通道：sandbox
  最近尝试：2026-09-20 16:52
  附件标识：sandbox:/mnt/data/...
  状态：当前未成功归档
```

可进一步显示 `owner_role / source_category / message_id / file_id / sandbox_path`，但均属于二级技术详情。再次点击折叠。

---

# 13. 信息密度原则

禁止一条附件一个大块信息卡，避免长距离滚动。

正式 UI 原则：

> **摘要 → 紧凑列表 → 单条展开**

目的：降低滚动距离、保持上下文连续、避免重复信息、技术信息按需呈现。

---

# 14. HTTP / 平台错误解释

原始错误继续完整保留。解释只通过 hover / focus / click 触发 tooltip / popover。

原则：

> **原始错误是 Evidence；中文说明是 Interpretation。**

## 14.1 HTTP 404 · Not Found

> ChatGPT 当前接口未找到该资源。可能涉及资源生命周期、存储位置变化或当前接口无法解析；不能仅据此确认文件已永久删除。

## 14.2 HTTP 403 · Forbidden

> ChatGPT 服务器拒绝了当前访问请求。可能与权限、资源访问策略或当前会话上下文有关；不代表文件一定不存在。

## 14.3 HTTP 500 · Internal Server Error

> ChatGPT 服务端处理请求时发生错误，通常表示服务端异常；可能具有临时性。

## 14.4 HTTP 415 · Unsupported Media Type

> ChatGPT 的内容交付接口未接受或未正确处理当前资源形式，可能涉及文件类型、MIME 类型或交付链兼容性；不代表文件内容已经损坏。

## 14.5 download_url missing or expired

UI 简写：`URL失效 ⓘ`

> ChatGPT 当前没有提供可用下载地址，或临时下载地址已经失效。仅凭这一结果无法判断资源本身是否仍然存在。

---

# 15. Fact / Interpretation 边界

禁止：

```text
404 → 文件已永久删除
403 → 文件不存在
415 → 文件损坏
expired → 永久丢失
500 → 本地程序错误
```

允许：原始错误 + 保留不确定性的解释。

---

# 16. 用户后续处理引导

引导只出现一次，不重复到每个附件。

## 16.1 用户上传文件

> 这是你曾上传到 ChatGPT 的文件。如果该文件重要，可先打开原会话检查；也可以按文件名在原电脑、NAS、网盘或使用 Everything 等本地文件搜索工具查找原件。

不得自动搜索用户电脑。

## 16.2 ChatGPT 生成交付文件

> 这是 ChatGPT 生成的交付文件。如果当前下载地址不可用，可打开原会话检查原始链接；必要时可尝试重新生成相关文件。

不得保证重新生成内容完全一致。

---

# 17. 多附件情况下的过滤

仅当当前会话存在较多未归档附件时显示：

```text
全部 12 | 用户上传 9 | ChatGPT生成 3
```

数量少时不显示额外过滤控件，避免为了极少数据增加永久 UI 复杂度。

---

# 18. 可审计运行报告（Auditable Run Reports）

v0.0.14.5 必须完整继承 v0.0.14.4 已通过 Browser Smoke 的报告机制，并在其基础上增加 provenance 与历史失败分类。

不得因 UI 或 provenance 重构而削弱 v0.0.14.4 已有报告。

## 18.1 所有报告必须包含明确时间信息

SYNC_COMPLETION 必须记录：运行开始、运行结束、报告生成。

LOCAL_PREFLIGHT 必须记录：扫描开始、扫描结束、报告生成。

时间要求：使用浏览器本地时间、精确到秒、包含 UTC offset。

## 18.2 报告类型必须显式标识

```text
报告类型: SYNC_COMPLETION
```

或：

```text
报告类型: LOCAL_PREFLIGHT
```

不能只依赖标题判断报告类型。

## 18.3 报告阶段与状态来源

SYNC_COMPLETION 至少显示：

```text
报告阶段: 同步事务结束后
状态来源: post-sync local reconciliation
手动重新检查: 否
```

LOCAL_PREFLIGHT 至少显示：

```text
报告阶段: 本地目录扫描 + 同步预检
状态来源: fresh local scan + current remote index
触发方式: local preflight scan
```

不能可靠区分时不得伪造更细粒度状态。

## 18.4 附件策略必须进入两类报告

固定记录 `includeAttachments / retryFailedAttachments / policy / 人类可读说明`。

标准策略：

```text
includeAttachments: false
retryFailedAttachments: false
policy: excluded
说明: 不下载附件 / 附件未纳入本次同步判断
```

```text
includeAttachments: true
retryFailedAttachments: false
policy: new_or_unattempted_only
说明: 下载新/未尝试附件；历史失败默认不重试
```

```text
includeAttachments: true
retryFailedAttachments: true
policy: include_known_failures
说明: 下载新附件，并显式重试历史已知失败附件
```

## 18.5 SYNC_COMPLETION 必须区分“本轮”与“累计”

【本轮附件结果】至少包括：

- 当前处理会话中的附件引用总数；
- 实际尝试下载；
- 下载成功；
- 本轮下载失败；
- 其中首次失败；
- 其中历史失败重试仍失败。

不得继续使用容易误解为“新附件数量”的“检测附件引用”。

## 18.6 本轮附件失败原因

本轮实际失败必须按原始 error 聚合。

无失败时也必须明确输出：

```text
本轮附件下载失败: 0
本轮附件失败原因: 无
本轮附件失败明细: 无
```

## 18.7 本轮失败逐条证据

只展开本轮实际尝试并失败的附件。

每条至少包含：当前会话最新标题、conversation_id、文件名、source_category、reference_kind、failure_stage、原始 error、本轮 attempt time。

技术标识可包括 file_id、sandbox_path、message_id。

历史累计失败不得每次全部展开。

## 18.8 当前本地附件状态

SYNC_COMPLETION 优先使用 post-sync reconciliation 后的当前状态。

LOCAL_PREFLIGHT 使用 fresh local scan 得到的当前状态。

至少包含：完整会话、不完整会话、已知失败附件、Manifest 跟踪附件路径、附件缺失/异常。

## 18.9 历史未成功归档附件分类（v0.0.14.5新增）

增加：

```text
【历史未成功归档附件】

总计: N

按来源:
- 用户上传
- ChatGPT生成交付文件
- 生成媒体
- Assistant资源
- Unknown

按资源通道:
- file
- sandbox

按失败阶段:
- metadata
- download_url
- binary
- other

按失败原因:
- metadata HTTP 404
- metadata HTTP 403
- metadata HTTP 500
- binary HTTP 415
- download_url missing or expired
- 其他原始 error

【来源 × 失败原因】
输出交叉统计
```

所有统计保留原始 error，不得用解释后的中文原因替代原始证据。

## 18.10 LOCAL_PREFLIGHT 不得伪造本轮下载行为

没有执行附件下载时明确写：

> 本次扫描未执行附件下载，无本轮附件失败记录。

不得从历史 failure ledger 推断“本轮失败”。

## 18.11 报告必须自包含

单独保存一份 txt/md 报告，即使脱离 UI 和聊天上下文，也必须能回答：版本、时间、报告类型、阶段、附件策略、本轮发生了什么、本轮失败、当前累计状态、历史失败分类、duplicate/error/cleanup warning 等。

## 18.12 Fact / Interpretation 分离

报告保存原始事实，例如 `binary HTTP 415`；可以另外提供解释，但不得把解释替代原始 error。

## 18.13 报告向后兼容要求

v0.0.14.5 不得删除 v0.0.14.4 已验证字段。

自动测试继续覆盖：时间字段、UTC offset、report type、report stage、state source、attachment policy、本轮附件统计、failure reason aggregation、per-run failure details、current cumulative state、LOCAL_PREFLIGHT 无虚构下载记录。

---

# 19. UI 与报告职责分离

UI：快速理解 + 导航。

详细报告：审计 + 排错 + 历史保存。

因此 UI 不需要默认展示 `conversation_id / message_id / full sandbox path / full failure object`，报告中可以保留。

---

# 20. 已成功附件也记录 provenance

虽然 UI 重点是未成功归档附件，但 provenance 不应只记录失败。

新成功附件也应记录：

```text
owner_role
source_category
reference_kind
```

这样以后可以准确回答成功保存了多少用户上传文件、多少 ChatGPT 生成资产。

---

# 21. 失败统计的解释原则

不同来源可能呈现不同失败分布，但统计相关性不等于根因。

例如 `assistant_generated_deliverable + binary HTTP 415` 可以描述为“当前观察到该类资源较多在 binary 阶段返回 415”，不能写成“ChatGPT生成文件一定因为 MIME 类型失败”。

---

# 22. 不属于 v0.0.14.5 的内容

严格禁止顺手加入：

- 新 downloader；
- 自动 repair；
- 自动重新生成 ChatGPT 文件；
- 更激进 retry；
- 新主状态；
- 自动定时同步；
- 新 Remote Index；
- Manifest 大版本迁移；
- 全量在线历史扫描；
- 自动搜索用户本地硬盘；
- Everything 集成；
- 云盘搜索；
- 自动判断“永久丢失”。

---

# 23. Core 安全边界

必须保持 v0.0.14.4 已验证不变量：

```text
classification != commit
write → verify → manifest commit → cleanup
LOCAL_ONLY never auto-delete
UNKNOWN != NONE
known attachment failures default no retry
failure evidence preserved
post-sync reconciliation
四主状态不变
```

v0.0.14.5 provenance：

> **只能解释事实，不能改变事实。**

---

# 24. 推荐实现模块

建议新增代码拆成：

```text
Attachment Provenance Classifier
        ↓
Attachment Failure Aggregator
        ↓
Conversation Attachment Integrity View
        ↓
Failure Explanation Dictionary
```

历史部分：

```text
Standalone Provenance Backfill Tool
```

不要把历史重建逻辑塞入日常同步 planner。

---

# 25. 建议实现顺序

## Stage A — Provenance Core

只完成新附件 provenance 分类、success/failure 都记录来源、向后兼容旧 Manifest、不改变任何同步状态。

## Stage B — Historical Backfill

完成 Local Dry Run、Audit、Optional Apply；Online Complement 仅保留为 fallback。不得先 Apply 再审计。

## Stage C — Conversation UI

完成会话列表附件缺口提示、附件维度筛选、会话详情附件摘要、紧凑未归档附件列表、单条展开、tooltip、打开原会话。

## Stage D — Report Integration

将 provenance / historical breakdown 整合进入 SYNC_COMPLETION 和 LOCAL_PREFLIGHT，同时保留 v0.0.14.4 已验证全部报告字段。

## Stage E — Regression + Browser Smoke

全部自动测试通过后，才进行真实浏览器验证。

---

# 26. 自动测试要求

至少覆盖：

## 数据模型
1. `user_upload` 正确识别；
2. `assistant_generated_deliverable` 正确识别；
3. `generated_media` 正确识别；
4. `assistant_asset` 保守分类；
5. 无证据时保留 `unknown`；
6. `file` 不自动等于 user_upload；
7. provenance 不参与同步分类。

## 历史补全
8. Dry Run 不写 Manifest；
9. Dry Run 不联网；
10. Dry Run 不下载附件；
11. Local JSON reconstruction 正确；
12. Unknown 保持 Unknown；
13. Online Complement 仅处理 unresolved；
14. Apply 只补 provenance，不修改状态/错误。

## UI
15. 主状态不改变；
16. 有附件缺口时显示次级提示；
17. 无缺口时不增加噪声；
18. 会话详情默认紧凑列表；
19. 长文件名截断；
20. 单条可原地展开/折叠；
21. tooltip 不覆盖原始错误；
22. “打开原会话”只出现一次；
23. 多附件时才出现来源筛选。

## 报告
24. v0.0.14.4 时间字段继续存在；
25. UTC offset 保留；
26. report type 保留；
27. report stage 保留；
28. attachment policy 保留；
29. 本轮与历史累计继续分离；
30. 历史 provenance 分类正确；
31. source × error 正确；
32. LOCAL_PREFLIGHT 不虚构下载；
33. 无失败时明确输出 0 / 无。

## Core 回归
34. attachment retry policy 不变；
35. project truth 不变；
36. transaction 不变；
37. content signature 不变；
38. post-sync reconciliation 不变；
39. LOCAL_ONLY 不自动删除；
40. unresolved identity 项目读取继续通过。

---

# 27. Browser Smoke 建议

至少验证：

- 正常完整会话；
- 有 1 个未成功归档附件；
- 一个会话有多个未归档附件；
- 用户上传 + 404；
- 用户上传 + 403；
- ChatGPT 生成 sandbox + 415；
- download_url expired；
- 长文件名；
- 项目内会话；
- 普通会话；
- 打开原会话；
- accountIdentityResolved=no；
- retry OFF；
- 报告日期时间；
- SYNC_COMPLETION；
- LOCAL_PREFLIGHT；
- 历史失败分类；
- 紧凑列表无长距离滚动。

---

# 28. Acceptance Criteria

## 数据

- 新附件均可产生 provenance；
- provenance 缺失时允许 `unknown`；
- 旧 Manifest 兼容；
- provenance 不参与同步分类；
- 原始 failure 不被覆盖。

## 历史

- 本地 JSON 可以重建旧 provenance；
- Dry Run 不修改 Manifest；
- Apply 必须显式触发；
- 无需在线时绝不联网；
- 不为填满字段进行猜测。

## UI

- 会话列表能看到附件缺口；
- 不增加第五主状态；
- 点击会话能看到该会话未成功归档附件；
- 默认紧凑列表；
- 每项可原地展开；
- HTTP 解释通过 tooltip/popover；
- 原会话链接只出现一次；
- 不产生大段重复滚动。

## 报告

- 保留 v0.0.14.4 全部报告字段；
- 有日期时间和 UTC offset；
- 有 report type / stage / state source；
- 有附件策略；
- 有本轮附件统计；
- 有历史 provenance 分类；
- 有来源 × 错误；
- 本轮失败与历史累计继续分离；
- Unknown 明确显示。

## Core

- v0.0.14.4 全部 regression PASS；
- 不改变 attachment retry；
- 不改变 project truth；
- 不改变 transaction；
- 不改变 content signature；
- 不改变 local reconciliation。

---

# 29. Stop Conditions

出现以下任一情况，立即停止实现并报告，不得继续扩大范围：

1. provenance 实现需要改变附件 PENDING 语义；
2. provenance 实现需要改变 Manifest 核心状态结构；
3. UI 实现要求新增第五主状态；
4. 历史补全要求全量在线重抓；
5. 历史补全要求自动重试失败附件；
6. 打开原会话无法可靠构造链接；
7. 为解释错误必须猜测根因；
8. 为做报告需要删除或覆盖已有 failure evidence；
9. v0.0.14.4 已通过的报告或 Core regression 出现退化。

---

# 30. Definition of Done

v0.0.14.5 的完成标准不是：

> 所有附件都成功下载。

而是：

> **所有当前能够获取的数据尽可能被保存；所有已知未成功归档内容都有足够的来源、会话上下文、失败阶段、原始错误和人工核查入口。**

从用户角度：

```text
会话列表
   │
   │  附件 3 未归档
   ▼
会话详情
   │
   │  文件名 | 来源 | 错误 | 阶段
   ▼
单条展开
   │
   │  时间 / 通道 / 标识 / 原始证据
   ▼
必要时
   │
   ├─ 打开 ChatGPT 原会话
   └─ 用户自行查找本地/NAS/网盘原件
```

从系统角度：

```text
远端会话
   ↓
尽可能获取
   ↓
本地归档
   │
   ├─ 成功 → 明确记录已归档 + provenance
   │
   └─ 失败 → 保存 provenance + 会话上下文 + failure stage + 原始 error
                                      ↓
                              用户可继续人工核查
```

---

# 31. 最终产品边界

ChatHarbor 不承诺：

> 100% 永久下载 ChatGPT 的所有历史资源。

ChatHarbor 承诺：

> **尽可能获取当前可取得的数据；不把任务结束伪装成内容完整；对未成功归档的内容提供透明、可追溯、可解释的证据，并把最终判断权交给用户。**

这也是 v0.0.14.5 的核心产品哲学。
