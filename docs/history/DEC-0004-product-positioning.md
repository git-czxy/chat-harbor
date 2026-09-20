# DEC-0004 — Archive Integrity over Claimed Completeness / 完整性审计优先于“完整备份”宣称

Date: 2026-09-20
Status: Human Accepted / Published

## 中文

ChatHarbor 不把“100% 完整备份”作为产品承诺。

产品承诺改为：

1. 尽可能保存当前可取得的对话、附件与相关资产；
2. 已知失败保留原始错误和失败阶段；
3. 区分附件来源，Unknown 可以保留；
4. 不把 403 / 404 / 415 / 500 / URL 失效擅自解释成永久删除或文件损坏；
5. 让用户可以从缺口回到对应原会话或本地来源继续核查。

该定位来自真实归档与附件失败审计，而不是营销目标。

## English

ChatHarbor does not make “100% complete backup” a product promise.

Its product contract is instead to:

1. preserve as much currently obtainable conversation and attachment data as possible;
2. retain raw errors and failure stages for known gaps;
3. preserve attachment provenance and allow Unknown to remain Unknown;
4. avoid translating 403 / 404 / 415 / 500 / expired URLs into unsupported claims of permanent deletion or corruption;
5. provide a path back to the original conversation or local source for further review.

This positioning comes from real archive and attachment-failure evidence, not from a marketing target.
