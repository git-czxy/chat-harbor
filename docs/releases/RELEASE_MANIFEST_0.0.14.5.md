# ChatHarbor v0.0.14.5 — Release Manifest

Date: 2026-09-20  
Status: **Human Approved / Release Ready**

## Primary artifacts

| Artifact | SHA-256 |
|---|---|
| `ChatHarbor.user.js` | `c600d498e8cbe92dc987a94abe319b4f2cd25edab3e4a85749827043a941b1b4` |
| `migration-tools/ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js` | `229b8a52ae8bf2582645520187102c3a1dcf58d2438e9b87f71e59c5cd336e20` |

## Lineage boundary

Current mainline direct upstream recorded by preserved clean-lineage evidence:

- `huhusmang/ChatGPT-Exporter`
- fixed commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- fixed userscript Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f`

Earlier Conservative / Generic / Pilot work remains historical evidence and is not a code ancestor of `main`.

## Development milestone consolidation

- `0.0.14.2` — validated development milestone; not separately released
- `0.0.14.3` — validated development milestone; not separately released
- `0.0.14.4` — validated development milestone; not separately released
- `0.0.14.5` — first formal public release

## Validation

- Automated current-release tests: PASS
- Browser Smoke: PASS
- Normal-conversation original-link routing: PASS
- Project-conversation original-link routing: PASS
- Historical provenance Dry Run: PASS (`280/280`, Unknown `0`)
- Historical provenance Apply: not executed; optional migration path, not a release blocker

## Public identity

- Maintainer: `git-czxy`
- Display name: 挠痒痒的电饭煲
- Repository: `https://github.com/git-czxy/chat-harbor`
- License: MIT for ChatHarbor modifications; third-party notices preserved separately
