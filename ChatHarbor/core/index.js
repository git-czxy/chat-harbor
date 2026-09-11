import { conversationIdentity } from '../models/conversation.js';

export function createConversationIndex(adapter) {
  return {
    async list(options = {}) {
      return (await adapter.listConversations(options)).map(item => ({ ...item, identity: conversationIdentity(item) }));
    },
    async fetch(item, options = {}) {
      return adapter.fetchConversation(item.conversationId, options);
    }
  };
}
