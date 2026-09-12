import { buildSelectedExportRequest, buildSelectedExecutionTargets, capabilityControls, preserveSelection, resolveSelectedConversations } from '../core/workflow.js';

export const WORKSPACE_LAYOUT = Object.freeze({
  panel: { gridTemplateColumns: 'minmax(0,1fr) 250px', gridTemplateRows: 'auto auto minmax(0,1fr)', overflow: 'hidden' },
  main: { minWidth: '0', minHeight: '0', overflow: 'hidden' },
  list: { flex: '1', minWidth: '0', minHeight: '0', overflowX: 'hidden', overflowY: 'auto' },
  row: { minWidth: '0', width: '100%', boxSizing: 'border-box' },
  title: { flex: '1', minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  rail: { minWidth: '0', minHeight: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  action: { marginTop: 'auto' }
});

export const WORKSPACE_SURFACE = Object.freeze({
  toolbar: ['search', 'scope', 'archive', 'exportStatus', 'time', 'refresh'],
  rail: ['selectionSummary', 'exportStrategy', 'recordManagement', 'progress', 'retry', 'exportActions']
});

export function workspaceAvailability(capabilities = {}) {
  return {
    toolbar: {
      search: { visible: true, enabled: true },
      scope: { visible: true, enabled: Boolean(capabilities.scope) },
      archive: { visible: true, enabled: Boolean(capabilities.archive) },
      exportStatus: { visible: true, enabled: false },
      time: { visible: true, enabled: false },
      refresh: { visible: true, enabled: true }
    },
    rail: {
      selectionSummary: { visible: true, enabled: true },
      exportStrategy: { visible: true, enabled: true },
      recordManagement: { visible: true, enabled: false },
      progress: { visible: true, enabled: true },
      retry: { visible: true, enabled: true },
      exportActions: {
        selected: { visible: true, enabled: true },
        currentFilter: { visible: true, enabled: false },
        currentScope: { visible: Boolean(capabilities.scope), enabled: false }
      }
    }
  };
}

export function executionControls(selectedCount, status = 'idle') {
  const active = status === 'running' || status === 'cancelling';
  return { active, exportEnabled: selectedCount > 0 && !active, selectionEnabled: !active, closeEnabled: !active, cancelVisible: status === 'running' || status === 'cancelling', cancelEnabled: status === 'running' };
}

export function retryControls(failureCount, status = 'idle') {
  const active = status === 'running' || status === 'cancelling';
  return { visible: failureCount > 0 && !active, enabled: failureCount > 0 && !active };
}

export const CANCEL_BUTTON_STYLE = Object.freeze({ width: '100%', padding: '10px', border: '0', borderRadius: '8px', background: '#dc2626', color: '#fff', fontWeight: '600', cursor: 'pointer' });

export function filterConversations(conversations, { query = '', archive = 'unarchived' } = {}) {
  const q = query.trim().toLowerCase();
  return conversations.filter(conversation => {
    if (archive === 'unarchived' && conversation.archived) return false;
    if (archive === 'archived' && !conversation.archived) return false;
    return !q || `${conversation.title} ${conversation.identity}`.toLowerCase().includes(q);
  });
}

export function createWorkspaceModel({ conversations = [], capabilities = {}, selectedIds = new Set(), strategy = '当前速度', batchCount = 1, skipLatest = false } = {}) {
  const selected = preserveSelection(selectedIds, conversations.map(c => c.identity));
  return {
    conversations,
    selected,
    query: '',
    archive: 'unarchived',
    controls: capabilityControls(capabilities),
    filtered() { return filterConversations(this.conversations, { query: this.query, archive: this.archive }); },
    summary() { return { matched: this.filtered().length, total: this.conversations.length, selected: this.selected.size }; },
    selectedExport() { return buildSelectedExportRequest({ selectedIds: [...this.selected], strategy, batchCount, skipLatest }); },
    selectedConversations() { return resolveSelectedConversations(this.selected, this.conversations); },
    executionTargets() { return buildSelectedExecutionTargets([...this.selected], this.conversations); }
  };
}
