import { deriveExportStatus } from './export-state.js';

export function buildExportConfirmation({ range, count, strategy, batchCount, skipLatest }) {
  if (count <= 0) return null;
  return { range, count, strategy, batchCount, skipLatest: Boolean(skipLatest) };
}

export function buildSelectedExportRequest({ selectedIds, strategy, batchCount, skipLatest = true }) {
  if (!Array.isArray(selectedIds) || selectedIds.length === 0) return null;
  const confirmation = buildExportConfirmation({ range: 'selected', count: selectedIds.length, strategy, batchCount, skipLatest });
  return { selectedIds: [...selectedIds], confirmation };
}

export function resolveSelectedConversations(selectedIds, conversations) {
  const selected = new Set(selectedIds || []);
  return conversations.filter(conversation => selected.has(conversation.identity));
}

export function buildSelectedExecutionTargets(selectedIds, conversations) {
  const resolved = resolveSelectedConversations(selectedIds, conversations);
  if (resolved.length !== selectedIds.length) throw new Error('Selected conversation identity could not be resolved');
  return resolved.map(conversation => conversation.conversationId);
}

export function buildFailedExecutionTargets(failures, targets) {
  const byIdentity = new Map((targets || []).map(target => [target.identity, target]));
  const identities = [...new Set((failures || []).map(failure => failure?.identity).filter(Boolean))];
  const resolved = identities.map(identity => byIdentity.get(identity));
  if (resolved.some(target => !target)) throw new Error('Failed conversation identity could not be resolved');
  return resolved;
}

export function reconcileRetryFailures(previousFailures, retryTargets, succeededIdentities, currentFailures) {
  const targetIds = new Set((retryTargets || []).map(target => target?.identity).filter(Boolean));
  const previous = new Map((previousFailures || []).map(failure => [failure?.identity, failure]).filter(([identity]) => Boolean(identity)));
  for (const identity of previous.keys()) if (!targetIds.has(identity)) throw new Error('Failed conversation identity could not be resolved');
  const remaining = new Map(previous);
  for (const identity of new Set(succeededIdentities || [])) {
    if (!targetIds.has(identity)) throw new Error('Succeeded conversation identity could not be resolved');
    remaining.delete(identity);
  }
  for (const failure of currentFailures || []) {
    if (!failure?.identity || !targetIds.has(failure.identity)) throw new Error('Failed conversation identity could not be resolved');
    remaining.set(failure.identity, failure);
  }
  return [...remaining.values()];
}

export function shouldSkipLatest(state, { skipLatest = true } = {}) {
  return Boolean(skipLatest && deriveExportStatus(state) === 'latest');
}

export function capabilityControls(capabilities = {}) {
  return { scope: capabilities.scope === true, archive: capabilities.archive === true };
}

export function preserveSelection(selected, filteredIds) {
  return new Set([...selected].filter(id => id != null));
}

export function reconcileSelectionAfterRefresh(selected, conversations) {
  const available = new Set((conversations || []).map(conversation => conversation?.identity).filter(Boolean));
  return new Set([...selected].filter(identity => available.has(identity)));
}
