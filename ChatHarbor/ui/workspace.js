import { buildSelectedExportRequest, capabilityControls, preserveSelection, resolveSelectedConversations } from '../core/workflow.js';

export function createWorkspaceModel({ conversations = [], capabilities = {}, selectedIds = new Set(), strategy = '当前速度', batchCount = 1, skipLatest = false } = {}) {
  const selected = preserveSelection(selectedIds, conversations.map(c => c.identity));
  return {
    conversations,
    selected,
    query: '',
    controls: capabilityControls(capabilities),
    filtered() { const q = this.query.trim().toLowerCase(); return q ? this.conversations.filter(c => `${c.title} ${c.identity}`.toLowerCase().includes(q)) : [...this.conversations]; },
    summary() { return { matched: this.filtered().length, total: this.conversations.length, selected: this.selected.size }; },
    selectedExport() { return buildSelectedExportRequest({ selectedIds: [...this.selected], strategy, batchCount, skipLatest }); },
    selectedConversations() { return resolveSelectedConversations(this.selected, this.conversations); }
  };
}
