# ChatHarbor History & Code Lineage

[中文](HISTORY.md) · [English](HISTORY.en.md)

This document records why ChatHarbor exists, why its implementation route changed more than once, and why historical exploration is not the same thing as current code ancestry.

## 1. Origin: preserve a real ChatGPT working history

ChatGPT has long been the maintainer's primary AI workspace. When the official full-data export link did not arrive in a usable timeframe, the immediate requirement was practical: **preserve long-term personal conversation history independently.**

Existing ChatGPT-specific exporters could retrieve much of the data, but large or frequent export runs raised concern about unnecessary server pressure and the possibility of triggering rate/risk-control false positives. The first goal was therefore not to create a new public product, but to make personal export slower, more controllable, and recoverable.

The risk-control concern was a design motivation, not a claim about a confirmed ChatGPT banning mechanism.

## 2. Conservative Lineage: direct extension of an existing ChatGPT exporter

The earliest variants directly modified an OwlCt ChatGPT-specific exporter and were pasted into Tampermonkey / Violentmonkey for personal use. Over time they added:

- multiple speed levels and randomized jitter;
- per-batch limits;
- long inter-batch pauses;
- local deduplication;
- two-stage pending / exported state;
- interruption recovery;
- retry / cancellation;
- cache and incremental discovery;
- ZIP / history recovery;
- UI changes shaped by real personal use.

This line evolved through Conservative v0.5.

### Historical metadata note

These variants were initially private, personal-use scripts. At the time, the maintainer was not yet familiar with userscript metadata, code provenance, or release conventions, so the metadata header remained largely inherited from upstream through Conservative v0.5 even as substantial functionality changed.

The old `@author` / `@source` fields therefore document upstream origin but **cannot by themselves prove that no substantial downstream changes were present**. Historical ancestry should be evaluated from source comparison, preserved artifacts, and repository evidence.

At the same time, these Conservative versions remained derivatives of the OwlCt codebase; they were not written from scratch.

## 3. Generalization: from a capable specialist tool toward a common architecture

As the ChatGPT-specific line matured, the project explored whether similar capabilities could be generalized to other AI platforms.

`wanda1416/ai-chat-exporter` provided an independent architectural reference: platform-specific API/auth/pagination/parsing behind an Adapter boundary connected to a shared export pipeline.

This led to **Option C — Extract & Recompose**:

- preserve mature ChatGPT-specific behavior;
- adopt a general Adapter architecture;
- establish an independent `Core + Platform Adapters` implementation;
- govern work through PDR, Changes, Decisions, Evidence, and Browser Verification.

This phase produced substantial reusable understanding: stable identity, Unknown boundaries, version-aware state, selection, cache/index, retry/cancel, progress, project/archive semantics, and the workspace UX were all systematically explored and tested here.

The earlier GitHub/PDR line is preserved at `legacy/pre-clean-lineage`.

## 4. Lineage Reset: why Option C did not remain the current implementation line

Option C was not a failure. It clarified important requirements and engineering boundaries. But continued extraction and recomposition across multiple donors also increased:

- provenance complexity;
- historical compatibility burden;
- authority conflicts between current implementation and older plans;
- state synchronization cost across UI / Core / donors;
- recovery cost for determining which conclusions were still current.

The project therefore chose to re-establish a **single, explicit, auditable code ancestor** rather than allowing historical donor logic to keep expanding the current Core.

That decision is the clean-lineage reset.

Earlier Conservative / Generic / Pilot work was preserved, but its role changed from code donor to:

- Product Requirement Evidence;
- Historical Exploration;
- Behavioral Reference;
- Regression Oracle.

## 5. Current clean lineage

The current mainline is based directly on the fixed upstream identity:

- repository: `huhusmang/ChatGPT-Exporter`
- pinned commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- pinned userscript Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`

From there, ChatHarbor progressively established:

- direct directory writes and Manifest state;
- version-aware selective sync;
- conservative request policy;
- desktop workspace;
- streaming transactions;
- Archive Layout v2;
- Remote Index / project truth;
- incremental attachment backfill;
- commit-accurate state;
- auditable reports;
- attachment provenance and failure explainability.

### Reconstructed Git history

Early clean-lineage work was primarily preserved as ZIP/source bundles. On 2026-09-16, Git commits/tags were reconstructed from those preserved artifacts, their checksums, and historical records.

Therefore:

- the preserved release/source artifacts are the historical evidence;
- reconstructed commits/tags restore version evolution;
- reconstructed hashes must not be presented as original Git hashes that existed at the time.

See `docs/history/RECONSTRUCTION.md` and `docs/history/INVENTORY_2026-09-16.md`.

## 6. From “sync tool” to “archive + integrity audit”

During 0.0.14.x, attachment failures briefly raised the question of whether public release was worthwhile.

Real archive audits then showed that unsuccessful attachment archival was not a single failure mode: the platform could currently return 403, 404, 415, or 500, or expose only an expired/missing temporary download URL. Different attachment sources also showed different failure distributions.

That evidence produced the final product-positioning convergence:

> **ChatHarbor does not promise completeness the platform itself cannot guarantee. It preserves what is currently obtainable and turns known gaps into explainable, traceable evidence that can be checked against the original conversation.**

The v0.0.14.5 product position is therefore:

**Local-first ChatGPT Archive & Integrity Audit**

rather than an exporter that merely claims everything was downloaded.

## 7. Current historical boundary

```text
Real need: official full export not available in time
        ↓
OwlCt ChatGPT-specific exporter
        ↓
Conservative Lineage v0.1 → v0.5
        ↓
        ├── + wanda1416 generic Adapter reference
        ↓
Option C / Core + Platform Adapters / PDR exploration
        ↓
Lineage Reset
        ↓
huhusmang fixed upstream
        ↓
ChatHarbor clean lineage 0.0.x
        ↓
v0.0.14.5
Local archive + integrity audit + transparent diagnostics
```

Historical exploration is preserved; current authority and current code ancestry remain explicit and singular.
