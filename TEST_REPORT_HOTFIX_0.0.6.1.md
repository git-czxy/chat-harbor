# ChatHarbor 0.0.6.1 Hotfix Test Report

## Scope

Entry/launcher visibility regression only. No sync-core redesign.

## Checks

- Python patcher syntax: PASS
- Fixed upstream blob guard retained: PASS
- Launcher auto-half-hide override present: PASS
- Existing picker reused; no second selector added: PASS
- First-level sync route label present: PASS
- Preflight and directory-sync button markers retained: PASS
- Build-time fail-closed runtime marker checks added: PASS
- Core integrated-sync patch remains otherwise unchanged from 0.0.6.0.

## Evidence boundary

Actual visibility in Tampermonkey + current ChatGPT DOM remains a real-browser check and cannot be substituted by static tests.
