// ==UserScript==
// @name         ChatHarbor Pilot - Core Vertical Slice
// @namespace    ChatHarbor
// @version      0.1.0-pilot
// @description  Test-only browser wiring for the ChatHarbor Core ChatGPT slice
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';
  if (window.__chatharborPilotLoaded) return;
  window.__chatharborPilotLoaded = true;

  const identity = (c) => `${c.platform}:${c.conversationId}`;
  const stable = (value) => Array.isArray(value) ? `[${value.map(stable).join(',')}]` : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}` : JSON.stringify(value ?? null);
  const digest = (text) => { let left = 0xcbf29ce484222325n; let right = 0x84222325cbf29ce4n; const mask = 0xffffffffffffffffn; for (let i = 0; i < text.length; i++) { const c = BigInt(text.charCodeAt(i)); left = ((left ^ c) * 0x100000001b3n) & mask; right = ((right ^ (c + BigInt(i))) * 0x100000001b3n) & mask; } return `fp128:${left.toString(16).padStart(16, '0')}${right.toString(16).padStart(16, '0')}`; };
  const observe = (c) => { if (!c.messages?.length) return { value: null, source: 'unknown' }; const canonical = { messages: c.messages.map(m => ({ messageId: m.messageId || null, parentId: m.parentId || null, role: m.role || null, contentType: m.contentType || null, content: m.content || '', createdAt: m.createdAt || null, updatedAt: m.updatedAt || null, attachments: m.attachments || [] })) }; return { value: digest(`chatharbor-content-v1:${stable(canonical)}`), source: 'canonical-message-fingerprint' }; };
  const normalize = (raw, meta = {}) => {
    const c = {
      platform: meta.platform || raw.platform,
      conversationId: String(meta.conversationId || raw.id || raw.conversationId),
      title: meta.title ?? raw.title ?? '',
      createdAt: meta.createdAt ?? raw.create_time ?? raw.createdAt ?? null,
      updatedAt: meta.updatedAt ?? raw.update_time ?? raw.updatedAt ?? null,
      scope: meta.scope ?? raw.scope ?? null,
      archived: meta.archived ?? raw.archived ?? null,
      contentVersion: meta.contentVersion ?? raw.contentVersion ?? null,
      messages: Array.isArray(raw.messages) ? raw.messages : [],
      attachments: Array.isArray(raw.attachments) ? raw.attachments : [],
      rawSource: raw
    };
    c.identity = identity(c);
    return c;
  };
  const extractChatGPTMessages = (raw) => {
    const mapping = raw?.mapping;
    if (!mapping || typeof mapping !== 'object') return Array.isArray(raw?.messages) ? raw.messages : [];
    const ids = Object.keys(mapping); const root = mapping['client-created-root'] ? 'client-created-root' : ids.find(id => !mapping[id]?.parent) || ids[0];
    const visited = new Set(); const messages = [];
    const walk = (id) => { if (!id || visited.has(id) || !mapping[id]) return; visited.add(id); const node = mapping[id]; const msg = node.message; const role = msg?.author?.role; const hidden = msg?.metadata?.is_visually_hidden_from_conversation || msg?.metadata?.is_contextual_answers_system_message;
      if (msg && (role === 'user' || role === 'assistant') && !hidden) { const parts = Array.isArray(msg.content?.parts) ? msg.content.parts : []; const content = parts.map(p => typeof p === 'string' ? p : p?.text || '').filter(Boolean).join('\n'); const attachments = (msg.metadata?.attachments || []).map(a => ({ id: a.id || a.file_id || a.asset_pointer || null, mimeType: a.mime_type || a.content_type || null, name: a.name || a.filename || null, size: a.size ?? null })); if (content || attachments.length) messages.push({ messageId: msg.id || id, parentId: node.parent || null, role, content, contentType: msg.content?.content_type || null, createdAt: msg.create_time || null, updatedAt: msg.update_time || null, attachments }); }
      (node.children || []).forEach(walk); };
    walk(root); return messages;
  };
  const markdown = (c) => {
    const text = (m) => typeof m?.content === 'string' ? m.content : Array.isArray(m?.content?.parts) ? m.content.parts.join('\n') : JSON.stringify(m?.content || '');
    return [`# ${c.title || 'Untitled conversation'}`, '', `- Platform: ${c.platform}`, `- Conversation ID: ${c.conversationId}`, '', ...c.messages.flatMap(m => [`## ${m.author?.role || m.role || 'message'}`, '', text(m), ''])].join('\n');
  };
  const layout = {
    panel: { gridTemplateColumns: 'minmax(0,1fr) 250px', gridTemplateRows: 'auto auto minmax(0,1fr)', overflow: 'hidden' },
    main: { minWidth: '0', minHeight: '0', overflow: 'hidden' },
    list: { flex: '1', minWidth: '0', minHeight: '0', overflowX: 'hidden', overflowY: 'auto' },
    row: { minWidth: '0', width: '100%', boxSizing: 'border-box' },
    title: { flex: '1', minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
    rail: { minWidth: '0', minHeight: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
    action: { marginTop: 'auto' }
  };
  const workspaceSurface = { toolbar: ['search', 'scope', 'archive', 'exportStatus', 'time', 'refresh'], rail: ['selectionSummary', 'exportStrategy', 'recordManagement', 'progress', 'retry', 'exportActions'] };
  const workspaceAvailability = (capabilities = {}) => ({ toolbar: { search: { visible: true, enabled: true }, scope: { visible: true, enabled: Boolean(capabilities.scope) }, archive: { visible: true, enabled: Boolean(capabilities.archive) }, exportStatus: { visible: true, enabled: false }, time: { visible: true, enabled: false }, refresh: { visible: true, enabled: true } }, rail: { selectionSummary: { visible: true, enabled: true }, exportStrategy: { visible: true, enabled: true }, recordManagement: { visible: true, enabled: false }, progress: { visible: true, enabled: true }, retry: { visible: true, enabled: true }, exportActions: { selected: { visible: true, enabled: true }, currentFilter: { visible: true, enabled: false }, currentScope: { visible: Boolean(capabilities.scope), enabled: false } } } });
  const executionControls = (selectedCount, status = 'idle') => { const active = status === 'running' || status === 'cancelling'; return { active, exportEnabled: selectedCount > 0 && !active, selectionEnabled: !active, closeEnabled: !active, cancelVisible: status === 'running' || status === 'cancelling', cancelEnabled: status === 'running' }; };
  const retryControls = (failureCount, status = 'idle') => { const active = status === 'running' || status === 'cancelling'; return { visible: failureCount > 0 && !active, enabled: failureCount > 0 && !active }; };
  const cancelButtonStyle = { width: '100%', padding: '10px', border: '0', borderRadius: '8px', background: '#dc2626', color: '#fff', fontWeight: '600', cursor: 'pointer' };
  class RetryCancelledError extends Error { constructor() { super('Retry cancelled'); this.name = 'RetryCancelledError'; } }
  const retryOperation = async (operation, { maxAttempts = 3, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), random = Math.random, isCancelRequested = () => false, refreshAuth = null, onRetry = () => {} } = {}) => { let refreshedAuth = false; let lastError; for (let attempt = 1; attempt <= maxAttempts; attempt++) { if (isCancelRequested()) throw new RetryCancelledError(); try { return await operation(); } catch (error) { lastError = error; if (isCancelRequested()) throw new RetryCancelledError(); const status = Number.isInteger(error?.status) ? error.status : null; if ((status === 401 || status === 403) && attempt < maxAttempts && !refreshedAuth && typeof refreshAuth === 'function') { refreshedAuth = true; if (await refreshAuth()) { if (isCancelRequested()) throw new RetryCancelledError(); continue; } throw error; } if (!(status === null || status >= 500) || attempt === maxAttempts) throw error; const delay = (2 ** attempt) * 1000 + Math.floor(random() * 501); onRetry({ attempt, delay, error }); if (isCancelRequested()) throw new RetryCancelledError(); await sleep(delay); if (isCancelRequested()) throw new RetryCancelledError(); } } throw lastError; };
  const reconcileRetryFailures = (previousFailures, retryTargets, succeededIdentities, currentFailures) => { const targetIds = new Set((retryTargets || []).map(target => target?.identity).filter(Boolean)); const previous = new Map((previousFailures || []).map(failure => [failure?.identity, failure]).filter(([identity]) => Boolean(identity))); for (const identity of previous.keys()) if (!targetIds.has(identity)) throw new Error('Failed conversation identity could not be resolved'); const remaining = new Map(previous); for (const identity of new Set(succeededIdentities || [])) { if (!targetIds.has(identity)) throw new Error('Succeeded conversation identity could not be resolved'); remaining.delete(identity); } for (const failure of currentFailures || []) { if (!failure?.identity || !targetIds.has(failure.identity)) throw new Error('Failed conversation identity could not be resolved'); remaining.set(failure.identity, failure); } return [...remaining.values()]; };
  const retryOptionsFor = (context, adapter) => ({ isCancelRequested: context.isCancelRequested, refreshAuth: () => adapter.refreshAuth() });
  const reconcileSelectionAfterRefresh = (selected, conversations) => { const available = new Set((conversations || []).map(conversation => conversation?.identity).filter(Boolean)); return new Set([...selected].filter(identity => available.has(identity))); };
  const INDEX_SNAPSHOT_SCHEMA = 'chatharbor-index-v2';
  const firstPageProbe = items => (items || []).map(item => ({ conversationId: item.conversationId, updatedAt: item.updatedAt ?? null }));
  const partitionProbe = page => ({ total: Number.isInteger(page?.total) ? page.total : null, items: firstPageProbe(page?.items) });
  const compoundProbe = (unarchived, archived) => ({ unarchived: partitionProbe(unarchived), archived: partitionProbe(archived) });
  const sameProbe = (left, right) => JSON.stringify(left || null) === JSON.stringify(right || null);
  const readIndexSnapshot = (storage, { platform, scopeKey }) => { try { const snapshot = storage?.read?.(); if (!snapshot || snapshot.schemaVersion !== INDEX_SNAPSHOT_SCHEMA || snapshot.platform !== platform || snapshot.scopeKey !== scopeKey || !Array.isArray(snapshot.conversations) || !snapshot.probe?.unarchived || !snapshot.probe?.archived || snapshot.conversations.some(item => !item?.conversationId || item.platform !== platform)) return null; return snapshot; } catch { return null; } };
  const loadPartition = async ({ adapter, archived, firstPage, pageSize, maxPages, onProgress, deduped }) => { let page = firstPage || await adapter.listPage({ offset: 0, limit: pageSize, archived }); const initialPage = page; let offset = 0; for (let pageNumber = 0; pageNumber < maxPages; pageNumber++) { const items = page.items || []; for (const item of items) deduped.set(identity(item), item); onProgress({ status: 'syncing', archived, page: pageNumber + 1, count: deduped.size }); offset = Number.isInteger(page.offset) ? page.offset + items.length : offset + items.length; const total = Number.isInteger(page.total) ? page.total : null; if (!items.length || (total !== null && offset >= total) || (total === null && items.length < pageSize)) break; if (pageNumber + 1 >= maxPages) throw new Error('Conversation index max-page guard reached'); page = await adapter.listPage({ offset, limit: pageSize, archived }); } return initialPage; };
  const loadIndexedConversations = async ({ adapter, storage, scopeKey = 'default', pageSize = 20, maxPages = 1000, force = false, now = () => new Date().toISOString(), onProgress = () => {} }) => { const cached = force ? null : readIndexSnapshot(storage, { platform: adapter.platform, scopeKey }); let unarchivedFirst; let archivedFirst; if (cached) { onProgress({ status: 'probing', archived: false }); unarchivedFirst = await adapter.listPage({ offset: 0, limit: pageSize, archived: false }); onProgress({ status: 'probing', archived: true }); archivedFirst = await adapter.listPage({ offset: 0, limit: pageSize, archived: true }); const probe = compoundProbe(unarchivedFirst, archivedFirst); if (sameProbe(probe, cached.probe)) return { conversations: cached.conversations, source: 'validated-cache', probe }; } const deduped = new Map(); unarchivedFirst = await loadPartition({ adapter, archived: false, firstPage: unarchivedFirst, pageSize, maxPages, onProgress, deduped }); archivedFirst = await loadPartition({ adapter, archived: true, firstPage: archivedFirst, pageSize, maxPages, onProgress, deduped }); const conversations = [...deduped.values()]; const probe = compoundProbe(unarchivedFirst, archivedFirst); const snapshot = { schemaVersion: INDEX_SNAPSHOT_SCHEMA, platform: adapter.platform, scopeKey, verifiedAt: now(), conversations, probe }; storage?.write?.(snapshot); return { conversations, source: force ? 'full-refresh' : cached ? 'refreshed-cache' : 'cache-miss', probe }; };
  const filterConversations = (conversations, { query = '', archive = 'unarchived' } = {}) => { const q = query.trim().toLowerCase(); return conversations.filter(conversation => { if (archive === 'unarchived' && conversation.archived) return false; if (archive === 'archived' && !conversation.archived) return false; return !q || `${conversation.title} ${conversation.identity}`.toLowerCase().includes(q); }); };
  const createExecutionController = (targets, execute, onUpdate = () => {}) => {
    const state = { total: targets.length, currentIndex: 0, currentIdentity: null, completed: 0, success: 0, skipped: 0, failed: 0, failures: [], status: 'idle', cancelRequested: false };
    const snapshot = () => ({ ...state, failures: [...state.failures], remaining: state.total - state.completed });
    const update = () => onUpdate(snapshot());
    return { snapshot, requestCancel() { if (state.status === 'running') { state.cancelRequested = true; state.status = 'cancelling'; update(); } }, async run() { if (state.status !== 'idle') throw new Error('Execution already started'); state.status = 'running'; update(); for (let index = 0; index < targets.length; index++) { if (state.cancelRequested) break; const target = targets[index]; state.currentIndex = index + 1; state.currentIdentity = target.identity; update(); try { await execute(target, { isCancelRequested: () => state.cancelRequested }); state.success++; } catch (error) { state.failed++; state.failures.push({ identity: target.identity, error: String(error?.message || error), status: Number.isInteger(error?.status) ? error.status : null }); } state.completed++; update(); } state.currentIdentity = null; state.status = state.cancelRequested ? 'cancelled' : 'completed'; update(); return snapshot(); } };
  };
  const exportPair = (c) => {
    const artifactId = c.contentVersion ? `${identity(c)}#${c.contentVersion}` : `${identity(c)}#artifact-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const observed = observe(c); const contentVersion = observed.value; const resolvedArtifactId = contentVersion ? `${identity(c)}#${contentVersion}` : artifactId;
    const manifest = { schemaVersion: 'chatharbor-export-state-v1', artifactVersion: 1, artifactId: resolvedArtifactId, identity: identity(c), platform: c.platform, conversationId: c.conversationId, titleAtExport: c.title, contentVersion, contentVersionSource: observed.source, exportedAt: new Date().toISOString(), sourceUpdatedAt: c.updatedAt || null, representations: ['json', 'markdown'], artifactRefs: [resolvedArtifactId], attachmentManifest: c.attachments };
    return { json: JSON.stringify({ ...c, identity: manifest.identity, contentVersion }, null, 2), md: markdown(c), manifest };
  };
  if (globalThis.__CHATHARBOR_TEST_HOOKS__) {
    globalThis.__CHATHARBOR_TEST_HOOKS__.observe = observe;
    globalThis.__CHATHARBOR_TEST_HOOKS__.exportPair = exportPair;
    globalThis.__CHATHARBOR_TEST_HOOKS__.layout = layout;
    globalThis.__CHATHARBOR_TEST_HOOKS__.workspaceSurface = workspaceSurface;
    globalThis.__CHATHARBOR_TEST_HOOKS__.workspaceAvailability = workspaceAvailability;
    globalThis.__CHATHARBOR_TEST_HOOKS__.createExecutionController = createExecutionController;
    globalThis.__CHATHARBOR_TEST_HOOKS__.executionControls = executionControls;
    globalThis.__CHATHARBOR_TEST_HOOKS__.retryControls = retryControls;
    globalThis.__CHATHARBOR_TEST_HOOKS__.cancelButtonStyle = cancelButtonStyle;
    globalThis.__CHATHARBOR_TEST_HOOKS__.retryOperation = retryOperation;
    globalThis.__CHATHARBOR_TEST_HOOKS__.RetryCancelledError = RetryCancelledError;
    globalThis.__CHATHARBOR_TEST_HOOKS__.reconcileRetryFailures = reconcileRetryFailures;
    globalThis.__CHATHARBOR_TEST_HOOKS__.retryOptionsFor = retryOptionsFor;
    globalThis.__CHATHARBOR_TEST_HOOKS__.loadIndexedConversations = loadIndexedConversations;
    globalThis.__CHATHARBOR_TEST_HOOKS__.firstPageProbe = firstPageProbe;
    globalThis.__CHATHARBOR_TEST_HOOKS__.compoundProbe = compoundProbe;
    globalThis.__CHATHARBOR_TEST_HOOKS__.filterConversations = filterConversations;
    globalThis.__CHATHARBOR_TEST_HOOKS__.reconcileSelectionAfterRefresh = reconcileSelectionAfterRefresh;
    return;
  }
  let accessToken = null;
  const token = async (refresh = false) => {
    if (accessToken && !refresh) return accessToken;
    const session = await (await fetch('/api/auth/session?unstable_client=true')).json();
    if (!session.accessToken) throw new Error('ChatGPT access token unavailable');
    accessToken = session.accessToken;
    return accessToken;
  };
  const headers = async () => {
    const h = { Authorization: `Bearer ${await token()}` };
    const did = document.cookie.match(/oai-did=([^;]+)/)?.[1];
    if (did) h['oai-device-id'] = did;
    return h;
  };
  const adapter = {
    platform: 'chatgpt',
    capabilities: { scope: false, archive: true, attachments: true, reasoning: false, sources: false, contentRevision: false },
    async detect() { return location.hostname === 'chatgpt.com' || location.hostname === 'chat.openai.com'; },
    async listPage({ offset = 0, limit = 20, archived = false } = {}) {
      const h = await headers();
      const r = await fetch(`/backend-api/conversations?offset=${offset}&limit=${limit}&order=updated${archived ? '&is_archived=true' : ''}`, { headers: h });
      if (!r.ok) { const error = new Error(`Conversation list failed: ${r.status}`); error.status = r.status; throw error; }
      const j = await r.json();
      return { items: (j.items || []).map(x => normalize(x, { platform: 'chatgpt', conversationId: x.id, title: x.title, createdAt: x.create_time, updatedAt: x.update_time, archived })), offset, total: Number.isInteger(j.total) ? j.total : null };
    },
    async listConversations() {
      return (await this.listPage()).items;
    },
    async fetchConversation(id) {
      const h = await headers();
      const r = await fetch(`/backend-api/conversation/${encodeURIComponent(id)}`, { headers: h });
      if (!r.ok) { const error = new Error(`Conversation fetch failed: ${r.status}`); error.status = r.status; throw error; }
      const raw = await r.json();
      const messages = extractChatGPTMessages(raw);
      return normalize({ ...raw, messages, attachments: messages.flatMap(m => m.attachments) }, { platform: 'chatgpt', conversationId: id });
    },
    async refreshAuth() {
      accessToken = null;
      try { await token(true); return true; }
      catch { return false; }
    }
  };
  const download = (name, content, type) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([content], { type })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); };
  const buildRequest = (ids, strategy) => ids.length ? { selectedIds: [...ids], confirmation: { range: 'selected', count: ids.length, strategy, batchCount: 1, skipLatest: false } } : null;
  const run = async () => {
    if (!(await adapter.detect())) throw new Error('ChatGPT not detected');
    const availability = workspaceAvailability(adapter.capabilities);
    const indexStorage = { read: () => { try { return JSON.parse(localStorage.getItem('chatharbor-index-chatgpt-default') || 'null'); } catch { return null; } }, write: snapshot => localStorage.setItem('chatharbor-index-chatgpt-default', JSON.stringify(snapshot)) };
    const indexed = await loadIndexedConversations({ adapter, storage: indexStorage, pageSize: 20 });
    let list = indexed.conversations;
    let indexSource = indexed.source;
    if (!list.length) throw new Error('No conversation returned');
    const selected = new Set(); let filtered = [...list];
    const overlay = document.createElement('div'); Object.assign(overlay.style, { position: 'fixed', inset: '0', zIndex: '2147483645', background: 'rgba(0,0,0,.42)', display: 'flex', alignItems: 'center', justifyContent: 'center' });
    const panel = document.createElement('section'); Object.assign(panel.style, { width: 'min(1080px,94vw)', height: 'min(720px,88vh)', background: '#fff', color: '#111', borderRadius: '14px', padding: '18px', display: 'grid', gap: '14px', font: '14px system-ui', boxSizing: 'border-box' }, layout.panel);
    panel.innerHTML = `<header style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:center"><strong style="font-size:20px">ChatHarbor Pilot Workspace</strong><button data-role="close">关闭</button></header><div data-role="toolbar" style="grid-column:1/-1;display:flex;gap:8px;align-items:center"><input data-role="search" placeholder="搜索标题或 Conversation ID" style="flex:1"><button data-role="scope" disabled>范围（不可用）</button><select data-role="archive"><option value="unarchived">未归档</option><option value="all">全部</option><option value="archived">已归档</option></select><button data-role="export-status" disabled>导出状态（不可用）</button><button data-role="time" disabled>时间（不可用）</button><button data-role="refresh">完整刷新</button><span data-role="status" style="color:#666;font-size:12px">${indexSource === 'validated-cache' ? '已验证缓存' : `已同步 ${list.length} 条`}</span></div><main data-role="main" style="display:flex;flex-direction:column;gap:10px"><div data-role="list" style="border:1px solid #ddd;border-radius:8px"></div></main><aside data-role="rail" style="border:1px solid #ddd;border-radius:8px;padding:12px;gap:12px"><section><strong>选择</strong><div data-role="summary"></div></section><section><strong>导出策略</strong><div data-role="strategy">当前 Pilot · 单批</div></section><section><strong>导出记录</strong><button disabled>当前不可用</button></section><div data-role="progress" hidden></div><button data-role="cancel" hidden>取消</button><button data-role="retry" hidden>重试失败项</button><div data-role="actions" style="display:flex;flex-direction:column;gap:8px"><button data-role="export-filter" disabled>导出当前筛选（不可用）</button><button data-role="export-scope" disabled hidden>导出当前范围（不可用）</button><button data-role="export" disabled style="padding:10px;border:0;border-radius:8px;background:#10a37f;color:#fff;font-weight:700">导出选中 0 条</button></div></aside>`;
    const listEl = panel.querySelector('[data-role="list"]'); const search = panel.querySelector('[data-role="search"]'); const scope = panel.querySelector('[data-role="scope"]'); const archive = panel.querySelector('[data-role="archive"]'); const summary = panel.querySelector('[data-role="summary"]'); const exportBtn = panel.querySelector('[data-role="export"]'); const filterExportBtn = panel.querySelector('[data-role="export-filter"]'); const scopeExportBtn = panel.querySelector('[data-role="export-scope"]'); const progress = panel.querySelector('[data-role="progress"]'); const cancelBtn = panel.querySelector('[data-role="cancel"]'); const retryBtn = panel.querySelector('[data-role="retry"]'); const refreshBtn = panel.querySelector('[data-role="refresh"]'); const statusLine = panel.querySelector('[data-role="status"]'); const closeBtn = panel.querySelector('[data-role="close"]'); let controller = null; let executionActive = false; let executionStatus = 'idle'; let lastFailures = []; let lastTargets = [];
    Object.assign(panel.querySelector('[data-role="main"]').style, layout.main); Object.assign(listEl.style, layout.list); Object.assign(panel.querySelector('[data-role="rail"]').style, layout.rail); Object.assign(cancelBtn.style, cancelButtonStyle); Object.assign(panel.querySelector('[data-role="actions"]').style, layout.action); scope.hidden = !availability.toolbar.scope.visible; scope.disabled = !availability.toolbar.scope.enabled; archive.disabled = !availability.toolbar.archive.enabled; scopeExportBtn.hidden = !availability.rail.exportActions.currentScope.visible;
    const render = () => { const controls = executionControls(selected.size, executionStatus); const retry = retryControls(lastFailures.length, executionStatus); filtered = filterConversations(list, { query: search.value, archive: archive.value }); listEl.innerHTML = ''; filtered.forEach(c => { const row = document.createElement('label'); Object.assign(row.style, { display: 'flex', gap: '8px', padding: '10px', borderBottom: '1px solid #eee', cursor: controls.selectionEnabled ? 'pointer' : 'default' }, layout.row); row.innerHTML = `<input type="checkbox" ${selected.has(c.identity) ? 'checked' : ''} ${controls.selectionEnabled ? '' : 'disabled'}><span>${c.title || '(未命名)'} <small style="color:#777">${c.conversationId}</small></span>`; Object.assign(row.querySelector('span').style, layout.title); row.querySelector('input').onchange = e => { if (!controls.selectionEnabled) return; e.target.checked ? selected.add(c.identity) : selected.delete(c.identity); render(); }; listEl.appendChild(row); }); summary.textContent = `已选 ${selected.size} 条 · 匹配 ${filtered.length} / 总计 ${list.length}`; exportBtn.textContent = `导出选中 ${selected.size} 条`; exportBtn.disabled = !controls.exportEnabled; filterExportBtn.disabled = !availability.rail.exportActions.currentFilter.enabled; scopeExportBtn.disabled = !availability.rail.exportActions.currentScope.enabled; closeBtn.disabled = !controls.closeEnabled; cancelBtn.hidden = !controls.cancelVisible; cancelBtn.disabled = !controls.cancelEnabled; cancelBtn.style.opacity = controls.cancelEnabled ? '1' : '0.55'; cancelBtn.style.cursor = controls.cancelEnabled ? 'pointer' : 'not-allowed'; retryBtn.hidden = !retry.visible; retryBtn.disabled = !retry.enabled; retryBtn.textContent = `重试失败 ${lastFailures.length} 条`; };
    search.oninput = render; archive.onchange = render; closeBtn.onclick = () => { if (!executionActive) overlay.remove(); }; refreshBtn.onclick = async () => { if (executionActive) return; statusLine.textContent = 'ChatGPT · 正在完整刷新…'; refreshBtn.disabled = true; try { const refreshed = await loadIndexedConversations({ adapter, storage: indexStorage, pageSize: 20, force: true, onProgress: state => { if (state.status === 'syncing') statusLine.textContent = `ChatGPT · 正在加载${state.archived ? '已归档' : '未归档'}第 ${state.page} 页（${state.count} 条）`; } }); list = refreshed.conversations; indexSource = refreshed.source; const retained = reconcileSelectionAfterRefresh(selected, list); selected.clear(); for (const selectedIdentity of retained) selected.add(selectedIdentity); statusLine.textContent = `ChatGPT · 已同步 ${list.length} 条`; render(); } catch (error) { statusLine.textContent = `ChatGPT · 刷新失败：${error.message}`; } finally { refreshBtn.disabled = false; } };
    const showProgress = state => { executionStatus = state.status; progress.hidden = false; progress.textContent = `状态：${state.status} · ${state.currentIndex}/${state.total}\n成功 ${state.success} · 失败 ${state.failed} · 跳过 ${state.skipped} · 剩余 ${state.remaining}${state.currentIdentity ? `\n当前：${state.currentIdentity}` : ''}`; render(); };
    cancelBtn.onclick = () => controller?.requestCancel();
    const executeTargets = async (targets, previousFailures = null) => { if (executionActive || !targets.length) return; executionActive = true; executionStatus = 'running'; lastTargets = [...targets]; const succeededIdentities = []; render(); controller = createExecutionController(targets, async (conversation, context) => { const c = await retryOperation(() => adapter.fetchConversation(conversation.conversationId), retryOptionsFor(context, adapter)); const out = exportPair(c); download(`chatharbor-${c.conversationId}.json`, out.json, 'application/json'); download(`chatharbor-${c.conversationId}.md`, out.md, 'text/markdown'); succeededIdentities.push(conversation.identity); console.info('[ChatHarbor Pilot] selected export', c, out.manifest); }, showProgress); try { const result = await controller.run(); lastFailures = previousFailures ? reconcileRetryFailures(previousFailures, targets, succeededIdentities, result.failures) : result.failures; } finally { executionActive = false; render(); } };
    retryBtn.onclick = () => { const previousFailures = [...lastFailures]; const failed = new Set(previousFailures.map(failure => failure.identity)); const targets = lastTargets.filter(target => failed.has(target.identity)); if (targets.length !== failed.size) throw new Error('Failed conversation identity could not be resolved'); executeTargets(targets, previousFailures); };
    exportBtn.onclick = async () => { if (executionActive) return; const request = buildRequest([...selected], '当前 Pilot'); if (!request) return; const selectedConversations = list.filter(c => request.selectedIds.includes(c.identity)); if (selectedConversations.length !== request.selectedIds.length) throw new Error('Selected conversation identity could not be resolved'); const message = `导出范围：当前选择\n条数：${request.confirmation.count}\n策略：${request.confirmation.strategy}\n预计批次：${request.confirmation.batchCount}\n跳过已是最新：${request.confirmation.skipLatest ? '是' : '否'}\n\n继续？`; if (!confirm(message)) return; await executeTargets(selectedConversations); };
    render(); overlay.appendChild(panel); document.body.appendChild(overlay);
  };
  const button = document.createElement('button');
  button.textContent = 'ChatHarbor Pilot';
  button.title = 'ChatHarbor Pilot · test one conversation';
  Object.assign(button.style, { position: 'fixed', right: '24px', bottom: '24px', zIndex: '2147483646', padding: '10px 14px', border: '0', borderRadius: '8px', background: '#10a37f', color: '#fff', font: '600 13px system-ui', cursor: 'pointer' });
  button.onclick = async () => { button.disabled = true; try { await run(); } catch (e) { console.error('[ChatHarbor Pilot]', e); alert(`ChatHarbor Pilot failed: ${e.message}`); } finally { button.disabled = false; } };
  document.body.appendChild(button);
})();
