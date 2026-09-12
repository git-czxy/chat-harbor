import { normalizeConversation } from '../models/conversation.js';

export function extractChatGPTMessages(raw) {
  const mapping = raw?.mapping;
  if (!mapping || typeof mapping !== 'object') return Array.isArray(raw?.messages) ? raw.messages : [];
  const ids = Object.keys(mapping);
  const root = mapping['client-created-root'] ? 'client-created-root' : ids.find(id => !mapping[id]?.parent) || ids[0];
  const visited = new Set();
  const messages = [];
  const walk = (id) => {
    if (!id || visited.has(id) || !mapping[id]) return;
    visited.add(id);
    const node = mapping[id];
    const msg = node.message;
    const role = msg?.author?.role;
    const hidden = msg?.metadata?.is_visually_hidden_from_conversation || msg?.metadata?.is_contextual_answers_system_message;
    if (msg && (role === 'user' || role === 'assistant') && !hidden) {
      const parts = Array.isArray(msg.content?.parts) ? msg.content.parts : [];
      const content = parts.map(part => typeof part === 'string' ? part : part?.text || '').filter(Boolean).join('\n');
      const attachments = (msg.metadata?.attachments || []).map(a => ({ id: a.id || a.file_id || a.asset_pointer || null, mimeType: a.mime_type || a.content_type || null, name: a.name || a.filename || null, size: a.size ?? null }));
      if (content || attachments.length) messages.push({ messageId: msg.id || id, parentId: node.parent || null, role, content, contentType: msg.content?.content_type || null, createdAt: msg.create_time || null, updatedAt: msg.update_time || null, attachments });
    }
    (node.children || []).forEach(walk);
  };
  walk(root);
  return messages;
}

export function createChatGPTAdapter({ list, fetch, refreshAuth } = {}) {
  return {
    platform: 'chatgpt',
    capabilities: {
      scope: false,
      archive: false,
      attachments: true,
      reasoning: false,
      sources: false,
      contentRevision: false
    },
    async detect() { return typeof list === 'function' && typeof fetch === 'function'; },
    async refreshAuth() { return typeof refreshAuth === 'function' ? Boolean(await refreshAuth()) : false; },
    async listConversations(options = {}) {
      const rows = await list(options);
      return rows.map(raw => normalizeConversation(raw, {
        platform: 'chatgpt', conversationId: raw.id,
        title: raw.title, createdAt: raw.create_time,
        updatedAt: raw.update_time
      }));
    },
    async fetchConversation(conversationId, options = {}) {
      const raw = await fetch(conversationId, options);
      const messages = extractChatGPTMessages(raw);
      return normalizeConversation({ ...raw, messages, attachments: messages.flatMap(message => message.attachments) }, { platform: 'chatgpt', conversationId });
    }
  };
}
