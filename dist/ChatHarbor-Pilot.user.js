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
    const manifest = { identity: identity(c), platform: c.platform, conversationId: c.conversationId, titleAtExport: c.title, contentVersion: c.contentVersion, exportedAt: new Date().toISOString(), representations: ['json', 'markdown'], attachmentManifest: c.attachments };
    return { json: JSON.stringify({ ...c, identity: manifest.identity }, null, 2), md: markdown(c), manifest };
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
      const r = await fetch('/backend-api/conversations?offset=0&limit=1&order=updated', { headers: h });
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
  const run = async () => {
    if (!(await adapter.detect())) throw new Error('ChatGPT not detected');
    const list = await adapter.listConversations();
    if (!list.length) throw new Error('No conversation returned');
    const c = await adapter.fetchConversation(list[0].conversationId);
    const out = exportPair(c);
    const base = `chatharbor-${c.conversationId}`;
    download(`${base}.json`, out.json, 'application/json');
    download(`${base}.md`, out.md, 'text/markdown');
    console.info('[ChatHarbor Pilot] adapter=list/fetch, normalized=', c, 'manifest=', out.manifest);
    alert(`ChatHarbor Pilot PASS\n${c.identity}\nJSON + Markdown downloaded\ncontentVersion: ${String(c.contentVersion)}`);
  };
  const button = document.createElement('button');
  button.textContent = 'ChatHarbor Pilot';
  button.title = 'ChatHarbor Pilot · test one conversation';
  Object.assign(button.style, { position: 'fixed', right: '24px', bottom: '24px', zIndex: '2147483646', padding: '10px 14px', border: '0', borderRadius: '8px', background: '#10a37f', color: '#fff', font: '600 13px system-ui', cursor: 'pointer' });
  button.onclick = async () => { button.disabled = true; try { await run(); } catch (e) { console.error('[ChatHarbor Pilot]', e); alert(`ChatHarbor Pilot failed: ${e.message}`); } finally { button.disabled = false; } };
  document.body.appendChild(button);
})();
