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

export function shouldSkipLatest(state, { skipLatest = true } = {}) {
  return Boolean(skipLatest && deriveExportStatus(state) === 'latest');
}

export function capabilityControls(capabilities = {}) {
  return { scope: capabilities.scope === true, archive: capabilities.archive === true };
}

export function preserveSelection(selected, filteredIds) {
  return new Set([...selected].filter(id => id != null));
}
