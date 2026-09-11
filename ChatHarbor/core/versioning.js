const VERSION_SCHEMA = 'chatharbor-content-v1';

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value ?? null);
}

function digest(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++) { hash ^= text.charCodeAt(i); hash = Math.imul(hash, 16777619); }
  return `fp:${(hash >>> 0).toString(16).padStart(8, '0')}`;
}

export function canonicalContent(conversation) {
  return { messages: (conversation.messages || []).map(message => ({ messageId: message.messageId || null, parentId: message.parentId || null, role: message.role || null, contentType: message.contentType || null, content: message.content || '', createdAt: message.createdAt || null, updatedAt: message.updatedAt || null, attachments: message.attachments || [] })) };
}

export function fingerprintContent(conversation) { return digest(`${VERSION_SCHEMA}:${stable(canonicalContent(conversation))}`); }

export function observeContentVersion(conversation, capabilities = {}) {
  if (capabilities.contentRevision && conversation.contentVersion) return { value: String(conversation.contentVersion), source: 'native', confidence: 'platform' };
  if (conversation.messages?.length) return { value: fingerprintContent(conversation), source: 'canonical-message-fingerprint', confidence: 'derived' };
  return { value: null, source: 'unknown', confidence: 'unknown' };
}
