# Architecture Specification — CHG-0003

## ChatHarbor Core

Core owns platform-neutral Conversation Identity (`platform + conversationId`), Content Version, Conversation Index/Cache, Export State, Manifest, Backup/Restore, Batch/Rate Control, Retry/Cancel/Progress, Export Pipeline, and output representations. Platform Adapters own detection, platform API/DOM access, list/fetch translation, capabilities, and platform-specific attachment retrieval.

## Data fidelity

`Raw Source -> Normalized Model -> Export Representations` is a preservation pipeline, not a lossy replacement. Retain raw payloads whenever supplied. The Normalized Model enables cross-platform indexing and workflow operations. JSON, Markdown, and TXT are representations; multiple representations may be produced for one content version. Representation changes never change conversation content version.

An export record identifies a conversation and content version and may reference multiple representations. A manifest records title-at-export, reliable source timestamps, content version/fingerprint when available, exported time, and attachment metadata. Attachment Manifest/Metadata is distinct from Download Conversation Attachments, which means retrieving user-linked images, PDFs, Word files, spreadsheets, or other resources.

## Core contracts

- Identity: `platform`, complete `conversationId`; title is display-only.
- Version: reliable adapter revision/latest-message identity/fingerprint when available; otherwise explicit Unknown, never title-only inference.
- Index: normalized metadata, cache snapshot, logical list separate from rendered DOM.
- State: unexported / has updates / latest, with backward-compatible legacy IDs and version-aware records.
- Pipeline: selected normalized conversations, records and representations, successful results retained on cancel, retryable failures exposed.

## Platform Adapter Contract

```js
detect(): boolean | Promise<boolean>
listConversations(options): Promise<ConversationMetadata[]>
fetchConversation(conversationId, options): Promise<RawConversation>
capabilities: { scope?: boolean, archive?: boolean, attachments?: boolean,
  reasoning?: boolean, sources?: boolean, contentRevision?: boolean }
```

`ConversationMetadata` contains `platform`, `conversationId`, `title`, optional `createdAt`, `updatedAt`, `scope`, `archived`, and `contentVersion`. Unsupported fields remain absent/Unknown. ChatGPT Project/Archive semantics are not universal requirements.
