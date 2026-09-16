# ChatHarbor Git History Reconstruction

Date: 2026-09-16

## Status

This repository is a **reconstructed Git history** made from preserved ChatHarbor release/source bundles.

- Historical ZIP/source artifacts are preserved evidence.
- Git commit objects and annotated tags in this repository were created during the reconstruction.
- They must **not** be represented as original historical Git commit hashes/tags.
- Historical dates are recorded in commit messages; commit object timestamps are reconstruction timestamps.

## Clean-lineage boundary

The main branch begins with preserved clean-lineage Gate snapshots and then follows the numbered releases.
The fixed upstream identity is recorded in the baseline files inside the snapshots:

- repository: `huhusmang/ChatGPT-Exporter`
- commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- Tampermonkey Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`

The historical ChatHarbor v0.4/v0.5 line is **not** an ancestor of this main branch because the provenance audit classified v0.5.0 as containing direct OwlCt-linked implementation. It is preserved separately as an orphan `legacy-reference` branch.

## Snapshot rule

For each historical node, the content committed is the extracted preserved release/source bundle with only the outer packaging directory removed when present. File contents are not rewritten for the historical commit.

The generated `.user.js` was not embedded in most historical release ZIPs; those packages generated it locally from the pinned upstream. The currently running `0.0.14.1` userscript is preserved separately under `artifacts/current/` in this reconstruction metadata commit.
