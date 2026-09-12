import { conversationIdentity } from '../models/conversation.js';
import { EXPORT_STATE_SCHEMA } from '../core/export-state.js';
import { observeContentVersion } from '../core/versioning.js';

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

export function buildExportManifest(conversation, { capabilities = {}, artifactId = null, exportedAt = new Date().toISOString() } = {}) {
  const identity = conversationIdentity(conversation);
  const observed = observeContentVersion(conversation, capabilities);
  const contentVersion = observed.value;
  const resolvedArtifactId = artifactId || (contentVersion != null ? `${identity}#${contentVersion}` : `${identity}#artifact-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  return { schemaVersion: EXPORT_STATE_SCHEMA, artifactVersion: 1, artifactId: resolvedArtifactId, identity, platform: conversation.platform, conversationId: conversation.conversationId, titleAtExport: conversation.title, contentVersion, contentVersionSource: observed.source, exportedAt, sourceUpdatedAt: conversation.updatedAt || null, representations: ['json', 'markdown'], artifactRefs: [resolvedArtifactId], attachmentManifest: conversation.attachments };
}

export function exportConversation(conversation, { capabilities = {}, artifactId = null } = {}) {
  const identity = conversationIdentity(conversation);
  const manifest = buildExportManifest(conversation, { capabilities, artifactId });
  return { identity, artifactId: manifest.artifactId, contentVersion: manifest.contentVersion, json: JSON.stringify({ ...conversation, identity, contentVersion: manifest.contentVersion }, null, 2), markdown: toMarkdown(conversation), manifest };
}
