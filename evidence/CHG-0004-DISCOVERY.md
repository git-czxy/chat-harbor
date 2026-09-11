# CHG-0004 Discovery Evidence

Direct source evidence: ChatGPT v0.4 uses mapping message IDs, children traversal, list `update_time`, and exported/pending ID sets. The current ChatHarbor pilot received a real ChatGPT payload with `contentVersion = null`; normalized messages and raw mapping were valid. The generic implementation has version-record scaffolding but writes null contentVersion when unavailable. No reliable native ChatGPT revision field was confirmed.

Decision boundary: a canonical normalized-message fingerprint is technically available, but its canonicalization policy and false-negative tolerance require implementation evidence. Therefore the specification uses a capability-aware hybrid with explicit Unknown fallback and does not promote any timestamp to a version.
