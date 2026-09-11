export function conversationIdentity(conversation) {
  if (!conversation?.platform || !conversation?.conversationId) throw new Error('platform and conversationId are required');
  return `${conversation.platform}:${conversation.conversationId}`;
}

export function normalizeConversation(raw, meta = {}) {
  const conversation = {
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
  conversation.identity = conversationIdentity(conversation);
  return conversation;
}
