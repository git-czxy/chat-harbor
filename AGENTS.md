# Agent Operating Rules

本项目采用 Project Development Runtime。

## Brownfield Boundary

这是已有 Trae 历史的 Brownfield 项目。先以当前代码、Git 和运行证据重建基线；旧计划只作为 Historical / Planned 参考，不得覆盖当前实现。本次 Adoption 的 Stop Condition 是：新 Codex 会话仅依赖仓库内容即可恢复项目身份、当前进度、下一步允许事项和未验证事项。

本轮 Adoption 已明确：不大规模修改业务代码、不处理 UI 重叠 Bug、不开始新功能开发。候选事项登记到 `backlog/BACKLOG.md`，不得因发现候选事项自行切换主线。

## 每次进入项目

按顺序读取：

1. `PROJECT.md`
2. `STATE.yaml`
3. `backlog/ACTIVE.md`
4. 当前 active change
5. 相关 Decision / Spec

## 基本规则

1. 实际代码和运行证据优先于旧计划。
2. Plan 不是实现证据。
3. Discussion / Suggestion 不等于 Human Decision。
4. Unknown 不得自动补全。
5. 已关闭的 Human Decision 不得静默覆盖。
6. 未满足 Acceptance Criteria 不得标记完成。
7. Stage Transition 不豁免前置条件。
8. 发现非阻塞问题进入 Backlog，不得自行切换主线。
9. 低风险工程细节自行处理，不反复请求人工确认。
10. 影响 Goal/Scope/UX 取舍/权限/安全/许可/重大不可逆事项时触发 Human Gate。
11. 每项 active work 必须有 Stop Condition。
12. 实施完成必须留下 Evidence，并更新 STATE。

## Codex 执行边界

允许自主：

- 代码实现；
- 明显 Bug 修复；
- 测试；
- 小范围重构；
- Git 提交；
- 技术细节。

必须暂停受影响部分并请求决策：

- 产品行为存在多个合理方向；
- Scope 变化；
- 重大架构替换；
- 删除/迁移重要数据；
- 权限、隐私、安全；
- License / 公开发布；
- 与现有 Human Decision 冲突。

## 完成回报

不要只说“已完成”。

至少给出：

- RESULT
- CHANGED
- VALIDATION
- EVIDENCE
- COMMIT / PR
- STATE
- UNKNOWN / BLOCKED
- NEXT ALLOWED
