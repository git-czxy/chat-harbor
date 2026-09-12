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
  const exportPair = (c) => {
    const artifactId = c.contentVersion ? `${identity(c)}#${c.contentVersion}` : `${identity(c)}#artifact-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const observed = observe(c); const contentVersion = observed.value; const resolvedArtifactId = contentVersion ? `${identity(c)}#${contentVersion}` : artifactId;
    const manifest = { schemaVersion: 'chatharbor-export-state-v1', artifactVersion: 1, artifactId: resolvedArtifactId, identity: identity(c), platform: c.platform, conversationId: c.conversationId, titleAtExport: c.title, contentVersion, contentVersionSource: observed.source, exportedAt: new Date().toISOString(), sourceUpdatedAt: c.updatedAt || null, representations: ['json', 'markdown'], artifactRefs: [resolvedArtifactId], attachmentManifest: c.attachments };
    return { json: JSON.stringify({ ...c, identity: manifest.identity, contentVersion }, null, 2), md: markdown(c), manifest };
  };
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
    const panel = document.createElement('section'); Object.assign(panel.style, { width: 'min(1080px,94vw)', height: 'min(720px,88vh)', background: '#fff', color: '#111', borderRadius: '14px', padding: '18px', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 250px', gap: '14px', font: '14px system-ui', boxSizing: 'border-box' });
    panel.innerHTML = `<header style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:center"><div><strong style="font-size:20px">ChatHarbor Pilot Workspace</strong><div data-role="status" style="color:#666;font-size:12px">ChatGPT · Test/Pilot</div></div><button data-role="close">关闭</button></header><main style="min-width:0;display:flex;flex-direction:column;gap:10px"><input data-role="search" placeholder="搜索标题或 Conversation ID"><div data-role="list" style="overflow:auto;flex:1;border:1px solid #ddd;border-radius:8px"></div></main><aside style="border:1px solid #ddd;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:12px;min-width:0"><div data-role="summary"></div><div><strong>导出策略</strong><div data-role="strategy">当前 Pilot · 单批</div></div><button data-role="export" disabled style="margin-top:auto;padding:10px;border:0;border-radius:8px;background:#10a37f;color:#fff;font-weight:700">导出选中 0 条</button></aside>`;
    const listEl = panel.querySelector('[data-role="list"]'); const search = panel.querySelector('[data-role="search"]'); const summary = panel.querySelector('[data-role="summary"]'); const exportBtn = panel.querySelector('[data-role="export"]');
    const render = () => { const q = search.value.trim().toLowerCase(); filtered = list.filter(c => !q || `${c.title} ${c.identity}`.toLowerCase().includes(q)); listEl.innerHTML = ''; filtered.forEach(c => { const row = document.createElement('label'); row.style.cssText = 'display:flex;gap:8px;padding:10px;border-bottom:1px solid #eee;cursor:pointer'; row.innerHTML = `<input type="checkbox" ${selected.has(c.identity) ? 'checked' : ''}><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.title || '(未命名)'} <small style="color:#777">${c.conversationId}</small></span>`; row.querySelector('input').onchange = e => { e.target.checked ? selected.add(c.identity) : selected.delete(c.identity); render(); }; listEl.appendChild(row); }); summary.textContent = `已选 ${selected.size} 条 · 匹配 ${filtered.length} / 总计 ${list.length}`; exportBtn.textContent = `导出选中 ${selected.size} 条`; exportBtn.disabled = selected.size === 0; };
    search.oninput = render; panel.querySelector('[data-role="close"]').onclick = () => overlay.remove();
    exportBtn.onclick = async () => { const request = buildRequest([...selected], '当前 Pilot'); if (!request) return; const selectedConversations = list.filter(c => request.selectedIds.includes(c.identity)); if (selectedConversations.length !== request.selectedIds.length) throw new Error('Selected conversation identity could not be resolved'); const message = `导出范围：当前选择\n条数：${request.confirmation.count}\n策略：${request.confirmation.strategy}\n预计批次：${request.confirmation.batchCount}\n跳过已是最新：${request.confirmation.skipLatest ? '是' : '否'}\n\n继续？`; if (!confirm(message)) return; exportBtn.disabled = true; for (const conversation of selectedConversations) { const c = await adapter.fetchConversation(conversation.conversationId); const out = exportPair(c); download(`chatharbor-${c.conversationId}.json`, out.json, 'application/json'); download(`chatharbor-${c.conversationId}.md`, out.md, 'text/markdown'); console.info('[ChatHarbor Pilot] selected export', c, out.manifest); } overlay.remove(); alert(`ChatHarbor Pilot PASS\n已导出 ${request.selectedIds.length} 条`); };
    render(); overlay.appendChild(panel); document.body.appendChild(overlay);
  };
  const button = document.createElement('button');
  button.textContent = 'ChatHarbor Pilot';
  button.title = 'ChatHarbor Pilot · test one conversation';
  Object.assign(button.style, { position: 'fixed', right: '24px', bottom: '24px', zIndex: '2147483646', padding: '10px 14px', border: '0', borderRadius: '8px', background: '#10a37f', color: '#fff', font: '600 13px system-ui', cursor: 'pointer' });
  button.onclick = async () => { button.disabled = true; try { await run(); } catch (e) { console.error('[ChatHarbor Pilot]', e); alert(`ChatHarbor Pilot failed: ${e.message}`); } finally { button.disabled = false; } };
  document.body.appendChild(button);
})();
