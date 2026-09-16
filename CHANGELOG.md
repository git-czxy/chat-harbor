# Changelog

## v0.5.0 — Version-aware Directory Sync

首个规范采用 SemVer 的 ChatHarbor 版本。

### Added

- ChatHarbor 正式项目命名。
- File System Access API / Directory Sync。
- 递归本地归档扫描。
- conversation_id 唯一身份识别。
- update_time + title 预筛。
- mapping/current_node SHA-256 内容签名。
- NEW / UPDATED / UPDATED_AND_RENAMED / RENAMED_ONLY / METADATA_ONLY 分类。
- 标题变化安全更名。
- conversation 粒度 manifest 提交与恢复信息。
- Directory Sync 资源文件使用 conversation 短 ID 前缀，降低跨会话同名覆盖风险。
- 目录同步预检增加已有变化候选明细（标题、conversation_id、本地/远端更新时间、标题差异）。
- 增加“仅核验已有变化项（不写盘）” dry-run，用于首次验收与异常审计；该模式不更新文件、manifest 或 exported 状态。
- 增加“仅同步已有变化项”写盘 Gate，可在不抓取 NEW 会话的情况下单独验证 UPDATED / RENAMED 类既有会话。
- 语言内部命名改为按书写体系区分：`zh-Hans`（简体中文）/ `zh-Hant`（繁体中文）；浏览器返回的 `zh-TW` / `zh-HK` / `zh-MO` 等仅作为输入映射，不再作为 ChatHarbor 自身语言标识。

### Preserved

- 原 v0.4 ZIP 导出路径。
- 保守请求速度档位。
- 最大批次限制。
- 批间随机暂停。
- 重试 / cancel。
- pending / exported 两阶段 ZIP 导出状态。
- JSON + Markdown + 图片/附件导出。

### Explicitly deferred

- 全面 UI 重做。
- 通用多平台 Core / Adapter Framework。
- Conversation Lineage。
- 历史版本库 / 差分 patch。

## v0.4 — Historical dedicated-edition baseline

`v0.4` 是用户此前为 ChatGPT 专用版自行使用的历史版本号，不对应 OwlCt 上游仓库的版本编号。本包保留原始附件副本作为 baseline，不回写历史版本。

### Acceptance fixes (same v0.5.0 validation cycle)

- 修复语言归一化优先级回归：当浏览器语言列表为 `zh-CN` / `zh-HK` 等旧式地区标签并同时包含 `en-US` 时，必须先按候选顺序映射到 `zh-Hans` / `zh-Hant`，不能因为内部 key 已改名而错误命中后续 English。
- 修复“仅同步已有变化项”完成后关闭主选择窗口的问题；局部同步现在保留主窗口，完成提示关闭后可继续操作。
