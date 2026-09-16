# ChatHarbor v0.5.0 — First-run test plan

首次测试请使用**282 条旧记录的复制目录**，不要直接对唯一原始备份操作。

## Gate A — 安装与语法

- Tampermonkey 能正常安装脚本。
- ChatGPT 页面出现 ChatHarbor 按钮。
- 旧 ZIP 导出入口仍可打开。
- 选择器能正常刷新列表。

## Gate B — Scan-only 预检

点击“同步本地目录”，选择 282 条旧记录的复制目录。预检应展示：

- 本地会话数；
- 远端会话数；
- NEW 数；
- 远端更新时间变化候选；
- 仅标题差异候选；
- UNCHANGED 数；
- LOCAL_ONLY 数；
- duplicate conversation_id 数；
- 已有会话变化候选的标题、ID、本地/远端更新时间与标题差异。

当前首次真实预检基线：

- 远端：393
- 本地：282
- NEW：111
- 远端更新时间变化候选：1
- 仅标题差异候选：0
- UNCHANGED：281
- LOCAL_ONLY：0
- duplicate conversation_id：0

这一步应保持为只读；点击取消不得写盘。

## Gate C — 变化项 dry-run 核验

在预检窗口点击“仅核验已有变化项（不写盘）”。

预期：

- 只抓取已有会话中的变化候选，不抓取 NEW；
- 根据 mapping/current_node 内容签名和 title 真实分类为 UPDATED / UPDATED_AND_RENAMED / RENAMED_ONLY / METADATA_ONLY；
- 显示 conversation ID、本地/远端更新时间、内容是否变化、标题是否变化；
- 不写入、覆盖、重命名或删除任何文件；
- 不更新 `ChatHarbor_manifest.json`；
- 不更新 exported / pending 状态。

Gate C 通过后，再进入写盘验证。

### Gate C 首次真实结果 — PASS

唯一的已有变化候选：

- 标题：`每日重点趋势简报`
- conversation_id：`6a95940b-8f34-83ee-a167-329a64a294a5`
- 本地更新时间：2026/9/10 09:24:26
- 远端更新时间：2026/9/13 09:39:26
- 内容变化：YES
- 标题变化：NO
- 分类：`UPDATED`

这验证了 ID-only 去重会遗漏“同一 conversation_id 后续继续增长”的真实场景。

## Gate D — 小样本写盘行为验证

在第一次写盘前，优先使用 **“仅同步已有变化项”**，只对上述 1 条 `UPDATED` 会话执行目录写入；不要同时抓取 111 条 NEW。

通过后再验证其他类型。

建议先验证 4 类真实样本：

1. NEW：新建一条测试会话；
2. RENAMED_ONLY：只修改一条已有会话标题；
3. UPDATED：已有会话追加一轮内容但标题不变；
4. UPDATED_AND_RENAMED：追加内容并修改标题。

同步后检查：

- JSON 中 conversation_id 不变；
- 标题变化后的新文件名已生成；
- 新文件成功后旧标题 JSON/MD 才消失；
- UPDATED 的 JSON 包含新增消息；
- Markdown 能正常打开；
- 图片/附件链接（如有）可用；
- 根目录出现 `ChatHarbor_manifest.json`。

## Gate E — 取消与恢复

- 在同步过程中点击浮动 ChatHarbor 按钮并选择取消；
- 已完成 conversation 应保留；
- 未完成 conversation 不应被错误登记为完成；
- 再次同步时已完成项应不再重复抓取（除非远端又更新）。

## Gate F — v0.4 回归

- ZIP 导出仍按批次生成；
- 批次暂停仍生效；
- 已导出/待确认逻辑仍正常；
- 从 ZIP 恢复已导出记录仍可用。

只有 Gate C/D 通过后，再对完整 NEW + updated 集合执行正式同步。

### Gate D 首次真实写盘结果 — 执行层 PASS / 文件层待复核

用户执行“仅同步已有变化项”后：

- Planned: 1
- Succeeded: 1
- Failed: 0
- UPDATED: 1
- UPDATED + RENAMED: 0
- RENAMED ONLY: 0
- METADATA ONLY: 0

同时暴露两个 UI/流程回归并已修复：

1. locale 内部 key 从地区型改为 `zh-Hans` / `zh-Hant` 后，语言检测采用“两轮扫描”导致 `zh-CN` 未先映射、反而命中后续 `en-US`，使局部 UI 变为英文；现改为按浏览器候选顺序逐项“精确匹配 + 归一化映射”。
2. “仅同步已有变化项”路径错误调用 `closeDialog()`，导致主选择窗口在局部同步开始时被关闭；现已移除该调用，局部同步应保持主窗口。

仍需人工复核本地目录：UPDATED JSON/Markdown 是否更新、是否无重复 conversation、`ChatHarbor_manifest.json` 是否记录最新 update_time/content_signature。
