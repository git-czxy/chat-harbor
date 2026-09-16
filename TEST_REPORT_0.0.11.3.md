# ChatHarbor 0.0.11.3 Test Report

Automated regression suite: PASS.

Packaging regression found and fixed: 0.0.11.1 accidentally retained userscript metadata `@version 0.0.11.0`; 0.0.11.2 asserts the metadata replacement explicitly.

Inherited 0.0.11.2 assertions:
- launcher storage namespace is `chatharbor-fab-v2`;
- integrated sync no longer emits duplicate per-item FAB percentage/status;
- launcher remains busy-locked while runtime progress is shown only in the workspace card;
- preflight-confirmed records are excluded from the runtime work queue;
- runtime denominator uses actionable candidates only (`1/N actionable`, not `1/all selected`);
- prior convergence/cache/layout/network-policy regressions remain PASS.

- generated userscript metadata is explicitly `@version 0.0.11.3`.


## 0.0.11.3 build-contract regression

- PASS current runtime wording: `按实际待处理范围开始流式核验与写入`.
- PASS obsolete invariant wording `按选择范围开始流式核验与写入` is absent from `required_runtime_markers`.
- PASS the build invariant now tracks the actionable-work runtime wording.
- Runtime semantics are otherwise identical to 0.0.11.2.
