# Brownfield Baseline Evidence

## Claim

第一次 PDR Adoption 已以当前仓库实现为基线；新会话可以从仓库内容恢复项目身份、当前进度、下一步允许事项和未验证事项。

## Classification

### Confirmed current

- Git 当前分支为 `master`，基线提交为 `cf90fad3f5331c66e1013d76ce300217c73fed1e`。
- 仓库包含一个通用 Userscript、一个 ChatGPT 专用 Userscript 及 v0.1–v0.4 版本文本。
- 通用脚本当前包含 ChatGPT/Kimi/Gemini/Grok/DeepSeek 适配器，以及速度、去重、分批 ZIP、重试、格式选项和选择列表相关实现；新平台灰度开关为 `ALLOW_GRAYSCALE = false`。
- ChatGPT v0.4 当前多选路径在超出批次上限时提示分批，然后将完整 `selectedList` 传入 `startSelectiveExportProcess`；未见旧计划所述的 `slice(0, MAX_EXPORT_PER_BATCH)` 截断。
- PDR 最小结构已建立：`PROJECT.md`、`AGENTS.md`、`STATE.yaml`、`backlog/`、`specs/`、`changes/archive/`、`decisions/`、`evidence/`。

### Historical

- `.trae/documents/ai-conversation-exporter-upgrade-plan.md` 及其“用户已拍板”、阶段和验证表述属于 Trae 历史记录；不自动等于当前授权或实现证据。
- `ChatGPT导出脚本（超保守版）v0.1.txt` 至 `v0.3.txt` 是历史版本材料。

### Planned but not implemented

- 旧计划提出的 Doubao、Qwen、Yuanbao 三个平台适配器在当前通用脚本的适配器解析路径中未见实现；旧计划未被执行为这些功能的证据。

### Partially implemented

- 旧计划所述安全/去重/分批/格式/选择器方向在当前通用脚本中已有代码，但本轮没有真实网站、登录态、下载结果或跨平台行为验证，因此只能判为“代码存在、运行未验证”。
- PDR 状态恢复结构已初始化；尚无 active Change、Spec 或验证过的真实运行 Evidence。

### Unknown

- 真实网站上的导出成功率、接口兼容性、浏览器下载行为和多平台运行结果。
- 两个插件同时启用时的 UI 重叠是否仍可复现；本轮按要求未处理。
- 上游 provenance、作者授权链、许可证兼容性和未来公开发布资格。
- 用户是否已对当前实现作最终接受。

### Conflict

- 旧计划把部分能力写成待实施目标，而当前通用脚本已经包含对应代码；按 PDR 规则保留当前实现为事实，并将计划标为 Historical / Planned，不回退或重建代码。
- 旧计划的“验证方法”不能替代实际验证；本轮只记录可观察的静态仓库证据。

## Method

检查了仓库文件结构、Git status/log/tree/remote、Trae 计划、脚本关键实现位置和 PDR 初始化结果；并通过标准输入执行 Node 语法检查。关键命令包括：

```powershell
git status --short --branch
git log --oneline --decorate -10
git remote -v
git ls-tree -r --name-only HEAD
Select-String -Path '*.txt' -Pattern 'exportConversations','ALLOW_GRAYSCALE','startSelectiveExportProcess'
Get-Content -Raw '通用AI对话导出脚本.txt' | node --check --input-type=commonjs
Get-Content -Raw 'ChatGPT导出脚本（超保守版）v0.4.txt' | node --check --input-type=commonjs
```

## Result

PARTIAL — 当前实现和治理文件已建立；两份当前脚本文本静态语法检查 PASS，但真实运行、UI 复现、许可核验和用户验收仍未验证。

## Limitations

本证据不证明真实网站运行成功，不证明 UI Bug 已修复，不证明新平台适配器可用，也不证明任何上游代码可公开发布。
