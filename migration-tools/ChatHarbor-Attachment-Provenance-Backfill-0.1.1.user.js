// ==UserScript==
// @name         ChatHarbor Attachment Provenance Backfill
// @name:zh-CN   ChatHarbor 附件来源补全
// @version      0.1.1
// @description  Auditable local provenance reconstruction for ChatHarbor attachments/failures, with explicit dry-run-first Manifest backfill and optional online complement for unresolved failures only.
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @grant        none
// ==/UserScript==

(function () {
'use strict';

const V = '0.1.1';
const DB = 'chatharbor-directory-handle-v1';
const STORE = 'handles';
const KEY = 'chatgpt-default';
const MANIFEST = 'ChatHarbor_manifest.json';
const ONLINE_DELAY_MIN_MS = 900;
const ONLINE_DELAY_JITTER_MS = 500;

let accessToken = null;
const capturedWorkspaceIds = new Set();
let lastAudit = null;

// Capture account/token opportunistically. The tool remains fully useful without this;
// online complement is optional and explicitly user-triggered.
(function interceptNetwork() {
    const rawFetch = window.fetch;
    window.fetch = async function (resource, options) {
        tryCaptureToken(options?.headers);
        const h = options?.headers;
        const account = h instanceof Headers ? h.get('ChatGPT-Account-Id') : h?.['ChatGPT-Account-Id'];
        if (account) capturedWorkspaceIds.add(account);
        return rawFetch.apply(this, arguments);
    };

    const rawOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function () {
        this.addEventListener('readystatechange', () => {
            if (this.readyState !== 4) return;
            try {
                tryCaptureToken(this.getRequestHeader('Authorization'));
                const id = this.getRequestHeader('ChatGPT-Account-Id');
                if (id) capturedWorkspaceIds.add(id);
            } catch (_) {}
        });
        return rawOpen.apply(this, arguments);
    };
})();

function tryCaptureToken(header) {
    if (!header) return;
    const h = typeof header === 'string'
        ? header
        : header instanceof Headers
            ? header.get('Authorization')
            : (header.Authorization || header.authorization);
    if (h?.startsWith('Bearer ')) {
        const token = h.slice(7);
        if (token && token.toLowerCase() !== 'dummy') accessToken = token;
    }
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const splitPath = p => String(p || '').split('/').filter(Boolean);
const inc = (map, key, n = 1) => map.set(key, (map.get(key) || 0) + n);
const safe = v => String(v ?? '').trim();

function localTimestamp(value = new Date()) {
    const d = value instanceof Date ? value : new Date(value);
    const pad = n => String(n).padStart(2, '0');
    const off = -d.getTimezoneOffset();
    const sign = off >= 0 ? '+' : '-';
    const oh = pad(Math.floor(Math.abs(off) / 60));
    const om = pad(Math.abs(off) % 60);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())} ${sign}${oh}:${om}`;
}

function normalizeError(error) {
    return safe(error).replace(/\s+/g, ' ').replace(/https?:\/\/\S+/gi, '<url>') || '<empty>';
}

function failureStage(error) {
    const s = normalizeError(error).toLowerCase();
    if (s.includes('metadata http')) return 'metadata';
    if (s.includes('download_url missing or expired')) return 'download_url';
    if (s.includes('binary http')) return 'binary';
    return 'other';
}

function sourceCategory(kind, ownerRole, signal = '') {
    const k = safe(kind).toLowerCase();
    const role = safe(ownerRole).toLowerCase();
    if (k === 'sandbox') return 'assistant_generated_deliverable';
    if (role === 'user') return 'user_upload';
    if (role === 'tool' && signal === 'generated_media') return 'generated_media';
    if (role === 'tool' || role === 'assistant') return 'assistant_asset';
    return 'unknown';
}

function sourceLabel(category) {
    return ({
        user_upload: '用户上传',
        assistant_generated_deliverable: 'ChatGPT生成交付文件',
        generated_media: '生成媒体',
        assistant_asset: 'Assistant文件资源',
        unknown: '未知'
    })[category] || category || '未知';
}

function resolutionLabel(origin) {
    return ({
        manifest_owner_role: 'Manifest已有来源',
        local_json: '本地JSON重建',
        online_detail: '在线详情补查',
        sandbox_channel_inference: 'sandbox通道推断',
        ambiguous: '匹配冲突',
        unknown: '未知'
    })[origin] || origin || '未知';
}

function extractFileId(pointer) {
    if (typeof pointer !== 'string') return null;
    const match = pointer.match(/file[-_][a-z0-9]+/i);
    return match ? match[0] : null;
}

function activeNodes(convData) {
    const mapping = convData?.mapping;
    if (!mapping || typeof mapping !== 'object') return [];
    const entries = Object.entries(mapping);
    if (!entries.length) return [];

    let currentNodeId = convData?.current_node;
    if (!currentNodeId || !mapping[currentNodeId]) {
        const leaves = entries
            .filter(([, node]) => !Array.isArray(node?.children) || node.children.length === 0)
            .sort(([, a], [, b]) => (Number(b?.message?.create_time) || 0) - (Number(a?.message?.create_time) || 0));
        currentNodeId = leaves[0]?.[0] || entries[entries.length - 1]?.[0];
    }

    const path = [];
    const visited = new Set();
    while (currentNodeId && !visited.has(currentNodeId)) {
        visited.add(currentNodeId);
        const node = mapping[currentNodeId];
        if (!node) break;
        path.push(node);
        currentNodeId = node.parent || null;
    }
    return path.reverse();
}

function collectProvenanceRefs(convData) {
    const refs = [];
    const dedupe = new Set();
    const add = ref => {
        const identity = ref.kind === 'sandbox'
            ? `sandbox:${ref.messageId || ''}:${ref.sandboxPath || ''}`
            : `file:${ref.fileId || ''}:${ref.messageId || ''}:${ref.signal || ''}`;
        if (!identity || dedupe.has(identity)) return;
        dedupe.add(identity);
        refs.push(ref);
    };

    for (const node of activeNodes(convData)) {
        const message = node?.message;
        if (!message) continue;
        const role = message.author?.role;
        if (!['user', 'assistant', 'tool'].includes(role)) continue;
        if (message.metadata?.is_visually_hidden_from_conversation) continue;

        if (role === 'user') {
            for (const attachment of message.metadata?.attachments || []) {
                const fileId = attachment?.id || attachment?.file_id;
                if (!fileId) continue;
                add({
                    kind: 'file',
                    fileId,
                    sandboxPath: null,
                    messageId: message.id || null,
                    name: attachment.name || fileId,
                    ownerRole: 'user',
                    sourceCategory: 'user_upload',
                    signal: 'user_metadata_attachment'
                });
            }
        }

        for (const part of message.content?.parts || []) {
            if (part && typeof part === 'object' && part.asset_pointer && /image|canvas|audio|video/i.test(part.content_type || '')) {
                const generatedToolMedia = role === 'tool' && Boolean(part.metadata?.dalle || part.metadata?.generation);
                if (role !== 'tool' || generatedToolMedia) {
                    const fileId = extractFileId(part.asset_pointer);
                    if (fileId) {
                        const signal = generatedToolMedia ? 'generated_media' : 'asset_pointer';
                        add({
                            kind: 'file',
                            fileId,
                            sandboxPath: null,
                            messageId: message.id || null,
                            name: generatedToolMedia ? 'generated_image' : (/image/i.test(part.content_type || '') ? 'image' : fileId),
                            ownerRole: role,
                            sourceCategory: sourceCategory('file', role, signal),
                            signal
                        });
                    }
                }
            }

            const text = typeof part === 'string' ? part : part?.text;
            if (role === 'assistant' && typeof text === 'string') {
                for (const match of text.matchAll(/\]\((sandbox:[^)]+)\)/gi)) {
                    const sandboxPath = match[1];
                    add({
                        kind: 'sandbox',
                        fileId: null,
                        sandboxPath,
                        messageId: message.id || null,
                        name: sandboxPath.split('/').pop() || 'generated_file',
                        ownerRole: 'assistant',
                        sourceCategory: 'assistant_generated_deliverable',
                        signal: 'assistant_sandbox_link'
                    });
                }
            }
        }
    }
    return refs;
}

function buildRefIndex(refs) {
    const fileByStrong = new Map();
    const fileById = new Map();
    const sandboxByStrong = new Map();

    const push = (map, key, ref) => {
        if (!key) return;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(ref);
    };

    for (const ref of refs) {
        if (ref.kind === 'sandbox') {
            push(sandboxByStrong, `${ref.messageId || ''}|${ref.sandboxPath || ''}`, ref);
        } else if (ref.fileId) {
            push(fileByStrong, `${ref.fileId}|${ref.messageId || ''}`, ref);
            push(fileById, ref.fileId, ref);
        }
    }
    return { fileByStrong, fileById, sandboxByStrong };
}

function stableUniqueResolution(refs) {
    if (!refs?.length) return null;
    const signatures = new Map();
    for (const ref of refs) {
        const sig = `${ref.ownerRole || ''}|${ref.sourceCategory || 'unknown'}`;
        if (!signatures.has(sig)) signatures.set(sig, ref);
    }
    if (signatures.size !== 1) {
        return { ownerRole: null, sourceCategory: 'unknown', origin: 'ambiguous', matchedRef: null };
    }
    const ref = [...signatures.values()][0];
    return {
        ownerRole: ref.ownerRole || null,
        sourceCategory: ref.sourceCategory || 'unknown',
        origin: 'local_json',
        matchedRef: ref
    };
}

function matchByIndex(item, index, origin = 'local_json') {
    const kind = itemKind(item);
    if (kind === 'sandbox') {
        const refs = index.sandboxByStrong.get(`${itemMessageId(item)}|${itemSandboxPath(item)}`) || [];
        const resolved = stableUniqueResolution(refs);
        if (resolved) return { ...resolved, origin: resolved.origin === 'ambiguous' ? 'ambiguous' : origin };
        // sandbox is itself a strong provenance signal even when old local JSON no longer carries the link.
        return {
            ownerRole: null,
            sourceCategory: 'assistant_generated_deliverable',
            origin: 'sandbox_channel_inference',
            matchedRef: null
        };
    }

    const fileId = itemFileId(item);
    if (!fileId) return { ownerRole: null, sourceCategory: 'unknown', origin: 'unknown', matchedRef: null };
    const msgId = itemMessageId(item);
    let refs = msgId ? (index.fileByStrong.get(`${fileId}|${msgId}`) || []) : [];
    if (!refs.length) refs = index.fileById.get(fileId) || [];
    const resolved = stableUniqueResolution(refs);
    if (!resolved) return { ownerRole: null, sourceCategory: 'unknown', origin: 'unknown', matchedRef: null };
    return { ...resolved, origin: resolved.origin === 'ambiguous' ? 'ambiguous' : origin };
}

function itemKind(item) {
    return (item?.kind === 'sandbox' || item?.sandbox_path || item?.source_sandbox_path) ? 'sandbox' : 'file';
}
function itemFileId(item) { return item?.file_id || item?.source_file_id || item?.fileId || null; }
function itemSandboxPath(item) { return item?.sandbox_path || item?.source_sandbox_path || item?.sandboxPath || null; }
function itemMessageId(item) { return item?.message_id || item?.messageId || null; }

function manifestAssetResolution(asset, localIndex) {
    const kind = itemKind(asset);
    if (asset?.source_category) {
        return { ownerRole: asset.owner_role || null, sourceCategory: asset.source_category, origin: 'manifest_owner_role', matchedRef: null };
    }
    const local = matchByIndex(asset, localIndex, 'local_json');
    if (local.sourceCategory !== 'unknown') return local;
    if (asset?.owner_role) {
        const signal = asset.owner_role === 'tool' && asset?.is_image ? 'generated_media' : '';
        return {
            ownerRole: asset.owner_role,
            sourceCategory: sourceCategory(kind, asset.owner_role, signal),
            origin: 'manifest_owner_role',
            matchedRef: null
        };
    }
    return local;
}

function failureResolution(failure, localIndex) {
    return matchByIndex(failure, localIndex, 'local_json');
}

async function openDb() {
    if (indexedDB.databases) {
        const databases = await indexedDB.databases();
        if (!databases.some(db => db?.name === DB)) throw new Error(`IndexedDB 不存在：${DB}`);
    }
    return await new Promise((resolve, reject) => {
        const request = indexedDB.open(DB);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
        request.onupgradeneeded = () => {
            try { request.transaction.abort(); } catch (_) {}
            reject(new Error('拒绝创建或升级 ChatHarbor IndexedDB；审计工具只允许读取现有目录句柄。'));
        };
    });
}

async function rootHandle() {
    const db = await openDb();
    try {
        return await new Promise((resolve, reject) => {
            const tx = db.transaction(STORE, 'readonly');
            const request = tx.objectStore(STORE).get(KEY);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
        });
    } finally {
        db.close();
    }
}

async function ensureReadPermission(root) {
    if (!root) throw new Error('未找到 ChatHarbor 保存目录句柄。请先在 ChatHarbor 中选择/授权保存目录。');
    if (typeof root.queryPermission !== 'function') return;
    let permission = await root.queryPermission({ mode: 'read' });
    if (permission !== 'granted' && root.requestPermission) permission = await root.requestPermission({ mode: 'read' });
    if (permission !== 'granted') throw new Error(`目录读取权限不是 granted：${permission}`);
}

async function readText(root, relativePath) {
    const segments = splitPath(relativePath);
    if (!segments.length) throw new Error('relative path missing');
    let dir = root;
    for (let i = 0; i < segments.length - 1; i++) {
        dir = await dir.getDirectoryHandle(segments[i], { create: false });
    }
    const handle = await dir.getFileHandle(segments[segments.length - 1], { create: false });
    return await (await handle.getFile()).text();
}

async function ensureReadWritePermission(root) {
    if (!root) throw new Error('未找到 ChatHarbor 保存目录句柄。');
    if (typeof root.queryPermission !== 'function') return;
    let permission = await root.queryPermission({ mode: 'readwrite' });
    if (permission !== 'granted' && root.requestPermission) permission = await root.requestPermission({ mode: 'readwrite' });
    if (permission !== 'granted') throw new Error(`目录读写权限不是 granted：${permission}`);
}

async function writeText(root, relativePath, text) {
    const segments = splitPath(relativePath);
    if (!segments.length) throw new Error('relative path missing');
    let dir = root;
    for (let i = 0; i < segments.length - 1; i++) dir = await dir.getDirectoryHandle(segments[i], { create: true });
    const handle = await dir.getFileHandle(segments[segments.length - 1], { create: true });
    const writable = await handle.createWritable();
    try {
        await writable.write(text);
        await writable.close();
    } catch (error) {
        try { await writable.abort(); } catch (_) {}
        throw error;
    }
}

async function sha256Text(text) {
    const bytes = new TextEncoder().encode(String(text));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2,'0')).join('');
}

function backupStamp(date = new Date()) {
    const p = n => String(n).padStart(2,'0');
    return `${date.getFullYear()}${p(date.getMonth()+1)}${p(date.getDate())}_${p(date.getHours())}${p(date.getMinutes())}${p(date.getSeconds())}`;
}

function stripProvenanceForInvariant(manifest) {
    const copy = structuredClone(manifest);
    for (const record of Object.values(copy?.conversations || {})) {
        for (const asset of Array.isArray(record?.assets) ? record.assets : []) {
            delete asset.owner_role; delete asset.source_category; delete asset.reference_kind;
        }
        for (const failure of Array.isArray(record?.attachment_failures) ? record.attachment_failures : []) {
            delete failure.owner_role; delete failure.source_category; delete failure.reference_kind;
        }
    }
    return copy;
}

function newAudit(manifest, startedAt) {
    return {
        startedAt,
        finishedAt: null,
        generatedAt: null,
        manifest,
        manifestRecords: Object.entries(manifest?.conversations || {}),
        targetRecords: 0,
        localJsonRead: 0,
        localJsonErrors: [],
        successAssets: [],
        failures: [],
        unresolvedFailures: [],
        online: {
            attempted: false,
            startedAt: null,
            finishedAt: null,
            conversationCount: 0,
            fetched: 0,
            resolved: 0,
            errors: []
        },
        apply: {
            attempted: false,
            appliedAt: null,
            backupPath: null,
            updatedAssets: 0,
            updatedFailures: 0,
            conflicts: [],
            verified: false,
            beforeSha256: null,
            afterSha256: null
        },
        manifestRaw: null,
        manifestSha256: null
    };
}

async function runLocalAudit(progress) {
    const startedAt = new Date();
    const root = await rootHandle();
    await ensureReadPermission(root);
    const manifestRaw = await readText(root, MANIFEST);
    const manifest = JSON.parse(manifestRaw);
    const audit = newAudit(manifest, startedAt);
    audit.manifestRaw = manifestRaw;
    audit.manifestSha256 = await sha256Text(manifestRaw);

    const records = audit.manifestRecords.filter(([, record]) =>
        (Array.isArray(record?.assets) && record.assets.length > 0) ||
        (Array.isArray(record?.attachment_failures) && record.attachment_failures.length > 0)
    );
    audit.targetRecords = records.length;

    for (let i = 0; i < records.length; i++) {
        const [conversationId, record] = records[i];
        progress?.(`本地 Dry Run ${i + 1}/${records.length}`, record?.title || conversationId);
        let convData = null;
        let localIndex = buildRefIndex([]);
        try {
            if (!record?.json_path) throw new Error('json_path missing');
            convData = JSON.parse(await readText(root, record.json_path));
            localIndex = buildRefIndex(collectProvenanceRefs(convData));
            audit.localJsonRead++;
        } catch (error) {
            audit.localJsonErrors.push({
                conversation_id: conversationId,
                title: record?.title || '',
                error: error?.message || String(error)
            });
        }

        const recordAssets = Array.isArray(record?.assets) ? record.assets : [];
        for (let assetIndex = 0; assetIndex < recordAssets.length; assetIndex++) {
            const asset = recordAssets[assetIndex];
            const resolution = manifestAssetResolution(asset, localIndex);
            audit.successAssets.push({
                asset_index: assetIndex,
                conversation_id: conversationId,
                title: record?.title || '',
                name: asset?.name || '',
                kind: itemKind(asset),
                file_id: itemFileId(asset),
                sandbox_path: itemSandboxPath(asset),
                message_id: itemMessageId(asset),
                resolution
            });
        }

        const recordFailures = Array.isArray(record?.attachment_failures) ? record.attachment_failures : [];
        for (let failureIndex = 0; failureIndex < recordFailures.length; failureIndex++) {
            const failure = recordFailures[failureIndex];
            const resolution = failureResolution(failure, localIndex);
            const row = {
                failure_index: failureIndex,
                conversation_id: conversationId,
                title: record?.title || '',
                name: failure?.name || '',
                kind: itemKind(failure),
                file_id: itemFileId(failure),
                sandbox_path: itemSandboxPath(failure),
                message_id: itemMessageId(failure),
                error: normalizeError(failure?.error),
                stage: failureStage(failure?.error),
                localResolution: resolution,
                onlineResolution: null
            };
            audit.failures.push(row);
            if (resolution.sourceCategory === 'unknown') audit.unresolvedFailures.push(row);
        }
    }

    audit.finishedAt = new Date();
    audit.generatedAt = new Date();
    return audit;
}

function effectiveResolution(row) {
    return row.onlineResolution || row.localResolution || { ownerRole: null, sourceCategory: 'unknown', origin: 'unknown' };
}

function sortedCounts(map) {
    return [...map.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), 'zh-CN'));
}

function summarizeRows(rows, resolver) {
    const byKind = new Map(), bySource = new Map(), byOrigin = new Map();
    for (const row of rows) {
        const r = resolver(row);
        inc(byKind, row.kind || 'unknown');
        inc(bySource, r.sourceCategory || 'unknown');
        inc(byOrigin, r.origin || 'unknown');
    }
    return { byKind, bySource, byOrigin };
}

function crossSourceError(failures) {
    const map = new Map();
    for (const row of failures) {
        const source = effectiveResolution(row).sourceCategory || 'unknown';
        if (!map.has(source)) map.set(source, new Map());
        inc(map.get(source), row.error || '<empty>');
    }
    return map;
}

function reportText(audit) {
    audit.generatedAt = new Date();
    const L = [];
    const successSummary = summarizeRows(audit.successAssets, row => row.resolution);
    const failureSummary = summarizeRows(audit.failures, effectiveResolution);
    const errorCounts = new Map(), stageCounts = new Map();
    for (const row of audit.failures) {
        inc(errorCounts, row.error);
        inc(stageCounts, row.stage);
    }
    const unresolved = audit.failures.filter(row => effectiveResolution(row).sourceCategory === 'unknown');
    const locallyResolved = audit.failures.filter(row => row.localResolution?.sourceCategory !== 'unknown').length;
    const onlineResolved = audit.failures.filter(row => row.onlineResolution?.sourceCategory && row.onlineResolution.sourceCategory !== 'unknown').length;
    const unresolvedConvs = new Map();
    for (const row of unresolved) {
        const k = row.conversation_id;
        if (!unresolvedConvs.has(k)) unresolvedConvs.set(k, { title: row.title, count: 0 });
        unresolvedConvs.get(k).count++;
    }

    L.push(
        `ChatHarbor Attachment Provenance Backfill Audit v${V}`,
        `Mode: ${audit.apply?.attempted ? 'DRY RUN + EXPLICIT APPLY' : 'READ-ONLY / DRY RUN'}`,
        '',
        '【审计信息】',
        `开始时间: ${localTimestamp(audit.startedAt)}`,
        `完成时间: ${localTimestamp(audit.finishedAt || new Date())}`,
        `报告生成: ${localTimestamp(audit.generatedAt)}`,
        `写入 Manifest: ${audit.apply?.attempted ? (audit.apply.verified ? '是（显式 Apply，已验证）' : '尝试过但未验证') : '否'}`,
        '附件下载: 否',
        '默认网络访问: 否',
        `在线补查: ${audit.online.attempted ? '已执行（仅 unresolved failure conversations）' : '未执行'}`,
        '',
        '【本地扫描】',
        `Manifest conversations: ${audit.manifestRecords.length}`,
        `含成功附件或失败记录的会话: ${audit.targetRecords}`,
        `成功读取本地 JSON: ${audit.localJsonRead}`,
        `本地 JSON 读取错误: ${audit.localJsonErrors.length}`,
        '',
        '【已下载附件来源】',
        `成功附件记录: ${audit.successAssets.length}`
    );
    for (const [k, v] of sortedCounts(successSummary.bySource)) L.push(`${sourceLabel(k)}: ${v}`);
    L.push('', '来源证据:');
    for (const [k, v] of sortedCounts(successSummary.byOrigin)) L.push(`${resolutionLabel(k)}: ${v}`);

    L.push(
        '',
        '【历史失败附件】',
        `失败记录总数: ${audit.failures.length}`,
        `本地成功识别来源: ${locallyResolved}`,
        `在线补查新增识别: ${onlineResolved}`,
        `仍为 Unknown: ${unresolved.length}`,
        `涉及 Unknown 会话: ${unresolvedConvs.size}`,
        '',
        '按资源通道:'
    );
    for (const [k, v] of sortedCounts(failureSummary.byKind)) L.push(`${k}: ${v}`);
    L.push('', '按来源:');
    for (const [k, v] of sortedCounts(failureSummary.bySource)) L.push(`${sourceLabel(k)}: ${v}`);
    L.push('', '按来源证据:');
    for (const [k, v] of sortedCounts(failureSummary.byOrigin)) L.push(`${resolutionLabel(k)}: ${v}`);
    L.push('', '按失败阶段:');
    for (const [k, v] of sortedCounts(stageCounts)) L.push(`${k}: ${v}`);
    L.push('', '按失败原因:');
    for (const [k, v] of sortedCounts(errorCounts)) L.push(`${v} × ${k}`);

    L.push('', '【来源 × 失败原因】');
    const cross = crossSourceError(audit.failures);
    for (const [source, errors] of [...cross.entries()].sort((a, b) => sourceLabel(a[0]).localeCompare(sourceLabel(b[0]), 'zh-CN'))) {
        L.push(`${sourceLabel(source)}:`);
        for (const [error, count] of sortedCounts(errors)) L.push(`  ${count} × ${error}`);
    }

    L.push('', '【仍为 Unknown 的失败记录】');
    if (!unresolved.length) {
        L.push('无');
    } else {
        for (const [id, info] of unresolvedConvs) {
            L.push(`${info.count} | ${info.title || '(无标题)'} | ${id}`);
            for (const row of unresolved.filter(x => x.conversation_id === id)) {
                const identity = row.kind === 'sandbox' ? row.sandbox_path : row.file_id;
                L.push(`    ${row.kind} | ${row.name || '-'} | ${identity || '-'} | ${row.error}`);
            }
        }
    }

    if (audit.localJsonErrors.length) {
        L.push('', '【本地 JSON 读取错误】');
        for (const row of audit.localJsonErrors) L.push(`${row.title || '(无标题)'} | ${row.conversation_id} | ${row.error}`);
    }

    if (audit.online.attempted) {
        L.push(
            '',
            '【在线补查】',
            `开始时间: ${localTimestamp(audit.online.startedAt)}`,
            `完成时间: ${localTimestamp(audit.online.finishedAt || new Date())}`,
            `计划补查会话: ${audit.online.conversationCount}`,
            `成功获取详情: ${audit.online.fetched}`,
            `新增识别失败记录: ${audit.online.resolved}`,
            `在线错误: ${audit.online.errors.length}`
        );
        for (const row of audit.online.errors) L.push(`${row.conversation_id} | ${row.title || ''} | ${row.error}`);
    }

    if (audit.apply?.attempted) {
        L.push(
            '',
            '【来源补全 Apply】',
            `执行时间: ${localTimestamp(audit.apply.appliedAt || new Date())}`,
            `备份 Manifest: ${audit.apply.backupPath || '-'}`,
            `补全成功附件记录: ${audit.apply.updatedAssets}`,
            `补全失败附件记录: ${audit.apply.updatedFailures}`,
            `冲突（未覆盖）: ${audit.apply.conflicts.length}`,
            `写回验证: ${audit.apply.verified ? 'PASS' : 'FAIL/未完成'}`,
            `写回前 SHA-256: ${audit.apply.beforeSha256 || '-'}`,
            `写回后 SHA-256: ${audit.apply.afterSha256 || '-'}`
        );
        for (const conflict of audit.apply.conflicts.slice(0, 20)) L.push(`  CONFLICT | ${conflict}`);
        if (audit.apply.conflicts.length > 20) L.push(`  ...另有 ${audit.apply.conflicts.length - 20} 条冲突`);
    }

    L.push(
        '',
        '【边界】',
        '1. file 不等于用户上传；来源必须结合 owner role / 本地或在线会话证据判断。',
        '2. sandbox 高置信度归类为 ChatGPT生成交付文件；这只是来源分类，不代表资源永久不可恢复。',
        '3. Unknown 保持 Unknown，不为填满字段进行猜测。',
        '4. Dry Run 不修改 Manifest；只有用户显式点击 Apply 后才补 provenance 字段，并先备份原 Manifest。',
        '5. 在线补查若执行，只读取本地无法判定的失败记录所在会话详情。',
        '',
        audit.apply?.attempted ? 'APPLY SCOPE - provenance fields only; no attachment retry/download.' : 'READ ONLY - no archive write, no Manifest write, no attachment retry/download.'
    );
    return L.join('\n');
}

function getOaiDeviceId() {
    const match = document.cookie.match(/oai-did=([^;]+)/);
    return match ? match[1] : null;
}

function detectAllWorkspaceIds() {
    const found = new Set(capturedWorkspaceIds);
    try {
        const el = document.getElementById('__NEXT_DATA__');
        if (el?.textContent) {
            const data = JSON.parse(el.textContent);
            const accounts = data?.props?.pageProps?.user?.accounts;
            if (accounts) {
                Object.values(accounts).forEach(acc => {
                    if (acc?.account?.id) found.add(acc.account.id);
                });
            }
        }
    } catch (_) {}
    return [...found];
}

function resolveWorkspaceId() {
    const match = document.cookie.match(/(?:^|; )_account=([^;]+)/);
    if (match?.[1]) return match[1];
    return detectAllWorkspaceIds()[0] || null;
}

async function ensureAccessToken() {
    if (accessToken) return accessToken;
    try {
        const response = await fetch('/api/auth/session?unstable_client=true', { credentials: 'include' });
        const session = await response.json();
        if (session?.accessToken) {
            accessToken = session.accessToken;
            return accessToken;
        }
    } catch (_) {}
    throw new Error('无法获取 Access Token。请刷新 ChatGPT 页面或打开任意一个对话后再试。');
}

async function fetchConversationDetail(conversationId) {
    await ensureAccessToken();
    const deviceId = getOaiDeviceId();
    if (!deviceId) throw new Error('无法获取 oai-device-id。');
    const headers = {
        'Authorization': `Bearer ${accessToken}`,
        'oai-device-id': deviceId
    };
    const workspaceId = resolveWorkspaceId();
    if (workspaceId) headers['ChatGPT-Account-Id'] = workspaceId;
    const response = await fetch(`/backend-api/conversation/${encodeURIComponent(conversationId)}`, {
        credentials: 'include',
        headers
    });
    if (!response.ok) throw new Error(`conversation detail HTTP ${response.status}`);
    return await response.json();
}

async function runOnlineComplement(audit, progress) {
    const unresolvedBefore = audit.failures.filter(row => effectiveResolution(row).sourceCategory === 'unknown');
    const byConversation = new Map();
    for (const row of unresolvedBefore) {
        if (!byConversation.has(row.conversation_id)) byConversation.set(row.conversation_id, []);
        byConversation.get(row.conversation_id).push(row);
    }
    const entries = [...byConversation.entries()];
    if (!entries.length) return audit;

    const ok = confirm(
        `只读在线补查将读取 ${entries.length} 个本地仍无法判定的失败会话详情。\n\n` +
        '不会下载附件，不会重试历史失败，不会修改 Manifest。\n\n是否继续？'
    );
    if (!ok) return audit;

    audit.online.attempted = true;
    audit.online.startedAt = new Date();
    audit.online.conversationCount = entries.length;

    for (let i = 0; i < entries.length; i++) {
        const [conversationId, rows] = entries[i];
        progress?.(`在线补查 ${i + 1}/${entries.length}`, rows[0]?.title || conversationId);
        try {
            const convData = await fetchConversationDetail(conversationId);
            audit.online.fetched++;
            const index = buildRefIndex(collectProvenanceRefs(convData));
            for (const row of rows) {
                const resolved = matchByIndex(row, index, 'online_detail');
                if (resolved.sourceCategory !== 'unknown') {
                    row.onlineResolution = resolved;
                    audit.online.resolved++;
                }
            }
        } catch (error) {
            audit.online.errors.push({
                conversation_id: conversationId,
                title: rows[0]?.title || '',
                error: error?.message || String(error)
            });
            if (/429/.test(String(error?.message || error))) break;
        }
        if (i < entries.length - 1) await sleep(ONLINE_DELAY_MIN_MS + Math.random() * ONLINE_DELAY_JITTER_MS);
    }
    audit.online.finishedAt = new Date();
    audit.generatedAt = new Date();
    return audit;
}

async function applyProvenanceBackfill(audit, progress) {
    if (!audit) throw new Error('没有可应用的 Dry Run 结果。');
    if (audit.apply?.attempted) throw new Error('本次审计已经执行过 Apply。请重新运行 Dry Run 后再操作。');
    const unresolved = audit.failures.filter(row => effectiveResolution(row).sourceCategory === 'unknown');
    if (unresolved.length) throw new Error(`仍有 ${unresolved.length} 条 Unknown。请先保留 Unknown 或完成必要补查，不自动猜测。`);

    const root = await rootHandle();
    await ensureReadWritePermission(root);
    progress?.('Apply 前检查', '确认 Manifest 自 Dry Run 后没有变化……');
    const currentRaw = await readText(root, MANIFEST);
    const currentSha = await sha256Text(currentRaw);
    if (currentSha !== audit.manifestSha256) {
        throw new Error('Manifest 在 Dry Run 后已经发生变化。为避免覆盖新的同步结果，本次 Apply 已停止；请重新运行 Dry Run。');
    }
    const manifest = JSON.parse(currentRaw);
    const invariantBefore = JSON.stringify(stripProvenanceForInvariant(manifest));
    const conflicts = [];
    let updatedAssets = 0, updatedFailures = 0;

    const fill = (target, row, resolution, label) => {
        if (!target || !resolution || resolution.sourceCategory === 'unknown') return false;
        const desired = {
            owner_role: resolution.ownerRole || null,
            source_category: resolution.sourceCategory,
            reference_kind: row.kind || itemKind(row)
        };
        let changed = false;
        for (const [field, value] of Object.entries(desired)) {
            if (value == null) continue;
            if (target[field] == null || target[field] === '') {
                target[field] = value; changed = true;
            } else if (String(target[field]) !== String(value)) {
                conflicts.push(`${label} | ${field} existing=${target[field]} resolved=${value}`);
            }
        }
        return changed;
    };

    for (const row of audit.successAssets) {
        const record = manifest?.conversations?.[row.conversation_id];
        const target = record?.assets?.[row.asset_index];
        if (fill(target, row, row.resolution, `asset ${row.conversation_id}#${row.asset_index}`)) updatedAssets++;
    }
    for (const row of audit.failures) {
        const record = manifest?.conversations?.[row.conversation_id];
        const target = record?.attachment_failures?.[row.failure_index];
        if (fill(target, row, effectiveResolution(row), `failure ${row.conversation_id}#${row.failure_index}`)) updatedFailures++;
    }

    const invariantAfter = JSON.stringify(stripProvenanceForInvariant(manifest));
    if (invariantAfter !== invariantBefore) throw new Error('安全检查失败：除 provenance 外的 Manifest 内容发生变化。Apply 已停止，未写入。');

    const backupPath = `ChatHarbor_manifest.pre_attachment_provenance_backfill_${backupStamp()}.json`;
    progress?.('创建备份', backupPath);
    await writeText(root, backupPath, currentRaw);
    const backupCheck = await readText(root, backupPath);
    if (await sha256Text(backupCheck) !== currentSha) throw new Error('备份 Manifest 校验失败；正式 Manifest 未修改。');

    const newRaw = JSON.stringify(manifest, null, 2) + '\n';
    progress?.('写入 provenance', `成功附件候选 ${updatedAssets} · 失败附件候选 ${updatedFailures}`);
    await writeText(root, MANIFEST, newRaw);
    const verifyRaw = await readText(root, MANIFEST);
    const verifyManifest = JSON.parse(verifyRaw);
    if (JSON.stringify(stripProvenanceForInvariant(verifyManifest)) !== invariantBefore) {
        throw new Error(`写回验证失败。已保留备份 ${backupPath}；请停止使用并恢复备份。`);
    }

    audit.apply.attempted = true;
    audit.apply.appliedAt = new Date();
    audit.apply.backupPath = backupPath;
    audit.apply.updatedAssets = updatedAssets;
    audit.apply.updatedFailures = updatedFailures;
    audit.apply.conflicts = conflicts;
    audit.apply.verified = true;
    audit.apply.beforeSha256 = currentSha;
    audit.apply.afterSha256 = await sha256Text(verifyRaw);
    audit.generatedAt = new Date();
    return audit;
}

