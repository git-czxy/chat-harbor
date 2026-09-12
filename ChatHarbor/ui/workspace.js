import { buildSelectedExportRequest, buildSelectedExecutionTargets, capabilityControls, preserveSelection, resolveSelectedConversations } from '../core/workflow.js';

export const WORKSPACE_LAYOUT = Object.freeze({
  panel: { gridTemplateColumns: 'minmax(0,1fr) 250px', gridTemplateRows: 'auto minmax(0,1fr)', overflow: 'hidden' },
  main: { minWidth: '0', minHeight: '0', overflow: 'hidden' },
  list: { flex: '1', minWidth: '0', minHeight: '0', overflowX: 'hidden', overflowY: 'auto' },
  row: { minWidth: '0', width: '100%', boxSizing: 'border-box' },
  title: { flex: '1', minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  rail: { minWidth: '0', minHeight: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  action: { marginTop: 'auto' }
});

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
    selectedConversations() { return resolveSelectedConversations(this.selected, this.conversations); },
    executionTargets() { return buildSelectedExecutionTargets([...this.selected], this.conversations); }
  };
}
