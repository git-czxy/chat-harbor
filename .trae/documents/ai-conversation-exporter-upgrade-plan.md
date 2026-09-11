# 《通用AI对话导出脚本》升级实施方案

## Context（背景与目标）

项目目标是打造"AI 通用的对话导出软件"。现有两份油猴脚本：

- **通用脚本**（`通用AI对话导出脚本.txt`）：覆盖 ChatGPT/Kimi/Gemini/Grok/DeepSeek 五个平台，采用 adapter 架构。但导出能力简陋：固定 500ms 节流、仅区间+附件、单 zip 全量、无去重/续传/分批/重试/速度档位/二次确认/历史备份。
- **ChatGPT v0.4 脚本**（`ChatGPT导出脚本（超保守版）v0.4.txt`）：ChatGPT 专用，含成熟的防风控安全体系（6档速度、两阶段去重、分批限速、指数退避重试、去重历史备份、选择列表筛选、二次确认、导出取消）。

本次目标（用户已拍板）：
1. **升级通用脚本**为主产物，把 v0.4 的安全体系移植并通用化到多平台。
2. 新增 **豆包 / 千问(通义) / 腾讯元宝** 三个平台适配器（搭架+灰度，离线无法实测 API，标注 TODO）。
3. **Kimi 国内版 + 国际版分开适配**（现仅 `kimi.com`）。
4. **修复 v0.4 多选 bug**：选中超批次上限时目前被 `slice` 截断为单批，应放行给底层分批引擎分 N 批执行。
5. 附加通用能力：多档速度节流、去重与续传、分批限速（批间长暂停）、自动重试退避、去重历史备份、二次确认、格式定制（reasoning/sources/manifest/纯文本）、筛选排序。

不改动 v0.4 其余部分；v0.4 仅修复多选 bug。

---

## 实施步骤

### 阶段 1：安全/去重/限速公共层（低风险，先行）

在 `通用AI对话导出脚本.txt` 内新增统一块（保持单文件单 IIFE，不做模块化拆分，按分区注释组织），插入位置参考现有 L1300（`sleep()` 前后）：

| 新增函数/常量 | 参考 v0.4 来源 | 说明 |
|---|---|---|
| `CONFIG`（`SPEED_LEVELS` 6档 + jitter、`MAX_EXPORT_PER_BATCH=20`、`BATCH_PAUSE_MIN/MAX`） | v0.4 L25-L39 | 速度/分批参数 |
| `getPlatformKey()`（`ai_exporter_exported_{platform}_v1` / `ai_exporter_pending_{platform}_v1`） | v0.4 L53 | 去重 key **按平台命名空间** |
| 去重族：`readIdSet/writeIdSet/getExportedIds/getPendingIds/isAlreadyExported/markConversationsPending/markConversationsExported/clearHistory` | v0.4 L53-L124 | 两阶段 pending/exported |
| `exportHistoryBackup/importHistoryBackup(file, platform)` | v0.4 L127-L210 | JSON 备份加 `platform` 字段、v1 兼容 |
| `getSettings/saveSettings` | — | 速度/批次/格式参数持久化，防御式读取 |
| `runJitter`/`randomPauseLocal`/`withExponentialBackoff`/`fetchWithRetry` | v0.4 L1218/L1744 | 分档速度 + 重试退避 |

### 阶段 2：分批限速导出引擎改版

重写通用脚本 `exportConversations()`（L1426-L1487）与 `runExport()`（L2535-L2558）：

- 新签名增加：`speedIndex`、`onBatch(batchBlob, filename, {batchIndex, totalBatches, okIds})`、`shouldContinue()`（取消探针，复用现有取消按钮）。
- 流程：list→去重过滤→`chunk(metas, batch)`→**每批独立 `ZipSink`**（防超大 zip 内存 OOM）→逐条 `fetchWithRetry(fetchConversation)`+附件→`markConversationsPending`→`sink.finish()`→`download()`（经 `onBatch`）→成功才 `markConversationsExported`。
- 连续失败 ≥3 触发网络保护暂停 `120*min(fails-2,5)` 秒；批间 `randomPauseLocal()` 长暂停。
- 新增 `buildBatchFilename(platform, selectionType, date, time, bi, total)`（参考 v0.4 L1400）。
- **兼容位**：`totalBatches===1` 时文件名不带 `_batchXofY` 后缀，单批体验与现状一致。
- 保留现有 `ZipSink`、`download()`、`sleep()`、`throttled()`（后者仅给附件下载用）。

```
单 zip 全量 ──► 每批独立 zip + 批间暂停 + 指数退避重试 + 去重标记
```

### 阶段 3：格式定制

把 exporter 从固定结构改为接受 `formatOptions` 对象（默认值存 `ai_exporter_settings.format`）：

- `DEFAULT_FORMAT = { outputFormat:'md'|'txt'|'json', includeReasoning, includeSources, includeAttachmentsManifest, includeMetaHeader, jsonPretty }`
- 改动：`renderMessage()`（L1536-L1554）按 `includeReasoning`/`includeSources` 跳过相应块；`renderMarkdown()`（L1556-L1581）按 `includeMetaHeader`/`includeAttachmentsManifest` 控制；新增轻量 `plainify()` 处理 txt。
- `markdownExporter(fmt)` / `jsonExporter(fmt)` 接收 fmt。