function downloadText(filename, text) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function overlay() {
    document.getElementById('ch-apba-overlay')?.remove();
    const o = document.createElement('div');
    o.id = 'ch-apba-overlay';
    o.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.42);display:flex;align-items:center;justify-content:center;padding:24px';
    const c = document.createElement('div');
    c.style.cssText = 'width:min(1180px,97vw);height:min(860px,94vh);background:#fff;color:#111827;border-radius:12px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 22px 60px rgba(0,0,0,.25)';
    const h = document.createElement('div');
    h.style.cssText = 'display:flex;gap:8px;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #ddd';
    const title = document.createElement('strong');
    title.textContent = `ChatHarbor 附件来源补全 v${V}`;
    const actions = document.createElement('div');
    const online = document.createElement('button');
    const apply = document.createElement('button');
    const copy = document.createElement('button');
    const save = document.createElement('button');
    const close = document.createElement('button');
    online.textContent = '在线补查 Unknown';
    apply.textContent = '应用来源补全';
    copy.textContent = '复制完整报告';
    save.textContent = '下载报告';
    close.textContent = '关闭';
    for (const b of [online, apply, copy, save, close]) b.style.cssText = 'margin-left:6px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:7px;background:#f8fafc;cursor:pointer';
    online.disabled = true;
    apply.disabled = true;
    apply.title = '显式写回 provenance 字段；执行前自动备份 Manifest，不下载附件、不改变同步状态。';
    close.onclick = () => o.remove();
    actions.append(online, apply, copy, save, close);
    h.append(title, actions);

    const status = document.createElement('div');
    status.style.cssText = 'padding:8px 14px;border-bottom:1px solid #e5e7eb;background:#f8fafc;font:12px/1.4 ui-monospace,Consolas,monospace;white-space:pre-wrap';
    status.textContent = '准备读取本地归档（只读）……';
    const body = document.createElement('pre');
    body.style.cssText = 'margin:0;padding:14px;overflow:auto;white-space:pre-wrap;word-break:break-word;flex:1;font:12px/1.5 ui-monospace,Consolas,monospace;background:#fff';
    c.append(h, status, body);
    o.append(c);
    document.body.append(o);
    return { o, body, status, online, apply, copy, save };
}

