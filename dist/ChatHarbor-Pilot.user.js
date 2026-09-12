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
    panel: { gridTemplateColumns: 'minmax(0,1fr) 250px', gridTemplateRows: 'auto minmax(0,1fr)', overflow: 'hidden' },
    main: { minWidth: '0', minHeight: '0', overflow: 'hidden' },
    list: { flex: '1', minWidth: '0', minHeight: '0', overflowX: 'hidden', overflowY: 'auto' },
    row: { minWidth: '0', width: '100%', boxSizing: 'border-box' },
    title: { flex: '1', minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
    rail: { minWidth: '0', minHeight: '0', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
    action: { marginTop: 'auto' }
  };
  const executionControls = (selectedCount, status = 'idle') => { const active = status === 'running' || status === 'cancelling'; return { active, exportEnabled: selectedCount > 0 && !active, selectionEnabled: !active, closeEnabled: !active }; };
  const createExecutionController = (targets, execute, onUpdate = () => {}) => {
    const state = { total: targets.length, currentIndex: 0, currentIdentity: null, completed: 0, success: 0, skipped: 0, failed: 0, failures: [], status: 'idle', cancelRequested: false };
    const snapshot = () => ({ ...state, failures: [...state.failures], remaining: state.total - state.completed });
    const update = () => onUpdate(snapshot());
    return { snapshot, requestCancel() { if (state.status === 'running') { state.cancelRequested = true; state.status = 'cancelling'; update(); } }, async run() { if (state.status !== 'idle') throw new Error('Execution already started'); state.status = 'running'; update(); for (let index = 0; index < targets.length; index++) { if (state.cancelRequested) break; const target = targets[index]; state.currentIndex = index + 1; state.currentIdentity = target.identity; update(); try { await execute(target); state.success++; } catch (error) { state.failed++; state.failures.push({ identity: target.identity, error: String(error?.message || error) }); } state.completed++; update(); } state.currentIdentity = null; state.status = state.cancelRequested ? 'cancelled' : 'completed'; update(); return snapshot(); } };
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
    globalThis.__CHATHARBOR_TEST_HOOKS__.createExecutionController = createExecutionController;
    globalThis.__CHATHARBOR_TEST_HOOKS__.executionControls = executionControls;
    return;
  }
  const token = async () => {
    const session = await (await fetch('/api/auth/session?unstable_client=true')).json();
    if (!session.accessToken) throw new Error('ChatGPT access token unavailable');
    return session.accessToken;
  };
  const headers = async () => {
    const h = { Authorization: `Bearer ${await token()}` };
    const did = document.cookie.match(/oai-did=([^;]+)/)?.[1];
    if (did) h['oai-device-id'] = did;
    return h;
  };
  const adapter = {
    platform: 'chatgpt',
    capabilities: { scope: false, archive: false, attachments: true, reasoning: false, sources: false, contentRevision: false },
    async detect() { return location.hostname === 'chatgpt.com' || location.hostname === 'chat.openai.com'; },
    async listConversations() {
      const h = await headers();
      const r = await fetch('/backend-api/conversations?offset=0&limit=20&order=updated', { headers: h });
      if (!r.ok) throw new Error(`Conversation list failed: ${r.status}`);
      const j = await r.json();
      return (j.items || []).map(x => normalize(x, { platform: 'chatgpt', conversationId: x.id, title: x.title, createdAt: x.create_time, updatedAt: x.update_time }));
    },
    async fetchConversation(id) {
      const h = await headers();
      const r = await fetch(`/backend-api/conversation/${encodeURIComponent(id)}`, { headers: h });
      if (!r.ok) throw new Error(`Conversation fetch failed: ${r.status}`);
      const raw = await r.json();
      const messages = extractChatGPTMessages(raw);
      return normalize({ ...raw, messages, attachments: messages.flatMap(m => m.attachments) }, { platform: 'chatgpt', conversationId: id });
    }
  };
  const download = (name, content, type) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([content], { type })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); };
  const buildRequest = (ids, strategy) => ids.length ? { selectedIds: [...ids], confirmation: { range: 'selected', count: ids.length, strategy, batchCount: 1, skipLatest: false } } : null;
  const run = async () => {
    if (!(await adapter.detect())) throw new Error('ChatGPT not detected');
    const list = await adapter.listConversations();
    if (!list.length) throw new Error('No conversation returned');
    const selected = new Set(); let filtered = [...list];
    const overlay = document.createElement('div'); Object.assign(overlay.style, { position: 'fixed', inset: '0', zIndex: '2147483645', background: 'rgba(0,0,0,.42)', display: 'flex', alignItems: 'center', justifyContent: 'center' });
    const panel = document.createElement('section'); Object.assign(panel.style, { width: 'min(1080px,94vw)', height: 'min(720px,88vh)', background: '#fff', color: '#111', borderRadius: '14px', padding: '18px', display: 'grid', gap: '14px', font: '14px system-ui', boxSizing: 'border-box' }, layout.panel);
    panel.innerHTML = `<header style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:center"><div><strong style="font-size:20px">ChatHarbor Pilot Workspace</strong><div data-role="status" style="color:#666;font-size:12px">ChatGPT · Test/Pilot</div></div><button data-role="close">关闭</button></header><main data-role="main" style="display:flex;flex-direction:column;gap:10px"><input data-role="search" placeholder="搜索标题或 Conversation ID"><div data-role="list" style="border:1px solid #ddd;border-radius:8px"></div></main><aside data-role="rail" style="border:1px solid #ddd;border-radius:8px;padding:12px;gap:12px"><div data-role="summary"></div><div><strong>导出策略</strong><div data-role="strategy">当前 Pilot · 单批</div></div><div data-role="progress" hidden></div><button data-role="cancel" hidden>取消</button><button data-role="export" disabled style="padding:10px;border:0;border-radius:8px;background:#10a37f;color:#fff;font-weight:700">导出选中 0 条</button></aside>`;
    const listEl = panel.querySelector('[data-role="list"]'); const search = panel.querySelector('[data-role="search"]'); const summary = panel.querySelector('[data-role="summary"]'); const exportBtn = panel.querySelector('[data-role="export"]'); const progress = panel.querySelector('[data-role="progress"]'); const cancelBtn = panel.querySelector('[data-role="cancel"]'); const closeBtn = panel.querySelector('[data-role="close"]'); let controller = null; let executionActive = false;
    Object.assign(panel.querySelector('[data-role="main"]').style, layout.main); Object.assign(listEl.style, layout.list); Object.assign(panel.querySelector('[data-role="rail"]').style, layout.rail); Object.assign(exportBtn.style, layout.action);
    const render = () => { const controls = executionControls(selected.size, executionActive ? 'running' : 'idle'); const q = search.value.trim().toLowerCase(); filtered = list.filter(c => !q || `${c.title} ${c.identity}`.toLowerCase().includes(q)); listEl.innerHTML = ''; filtered.forEach(c => { const row = document.createElement('label'); Object.assign(row.style, { display: 'flex', gap: '8px', padding: '10px', borderBottom: '1px solid #eee', cursor: controls.selectionEnabled ? 'pointer' : 'default' }, layout.row); row.innerHTML = `<input type="checkbox" ${selected.has(c.identity) ? 'checked' : ''} ${controls.selectionEnabled ? '' : 'disabled'}><span>${c.title || '(未命名)'} <small style="color:#777">${c.conversationId}</small></span>`; Object.assign(row.querySelector('span').style, layout.title); row.querySelector('input').onchange = e => { if (!controls.selectionEnabled) return; e.target.checked ? selected.add(c.identity) : selected.delete(c.identity); render(); }; listEl.appendChild(row); }); summary.textContent = `已选 ${selected.size} 条 · 匹配 ${filtered.length} / 总计 ${list.length}`; exportBtn.textContent = `导出选中 ${selected.size} 条`; exportBtn.disabled = !controls.exportEnabled; closeBtn.disabled = !controls.closeEnabled; };
    search.oninput = render; closeBtn.onclick = () => { if (!executionActive) overlay.remove(); };
    const showProgress = state => { progress.hidden = false; progress.textContent = `状态：${state.status} · ${state.currentIndex}/${state.total}\n成功 ${state.success} · 失败 ${state.failed} · 跳过 ${state.skipped} · 剩余 ${state.remaining}${state.currentIdentity ? `\n当前：${state.currentIdentity}` : ''}`; cancelBtn.hidden = state.status !== 'running' && state.status !== 'cancelling'; cancelBtn.disabled = state.status === 'cancelling'; };
    cancelBtn.onclick = () => controller?.requestCancel();
    exportBtn.onclick = async () => { if (executionActive) return; const request = buildRequest([...selected], '当前 Pilot'); if (!request) return; const selectedConversations = list.filter(c => request.selectedIds.includes(c.identity)); if (selectedConversations.length !== request.selectedIds.length) throw new Error('Selected conversation identity could not be resolved'); const message = `导出范围：当前选择\n条数：${request.confirmation.count}\n策略：${request.confirmation.strategy}\n预计批次：${request.confirmation.batchCount}\n跳过已是最新：${request.confirmation.skipLatest ? '是' : '否'}\n\n继续？`; if (!confirm(message)) return; executionActive = true; render(); controller = createExecutionController(selectedConversations, async conversation => { const c = await adapter.fetchConversation(conversation.conversationId); const out = exportPair(c); download(`chatharbor-${c.conversationId}.json`, out.json, 'application/json'); download(`chatharbor-${c.conversationId}.md`, out.md, 'text/markdown'); console.info('[ChatHarbor Pilot] selected export', c, out.manifest); }, showProgress); try { await controller.run(); } finally { executionActive = false; render(); } };
    render(); overlay.appendChild(panel); document.body.appendChild(overlay);
  };
  const button = document.createElement('button');
  button.textContent = 'ChatHarbor Pilot';
  button.title = 'ChatHarbor Pilot · test one conversation';
  Object.assign(button.style, { position: 'fixed', right: '24px', bottom: '24px', zIndex: '2147483646', padding: '10px 14px', border: '0', borderRadius: '8px', background: '#10a37f', color: '#fff', font: '600 13px system-ui', cursor: 'pointer' });
  button.onclick = async () => { button.disabled = true; try { await run(); } catch (e) { console.error('[ChatHarbor Pilot]', e); alert(`ChatHarbor Pilot failed: ${e.message}`); } finally { button.disabled = false; } };
  document.body.appendChild(button);
})();
