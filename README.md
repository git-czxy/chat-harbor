<div align="center">

# ChatHarbor

**本地优先的 ChatGPT 对话归档与完整性审计工具**

[中文](README.md) · [English](README.en.md)

</div>

ChatHarbor 用于把你自己的 ChatGPT 对话持续保存到本地，并明确告诉你：**哪些内容已经归档、哪些附件尚未成功取得、平台返回了什么错误、对应哪个原始会话。**

当前公开版本：**v0.0.14.5**

> ChatHarbor 不承诺“100% 完整备份”。它承诺的是：尽可能取得当前可访问的数据，并对已知缺口保持透明、可追溯、可核查。

## 主要能力

- **增量同步**：以 `conversation_id` 作为稳定身份；远端时间只用于预筛，内容签名用于最终内容判断。
- **本地归档**：保存原始 JSON、Markdown、附件资源与 Manifest。
- **项目 / 归档状态**：支持 ChatGPT 普通会话、项目会话与归档状态的统一查看。
- **附件完整性审计**：区分用户上传、ChatGPT 生成交付文件、生成媒体等来源；记录未成功归档附件的原始错误与失败阶段。
- **会话级恢复入口**：从附件缺口直接回到对应 ChatGPT 原会话核查。
- **保守请求策略**：支持请求间隔、批次暂停、重试、暂停 / 恢复与安全取消，减少不必要的请求压力。
- **事务式写入**：写入 → 校验 → Manifest 提交 → 仅清理已跟踪旧路径；`LOCAL_ONLY` 不会被普通同步自动删除。
- **可审计报告**：同步完成与本地预检均可生成带时间、策略、当轮结果和历史完整性摘要的报告。

## 安装

推荐环境：**桌面 Chromium 浏览器（Edge / Chrome）+ Tampermonkey**。当前归档流程依赖浏览器目录访问能力，其他浏览器或 Userscript 管理器的兼容性可能不同。

1. 安装 Tampermonkey。
2. 推荐从 [Greasy Fork](https://greasyfork.org/scripts/596705-chatharbor) 安装；也可以直接打开 [`ChatHarbor.user.js`](https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js) 从 GitHub 安装。
3. 打开 `https://chatgpt.com/`，点击页面右侧 ChatHarbor 入口。
4. 第一次使用时选择一个本地保存目录。

Greasy Fork 是辅助发行渠道，GitHub 仍是代码与正式版本的权威来源。通过 GitHub 直接安装的脚本使用仓库 `main` 分支作为更新源；通过 Greasy Fork 安装的脚本由 Greasy Fork 提供后续更新。

## 使用原则

ChatHarbor 的用户主状态始终只有四种：

- **已同步**
- **待同步**
- **需确认**
- **异常**

附件完整性是独立维度。一个会话可以“已同步”，同时显示“附件 3 未归档”；这表示会话主体已完成同步，但仍存在明确记录的附件缺口。

对于 403 / 404 / 415 / 500 或临时下载地址失效，ChatHarbor 保留平台原始错误，并提供解释，但**不会把这些状态擅自翻译成“永久丢失”或“文件损坏”**。

## 数据与隐私

- ChatHarbor 在你的浏览器登录态下读取 ChatGPT 自身接口，并把归档写入你选择的本地目录。
- ChatHarbor 没有自己的上传服务器，不会把你的对话归档上传给本项目维护者。
- Userscript 通过 `cdnjs.cloudflare.com` 加载 JSZip 依赖；除此之外，核心数据访问发生在 ChatGPT 与你选择的本地目录之间。
- 建议在首次大规模同步前先用少量会话测试保存位置与浏览器权限。

## 历史与代码血统

ChatHarbor 的历史并不是简单的“旧版 → 新版”。它经历了几条明确的探索路线：

1. **现实需求起点**：ChatGPT 是维护者的主力 AI，而官方完整导出链接长期未能及时取得，因此需要自行保存长期会话。
2. **Conservative Lineage**：直接在 OwlCt 的 ChatGPT 专用导出工具基础上，为个人实际使用逐步加入慢速 / 抖动、分批、暂停、去重、恢复、重试、取消与 UI 等能力。直到保守版 v0.5，这些版本主要直接复制进 Tampermonkey / Violentmonkey 使用，脚本头部没有同步完成规范化修改。
3. **Generalization / Option C 探索**：参考 `wanda1416/ai-chat-exporter` 的多平台 Adapter 思路，尝试 `Core + Platform Adapters` 的重组路线，并留下 PDR、Change、Evidence 与 Browser Verification 记录。
4. **Lineage Reset**：为了降低多 donor 重组带来的 provenance、兼容和 Authority 复杂度，当前实现重新建立单一、可审计的 clean lineage。
5. **Current clean lineage**：当前代码主线直接基于固定的 `huhusmang/ChatGPT-Exporter` 上游快照，并从保存的 Gate / Release 工件重建 Git 历史；旧 Conservative / Pilot 路线保留为需求证据、行为参考和回归 oracle，而不是当前代码祖先。
6. **当前产品定位**：在真实附件失败审计之后，ChatHarbor 收敛为“本地归档 + 完整性审计 + 透明失败诊断”，不再用“100% 备份”作为承诺。

完整说明见：[HISTORY.md](HISTORY.md)。

旧 GitHub/PDR 路线保留在：`legacy/pre-clean-lineage`。

> **Git 历史说明：** 当前 clean-lineage 的早期 Git commits / tags 是根据保存的发布包和校验值在 2026-09-16 重建的。它们用于恢复版本演进，不应被描述成当时原始生成的 Git commit hash。详见 [`docs/history/RECONSTRUCTION.md`](docs/history/RECONSTRUCTION.md)。

## v0.0.14.5

本版主要完成：

- 附件来源 provenance；
- 未成功归档附件的会话级查看；
- 403 / 404 / 415 / 500 / URL 失效解释；
- 原会话导航；
- 可审计同步 / 预检报告；
- 历史附件来源独立 Backfill 工具；
- Userscript 产品身份与上游来源清理；
- 项目标签与附件详情 UI 收尾。

详见 [CHANGELOG.md](CHANGELOG.md) 与 [`docs/releases/v0.0.14.5.md`](docs/releases/v0.0.14.5.md)。

## 历史来源补全工具

`migration-tools/ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js` 是一次性 Migration / Repair Tool，用于给旧 Manifest 补充附件来源字段。

它默认 **Dry Run**，不会下载附件，也不会修改 Manifest。请先阅读工具内说明；它不是日常同步 Core 的组成部分。

## 作者与来源

维护者：**挠痒痒的电饭煲（[@git-czxy](https://github.com/git-czxy)）**

当前 clean-lineage 的直接上游、历史 Conservative / Generic 路线及许可证说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## License

ChatHarbor 自有修改以 [MIT License](LICENSE) 发布。第三方来源与原始许可声明请同时参阅 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
