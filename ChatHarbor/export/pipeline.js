import { conversationIdentity } from '../models/conversation.js';
import { EXPORT_STATE_SCHEMA } from '../core/export-state.js';

function messageText(message) {
  const content = message?.content;
  if (typeof content === 'string') return content;
  if (Array.isArray(content?.parts)) return content.parts.filter(Boolean).join('\n');
  return content ? JSON.stringify(content) : '';
}

export function toMarkdown(conversation) {
  const lines = [`# ${conversation.title || 'Untitled conversation'}`, '', `- Platform: ${conversation.platform}`, `- Conversation ID: ${conversation.conversationId}`, ''];
  for (const message of conversation.messages) lines.push(`## ${message.author?.role || message.role || 'message'}`, '', messageText(message), '');
  return lines.join('\n');
}

export function exportConversation(conversation) {
  const identity = conversationIdentity(conversation);
  const manifest = { schemaVersion: EXPORT_STATE_SCHEMA, artifactVersion: 1, identity, platform: conversation.platform, conversationId: conversation.conversationId, titleAtExport: conversation.title, contentVersion: conversation.contentVersion, exportedAt: new Date().toISOString(), sourceUpdatedAt: conversation.updatedAt || null, representations: ['json', 'markdown'], attachmentManifest: conversation.attachments };
  return { identity, contentVersion: conversation.contentVersion, json: JSON.stringify({ ...conversation, identity }, null, 2), markdown: toMarkdown(conversation), manifest };
}