### 阶段 4：选择列表 UI + 筛选排序 + 二次确认

新增 `showConversationPicker(adapter, run)` 取代 `askChoices()`（L2574，后者降级保留为兼容回退）：

- 数据源：`for await (m of adapter.listConversations()) metas.push(m)`。
- state：`{list, filtered, selected:Set, query, exportStatus:'all'|'exported'|'unexported', timeField, startDate, endDate, sortBy, pageSize, visibleCount, loading}`。
- `applyFilters()` 关键词/导出状态/日期；`renderList()` 分页+checkbox 多选+全选/清空。
- 速度档位 + 批次上限控件放选择器内，改动后 `saveSettings()`。
- **二次确认**：点导出时仅提示"共 N 条、将分 M 批、每批 ≤K、批间暂停"，**绝不截断**。附"去重历史"按钮（导出/导入备份、清空历史）。

### 阶段 5：新增平台 adapter + Kimi 拆分（灰度）

统一接口 `{platform, detect(), listConversations(), fetchConversation(id)?, refreshToken?}`。因离线无登录态无法实测，**全部默认灰度关闭**：`resolveAdapter()`（L2526）默认排除新平台，仅当常亮 `ALLOW_GRAYSCALE=true` 或 URL 显式 `?exporter_test=xxx` 才启用；端点标注 `// TODO(实测)`。

- **Kimi 拆分**：`KimiAdapter`（国际，`kimi.com`，platform=`kimi`）+ `KimiDomesticAdapter`（`kimi.moonshot.cn` 等，platform=`kimi_cn`）。区分现有 L1082 BASE_URL 与国内版；`resolveAdapter` 数组先精确后通配。
- **DoubaoAdapter**（`platform='doubao'`，@match `www.doubao.com/*`）：端点 `https://www.doubao.com/samantha/thread/` 系列；DOM 备选 `[data-testid="chat_list_thread_item"]`，`id.split("_")[1]`。TODO 实测。
- **QwenAdapter**（`platform='qwen'`，@match `qianwen.aliyun.com/*`）：session 列表/历史接口 TODO 实测。
- **YuanbaoAdapter**（`platform='yuanbao'`，@match `yuanbao.tencent.com/*`）：TODO 实测。
- 头部 `@match` 追加对应域名；灰度阶段 `listConversations` 未实现时 `throw` 定制错误，不污染主流程。

### 阶段 6：v0.4 多选 bug 修复

文件 `ChatGPT导出脚本（超保守版）v0.4.txt`，`exportBtn.onclick`（L2258-L2267）：

- 根因：调用 `startSelectiveExportProcess` 前 `selectedList.slice(0, MAX_EXPORT_PER_BATCH)` 截断成单批；底层 `exportConversations`（L1202-L1370）本身已支持全量分批，无需改引擎。
- 改为：移除 `slice`，仅当 `selectedList.length > MAX` 时 `confirm` 提示"共 N 条将分 M 批导出"，确认后**全量**传给 `startSelectiveExportProcess`。确认文案用中英双语（建议新增 `t('alert.multiBatch', {total, batches})`，L2262 的 `t('alert.batchLimit')` 可废弃或改义）。

关键文件：`通用AI对话导出脚本.txt`（改造主体：L12 @match、L1300 常量、L1426 exportConversations、L1488 exporters、L2535 runExport、L2574 askChoices、L1261 KimiAdapter、L2526 resolveAdapter）、`ChatGPT导出脚本（超保守版）v0.4.txt`（移植源 L25-L39/L53-L124/L1202-L1370/L1721-L1777/L2023-L2414、修复 L2258-L2267）。

复用现有：`sleep()`L1303、`ZipSink`L2451、`download()`L2502、`throttled()`L1306、`conversationBaseName`L1298。

---

## 执行顺序与验证

| 阶段 | 验证方法 |
|---|---|
| 1 安全层 | `node --check` 语法（抽取 IIFE 体用 `new Function` 校验）；grep 函数引用完整；实站在 GPT 页测试历史导出/导入 |
| 2 分批引擎 | 语法过；审查 `onBatch`/ZipSink 每批生命周期不 cross-use；实站 GPT/Kimi 跑 3 条小批量验证 `_batchXofY` 文件名 |
| 3 格式 | 语法过；实站验证关闭 reasoning/sources/manifest 后的 md/txt 输出 |
| 4 UI | 语法过；实站验证筛选（关键词/日期/已导出）、多选、二次确认文案 |
| 5 新平台/Kimi | `resolveAdapter` 顺序审查；确认 `ALLOW_GRAYSCALE=false` 不误触发；Kimi 国际/国内各开一页验证 `detect()` 单选 |
| 6 v0.4 bug | 实站：选中 25 条(>20)，确认提示 2 批，产出 batch1of2/batch2of2 两个 zip |

## 风险与回退
- 分批改造是最大变更：先保"单批=1 个 zip 文件名不变"作兼容位，≤3 对话体验与现状一致。
- 新平台 adapter 全程灰度，定制抛错不污染 `resolveAdapter`。
- localStorage key 全带 `_v1`；类型变化升 `_v2`，`readIdSet` 容错返回空集合，老数据安全。
- 油猴脚本无 CI，核心验证靠 `node --check` 语法 + 结构审查 + 用户实站测试。