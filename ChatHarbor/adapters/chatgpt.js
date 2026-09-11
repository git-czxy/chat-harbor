import { normalizeConversation } from '../models/conversation.js';

export function createChatGPTAdapter({ list, fetch }) {
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
      return normalizeConversation(raw, { platform: 'chatgpt', conversationId });
    }
  };
}
