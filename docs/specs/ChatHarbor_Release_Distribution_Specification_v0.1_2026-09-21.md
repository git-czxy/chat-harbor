# ChatHarbor Release & Distribution Specification v0.1

Date: **2026-09-21**  
Status: **Confirmed / Active**  
Scope: **Post-v0.0.14.5 release governance**  
Authority: Human-confirmed decisions A + B, durable in the current GitHub clean lineage.

## 1. Purpose

This specification defines the minimum release/distribution governance required before any next-version development code reaches `main`.

It exists because `main` currently serves two roles at once:

1. Current stable / Current Truth branch;
2. the live Userscript installation and update source through:

```text
@downloadURL https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js
@updateURL   https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js
```

As long as `main` directly feeds installed Userscripts, unreleased code with an increased `@version` must not be merged into `main`.

## 2. Current baseline

At adoption of this specification:

- Stable release: `v0.0.14.5`
- Stable code baseline: `main`
- Historical branch: `legacy/pre-clean-lineage`
- `master` is a non-authoritative historical residue currently pointing to the same old commit as `legacy/pre-clean-lineage`.
- `master` is not Current Authority and is not part of the active release flow.

No v0.0.14.5 product behavior is reopened by this specification.

## 3. Confirmed branch model

### 3.1 `main`

`main` is the authoritative stable branch.

It carries:

- Current stable code;
- Current repository truth for released behavior;
- the source served by the current Userscript `@downloadURL` and `@updateURL`;
- release-governance documentation that does not change runtime behavior.

Rules:

- Unreleased next-version runtime code must not be merged into `main`.
- A raised Userscript `@version` must not reach `main` until that build is release-ready.
- Documentation-only governance changes may be committed to `main` when they do not alter the distributed Userscript.
- Stable runtime behavior on `main` must remain release-grade.

### 3.2 `develop`

`develop` is the integration branch for next-version development.

It carries:

- approved next-version changes;
- unreleased version metadata;
- integration work before release readiness.

Rules:

- New product development begins from `develop`, not directly from `main`.
- Development may use short-lived `feature/*` branches when isolation is useful.
- Feature branches merge into `develop`, not directly into `main`, unless the change is an urgent stable hotfix with its own explicit release decision.
- `develop` is not a stable distribution source.

### 3.3 Historical branches

`legacy/pre-clean-lineage` remains:

- Historical Exploration;
- Product Requirement Evidence;
- Behavioral Reference;
- Regression Oracle.

It is not a current code ancestor or development base.

`master` has no Current Authority. Its cleanup is a low-priority repository-hygiene task and is not a release blocker.

## 4. Confirmed distribution authority

### 4.1 GitHub

GitHub is the authoritative source and release authority for ChatHarbor.

Authoritative artifacts include:

- repository code;
- durable specifications;
- release-ready `main`;
- version tag;
- GitHub Release;
- published release assets and checksums when provided.

### 4.2 GreasyFork

GreasyFork is a **secondary distribution channel**, not an independent source of truth.

Rules:

- Do not maintain a divergent GreasyFork-only source tree.
- Do not independently patch runtime code in GreasyFork.
- Public GreasyFork releases must correspond to a GitHub-authoritative release.
- If GreasyFork metadata or packaging requires platform-specific adaptation, that adaptation must be explicit, minimal, reproducible, and documented rather than becoming a parallel product branch.

## 5. Release flow

The default release path is:

```text
spec / confirmed requirement
        ↓
develop (and feature/* when useful)
        ↓
tests + browser validation + release readiness
        ↓
version / changelog / release-note consistency check
        ↓
merge release-ready state into main
        ↓
tag + GitHub Release
        ↓
GreasyFork publication / synchronization
```

The stable distribution invariant is:

> Code served from `main` must not advertise an unreleased higher Userscript version.

## 6. Minimum release gate

Before a next version is merged into `main`, verify at minimum:

- the relevant durable spec is complete enough to define the change;
- required automated tests pass;
- required browser smoke validation passes for affected behavior;
- Userscript `@version` is intentional;
- `CHANGELOG.md` is consistent with the release;
- release notes are prepared;
- upstream/provenance/license notices remain correct when affected;
- the release candidate does not silently reintroduce historical lineage as Current Authority.

Additional CI/checksum automation may be added later only where it provides real release value.

## 7. Non-goals

This specification does **not**:

- modify ChatHarbor v0.0.14.5 runtime behavior;
- change the current Userscript `@downloadURL` or `@updateURL`;
- require a separate `stable` branch;
- require complex CI/CD;
- require immediate cleanup of `master`;
- start browser-extension development;
- authorize speculative product features.

## 8. Current stop condition

This governance prerequisite is satisfied when:

1. this specification is durable in the repository; and
2. `develop` exists from the current stable/governance baseline.

After that, the next workstream may proceed to **GreasyFork release preparation** without modifying product functionality.
