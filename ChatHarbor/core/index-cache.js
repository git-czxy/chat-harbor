import { conversationIdentity } from '../models/conversation.js';

export const INDEX_SNAPSHOT_SCHEMA = 'chatharbor-index-v2';

export function firstPageProbe(items) {
  return (items || []).map(item => ({ conversationId: item.conversationId, updatedAt: item.updatedAt ?? null }));
}

export function partitionProbe(page) {
  return { total: Number.isInteger(page?.total) ? page.total : null, items: firstPageProbe(page?.items) };
}

export function compoundProbe(unarchived, archived) {
  return { unarchived: partitionProbe(unarchived), archived: partitionProbe(archived) };
}

export function sameProbe(left, right) {
  return JSON.stringify(left || null) === JSON.stringify(right || null);
}

export function readIndexSnapshot(storage, { platform, scopeKey }) {
  try {
    const snapshot = storage?.read?.();
    if (!snapshot || snapshot.schemaVersion !== INDEX_SNAPSHOT_SCHEMA || snapshot.platform !== platform || snapshot.scopeKey !== scopeKey || !Array.isArray(snapshot.conversations) || !snapshot.probe?.unarchived || !snapshot.probe?.archived) return null;
    if (snapshot.conversations.some(item => !item?.conversationId || item.platform !== platform)) return null;
    return snapshot;
  } catch { return null; }
}

async function loadPartition({ adapter, archived, firstPage, pageSize, maxPages, onProgress, deduped }) {
  let page = firstPage || await adapter.listPage({ offset: 0, limit: pageSize, archived });
  const initialPage = page;
  let offset = 0;
  for (let pageNumber = 0; pageNumber < maxPages; pageNumber++) {
    const items = page.items || [];
    for (const item of items) deduped.set(conversationIdentity(item), item);
    onProgress({ status: 'syncing', archived, page: pageNumber + 1, count: deduped.size });
    offset = Number.isInteger(page.offset) ? page.offset + items.length : offset + items.length;
    const total = Number.isInteger(page.total) ? page.total : null;
    if (!items.length || (total !== null && offset >= total) || (total === null && items.length < pageSize)) break;
    if (pageNumber + 1 >= maxPages) throw new Error('Conversation index max-page guard reached');
    page = await adapter.listPage({ offset, limit: pageSize, archived });
  }
  return initialPage;
}

export async function loadIndexedConversations({ adapter, storage, scopeKey = 'default', pageSize = 20, maxPages = 1000, force = false, now = () => new Date().toISOString(), onProgress = () => {} }) {
  const cached = force ? null : readIndexSnapshot(storage, { platform: adapter.platform, scopeKey });
  let unarchivedFirst;
  let archivedFirst;
  if (cached) {
    onProgress({ status: 'probing', archived: false });
    unarchivedFirst = await adapter.listPage({ offset: 0, limit: pageSize, archived: false });
    onProgress({ status: 'probing', archived: true });
    archivedFirst = await adapter.listPage({ offset: 0, limit: pageSize, archived: true });
    const probe = compoundProbe(unarchivedFirst, archivedFirst);
    if (sameProbe(probe, cached.probe)) return { conversations: cached.conversations, source: 'validated-cache', probe };
  }
  const deduped = new Map();
  unarchivedFirst = await loadPartition({ adapter, archived: false, firstPage: unarchivedFirst, pageSize, maxPages, onProgress, deduped });
  archivedFirst = await loadPartition({ adapter, archived: true, firstPage: archivedFirst, pageSize, maxPages, onProgress, deduped });
  const conversations = [...deduped.values()];
  const probe = compoundProbe(unarchivedFirst, archivedFirst);
  const snapshot = { schemaVersion: INDEX_SNAPSHOT_SCHEMA, platform: adapter.platform, scopeKey, verifiedAt: now(), conversations, probe };
  storage?.write?.(snapshot);
  return { conversations, source: force ? 'full-refresh' : cached ? 'refreshed-cache' : 'cache-miss', probe };
}
