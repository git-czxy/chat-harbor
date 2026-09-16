# ChatHarbor 0.0.10.0 — Archive Layout v2 + Local Migration

This release establishes the pre-release archive layout intended to remove the hierarchy ambiguity found during real use.

## What changes

The selected ChatGPT archive root now uses:

```text
chatgpt/
├─ ChatHarbor_manifest.json
├─ conversations/
└─ projects/
   └─ <project>/
```

- Non-project conversations live under `conversations/`.
- Project conversations live under `projects/<project>/`.
- Each conversation's `_files/` directory stays beside its JSON and Markdown.
- Manifest adds `provider = chatgpt` and `archive_layout_version = 2`.
- This leaves the parent directory free for future sibling provider roots such as `claude/` or `gemini/`; no non-ChatGPT adapter is implemented in this version.

## Existing Layout v1 archives

When a v1 Manifest is detected, normal sync is disabled and the Local archive card shows an explicit **Upgrade archive to Layout v2** action.

The upgrade:

- is local-only;
- does not fetch conversation detail or re-download attachments;
- verifies copied bytes with SHA-256;
- commits each conversation before cleaning its old tracked path;
- is resumable after interruption;
- preserves untracked legacy files/directories;
- automatically runs a normal read-only Plan after success.

If the remote metadata has not changed, migrated conversations should return to `Synced / 已同步` and require no detail fetch merely because their local path changed.

For the current real archive Manifest supplied during development, the migration target mapping contains 83 tracked conversations (58 project / 25 non-project) and produced no target-path collisions in structural preflight.

## Included pending refinements

This release also includes the previously prepared 0.0.9.3 UI clarity changes:

- runtime progress says `当前第 X / N 条` rather than implying X completed conversations;
- archived conversations use a pale amber pill while active/non-archived remains neutral gray;
- Local archive summary shows total tracked conversations split into project and non-project counts.

The cached canonical remote index, single selection sync scope, streaming Fetch → Classify → Atomic Sync → Manifest, conservative network policy, MM:SS batch countdown, pause/resume/cancel and tracked-only cleanup remain in place.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Generated userscript:

```text
ChatHarbor-IntegratedSync-0.0.10.0.user.js
```

For your current archive, select the existing provider root:

```text
D:\Projects\ChatHarbor\chats\chatgpt
```

Do **not** select its parent `chats` directory. After selection, ChatHarbor detects Layout v1 and offers the local-only upgrade.
