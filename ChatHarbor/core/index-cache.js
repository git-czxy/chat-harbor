import { conversationIdentity } from '../models/conversation.js';

export const INDEX_SNAPSHOT_SCHEMA = 'chatharbor-index-v1';

export function firstPageProbe(items) {
  return (items || []).map(item => ({ conversationId: item.conversationId, updatedAt: item.updatedAt ?? null }));
}

export function sameProbe(left, right) {
  return JSON.stringify(left || []) === JSON.stringify(right || []);
}

export function readIndexSnapshot(storage, { platform, scopeKey }) {
  try {
    const snapshot = storage?.read?.();
    if (!snapshot || snapshot.schemaVersion !== INDEX_SNAPSHOT_SCHEMA || snapshot.platform !== platform || snapshot.scopeKey !== scopeKey || !Array.isArray(snapshot.conversations) || !Array.isArray(snapshot.probe)) return null;
    if (snapshot.conversations.some(item => !item?.conversationId || item.platform !== platform)) return null;
    return snapshot;
  } catch { return null; }
}

export async function loadIndexedConversations({ adapter, storage, scopeKey = 'default', pageSize = 20, maxPages = 1000, force = false, now = () => new Date().toISOString(), onProgress = () => {} }) {
  const cached = force ? null : readIndexSnapshot(storage, { platform: adapter.platform, scopeKey });
  onProgress({ status: 'probing' });
  const first = await adapter.listPage({ offset: 0, limit: pageSize });
  const probe = firstPageProbe(first.items);
  if (cached && sameProbe(probe, cached.probe)) return { conversations: cached.conversations, source: 'validated-cache', probe };
  const deduped = new Map();
  let page = first;
  let offset = 0;
  for (let pageNumber = 0; pageNumber < maxPages; pageNumber++) {
    const items = page.items || [];
    for (const item of items) deduped.set(conversationIdentity(item), item);
    onProgress({ status: 'syncing', page: pageNumber + 1, count: deduped.size });
    offset = Number.isInteger(page.offset) ? page.offset + items.length : offset + items.length;
    const total = Number.isInteger(page.total) ? page.total : null;
    if (!items.length || (total !== null && offset >= total) || (total === null && items.length < pageSize)) break;
    if (pageNumber + 1 >= maxPages) throw new Error('Conversation index max-page guard reached');
    page = await adapter.listPage({ offset, limit: pageSize });
  }
  const conversations = [...deduped.values()];
  const snapshot = { schemaVersion: INDEX_SNAPSHOT_SCHEMA, platform: adapter.platform, scopeKey, verifiedAt: now(), conversations, probe };
  storage?.write?.(snapshot);
  return { conversations, source: force ? 'full-refresh' : cached ? 'refreshed-cache' : 'cache-miss', probe };
}
