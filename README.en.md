<div align="center">

# ChatHarbor

**A local-first ChatGPT archive and integrity-audit userscript**

[中文](README.md) · [English](README.en.md)

</div>

ChatHarbor continuously archives your own ChatGPT conversations to local storage and makes archive gaps explicit: **what has been saved, which attachments were not successfully archived, what error the platform returned, and which original conversation you can inspect.**

Current public version: **v0.0.14.5**

> ChatHarbor does not promise a “100% complete backup.” It promises to acquire what is currently obtainable and to keep known gaps transparent, traceable, and reviewable.

## Highlights

- **Incremental sync** — `conversation_id` is the stable identity; remote timestamps are only pre-filters, while content signatures are used for final content comparison.
- **Local archive** — stores raw JSON, Markdown, attachment assets, and a Manifest.
- **Project / archive awareness** — normal chats, project chats, and archive state are visible in one workspace.
- **Attachment integrity audit** — distinguishes user uploads, ChatGPT-generated deliverables, generated media, and other sources; preserves raw failure evidence and failure stage.
- **Conversation-centric recovery** — jump from an unarchived attachment directly to its original ChatGPT conversation.
- **Conservative request policy** — request spacing, batch pauses, bounded retry, pause/resume, and safe cancellation reduce unnecessary request pressure.
- **Transactional writes** — write → verify → Manifest commit → tracked-only cleanup. `LOCAL_ONLY` is never auto-deleted by ordinary sync.
- **Auditable reports** — sync completion and local preflight reports include timestamps, policy, per-run results, and cumulative integrity summaries.

## Installation

Recommended: **desktop Chromium (Edge / Chrome) + Tampermonkey**. The archive workflow relies on browser directory-access APIs; compatibility may differ in other browsers or userscript managers.

1. Install Tampermonkey.
2. Open [`ChatHarbor.user.js`](https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js) and install it.
3. Open `https://chatgpt.com/` and click the ChatHarbor launcher on the right edge.
4. On first use, choose a local archive directory.

The userscript metadata points update checks to the `main` branch of this repository.

## Status semantics

ChatHarbor intentionally keeps only four primary user-facing states:

- **Synced**
- **To sync**
- **Needs confirmation**
- **Error**

Attachment completeness is a separate dimension. A conversation may be “Synced” while also showing “3 attachments unarchived”: the conversation body is synchronized, but specific attachment gaps remain recorded.

For HTTP 403 / 404 / 415 / 500 or an expired/missing download URL, ChatHarbor preserves the raw platform error and offers an interpretation. It **does not** turn those observations into unsupported claims such as “permanently deleted” or “corrupted.”

## Data & privacy

- ChatHarbor reads ChatGPT's own endpoints in your existing browser session and writes the archive to the local directory you select.
- ChatHarbor has no project-operated upload server and does not send your archive to the maintainer.
- The userscript loads JSZip from `cdnjs.cloudflare.com`; otherwise the core data path is between ChatGPT and your chosen local directory.
- Before a large first sync, test the selected directory and browser permissions with a small set of conversations.

## History & code lineage

ChatHarbor did not evolve through a simple “old version → new version” path:

1. **Real-world origin** — ChatGPT was the maintainer's primary AI workspace, while the official full-export link was not arriving in a usable timeframe, creating a need to preserve long-term conversation history independently.
2. **Conservative Lineage** — an OwlCt-based ChatGPT-specific exporter was directly modified for personal use, progressively adding slower pacing/jitter, batching, pauses, deduplication, recovery, retry, cancellation, and workflow/UI changes. Through Conservative v0.5 these variants were mainly pasted directly into Tampermonkey / Violentmonkey, so their userscript metadata headers were not consistently updated.
3. **Generalization / Option C exploration** — `wanda1416/ai-chat-exporter` provided an independent multi-platform Adapter reference, leading to a `Core + Platform Adapters` recomposition experiment with PDR, Change, Evidence, and Browser Verification records.
4. **Lineage Reset** — continued multi-donor recomposition increased provenance, compatibility, and authority complexity, so the current implementation re-established a single auditable code ancestry.
5. **Current clean lineage** — the current mainline is based directly on a fixed `huhusmang/ChatGPT-Exporter` upstream snapshot. Its early Git history was reconstructed from preserved Gate / Release artifacts. The earlier Conservative / Pilot work remains requirements evidence, behavioral reference, and a regression oracle, but is not a code ancestor of the current mainline.
6. **Current product position** — after auditing real attachment failures, ChatHarbor converged on “local archive + integrity audit + transparent failure diagnostics” instead of claiming perfect backup completeness.

See [HISTORY.en.md](HISTORY.en.md) for the full narrative.

The earlier GitHub/PDR line is preserved at `legacy/pre-clean-lineage`.

> **Git history note:** early clean-lineage commits/tags were reconstructed on 2026-09-16 from preserved release packages and checksums. They document version evolution but must not be presented as the original historical Git hashes. See [`docs/history/RECONSTRUCTION.md`](docs/history/RECONSTRUCTION.md).

## v0.0.14.5

This release completes:

- attachment provenance;
- conversation-level inspection of unarchived attachments;
- explanations for 403 / 404 / 415 / 500 / expired URLs;
- original-conversation navigation;
- auditable sync/preflight reports;
- a standalone historical provenance backfill tool;
- userscript identity / upstream attribution cleanup;
- final project-chip and attachment-detail UI refinement.

See [CHANGELOG.md](CHANGELOG.md) and [`docs/releases/v0.0.14.5.md`](docs/releases/v0.0.14.5.md).

## Historical provenance backfill tool

`migration-tools/ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js` is a one-time Migration / Repair Tool for enriching older Manifest attachment records with provenance fields.

It defaults to **Dry Run**, does not download attachments, and does not modify the Manifest until explicitly applied. It is intentionally separate from the daily sync Core.

## Author & attribution

Maintainer: **挠痒痒的电饭煲 ([@git-czxy](https://github.com/git-czxy))**

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the direct clean-lineage upstream, the historical Conservative / Generic lines, and licensing notes.

## License

ChatHarbor's own modifications are released under the [MIT License](LICENSE). Third-party source and license notices remain subject to [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
