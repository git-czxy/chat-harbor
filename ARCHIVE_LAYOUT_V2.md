# ChatHarbor Archive Layout v2

## Provider namespace

The directory selected by the ChatGPT adapter is the **ChatGPT provider archive root**.
A multi-provider parent can therefore contain sibling provider roots:

```text
chats/
├─ chatgpt/
├─ claude/
├─ gemini/
└─ ...
```

ChatHarbor 0.0.10.0 implements only the `chatgpt` adapter. The provider namespace is reserved now so future adapters do not need to redesign the local archive model.

Within one provider root, `conversation_id` remains the Manifest identity. Across providers, the effective global identity is `(provider, conversation_id)`.

## ChatGPT Layout v2

```text
chatgpt/
├─ ChatHarbor_manifest.json
├─ conversations/
│  ├─ title_shortId.json
│  ├─ title_shortId.md
│  └─ title_shortId_files/
└─ projects/
   ├─ Project A/
   │  ├─ title_shortId.json
   │  ├─ title_shortId.md
   │  └─ title_shortId_files/
   └─ Project B/
      └─ ...
```

`conversations/` contains conversations without a ChatGPT Project. `projects/` is the namespace for ChatGPT Project containers. Conversation asset directories are always adjacent to their JSON and Markdown, so they are no longer siblings of project containers at the provider root.

Manifest root fields include:

```json
{
  "schema_version": 1,
  "provider": "chatgpt",
  "archive_layout_version": 2,
  "identity": "conversation_id",
  "signature_version": "sha256-current_node+mapping-v1"
}
```

Manifest schema, archive layout and content-signature version remain independent version axes.

## Layout v1 → v2 migration

Migration is intentionally **local-only**:

```text
read old Manifest
→ verify tracked source JSON / Markdown
→ copy to v2 target path
→ SHA-256 verify target bytes
→ commit new paths to Manifest
→ remove only old Manifest-tracked paths
→ preserve untracked legacy material
→ verify all canonical v2 paths
→ archive_layout_version = 2
```

No conversation-detail or attachment request is made during migration. Existing `conversation_id`, `content_signature`, remote metadata and file contents are preserved. Therefore a migrated conversation whose remote metadata has not changed remains eligible for the `UNCHANGED / 已同步` fast path after the next read-only Plan.

Migration is resumable. During each per-conversation transaction the Manifest records the previous tracked paths until cleanup is complete. If the browser or machine stops after the new Manifest path is committed but before old-path cleanup, the next migration run resumes cleanup rather than re-downloading data.

Migration never recursively deletes legacy asset directories. If an old directory contains an untracked file, that directory is left in place and reported as a safe leftover.

## Release policy

Layout migration is an exceptional maintenance path, not part of ordinary synchronization. A published stable version should start new users directly on the current layout. Historical migration code may later move to `tools/migrations/` during source normalization rather than remain on the primary runtime path indefinitely.
