# ChatHarbor 0.0.11.1 Test Report

Automated regression suite: PASS.

Additional 0.0.11.1 assertions:
- launcher storage namespace is `chatharbor-fab-v2`;
- integrated sync no longer emits duplicate per-item FAB percentage/status;
- launcher remains busy-locked while runtime progress is shown only in the workspace card;
- preflight-confirmed records are excluded from the runtime work queue;
- runtime denominator uses actionable candidates only (`1/N actionable`, not `1/all selected`);
- prior convergence/cache/layout/network-policy regressions remain PASS.
