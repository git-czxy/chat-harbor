# ChatHarbor

ChatHarbor 是一个本地优先的 AI 对话归档与同步工具。当前仅支持 **ChatGPT**；其他平台只在真实需求出现后再增加 Adapter，不预先建设通用多平台框架。

## 当前版本

- 历史基线：`v0.4`（用户自定义的专用版版本号）
- 当前开发版：`v0.5.0`
- `v0.5.0` 核心：**Version-aware Scan + Directory Sync**

## v0.5.0 做了什么

在保留既有 ZIP 导出、保守请求节奏、自动分批、随机暂停、重试、取消和导出状态恢复能力的基础上，新增：

1. 使用 Chromium / Edge 的 File System Access API 直接选择本地归档目录；
2. 递归扫描目录内已有 ChatGPT conversation JSON；
3. 以 `conversation_id` 为唯一身份，不以标题或文件名判断同一会话；
4. 使用远端 `update_time` + 标题差异做低成本预筛；
5. 对候选变化重新抓取完整 conversation detail，并以 `mapping + current_node` 的 SHA-256 内容签名做最终分类；
6. 支持 `NEW / UPDATED / UPDATED_AND_RENAMED / RENAMED_ONLY / METADATA_ONLY / UNCHANGED`；
7. 标题变化时采用“先写新文件并校验，再删除旧文件”的安全顺序；
8. Directory Sync 不经过 ZIP，不会为每个文件触发浏览器下载提示；
9. 网络侧仍按原有 batch size、请求延迟和批间随机暂停执行；
10. 每个 conversation 成功写盘后更新 `ChatHarbor_manifest.json`，提高中断后的可恢复性。

## 如何使用 Directory Sync

1. 安装 `ChatHarbor-v0.5.0.user.js` 到 Tampermonkey。
2. 在 Edge / Chromium 中打开 ChatGPT。
3. 打开 ChatHarbor，进入“选择对话导出”列表。
4. 点击 **同步本地目录**。
5. 选择一个**用于测试的归档副本目录**。第一次验证不要直接使用唯一的原始备份。
6. ChatHarbor 会先强制刷新远端列表，再扫描本地 JSON，并弹出预检摘要。
7. 预检后可选择：
   - **仅核验已有变化项（不写盘）**；
   - **仅同步已有变化项**；
   - **开始全部同步**（NEW + 已有变化项）。

## 版本判断语义

- **Identity**：`conversation_id`
- **Remote change prefilter**：`update_time` 或标题变化
- **Content change verification**：`SHA-256(stable(mapping + current_node))`

因此，即使 ChatGPT “只改标题”时也会改变 `update_time`，最终仍可通过内容签名识别为 `RENAMED_ONLY`。

## 本地安全策略

- 本地只存在、远端列表不存在的会话：**不自动删除**。
- 扫描发现同一 `conversation_id` 多份本地 JSON：报告重复，但不自动清理。
- legacy 归档中未被 manifest 明确追踪的旧图片/附件：不自动删除。
- v0.5 以后由 manifest 追踪的旧资源，只有在新的 conversation 完整落盘后才允许清理。
- 标题变化不会改变 conversation identity。

## 当前限制

- Directory Sync 依赖 File System Access API，主要面向 Edge / Chromium。
- 当前每次同步都由用户重新选择目录；尚未持久保存 Directory Handle。
- 当前只支持 ChatGPT。
- UI 只做支持 v0.5 同步所需的最小改动；此前讨论的 Workspace/UI Refresh 后置。
- 不实现 Conversation Lineage、历史版本仓库、差分 patch、多云同步等未被当前真实需求证明的能力。


## 语言标识约定

ChatHarbor 按**书写体系**区分中文，而不是按地区命名：

- `zh-Hans`：简体中文
- `zh-Hant`：繁体中文
- `en-US`：English

浏览器可能返回 `zh-CN`、`zh-TW`、`zh-HK`、`zh-MO` 等 locale；这些只作为输入检测，内部统一映射为 `zh-Hans` 或 `zh-Hant`。外部 UI 使用“简体中文 / 繁体中文”，不使用地区名称代替书写体系。

## 来源与致谢

ChatHarbor 直接起源于：

- **OwlCt/ChatGPT-Export** — https://github.com/OwlCt/ChatGPT-Export

感谢 OwlCt 及其上游贡献者提供原始导出器与开源基础。ChatHarbor 保留并遵循原项目 MIT License 的来源链和许可要求。

上游项目自身还有更早的 lineage；详见 `ACKNOWLEDGEMENTS.md`。
## Directory Sync safety check

Before writing, ChatHarbor shows a version-aware preflight summary. Existing-conversation change candidates can be fetched in a **verification-only / no-write** mode to determine whether the change is UPDATED, UPDATED_AND_RENAMED, RENAMED_ONLY, or METADATA_ONLY. This dry-run does not modify files, the directory manifest, or exported-state records.

