# ChatHarbor Incremental State Invariants — 0.0.13.0

These invariants define the correctness boundary for incremental synchronization.

## I-01 — Same observation must converge

If the remote list observation, local archive, selected content policy, and provider identity are unchanged, a previously verified conversation must converge to `UNCHANGED` and must not require repeated detail fetches.

A successful detail verification must therefore advance the remote-list checkpoint even when the final content signature is unchanged.

## I-02 — Source semantics must not be mixed

Remote-list metadata and conversation-detail metadata are different observations.

The cheap preflight comparator uses the persisted remote-list checkpoint (`remote_list_*`). Detail metadata can be retained for diagnosis/source fidelity but must not silently replace the list checkpoint used on the next run.

## I-03 — Unknown is not an empty value

`unknown`, `none`, `false`, empty string, and missing fields are not interchangeable.

When root/project/archive sources conflict or cannot establish a fact, ChatHarbor preserves `unknown` rather than inventing a definite project/archive state.

## I-04 — Remote cache is disposable acceleration data

The IndexedDB Remote Index cache is not archive authority.

- The Manifest is the durable local archive ledger/index.
- A complete fresh remote snapshot is the observation authority for one sync run.
- The remote cache may be discarded and rebuilt at any time.

Cache identity must be provider + unambiguous account/workspace identity. Ambiguous identity disables persistent cache reuse.

## I-05 — Partial discovery cannot prove absence

A head-only/partial Remote Index refresh may prove that the checked latest window is stable, but it cannot independently prove remote deletion or `LOCAL_ONLY`.

Only a complete remote universe is allowed to make absence-based conclusions.

## I-06 — Content state and attachment completeness are independent

A conversation may be content-`UNCHANGED` while attachment completeness is `unknown`, `not_downloaded`, or `partial`.

Attachment policy must not turn attachment backfill into a false content update. Conversely, default no-download mode must not trigger detail verification merely because attachment completeness is unknown.

## I-07 — Manifest-first is not Manifest-only

Normal local planning uses the Manifest as the primary local index and fast-checks tracked files. The filesystem is still enumerated to detect unexpected/untracked material.

Tracked path absence/size mismatch is blocking evidence and must not be silently repaired by remote overwrite.

## I-08 — Run inputs are snapshots

At sync start, selection, network policy, attachment policy, and remote observation are fixed for that run. UI changes or background Remote Index refreshes must not alter the executing task mid-run.

## I-09 — Incomplete work remains resumable at conversation granularity

Streaming order remains:

```text
Fetch candidate -> Classify -> Atomic local/Manifest commit -> next conversation
```

After cancellation or interruption, completed conversation commits remain authoritative. Records whose observation checkpoint was committed must not be re-verified merely because the previous run did not finish globally.

## I-10 — Full refresh is the conservative fallback

Fast Remote Index refresh is an optimization only. Any of the following must fall back to a full refresh:

- no usable complete cache;
- cache schema/provider mismatch;
- periodic full-refresh deadline reached;
- newest-window fingerprint changed;
- source refresh failure/ambiguity that prevents a reliable complete snapshot;
- explicit user full refresh.

## Attachment incremental invariants (0.0.11.4)

```text
legacy positive evidence may prove COMPLETE; legacy zero without checked-at remains UNKNOWN
current-reference asset already tracked -> reuse, do not redownload
backfill downloads only references missing from the Manifest asset identity set
attachment progress is completion-based and monotonic
failed/missing attachment references remain PARTIAL and are retryable
```

A legacy record is inferred `complete` only when it has a positive `attachment_detected`, zero failures, downloaded count covering the detected count, and at least that many tracked assets. A zero legacy count is deliberately not interpreted as `none` unless there is an explicit later `attachments_checked_at` fact.

## Runtime horizontal invariants (0.0.13.0)

### I-11 — Network policy is horizontal
Every ChatHarbor `/backend-api/` control-plane request uses one shared serialized scheduler. A 429 creates one global cooldown shared by discovery, project enumeration, detail verification and attachment metadata. Signed/direct binary transfer is a separate data path, but its 429 also advances the global cooldown.

### I-12 — Classification is not commit
A predicted `finalAction` is not a successful sync fact. UI state may become committed only after the corresponding file/Manifest transaction succeeds. Commit failure must remain visible as an error.

### I-13 — Manifest asset identity requires physical evidence
A Manifest-tracked attachment is reusable only when the tracked path still exists and, when an expected byte size is known, the physical size matches. Missing/mismatched assets are repair candidates rather than silently trusted Manifest facts.

### I-14 — Active-run remote observation is immutable
A sync run freezes one remote snapshot. Background/cache refresh may not replace that snapshot, rerun Preflight against changing state, or alter visible run facts until the run ends.

### I-15 — Newly written attachment residue is not authoritative
Attachments written during a conversation transaction are not authoritative until Manifest commit succeeds. If Manifest commit fails, newly created attachment paths are removed best-effort and the prior in-memory Manifest record is restored.

## Remote discovery / network scheduling additions (0.0.13.0)

- **Shared control does not imply shared cadence.** Discovery, detail and attachment-metadata traffic share serialization/error/cooldown policy but use lane-appropriate spacing.
- **Only HTTP 429 is a cross-lane cooldown condition.** A transient 5xx/network failure retries the affected request without globally freezing unrelated lanes.
- **Partial discovery is display evidence, not absence evidence.** An incomplete Remote Index may accelerate UI/recovery but cannot prove `LOCAL_ONLY` or authorize a write sync.
- **Existing complete cache outranks progressive incomplete refresh state.** Do not overwrite a known-complete cached universe with an in-progress partial snapshot.
- **Long waits must be observable.** Discovery cadence and 429 cooldown must not present as an unexplained frozen loading screen.
