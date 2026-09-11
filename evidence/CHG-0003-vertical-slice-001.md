# CHG-0003 Vertical Slice 001 Evidence

## Scope

ChatGPT Adapter -> normalized conversation model -> ChatHarbor Core index -> JSON + Markdown export.

## Implemented source boundary

- `ChatHarbor/models/conversation.js`: stable identity and normalization.
- `ChatHarbor/adapters/chatgpt.js`: ChatGPT adapter contract and conservative capabilities.
- `ChatHarbor/core/index.js`: platform-neutral index/fetch boundary.
- `ChatHarbor/export/pipeline.js`: two representations sharing identity/content version.
- `ChatHarbor/test/vertical-slice.test.js`: executable contract checks.
- `dist/ChatHarbor-Pilot.user.js`: self-contained test-only userscript browser wiring; it mirrors the source contracts because browser userscripts cannot import the repository ES modules directly.

Legacy scripts were not modified or deleted. The adapter receives API access through injected list/fetch functions; browser API wiring remains a later integration step.

## Results

- Adapter detection and normalized list: PASS.
- Fetch to normalized conversation: PASS.
- `platform + conversationId` identity: PASS.
- Title change does not change identity: PASS.
- Unavailable content version remains `null`: PASS.
- Same normalized conversation produces JSON and Markdown: PASS.
- JSON and manifest retain the same full identity: PASS.
- Attachment manifest is retained separately; downloading resources is not claimed complete.
- Node syntax: PASS for all new modules.
- Executable vertical-slice test: PASS (`vertical slice PASS`).
- `git diff --check`: PASS.
- PDR validate: PASS.

## Browser integration status

The installable pilot calls `/api/auth/session?unstable_client=true`, then `/backend-api/conversations?offset=0&limit=1&order=updated`, then `/backend-api/conversation/{id}`. It uses the new adapter normalization and export-pair semantics inside the single distributable, and never calls the legacy export entry or full-export workflow. It downloads exactly one JSON and one Markdown representation and logs the normalized model/manifest for inspection.

## Unknown / Human test

Live ChatGPT API/browser wiring, real payload coverage, attachment download, and browser end-to-end behavior remain Unknown/Human Test. This slice deliberately does not claim those validations.