async function run(btn) {
    const old = btn.textContent;
    btn.disabled = true;
    btn.textContent = '审计中…';
    const U = overlay();
    let text = '';
    const render = () => {
        text = lastAudit ? reportText(lastAudit) : text;
        U.body.textContent = text;
        const unresolved = lastAudit ? lastAudit.failures.filter(row => effectiveResolution(row).sourceCategory === 'unknown') : [];
        const convs = new Set(unresolved.map(row => row.conversation_id));
        U.online.disabled = !lastAudit || convs.size === 0 || lastAudit.online.attempted;
        U.online.textContent = convs.size ? `在线补查 Unknown（${convs.size}会话）` : '在线补查 Unknown（0）';
        U.apply.disabled = !lastAudit || unresolved.length > 0 || Boolean(lastAudit.apply?.attempted);
        U.apply.textContent = lastAudit?.apply?.attempted ? '来源补全已应用' : `应用来源补全（${lastAudit ? lastAudit.failures.length : 0}失败记录）`;
    };

    U.copy.onclick = async () => {
        try {
            await navigator.clipboard.writeText(text);
            U.copy.textContent = '已复制';
            setTimeout(() => U.copy.textContent = '复制完整报告', 1000);
        } catch (_) {}
    };
    U.save.onclick = () => {
        const stamp = new Date().toISOString().replace(/[:.]/g, '-');
        downloadText(`ChatHarbor_Attachment_Provenance_Audit_${stamp}.txt`, text);
    };
    U.apply.onclick = async () => {
        if (!lastAudit) return;
        const ok = confirm(
            '即将把 Dry Run 已确认的 provenance（owner_role / source_category / reference_kind）补入 Manifest。\n\n' +
            '执行前会创建原 Manifest 备份；不会下载附件，不会修改 attachment_state、失败原因或同步状态。\n\n是否继续？'
        );
        if (!ok) return;
        U.apply.disabled = true;
        try {
            await applyProvenanceBackfill(lastAudit, (phase, detail) => { U.status.textContent = `${phase}\n${detail || ''}`; });
            render();
            U.status.textContent = `来源补全 Apply 完成并验证通过。备份：${lastAudit.apply.backupPath}`;
        } catch (error) {
            U.status.textContent = `Apply 停止：${error?.message || error}`;
            render();
        }
    };

    U.online.onclick = async () => {
        U.online.disabled = true;
        try {
            await runOnlineComplement(lastAudit, (phase, detail) => {
                U.status.textContent = `${phase}\n${detail || ''}`;
            });
            render();
            U.status.textContent = '在线补查完成。仍为只读；未下载附件，未修改 Manifest。';
        } catch (error) {
            U.status.textContent = `在线补查停止：${error?.message || error}`;
            render();
        }
    };

    try {
        lastAudit = await runLocalAudit((phase, detail) => {
            U.status.textContent = `${phase}\n${detail || ''}`;
        });
        render();
        U.status.textContent = '本地 Dry Run 完成。未联网、未写文件、未修改 Manifest。';
    } catch (error) {
        text = `ChatHarbor Attachment Provenance Backfill v${V}\nStage: AUDIT STOPPED\n\n${error?.stack || error}\n\nREAD ONLY`;
        U.body.textContent = text;
        U.body.style.background = '#fef2f2';
        U.status.textContent = '审计停止。';
    } finally {
        btn.disabled = false;
        btn.textContent = old;
    }
}

function install() {
    if (document.getElementById('ch-apba-btn')) return;
    const b = document.createElement('button');
    b.id = 'ch-apba-btn';
    b.textContent = 'CH 附件来源补全';
    b.title = '先本地 Dry Run；只有你明确点击 Apply 后才补 provenance，执行前自动备份 Manifest';
    b.style.cssText = 'position:fixed;left:16px;bottom:92px;z-index:2147483646;padding:8px 11px;border:1px solid #475569;border-radius:8px;background:#f8fafc;color:#334155;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.12)';
    b.onclick = () => run(b);
    document.body.appendChild(b);
}

document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', install, { once: true })
    : install();
})();
