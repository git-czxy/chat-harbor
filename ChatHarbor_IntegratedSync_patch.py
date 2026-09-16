#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_GIT_BLOB = "3a5dfe6a696e03db7028232d45b136104e67b51f"

def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

if len(sys.argv) < 2:
    print("Usage: python ChatHarbor_IntegratedSync_patch.py <Tampermonkey.js> [output.user.js]")
    raise SystemExit(2)

src = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("ChatHarbor-IntegratedSync.user.js")
raw = src.read_bytes()

actual_blob = git_blob_sha1(raw)
if actual_blob != EXPECTED_GIT_BLOB:
    raise SystemExit(
        "Baseline mismatch.\n"
        f"Expected git blob: {EXPECTED_GIT_BLOB}\n"
        f"Actual git blob:   {actual_blob}\n"
        "Refusing to patch a different upstream version."
    )

text = raw.decode("utf-8")

text = text.replace(
    "// @name         ChatGPT Universal Exporter (Markdown Support)\n"
    "// @version      1.5.0\n"
    "// @description  Export ChatGPT conversations with visible uploads and generated files as JSON+Markdown ZIP backups.\n"
    "// @author       huhu\n",
    "// @name         ChatHarbor Integrated Sync (Clean Lineage)\n"
    "// @name:zh-CN   ChatHarbor 集成同步版（干净来源）\n"
    "// @version      0.0.14.0\n"
    "// @description  ChatHarbor local-first ChatGPT conversation sync with safe incremental updates, attachment recovery, conservative request pacing, and simple user-facing status.\n"
    "// @description:zh-CN ChatHarbor 本地优先的 ChatGPT 对话同步：安全增量更新、附件补齐、保守请求节奏和简明状态展示。\n"
    "// @author       huhu; ChatHarbor contributors\n"
)

anchor = "    async function exportConversations(options = {}) {\n"
if anchor not in text:
    raise SystemExit("Insertion anchor not found: exportConversations")

directory_writer = r'''
    // ======================== ChatHarbor Gate 3: Manifest + Identity ========================
    // Clean-lineage implementation on huhusmang/ChatGPT-Exporter.
    //
    // Gate 3 adds:
    // - direct directory writing
    // - conversation_id as canonical archive identity
    // - per-conversation manifest commits
    // - content signature recording used by the integrated version-aware classifier
    // - visible progress feedback in the existing picker
    //
    // Integrated Sync preserves the validated Gate 3 / 3.1 writer invariants while routing
    // physical paths through Archive Layout v2. Archive Scan, Planner, classification and
    // selective transaction logic remain separate ChatHarbor layers.

    const CH_MANIFEST_NAME = 'ChatHarbor_manifest.json';
    const CH_MANIFEST_SCHEMA_VERSION = 1;
    const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';
    const CH_PROVIDER = 'chatgpt';
    const CH_PROVIDER_LABEL = 'ChatGPT';
    const CH_ARCHIVE_LAYOUT_VERSION = 2;
    const CH_LAYOUT_CONVERSATIONS_DIR = 'conversations';
    const CH_LAYOUT_PROJECTS_DIR = 'projects';
    const CH_REMOTE_CACHE_DB = 'chatharbor-remote-index-v1';
    const CH_REMOTE_CACHE_STORE = 'snapshots';
    const CH_REMOTE_CACHE_SCHEMA = 1;
    const CH_REMOTE_HEAD_LIMIT = 20;
    const CH_REMOTE_FULL_REFRESH_MS = 24 * 60 * 60 * 1000;
    const CH_REMOTE_SYNC_FRESH_MS = 2 * 60 * 1000;
    const CH_DIRECTORY_HANDLE_DB = 'chatharbor-directory-handle-v1';
    const CH_DIRECTORY_HANDLE_STORE = 'handles';
    const CH_DIRECTORY_HANDLE_KEY = 'chatgpt-default';

    async function chOpenDirectoryHandleDb() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(CH_DIRECTORY_HANDLE_DB, 1);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (!db.objectStoreNames.contains(CH_DIRECTORY_HANDLE_STORE)) db.createObjectStore(CH_DIRECTORY_HANDLE_STORE);
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error || new Error('directory handle db open failed'));
        });
    }
    async function chDirectoryHandleLoad() {
        try {
            const db = await chOpenDirectoryHandleDb();
            return await new Promise(resolve => {
                const req = db.transaction(CH_DIRECTORY_HANDLE_STORE, 'readonly').objectStore(CH_DIRECTORY_HANDLE_STORE).get(CH_DIRECTORY_HANDLE_KEY);
                req.onsuccess = () => resolve(req.result || null);
                req.onerror = () => resolve(null);
            });
        } catch (_) { return null; }
    }
    async function chDirectoryHandleSave(handle) {
        try {
            const db = await chOpenDirectoryHandleDb();
            await new Promise((resolve, reject) => {
                const tx = db.transaction(CH_DIRECTORY_HANDLE_STORE, 'readwrite');
                tx.objectStore(CH_DIRECTORY_HANDLE_STORE).put(handle, CH_DIRECTORY_HANDLE_KEY);
                tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error);
            });
        } catch (_) {}
    }
    async function chDirectoryHandlePermission(handle, request = false) {
        if (!handle) return 'denied';
        try {
            let permission = await handle.queryPermission({ mode:'readwrite' });
            if (permission !== 'granted' && request && handle.requestPermission) permission = await handle.requestPermission({ mode:'readwrite' });
            return permission;
        } catch (_) { return 'denied'; }
    }


    // ======================== ChatHarbor Conservative Network Policy ========================
    // Clean reimplementation of the historical ChatHarbor conservative behavior contract.
    const CH_NETWORK_POLICY_KEY = 'chatharbor_network_policy_v2';
    const CH_SPEED_LEVELS = [
        { name: '少量任务（较快）', base: 4000, jitter: 3000, batchSize: 15, pauseMinSec: 60, pauseMaxSec: 90 },
        { name: '日常使用（平衡）', base: 8000, jitter: 4000, batchSize: 12, pauseMinSec: 90, pauseMaxSec: 120 },
        { name: '大量任务（更稳）', base: 12000, jitter: 6000, batchSize: 10, pauseMinSec: 120, pauseMaxSec: 180 },
        { name: '保守模式（最稳）', base: 18000, jitter: 7000, batchSize: 8, pauseMinSec: 180, pauseMaxSec: 300 }
    ];
    const CH_DEFAULT_NETWORK_POLICY = Object.freeze({
        speedIndex: 2,
        batchSize: 10,
        batchPauseMinSec: 120,
        batchPauseMaxSec: 180,
        maxRetries: 2
    });

    function chNormalizeNetworkPolicy(value = {}) {
        const rawSpeed = Number(value.speedIndex);
        const speedIndex = Number.isFinite(rawSpeed)
            ? Math.max(0, Math.min(CH_SPEED_LEVELS.length - 1, Math.trunc(rawSpeed)))
            : CH_DEFAULT_NETWORK_POLICY.speedIndex;
        const rawBatch = Number(value.batchSize);
        const batchSize = Number.isFinite(rawBatch)
            ? Math.max(1, Math.min(200, Math.trunc(rawBatch)))
            : CH_DEFAULT_NETWORK_POLICY.batchSize;
        const rawMin = Number(value.batchPauseMinSec);
        const rawMax = Number(value.batchPauseMaxSec);
        const minSec = Number.isFinite(rawMin)
            ? Math.max(0, Math.min(3600, Math.trunc(rawMin)))
            : CH_DEFAULT_NETWORK_POLICY.batchPauseMinSec;
        const maxCandidate = Number.isFinite(rawMax)
            ? Math.max(0, Math.min(3600, Math.trunc(rawMax)))
            : CH_DEFAULT_NETWORK_POLICY.batchPauseMaxSec;
        const rawRetries = Number(value.maxRetries);
        const maxRetries = Number.isFinite(rawRetries)
            ? Math.max(0, Math.min(5, Math.trunc(rawRetries)))
            : CH_DEFAULT_NETWORK_POLICY.maxRetries;
        return {
            speedIndex,
            batchSize,
            batchPauseMinSec: minSec,
            batchPauseMaxSec: Math.max(minSec, maxCandidate),
            maxRetries
        };
    }

    function chLoadNetworkPolicy() {
        try {
            const raw = localStorage.getItem(CH_NETWORK_POLICY_KEY);
            return chNormalizeNetworkPolicy(raw ? JSON.parse(raw) : CH_DEFAULT_NETWORK_POLICY);
        } catch (_) {
            return { ...CH_DEFAULT_NETWORK_POLICY };
        }
    }

    function chSaveNetworkPolicy(policy) {
        const normalized = chNormalizeNetworkPolicy(policy);
        try { localStorage.setItem(CH_NETWORK_POLICY_KEY, JSON.stringify(normalized)); } catch (_) {}
        return normalized;
    }

    function chNetworkDelayMs(policy) {
        const p = chNormalizeNetworkPolicy(policy);
        const speed = CH_SPEED_LEVELS[p.speedIndex];
        return speed.base + Math.random() * speed.jitter;
    }

    function chNetworkBatchPauseMs(policy) {
        const p = chNormalizeNetworkPolicy(policy);
        const span = p.batchPauseMaxSec - p.batchPauseMinSec;
        return Math.round((p.batchPauseMinSec + Math.random() * span) * 1000);
    }

    function chNetworkPolicySummary(policy) {
        const p = chNormalizeNetworkPolicy(policy);
        return CH_SPEED_LEVELS[p.speedIndex].name;
    }

    function chNetworkPolicyDetail(policy) {
        const p = chNormalizeNetworkPolicy(policy);
        const speed = CH_SPEED_LEVELS[p.speedIndex];
        const minSec = Math.round(speed.base / 1000);
        const maxSec = Math.round((speed.base + speed.jitter) / 1000);
        return `对话间隔 ${minSec}–${maxSec} 秒 · 每 ${p.batchSize} 条休息 ${p.batchPauseMinSec}–${p.batchPauseMaxSec} 秒`;
    }

    // ======================== Shared ChatHarbor Backend Scheduler ========================
    // One scheduler owns serialization, global HTTP 429 cooldown and retry classification,
    // but request lanes keep different cadences. Discovery must remain responsive; expensive
    // conversation detail remains conservative; attachment metadata is rate-limited without
    // inheriting the full detail delay. Signed/direct binary transfers remain a separate path.
    const chRawChatHarborFetch = window.fetch.bind(window);
    const CH_BACKEND_LANE_DISCOVERY = 'discovery';
    const CH_BACKEND_LANE_DETAIL = 'detail';
    const CH_BACKEND_LANE_ATTACHMENT = 'attachment';
    const CH_DISCOVERY_BASE_MS = 1000;
    const CH_DISCOVERY_JITTER_MS = 500;
    const CH_ATTACHMENT_META_BASE_MS = 3000;
    const CH_ATTACHMENT_META_JITTER_MS = 2000;
    const CH_ATTACHMENT_META_BATCH_SIZE = 10;
    const CH_ATTACHMENT_META_PAUSE_MIN_MS = 30000;
    const CH_ATTACHMENT_META_PAUSE_JITTER_MS = 30000;
    const chBackendScheduler = {
        tail: Promise.resolve(),
        cooldownUntil: 0,
        cooldownReason: null,
        rateLimitLevel: 0,
        laneNextAllowedAt: {
            discovery: 0,
            detail: 0,
            attachment: 0
        },
        laneRequestCount: {
            discovery: 0,
            detail: 0,
            attachment: 0
        }
    };
    let chNetworkStatusHook = null;
    const chBackendContext = { detailTitle: null, detailId: null, attachmentName: null };

    function chSetNetworkStatusHook(fn) {
        chNetworkStatusHook = typeof fn === 'function' ? fn : null;
    }

    function chEmitNetworkStatus(info = null) {
        try { if (chNetworkStatusHook) chNetworkStatusHook(info); } catch (_) {}
    }

    function chIsBackendControlUrl(resource) {
        try {
            const url = resource instanceof Request ? resource.url : String(resource || '');
            const parsed = new URL(url, location.origin);
            return parsed.origin === location.origin && parsed.pathname.startsWith('/backend-api/');
        } catch (_) {
            return false;
        }
    }

    function chBackendLaneFor(resource) {
        try {
            const url = resource instanceof Request ? resource.url : String(resource || '');
            const parsed = new URL(url, location.origin);
            const path = parsed.pathname;
            if (/^\/backend-api\/conversations\/?$/i.test(path)) return CH_BACKEND_LANE_DISCOVERY;
            if (/^\/backend-api\/gizmos(?:\/|$)/i.test(path)) return CH_BACKEND_LANE_DISCOVERY;
            if (/^\/backend-api\/files\/download\//i.test(path)) return CH_BACKEND_LANE_ATTACHMENT;
            if (/\/interpreter\/download$/i.test(path)) return CH_BACKEND_LANE_ATTACHMENT;
            if (/^\/backend-api\/conversation\/[^/]+\/?$/i.test(path)) return CH_BACKEND_LANE_DETAIL;
            return CH_BACKEND_LANE_DETAIL;
        } catch (_) {
            return CH_BACKEND_LANE_DETAIL;
        }
    }

    function chBackendPolicy() {
        return chNormalizeNetworkPolicy(chSyncRun?.active ? chSyncRun.policy : chLoadNetworkPolicy());
    }

    function chBackendRequestDescriptor(resource, lane = null) {
        try {
            const url = resource instanceof Request ? resource.url : String(resource || '');
            const parsed = new URL(url, location.origin);
            const path = parsed.pathname;
            const resolvedLane = lane || chBackendLaneFor(resource);
            if (/^\/backend-api\/conversations\/?$/i.test(path)) return '云端对话';
            if (/^\/backend-api\/gizmos\/snorlax\/sidebar/i.test(path)) return '项目对话';
            const projectMatch = path.match(/^\/backend-api\/gizmos\/([^/]+)\/conversations/i);
            if (projectMatch) return `项目对话 · ${projectMatch[1].slice(0, 18)}`;
            if (resolvedLane === CH_BACKEND_LANE_ATTACHMENT) {
                const label = chBackendContext.attachmentName;
                if (label) return `附件 · ${String(label).slice(0, 52)}`;
                const fileMatch = path.match(/^\/backend-api\/files\/download\/([^/]+)/i);
                if (fileMatch) return `附件 · ${fileMatch[1].slice(0, 28)}`;
                return '附件信息';
            }
            if (resolvedLane === CH_BACKEND_LANE_DETAIL) {
                const label = chBackendContext.detailTitle;
                if (label) return `对话 · ${String(label).slice(0, 52)}`;
                const detailMatch = path.match(/^\/backend-api\/conversation\/([^/]+)/i);
                if (detailMatch) return `对话 · ${detailMatch[1].slice(0, 18)}`;
                return '对话内容';
            }
            return 'ChatGPT 请求';
        } catch (_) {
            return lane === CH_BACKEND_LANE_DISCOVERY ? '云端对话' : lane === CH_BACKEND_LANE_ATTACHMENT ? '附件信息' : '对话内容';
        }
    }

    function chRetryDelayForFailure({ status = null, lane = CH_BACKEND_LANE_DETAIL, attempt = 1, binary = false } = {}) {
        const n = Math.max(1, Number(attempt) || 1);
        if (status === 429) return 300000 * n;
        if (status === 401 || status === 403 || status === 404) return null;
        if (status != null && !(status >= 500 && status <= 599)) return null;
        if (binary) return 10000 * n;
        if (lane === CH_BACKEND_LANE_DISCOVERY) return 5000 * n;
        if (lane === CH_BACKEND_LANE_ATTACHMENT) return 5000 * n;
        return 15000 * n;
    }

    function chRetryPrimary(status, binary = false) {
        if (status === 429) return '请求过多，暂时休息';
        if (status >= 500 && status <= 599) return `服务器暂时出错（${status}）`;
        return binary ? '附件下载网络异常' : '网络连接异常';
    }

    function chLaneDelayMs(lane, policy) {
        if (lane === CH_BACKEND_LANE_DISCOVERY) {
            return CH_DISCOVERY_BASE_MS + Math.random() * CH_DISCOVERY_JITTER_MS;
        }
        const factor = 1 + 0.5 * Math.max(0, Number(chBackendScheduler.rateLimitLevel || 0));
        if (lane === CH_BACKEND_LANE_ATTACHMENT) {
            return (CH_ATTACHMENT_META_BASE_MS + Math.random() * CH_ATTACHMENT_META_JITTER_MS) * factor;
        }
        return chNetworkDelayMs(policy) * factor;
    }

    function chRegisterRateLimit() {
        chBackendScheduler.rateLimitLevel = Math.min(4, Number(chBackendScheduler.rateLimitLevel || 0) + 1);
    }

    async function chSchedulerSleep(ms, primary = '', secondary = '', countdown = false) {
        const duration = Math.max(0, Math.round(Number(ms) || 0));
        if (!duration) return;
        if (chSyncRun?.active) {
            return chControlledSleep(duration, primary || '保守网络等待', secondary, { countdown });
        }
        const deadline = Date.now() + duration;
        while (Date.now() < deadline) {
            const remaining = Math.max(0, deadline - Date.now());
            chEmitNetworkStatus({ primary, secondary, countdown, remainingMs: remaining });
            await sleep(Math.min(1000, Math.max(1, remaining)));
        }
        chEmitNetworkStatus(null);
    }

    async function chWithBackendSerial(task) {
        const previous = chBackendScheduler.tail;
        let release;
        chBackendScheduler.tail = new Promise(resolve => { release = resolve; });
        await previous;
        try { return await task(); }
        finally { try { release(); } catch (_) {} }
    }

    async function chWaitForBackendGate(label = '', lane = CH_BACKEND_LANE_DETAIL) {
        const now = Date.now();
        const laneDeadline = Number(chBackendScheduler.laneNextAllowedAt?.[lane] || 0);
        const cooldownDeadline = Number(chBackendScheduler.cooldownUntil || 0);
        const deadline = Math.max(laneDeadline, cooldownDeadline);
        if (deadline <= now) {
            if (cooldownDeadline <= now) {
                chBackendScheduler.cooldownUntil = 0;
                chBackendScheduler.cooldownReason = null;
            }
            chEmitNetworkStatus(null);
            return;
        }
        const waitMs = deadline - now;
        const is429 = chBackendScheduler.cooldownReason === 'HTTP_429' && cooldownDeadline >= deadline;
        const laneLabel = lane === CH_BACKEND_LANE_DISCOVERY ? '云端对话' : lane === CH_BACKEND_LANE_ATTACHMENT ? '附件信息' : '对话内容';
        await chSchedulerSleep(
            waitMs,
            is429 ? '请求过多，暂时休息' : '等待下一次请求',
            `${label ? `${label} · ` : ''}${is429 ? '稍后自动继续' : `${laneLabel}`}`,
            is429
        );
    }

    function chAfterBackendAttempt(policy, lane) {
        const p = chNormalizeNetworkPolicy(policy);
        chBackendScheduler.laneRequestCount[lane] = Number(chBackendScheduler.laneRequestCount[lane] || 0) + 1;
        let delay = chLaneDelayMs(lane, p);
        // Batch pauses belong only to expensive conversation-detail traffic. Discovery and
        // attachment metadata have their own lightweight lane cadence and never consume the
        // detail batch counter.
        if (lane === CH_BACKEND_LANE_DETAIL && chBackendScheduler.laneRequestCount[lane] % p.batchSize === 0) {
            delay = Math.max(delay, chNetworkBatchPauseMs(p) * (1 + 0.5 * Math.max(0, Number(chBackendScheduler.rateLimitLevel || 0))));
        }
        if (lane === CH_BACKEND_LANE_ATTACHMENT && chBackendScheduler.laneRequestCount[lane] % CH_ATTACHMENT_META_BATCH_SIZE === 0) {
            const attachmentPause = CH_ATTACHMENT_META_PAUSE_MIN_MS + Math.random() * CH_ATTACHMENT_META_PAUSE_JITTER_MS;
            delay = Math.max(delay, attachmentPause * (1 + 0.5 * Math.max(0, Number(chBackendScheduler.rateLimitLevel || 0))));
        }
        chBackendScheduler.laneNextAllowedAt[lane] = Math.max(
            Number(chBackendScheduler.laneNextAllowedAt[lane] || 0),
            Date.now() + delay
        );
    }

    async function chBackendFetch(resource, options = {}) {
        if (!chIsBackendControlUrl(resource)) return chRawChatHarborFetch(resource, options);
        const lane = chBackendLaneFor(resource);
        return chWithBackendSerial(async () => {
            const policy = chBackendPolicy();
            const maxAttempts = 1 + policy.maxRetries;
            let lastError = null;
            let lastResponse = null;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                if (chSyncRun?.active) await chControlCheckpoint('backend-request');
                await chWaitForBackendGate('', lane);
                try {
                    const response = await chRawChatHarborFetch(resource, options);
                    lastResponse = response;
                    chAfterBackendAttempt(policy, lane);
                    const status = Number(response?.status || 0);
                    const requestLabel = chBackendRequestDescriptor(resource, lane);
                    if (status === 429) {
                        const retryMs = chRetryDelayForFailure({ status, lane, attempt });
                        chBackendScheduler.cooldownUntil = Math.max(chBackendScheduler.cooldownUntil || 0, Date.now() + retryMs);
                        chBackendScheduler.cooldownReason = 'HTTP_429';
                        chRegisterRateLimit();
                        if (attempt < maxAttempts) {
                            await chWaitForBackendGate(`${requestLabel} · 第 ${attempt}/${policy.maxRetries} 次重试前`, lane);
                            continue;
                        }
                    } else if (status >= 500 && status <= 599 && attempt < maxAttempts) {
                        const retryMs = chRetryDelayForFailure({ status, lane, attempt });
                        await chSchedulerSleep(retryMs, chRetryPrimary(status), `${requestLabel} · 第 ${attempt}/${policy.maxRetries} 次重试前`, true);
                        continue;
                    }
                    // 401/403/404 and other non-retryable HTTP responses return immediately to
                    // the owning operation, which records the concrete conversation/asset failure.
                    return response;
                } catch (err) {
                    if (chIsCancellation(err)) throw err;
                    lastError = err;
                    chAfterBackendAttempt(policy, lane);
                    if (attempt >= maxAttempts) break;
                    const requestLabel = chBackendRequestDescriptor(resource, lane);
                    const retryMs = chRetryDelayForFailure({ status: null, lane, attempt });
                    await chSchedulerSleep(retryMs, chRetryPrimary(null), `${requestLabel} · 第 ${attempt}/${policy.maxRetries} 次重试前`, true);
                }
            }
            if (lastResponse) return lastResponse;
            throw lastError || new Error('ChatHarbor backend request failed');
        });
    }

    async function chDataTransferFetch(resource, options = {}) {
        const policy = chBackendPolicy();
        const maxAttempts = 1 + policy.maxRetries;
        let lastError = null;
        let lastResponse = null;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            if (chSyncRun?.active) await chControlCheckpoint('binary-transfer');
            if ((chBackendScheduler.cooldownUntil || 0) > Date.now()) await chWaitForBackendGate('附件数据下载', CH_BACKEND_LANE_ATTACHMENT);
            try {
                const response = await chRawChatHarborFetch(resource, options);
                lastResponse = response;
                const status = Number(response?.status || 0);
                if (status === 429) {
                    const retryMs = chRetryDelayForFailure({ status, lane: CH_BACKEND_LANE_ATTACHMENT, attempt, binary: true });
                    chBackendScheduler.cooldownUntil = Math.max(chBackendScheduler.cooldownUntil || 0, Date.now() + retryMs);
                    chBackendScheduler.cooldownReason = 'HTTP_429';
                        chRegisterRateLimit();
                    if (attempt < maxAttempts) { await chWaitForBackendGate(`附件数据 · 第 ${attempt}/${policy.maxRetries} 次重试前`, CH_BACKEND_LANE_ATTACHMENT); continue; }
                } else if (status >= 500 && status <= 599 && attempt < maxAttempts) {
                    const retryMs = chRetryDelayForFailure({ status, lane: CH_BACKEND_LANE_ATTACHMENT, attempt, binary: true });
                    await chSchedulerSleep(retryMs, chRetryPrimary(status, true), `附件数据 · 第 ${attempt}/${policy.maxRetries} 次重试前`, true);
                    continue;
                }
                return response;
            } catch (err) {
                if (chIsCancellation(err)) throw err;
                lastError = err;
                if (attempt >= maxAttempts) break;
                const retryMs = chRetryDelayForFailure({ status: null, lane: CH_BACKEND_LANE_ATTACHMENT, attempt, binary: true });
                await chSchedulerSleep(retryMs, chRetryPrimary(null, true), `附件数据 · 第 ${attempt}/${policy.maxRetries} 次重试前`, true);
            }
        }
        if (lastResponse) return lastResponse;
        throw lastError || new Error('ChatHarbor binary transfer failed');
    }

    const chSyncRun = {
        active: false,
        paused: false,
        cancelRequested: false,
        cancelReason: null,
        phase: 'idle',
        policy: chLoadNetworkPolicy(),
        waiters: [],
        sleepDeadline: null,
        sleepPrimary: null
    };

    function chBeginControlledRun(policy = null) {
        if (chSyncRun.active) throw new Error('已有同步任务正在运行。');
        chSyncRun.active = true;
        chSyncRun.paused = false;
        chSyncRun.cancelRequested = false;
        chSyncRun.cancelReason = null;
        chSyncRun.phase = 'starting';
        chSyncRun.policy = chSaveNetworkPolicy(policy || chLoadNetworkPolicy());
        chSyncRun.waiters = [];
        chSyncRun.sleepDeadline = null;
        chSyncRun.sleepPrimary = null;
        chUpdateRunControlUi();
        return chSyncRun;
    }

    function chEndControlledRun() {
        const waiters = chSyncRun.waiters.splice(0);
        waiters.forEach(resolve => { try { resolve(); } catch (_) {} });
        chSyncRun.active = false;
        chSyncRun.paused = false;
        chSyncRun.cancelRequested = false;
        chSyncRun.cancelReason = null;
        chSyncRun.phase = 'idle';
        chSyncRun.sleepDeadline = null;
        chSyncRun.sleepPrimary = null;
        chUpdateRunControlUi();
    }

    function chRequestPause() {
        if (!chSyncRun.active || chSyncRun.cancelRequested) return false;
        chSyncRun.paused = true;
        chUpdateRunControlUi();
        return true;
    }

    function chResumeRun() {
        if (!chSyncRun.active) return false;
        chSyncRun.paused = false;
        const waiters = chSyncRun.waiters.splice(0);
        waiters.forEach(resolve => { try { resolve(); } catch (_) {} });
        chUpdateRunControlUi();
        return true;
    }

    function chRequestCancel(reason = 'USER_CANCELLED') {
        if (!chSyncRun.active) return false;
        chSyncRun.cancelRequested = true;
        chSyncRun.cancelReason = reason;
        chSyncRun.paused = false;
        const waiters = chSyncRun.waiters.splice(0);
        waiters.forEach(resolve => { try { resolve(); } catch (_) {} });
        chUpdateRunControlUi();
        return true;
    }

    function chCancellationError(message = '同步已取消。') {
        const err = new Error(message);
        err.name = 'ChatHarborCancelled';
        err.code = 'CHATHARBOR_CANCELLED';
        return err;
    }

    function chIsCancellation(err) {
        return err?.code === 'CHATHARBOR_CANCELLED' || err?.name === 'ChatHarborCancelled';
    }

    async function chControlCheckpoint(phase = null) {
        if (phase) chSyncRun.phase = phase;
        if (chSyncRun.cancelRequested) throw chCancellationError();
        while (chSyncRun.paused && !chSyncRun.cancelRequested) {
            chSetProgress('已暂停', '点击“继续”恢复；暂停期间不会发起新的详情请求或开始新的会话写入。', null);
            await new Promise(resolve => chSyncRun.waiters.push(resolve));
        }
        if (chSyncRun.cancelRequested) throw chCancellationError();
    }

    function chFormatRemainingDuration(ms) {
        const totalSeconds = Math.max(0, Math.ceil((Number(ms) || 0) / 1000));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    async function chControlledSleep(ms, primary = '保守网络等待', secondary = '', options = {}) {
        const duration = Math.max(0, Math.round(Number(ms) || 0));
        const deadline = Date.now() + duration;
        const countdown = Boolean(options?.countdown);
        chSyncRun.sleepDeadline = deadline;
        chSyncRun.sleepPrimary = primary;
        let systemSuspended = false;
        try {
            while (true) {
                await chControlCheckpoint();
                const remaining = deadline - Date.now();
                if (remaining <= 0) break;
                if (remaining >= 1000) {
                    const waitText = countdown
                        ? `${secondary ? `${secondary} · ` : ''}剩余 ${chFormatRemainingDuration(remaining)}`
                        : (secondary || `剩余约 ${Math.ceil(remaining / 1000)} 秒`);
                    chSetProgress(primary, waitText, null);
                }
                const chunk = Math.min(1000, remaining);
                const before = Date.now();
                await sleep(chunk);
                const elapsed = Date.now() - before;
                // Browsers suspend timers during OS sleep / long background throttling.
                // Detect elapsed wall time instead of counting timer ticks.
                if (elapsed > chunk + 15000) systemSuspended = true;
            }
        } finally {
            chSyncRun.sleepDeadline = null;
            chSyncRun.sleepPrimary = null;
        }
        await chControlCheckpoint();
        if (systemSuspended && !chSyncRun.paused && !chSyncRun.cancelRequested) {
            const guardMs = chNetworkDelayMs(chSyncRun.policy);
            const guardDeadline = Date.now() + guardMs;
            while (Date.now() < guardDeadline) {
                await chControlCheckpoint('wake-guard');
                const remaining = guardDeadline - Date.now();
                chSetProgress('恢复保护等待', `检测到系统休眠/长时间挂起 · ${Math.max(1, Math.ceil(remaining / 1000))} 秒后继续`, null);
                await sleep(Math.min(1000, Math.max(1, remaining)));
            }
        }
        await chControlCheckpoint();
    }

    function chReconcileRuntimeState() {
        if (!chSyncRun.active) return;
        chUpdateRunControlUi();
        // Absolute deadlines are evaluated by chControlledSleep when timers resume.
        // User pause remains authoritative and is never auto-resumed here.
        if (chSyncRun.paused) return;
        if (chSyncRun.sleepDeadline && Date.now() >= chSyncRun.sleepDeadline) {
            const waiters = chSyncRun.waiters.splice(0);
            waiters.forEach(resolve => { try { resolve(); } catch (_) {} });
        }
    }

    document.addEventListener('visibilitychange', () => { if (!document.hidden) chReconcileRuntimeState(); });
    window.addEventListener('focus', chReconcileRuntimeState);
    window.addEventListener('pageshow', chReconcileRuntimeState);

    function chErrorStatus(err) {
        if (Number.isFinite(err?.status)) return Number(err.status);
        const match = String(err?.message || '').match(/\((\d{3})\)|HTTP\s+(\d{3})|\b(429|5\d\d|401|403)\b/i);
        return match ? Number(match[1] || match[2] || match[3]) : null;
    }

    function chRetryDelayMs(err, attempt) {
        const status = chErrorStatus(err);
        if (status === 429) return 300000 * Math.max(1, attempt);
        if (status && status >= 500) return 30000 * Math.max(1, attempt);
        if (status === 401 || status === 403) return null;
        return 30000 * Math.max(1, attempt);
    }

    async function chGetConversationConservative(id, workspaceId = null, title = null) {
        await chControlCheckpoint('detail-fetch');
        const previousTitle = chBackendContext.detailTitle;
        const previousId = chBackendContext.detailId;
        chBackendContext.detailTitle = title || null;
        chBackendContext.detailId = id || null;
        try {
            return await getConversation(id, workspaceId);
        } finally {
            chBackendContext.detailTitle = previousTitle;
            chBackendContext.detailId = previousId;
        }
    }

    function chUpdateRunControlUi() {
        const pauseBtn = document.getElementById('ch-pause-sync-btn');
        const cancelBtn = document.getElementById('ch-cancel-sync-btn');
        const backBtn = document.getElementById('back-btn');
        if (pauseBtn) {
            pauseBtn.style.display = chSyncRun.active ? '' : 'none';
            pauseBtn.disabled = !chSyncRun.active || chSyncRun.cancelRequested;
            pauseBtn.textContent = chSyncRun.paused ? '继续' : '暂停';
        }
        if (cancelBtn) {
            cancelBtn.style.display = chSyncRun.active ? '' : 'none';
            cancelBtn.disabled = !chSyncRun.active || chSyncRun.cancelRequested;
            cancelBtn.textContent = chSyncRun.cancelRequested ? '正在取消…' : '取消同步';
        }
        if (backBtn) {
            backBtn.disabled = chSyncRun.active;
            backBtn.title = chSyncRun.active ? '同步运行期间请先暂停/取消；“返回”不会被当作停止操作。' : '';
        }
    }

    function chExpectedByteLength(data) {
        if (typeof data === 'string') return new TextEncoder().encode(data).byteLength;
        if (data instanceof Blob) return data.size;
        if (data instanceof ArrayBuffer) return data.byteLength;
        if (ArrayBuffer.isView(data)) return data.byteLength;
        throw new Error('Unsupported directory-write payload');
    }

    async function chWriteRawFile(dirHandle, filename, data) {
        const fileHandle = await dirHandle.getFileHandle(filename, { create: true });
        const writable = await fileHandle.createWritable({ keepExistingData: false });
        try {
            await writable.write(data);
            await writable.close();
        } catch (err) {
            try { await writable.abort(); } catch (_) {}
            throw err;
        }
        return fileHandle;
    }

    async function chVerifiedDirectoryWrite(dirHandle, filename, data) {
        const tempName = `.${filename}.chatharbor.tmp`;
        const expectedBytes = chExpectedByteLength(data);

        const tempHandle = await chWriteRawFile(dirHandle, tempName, data);
        const tempFile = await tempHandle.getFile();
        if (tempFile.size !== expectedBytes) {
            try { await dirHandle.removeEntry(tempName); } catch (_) {}
            throw new Error(`Temporary write verification failed: ${filename}`);
        }

        const finalHandle = await chWriteRawFile(dirHandle, filename, data);
        const finalFile = await finalHandle.getFile();
        if (finalFile.size !== expectedBytes) {
            throw new Error(`Final write verification failed: ${filename}`);
        }

        try { await dirHandle.removeEntry(tempName); } catch (_) {}
        return finalHandle;
    }

    function chNewManifest() {
        const now = new Date().toISOString();
        return {
            schema_version: CH_MANIFEST_SCHEMA_VERSION,
            product: 'ChatHarbor',
            source: CH_PROVIDER_LABEL,
            provider: CH_PROVIDER,
            archive_layout_version: CH_ARCHIVE_LAYOUT_VERSION,
            created_at: now,
            updated_at: now,
            identity: 'conversation_id',
            signature_version: CH_SIGNATURE_VERSION,
            conversations: {}
        };
    }

    function chManifestLayoutVersion(manifest) {
        if (!manifest || typeof manifest !== 'object') return CH_ARCHIVE_LAYOUT_VERSION;
        const raw = Number(manifest.archive_layout_version);
        if (Number.isFinite(raw) && raw >= 1) return Math.trunc(raw);
        // Pre-Layout-v2 manifests did not carry an explicit layout version.
        return 1;
    }

    function chManifestProvider(manifest) {
        const provider = String(manifest?.provider || '').trim().toLowerCase();
        if (provider) return provider;
        // Legacy clean-lineage manifests used source: ChatGPT without provider.
        const source = String(manifest?.source || '').trim().toLowerCase();
        return source === 'chatgpt' ? CH_PROVIDER : null;
    }

    function chManifestRequiresLayoutMigration(manifest) {
        if (!manifest || typeof manifest !== 'object') return false;
        if (manifest.migration_state?.type === 'archive_layout' &&
            Number(manifest.migration_state?.to) === CH_ARCHIVE_LAYOUT_VERSION) return true;
        return chManifestLayoutVersion(manifest) < CH_ARCHIVE_LAYOUT_VERSION;
    }

    function chValidateManifestCompatibility(manifest) {
        if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
            throw new Error('manifest root is not an object');
        }
        if (manifest.schema_version !== CH_MANIFEST_SCHEMA_VERSION) {
            throw new Error(`unsupported manifest schema: ${manifest.schema_version ?? 'missing'}`);
        }
        if (manifest.identity !== 'conversation_id') {
            throw new Error(`unsupported manifest identity: ${manifest.identity ?? 'missing'}`);
        }
        if (manifest.signature_version && manifest.signature_version !== CH_SIGNATURE_VERSION) {
            throw new Error(`unsupported signature version: ${manifest.signature_version}`);
        }
        if (!manifest.conversations || typeof manifest.conversations !== 'object' || Array.isArray(manifest.conversations)) {
            throw new Error('manifest.conversations is invalid');
        }
        const provider = chManifestProvider(manifest);
        if (provider && provider !== CH_PROVIDER) {
            throw new Error(`provider mismatch: expected ${CH_PROVIDER}, found ${provider}`);
        }
        const layout = chManifestLayoutVersion(manifest);
        if (layout > CH_ARCHIVE_LAYOUT_VERSION) {
            throw new Error(`unsupported archive layout: ${layout}`);
        }
        return manifest;
    }

    async function chReadManifest(rootHandle) {
        try {
            const handle = await rootHandle.getFileHandle(CH_MANIFEST_NAME);
            const file = await handle.getFile();
            const text = await file.text();
            const manifest = JSON.parse(text);

            chValidateManifestCompatibility(manifest);
            return manifest;
        } catch (err) {
            if (err?.name === 'NotFoundError') return chNewManifest();
            if (err instanceof SyntaxError) {
                throw new Error(`无法解析 ${CH_MANIFEST_NAME}，已停止以避免覆盖损坏的 manifest。`);
            }
            if (String(err?.message || '').includes('manifest')) throw err;
            throw err;
        }
    }

    async function chWriteManifest(rootHandle, manifest) {
        manifest.updated_at = new Date().toISOString();
        const text = JSON.stringify(manifest, null, 2);
        await chVerifiedDirectoryWrite(rootHandle, CH_MANIFEST_NAME, text);
        return text;
    }

    function chHex(buffer) {
        return Array.from(new Uint8Array(buffer))
            .map(byte => byte.toString(16).padStart(2, '0'))
            .join('');
    }

    async function chContentSignature(convData) {
        const signaturePayload = JSON.stringify({
            current_node: convData?.current_node ?? null,
            mapping: convData?.mapping ?? {}
        });
        const digest = await crypto.subtle.digest(
            'SHA-256',
            new TextEncoder().encode(signaturePayload)
        );
        return chHex(digest);
    }

    function chGetConversationId(entry, convData) {
        const id = convData?.conversation_id || convData?.id || entry?.id || null;
        if (!id) throw new Error('conversation_id missing; refusing archive commit');
        return id;
    }

    function chProgressElements() {
        return {
            root: document.getElementById('ch-sync-progress'),
            primary: document.getElementById('ch-sync-progress-primary'),
            secondary: document.getElementById('ch-sync-progress-secondary'),
            pct: document.getElementById('ch-sync-progress-pct'),
            bar: document.getElementById('ch-sync-progress-bar')
        };
    }

    const chRuntimeProgress = { active:false, processed:0, total:0, currentTitle:'' };

    function chSetRuntimeProgress({ active = chRuntimeProgress.active, processed = chRuntimeProgress.processed, total = chRuntimeProgress.total, currentTitle = chRuntimeProgress.currentTitle } = {}) {
        chRuntimeProgress.active = Boolean(active);
        chRuntimeProgress.processed = Math.max(0, Number(processed) || 0);
        chRuntimeProgress.total = Math.max(0, Number(total) || 0);
        chRuntimeProgress.currentTitle = String(currentTitle || '');
    }

    function chSetProgress(primary, secondary = '', percent = null) {
        const els = chProgressElements();
        if (!els.root) return;
        els.root.style.display = 'block';

        let shownPrimary = primary || '';
        let shownSecondary = secondary || '';
        let normalized = Number.isFinite(percent) ? Math.max(0, Math.min(100, Math.round(percent))) : null;
        if (chRuntimeProgress.active && chRuntimeProgress.total > 0) {
            const done = Math.min(chRuntimeProgress.processed, chRuntimeProgress.total);
            normalized = Math.round((done / chRuntimeProgress.total) * 100);
            shownPrimary = `会话进度 ${done} / ${chRuntimeProgress.total}`;
            const current = chRuntimeProgress.currentTitle ? `当前：${chRuntimeProgress.currentTitle}` : '';
            const action = [primary, secondary].filter(Boolean).join(' · ');
            shownSecondary = [current, action].filter(Boolean).join('\n');
        }
        if (els.primary) els.primary.textContent = shownPrimary;
        if (els.secondary) { els.secondary.textContent = shownSecondary; els.secondary.style.whiteSpace = 'pre-line'; }
        if (els.pct) els.pct.textContent = normalized == null ? '' : `${normalized}%`;
        if (els.bar) {
            els.bar.style.width = normalized == null ? '0%' : `${normalized}%`;
            els.bar.style.opacity = normalized == null ? '0.35' : '1';
        }
    }

    function chProgressPercent(conversationIndex, conversationTotal, fractionWithinConversation) {
        if (!conversationTotal) return 0;
        const fraction = Math.max(0, Math.min(1, Number(fractionWithinConversation) || 0));
        return ((conversationIndex + fraction) / conversationTotal) * 100;
    }

    function chReportProgress(btn, {
        conversationIndex,
        conversationTotal,
        title,
        phase,
        detail = '',
        fraction = 0
    }) {
        const shortTitle = String(title || 'Untitled Conversation').slice(0, 42);
        chSetRuntimeProgress({ currentTitle: shortTitle });
        const shownPhase = phase === '下载附件' ? '正在下载附件'
            : phase === '保留已有附件' ? '正在检查附件'
            : ['写入 JSON','写入 Markdown','计算内容签名','提交 manifest','完成'].includes(phase) ? '正在保存'
            : (phase || '正在处理');
        chSetProgress(shownPhase, detail || '', null);
        // Runtime progress is intentionally shown only in the workspace progress card.
        // Keep the launcher free of duplicate percentage/status pills.
    }

    function chPlanAttachmentBackfill(convData, existingRecord = null) {
        const references = collectVisibleAttachments(convData || {});
        const assets = Array.isArray(existingRecord?.assets) ? existingRecord.assets : [];
        const existingByKey = new Map();
        for (const asset of assets) {
            const key = chAssetReferenceKey(asset);
            if (key && asset?.path && !existingByKey.has(key)) existingByKey.set(key, asset);
        }

        const retained = [];
        const missing = [];
        for (const reference of references) {
            const key = chAttachmentReferenceKey(reference);
            const asset = key ? existingByKey.get(key) : null;
            if (asset) retained.push({ reference, asset, key });
            else missing.push(reference);
        }
        return { references, retained, missing };
    }

    function chExistingAssetAsDownloadedFile(asset, targetPrefix) {
        const relativeLink = chRelativeMarkdownPath(targetPrefix, asset?.path || '');
        return {
            name: asset?.name || 'attachment',
            path: relativeLink,
            disk_path: asset?.path || '',
            root_path: asset?.path || '',
            kind: asset?.kind || 'file',
            isImage: Boolean(asset?.is_image),
            messageId: asset?.message_id || null,
            ownerRole: asset?.owner_role || null,
            size_bytes: Number(asset?.size_bytes || 0),
            source_file_id: asset?.source_file_id || null,
            source_sandbox_path: asset?.source_sandbox_path || null,
            reusedExisting: true
        };
    }

    async function chWriteAttachmentsToDirectory(
        targetDir,
        convData,
        workspaceId,
        progress = null,
        options = {}
    ) {
        const targetPrefix = String(options.targetPrefix || '');
        const existingRecord = options.existingRecord || null;
        const fetchBinary = options.fetchAttachmentBinary || fetchAttachmentBinary;
        const writeBinary = options.writeAttachment || chVerifiedDirectoryWrite;
        const backfillPlan = chPlanAttachmentBackfill(convData, existingRecord);
        const references = backfillPlan.references;
        const failures = [];
        const files = [];
        const sandboxPaths = new Map();
        const usedNames = new Set();
        const newlyWrittenRootPaths = [];
        const rootHandle = options.rootHandle || null;

        if (references.length === 0) {
            return {
                detected: 0,
                files,
                failures,
                sandboxPaths,
                folderName: null,
                assetDirPath: null,
                reusedCount: 0,
                downloadedNow: 0,
                missingBefore: 0,
                newlyWrittenRootPaths: []
            };
        }

        const folderName = generateUniqueFilename(convData).replace(/\.json$/i, '') + '_files';
        const missingRefs = [...backfillPlan.missing];
        const verifiedRetained = [];
        for (const item of backfillPlan.retained) {
            let reusable = true;
            if (rootHandle && item.asset?.path) {
                const meta = await chRelativeFileMeta(rootHandle, item.asset.path);
                const expectedSize = Number(item.asset?.size_bytes || 0);
                reusable = Boolean(meta.exists) && !(expectedSize > 0 && meta.size != null && meta.size !== expectedSize);
            }
            if (reusable) verifiedRetained.push(item);
            else missingRefs.push(item.reference);
        }
        const assetDir = missingRefs.length > 0
            ? await targetDir.getDirectoryHandle(folderName, { create: true })
            : null;

        // Reuse only assets whose Manifest identity and physical file both remain valid.
        for (const item of verifiedRetained) {
            const file = chExistingAssetAsDownloadedFile(item.asset, targetPrefix);
            files.push(file);
            if (file.name) usedNames.add(file.name);
            if (item.reference?.kind === 'sandbox' && item.reference?.messageId && item.reference?.sandboxPath) {
                sandboxPaths.set(`${item.reference.messageId}|${item.reference.sandboxPath}`, file.path);
            }
        }

        const retainedCount = files.length;
        if (progress && retainedCount > 0) {
            progress({
                assetIndex: retainedCount,
                assetTotal: references.length,
                name: `复用已有 ${retainedCount} 个附件`,
                reusedCount: retainedCount,
                downloadedNow: 0
            });
        }

        for (let i = 0; i < missingRefs.length; i++) {
            const reference = missingRefs[i];
            try {
                const previousAttachmentName = chBackendContext.attachmentName;
                chBackendContext.attachmentName = reference.name || reference.fileId || reference.sandboxPath || 'attachment';
                let downloaded;
                try {
                    downloaded = await fetchBinary(reference, convData, workspaceId);
                } finally {
                    chBackendContext.attachmentName = previousAttachmentName;
                }
                const filename = uniqueAttachmentName(downloaded.filename, usedNames);
                await writeBinary(assetDir, filename, downloaded.data);

                const diskPath = `${folderName}/${filename}`;
                const rootPath = `${targetPrefix}${diskPath}`;
                newlyWrittenRootPaths.push(rootPath);
                const relativePath = encodeRelativePath(diskPath);

                files.push({
                    name: filename,
                    path: relativePath,
                    disk_path: diskPath,
                    root_path: rootPath,
                    kind: reference.kind,
                    isImage: reference.isImage,
                    messageId: reference.messageId,
                    ownerRole: reference.ownerRole,
                    size_bytes: chExpectedByteLength(downloaded.data),
                    source_file_id: reference.fileId || null,
                    source_sandbox_path: reference.sandboxPath || null,
                    reusedExisting: false
                });

                if (reference.kind === 'sandbox') {
                    sandboxPaths.set(`${reference.messageId}|${reference.sandboxPath}`, relativePath);
                }
            } catch (error) {
                failures.push({
                    kind: reference.kind,
                    file_id: reference.fileId || null,
                    sandbox_path: reference.sandboxPath || null,
                    message_id: reference.messageId || null,
                    name: reference.name,
                    error: error?.message || String(error)
                });
            }

            // Progress is completion-based and monotonic.  Do not emit a second "before"
            // value for the same attachment; the counter advances exactly once per attempt.
            if (progress) {
                progress({
                    assetIndex: retainedCount + i + 1,
                    assetTotal: references.length,
                    name: reference.name || reference.fileId || reference.sandboxPath || 'attachment',
                    reusedCount: retainedCount,
                    downloadedNow: i + 1
                });
            }

        }

        const primaryAssetDir = missingRefs.length > 0
            ? `${targetPrefix}${folderName}`
            : (existingRecord?.asset_dir || (files[0]?.root_path ? chPathDirname(files[0].root_path) : null));

        return {
            detected: references.length,
            files,
            failures,
            sandboxPaths,
            folderName,
            assetDirPath: primaryAssetDir,
            reusedCount: retainedCount,
            downloadedNow: files.length - retainedCount,
            attemptedNow: missingRefs.length,
            missingBefore: missingRefs.length,
            newlyWrittenRootPaths
        };
    }

    function chExistingAttachmentResult(existingRecord) {
        const assets = Array.isArray(existingRecord?.assets) ? existingRecord.assets : [];
        if (assets.length === 0) return null;

        const sandboxPaths = new Map();
        let sandboxSourceComplete = true;

        const files = assets.map(asset => {
            if (asset?.kind === 'sandbox') {
                if (asset.message_id && asset.source_sandbox_path) {
                    sandboxPaths.set(
                        `${asset.message_id}|${asset.source_sandbox_path}`,
                        asset.markdown_path
                    );
                } else {
                    sandboxSourceComplete = false;
                }
            }

            return {
                name: asset.name,
                path: asset.markdown_path,
                disk_path: asset.path,
                kind: asset.kind,
                isImage: Boolean(asset.is_image),
                messageId: asset.message_id || null,
                ownerRole: asset.owner_role || null,
                size_bytes: asset.size_bytes || 0,
                source_file_id: asset.source_file_id || null,
                source_sandbox_path: asset.source_sandbox_path || null
            };
        });

        return {
            detected: existingRecord.attachment_detected ?? assets.length,
            files,
            failures: Array.isArray(existingRecord.attachment_failures)
                ? existingRecord.attachment_failures
                : [],
            sandboxPaths,
            folderName: existingRecord.asset_dir
                ? String(existingRecord.asset_dir).split('/').pop()
                : null,
            reusedExisting: true,
            sandboxSourceComplete
        };
    }

    async function chReadExistingText(rootHandle, relativePath) {
        const segments = String(relativePath || '')
            .split('/')
            .filter(Boolean);

        if (segments.length === 0) throw new Error('existing path missing');

        let dir = rootHandle;
        for (let i = 0; i < segments.length - 1; i++) {
            dir = await dir.getDirectoryHandle(segments[i]);
        }

        const handle = await dir.getFileHandle(segments[segments.length - 1]);
        const file = await handle.getFile();
        return await file.text();
    }

    async function chWriteConversationToDirectory({
        rootHandle,
        entry,
        convData,
        workspaceId,
        includeAttachments,
        existingRecord = null,
        existingAttachmentResultOverride = null,
        btn,
        conversationIndex,
        conversationTotal
    }) {
        const conversationId = chGetConversationId(entry, convData);
        const title = convData?.title || entry?.title || 'Untitled Conversation';

        const relativePrefix = chTargetRelativePrefix(entry);
        const targetDir = await chEnsureRelativeDirectory(rootHandle, relativePrefix);

        let attachmentResult = null;
        const preserveExistingAssets =
            !includeAttachments &&
            existingRecord &&
            (
                existingRecord.asset_dir ||
                (Array.isArray(existingRecord.assets) && existingRecord.assets.length > 0)
            );

        if (includeAttachments) {
            attachmentResult = await chWriteAttachmentsToDirectory(
                targetDir,
                convData,
                workspaceId,
                ({ assetIndex, assetTotal, name }) => {
                    const ratio = assetTotal ? assetIndex / assetTotal : 1;
                    chReportProgress(btn, {
                        conversationIndex,
                        conversationTotal,
                        title,
                        phase: '下载附件',
                        detail: `${assetIndex}/${assetTotal} · ${name}`,
                        fraction: 0.15 + ratio * 0.55
                    });
                },
                { targetPrefix: relativePrefix, existingRecord, rootHandle }
            );
        } else if (preserveExistingAssets) {
            attachmentResult = existingAttachmentResultOverride || chExistingAttachmentResult(existingRecord);
            chReportProgress(btn, {
                conversationIndex,
                conversationTotal,
                title,
                phase: '保留已有附件',
                detail: `${existingRecord.assets?.length || 0} 个已跟踪附件`,
                fraction: 0.70
            });
        }

        const jsonFilename = generateUniqueFilename(convData);
        const markdownFilename = generateMarkdownFilename(convData);
        const jsonText = JSON.stringify(convData, null, 2);

        let markdownText;
        if (
            preserveExistingAssets &&
            attachmentResult &&
            attachmentResult.sandboxSourceComplete === false &&
            existingRecord?.markdown_path
        ) {
            // Gate-3 manifests did not yet store original sandbox paths.
            // To avoid degrading already-valid local links during this one-time transition,
            // preserve the existing Markdown rather than rewriting it with unresolved sandbox URLs.
            markdownText = await chReadExistingText(rootHandle, existingRecord.markdown_path);
        } else {
            markdownText = convertConversationToMarkdown(convData, attachmentResult);
        }

        chReportProgress(btn, {
            conversationIndex,
            conversationTotal,
            title,
            phase: '写入 JSON',
            fraction: 0.76
        });
        await chVerifiedDirectoryWrite(targetDir, jsonFilename, jsonText);

        chReportProgress(btn, {
            conversationIndex,
            conversationTotal,
            title,
            phase: '写入 Markdown',
            fraction: 0.84
        });
        await chVerifiedDirectoryWrite(targetDir, markdownFilename, markdownText);

        chReportProgress(btn, {
            conversationIndex,
            conversationTotal,
            title,
            phase: '计算内容签名',
            fraction: 0.90
        });
        const contentSignature = await chContentSignature(convData);
        const syncedAt = new Date().toISOString();

        const assetDir = preserveExistingAssets
            ? (existingRecord.asset_dir || null)
            : (attachmentResult?.assetDirPath || (attachmentResult?.folderName ? `${relativePrefix}${attachmentResult.folderName}` : null));

        const assets = preserveExistingAssets
            ? (Array.isArray(existingRecord.assets) ? existingRecord.assets : [])
            : (attachmentResult?.files || []).map(file => ({
                path: file.root_path || `${relativePrefix}${file.disk_path}`,
                markdown_path: file.path,
                name: file.name,
                kind: file.kind,
                is_image: Boolean(file.isImage),
                message_id: file.messageId || null,
                owner_role: file.ownerRole || null,
                size_bytes: file.size_bytes,
                source_file_id: file.source_file_id || null,
                source_sandbox_path: file.source_sandbox_path || null
            }));

        const observed = chRemoteObservation(entry, existingRecord);
        const inspectedAttachments = chInspectAttachmentCompleteness(convData, {
            ...(existingRecord || {}),
            assets,
            attachment_failed: preserveExistingAssets ? (existingRecord?.attachment_failed ?? 0) : (attachmentResult?.failures?.length || 0)
        });
        const attachmentDetected = includeAttachments
            ? (attachmentResult?.detected ?? inspectedAttachments.detected)
            : inspectedAttachments.detected;
        const attachmentDownloaded = includeAttachments ? assets.length : (preserveExistingAssets ? (existingRecord?.attachment_downloaded ?? assets.length) : 0);
        const attachmentFailed = includeAttachments ? (attachmentResult?.failures?.length || 0) : (preserveExistingAssets ? (existingRecord?.attachment_failed ?? 0) : 0);
        const attachmentState = includeAttachments
            ? (attachmentDetected === 0 ? 'none' : (attachmentFailed === 0 && attachmentDownloaded >= attachmentDetected ? 'complete' : 'partial'))
            : inspectedAttachments.state;

        return {
            conversation_id: conversationId,
            title,
            create_time: convData?.create_time ?? entry?.create_time ?? null,
            remote_update_time: convData?.update_time ?? entry?.update_time ?? null,
            is_archived: observed.remote_list_is_archived ?? convData?.is_archived ?? entry?.is_archived ?? false,
            project_id: observed.remote_list_project_id ?? null,
            project_title: observed.remote_list_project_title ?? null,
            ...observed,
            provider: CH_PROVIDER,
            archive_layout_version: CH_ARCHIVE_LAYOUT_VERSION,
            content_signature: contentSignature,
            signature_version: CH_SIGNATURE_VERSION,
            json_path: `${relativePrefix}${jsonFilename}`,
            markdown_path: `${relativePrefix}${markdownFilename}`,
            json_bytes: chExpectedByteLength(jsonText),
            markdown_bytes: chExpectedByteLength(markdownText),
            asset_dir: assetDir,
            assets,
            attachment_state: attachmentState,
            attachments_checked_at: new Date().toISOString(),
            attachment_detected: attachmentDetected,
            attachment_downloaded: attachmentDownloaded,
            attachment_failed: attachmentFailed,
            attachment_failures: preserveExistingAssets ? (existingRecord?.attachment_failures || []) : (attachmentResult?.failures || []),
            attachments_preserved_without_download: Boolean(preserveExistingAssets),
            synced_at: syncedAt,
            __ch_new_asset_paths: attachmentResult?.newlyWrittenRootPaths || []
        };
    }

    async function chDirectoryWriteSelected({
        rootHandle,
        mode = 'personal',
        workspaceId = null,
        conversationEntries = [],
        includeAttachments = false
    }) {
        if (!rootHandle) throw new Error('Directory handle is required');
        if (!Array.isArray(conversationEntries) || conversationEntries.length === 0) {
            throw new Error('No conversations selected');
        }

        const btn = getExportButton();
        btn.disabled = true;

        chSetProgress('准备同步', '检查登录状态…', 0);

        if (!await ensureAccessToken()) {
            btn.disabled = false;
            setFabStatus(btn, EXPORT_BUTTON_LABEL);
            return;
        }

        chSetProgress('准备同步', `读取 ${CH_MANIFEST_NAME}…`, 1);
        const manifest = await chReadManifest(rootHandle);

        const results = [];
        let failed = 0;

        try {
            for (let i = 0; i < conversationEntries.length; i++) {
                const entry = conversationEntries[i];
                const title = entry?.title || 'Untitled Conversation';

                chReportProgress(btn, {
                    conversationIndex: i,
                    conversationTotal: conversationEntries.length,
                    title,
                    phase: '获取对话',
                    detail: entry?.id || '',
                    fraction: 0.05
                });

                try {
                    const convData = await getConversation(entry.id, workspaceId);

                    const resolvedConversationId =
                        convData?.conversation_id || convData?.id || entry?.id || null;
                    const existingRecord = resolvedConversationId
                        ? (manifest.conversations[resolvedConversationId] || null)
                        : null;

                    const record = await chWriteConversationToDirectory({
                        rootHandle,
                        entry,
                        convData,
                        workspaceId,
                        includeAttachments,
                        existingRecord,
                        btn,
                        conversationIndex: i,
                        conversationTotal: conversationEntries.length
                    });

                    chReportProgress(btn, {
                        conversationIndex: i,
                        conversationTotal: conversationEntries.length,
                        title,
                        phase: '提交 manifest',
                        detail: record.conversation_id,
                        fraction: 0.96
                    });

                    // conversation_id is the manifest key and canonical identity.
                    manifest.conversations[record.conversation_id] = record;
                    await chWriteManifest(rootHandle, manifest);

                    results.push(record);

                    chReportProgress(btn, {
                        conversationIndex: i,
                        conversationTotal: conversationEntries.length,
                        title,
                        phase: '完成',
                        detail: record.conversation_id,
                        fraction: 1
                    });
                } catch (err) {
                    failed++;
                    console.error('[ChatHarbor Gate 3.1] Directory/manifest commit failed:', entry?.id, err);
                    chSetProgress(
                        `同步 ${i + 1} / ${conversationEntries.length} · 失败`,
                        `${title} · ${err?.message || err}`,
                        chProgressPercent(i, conversationEntries.length, 1)
                    );
                }

                if (i + 1 < conversationEntries.length) await sleep(jitter());
            }

            const downloadedAttachments = results.reduce(
                (n, item) => n + item.attachment_downloaded, 0
            );
            const failedAttachments = results.reduce(
                (n, item) => n + item.attachment_failed, 0
            );

            const manifestCount = Object.keys(manifest.conversations).length;

            chSetProgress(
                failed ? 'Gate 3.1 完成（存在失败）' : 'Gate 3.1 完成',
                `成功 ${results.length} / ${conversationEntries.length} · manifest 共 ${manifestCount} 条`,
                100
            );
            // Non-blocking completion: keep 100% visible immediately.
            setFabStatus(btn, failed ? '⚠️ Gate 3.1 完成' : '✅ Gate 3.1 完成');


            return {
                planned: conversationEntries.length,
                succeeded: results.length,
                failed,
                manifest_count: manifestCount,
                results
            };
        } finally {
            setTimeout(() => {
                btn.disabled = false;
                setFabStatus(btn, EXPORT_BUTTON_LABEL);
            }, 1500);
        }
    }

    // ======================== ChatHarbor Integrated Sync: Read-only Archive Scan + Preflight Planner ========================
    // This layer is intentionally read-only:
    // - no conversation detail fetch
    // - no archive writes
    // - no manifest commits
    // - no rename cleanup
    // - no deletion of LOCAL_ONLY / legacy assets

    function chJoinRelativePath(...parts) {
        return parts
            .flatMap(part => String(part || '').split('/'))
            .filter(Boolean)
            .join('/');
    }

    function chRemoteConversationId(entry) {
        const id = entry?.id || entry?.conversation_id || null;
        return id ? String(id) : '';
    }

    function chTimeRelation(a, b) {
        const aa = normalizeEpochSeconds(a);
        const bb = normalizeEpochSeconds(b);
        if (!aa || !bb) return 'unknown';
        return Math.abs(aa - bb) <= 0.001 ? 'same' : 'different';
    }

    function chTimeEquivalent(a, b) {
        return chTimeRelation(a, b) === 'same';
    }

    function chRecordListTitle(record) {
        return Object.prototype.hasOwnProperty.call(record || {}, 'remote_list_title')
            ? String(record?.remote_list_title ?? '')
            : String(record?.title ?? '');
    }

    function chRecordListUpdateTime(record) {
        return Object.prototype.hasOwnProperty.call(record || {}, 'remote_list_update_time')
            ? record?.remote_list_update_time
            : record?.remote_update_time;
    }

    function chRecordListArchiveState(record) {
        return Object.prototype.hasOwnProperty.call(record || {}, 'remote_list_is_archived')
            ? record?.remote_list_is_archived
            : (Object.prototype.hasOwnProperty.call(record || {}, 'is_archived') ? Boolean(record?.is_archived) : null);
    }

    function chRecordListProjectId(record) {
        return Object.prototype.hasOwnProperty.call(record || {}, 'remote_list_project_id')
            ? record?.remote_list_project_id
            : (Object.prototype.hasOwnProperty.call(record || {}, 'project_id') ? record?.project_id : null);
    }

    function chRecordListProjectTitle(record) {
        return Object.prototype.hasOwnProperty.call(record || {}, 'remote_list_project_title')
            ? record?.remote_list_project_title
            : (Object.prototype.hasOwnProperty.call(record || {}, 'project_title') ? record?.project_title : null);
    }

    function chRemoteObservation(entry, existingRecord = null) {
        const existing = existingRecord || {};
        const projectState = entry?.__chProjectState || ((entry?.projectId || entry?.projectTitle) ? 'known' : 'unknown');
        const archiveState = entry?.__chArchiveState || (Object.prototype.hasOwnProperty.call(entry || {}, 'is_archived') ? 'known' : 'unknown');
        return {
            remote_list_title: String(entry?.title ?? chRecordListTitle(existing)),
            remote_list_update_time: normalizeEpochSeconds(entry?.update_time || 0) || null,
            remote_list_is_archived: archiveState === 'unknown'
                ? chRecordListArchiveState(existing)
                : Boolean(entry?.is_archived),
            remote_list_project_id: projectState === 'unknown'
                ? chRecordListProjectId(existing)
                : (entry?.projectId ?? null),
            remote_list_project_title: projectState === 'unknown'
                ? chRecordListProjectTitle(existing)
                : (entry?.projectTitle ?? null),
            remote_observed_at: new Date().toISOString()
        };
    }

    function chInferLegacyAttachmentState(record) {
        if (!record || typeof record !== 'object') return 'unknown';
        const assets = Array.isArray(record.assets) ? record.assets : [];
        const detected = Number(record.attachment_detected);
        const downloaded = Number(record.attachment_downloaded);
        const failed = Number(record.attachment_failed);
        const countsKnown = [detected, downloaded, failed].every(Number.isFinite);

        // A positive legacy detected count proves that the detail was inspected.  When all
        // detected assets were downloaded, no failures remain, and the Manifest tracks at
        // least that many files, the old record is strong enough to upgrade to COMPLETE
        // without another network verification.
        if (countsKnown && detected > 0) {
            if (failed === 0 && downloaded >= detected && assets.length >= detected) return 'complete';
            if (downloaded > 0 || failed > 0 || assets.length > 0) return 'partial';
            return 'not_downloaded';
        }

        // Zero in old manifests is ambiguous: it can mean "none" or "not inspected".
        // Only a newer explicit checked-at marker makes zero safe to interpret as NONE.
        if (countsKnown && detected === 0 && record.attachments_checked_at) return 'none';
        if (assets.length > 0) return 'partial';
        return 'unknown';
    }

    function chRecordAttachmentState(record) {
        const value = String(record?.attachment_state || '').toLowerCase();
        if (['unknown','none','complete','partial','not_downloaded'].includes(value)) return value;
        return chInferLegacyAttachmentState(record);
    }

    function chAttachmentReferenceKey(ref) {
        if (!ref) return '';
        if (ref.kind === 'sandbox') return `sandbox:${ref.messageId || ''}:${ref.sandboxPath || ''}`;
        return `file:${ref.fileId || ''}`;
    }

    function chAssetReferenceKey(asset) {
        if (!asset) return '';
        if (asset.kind === 'sandbox') return `sandbox:${asset.message_id || ''}:${asset.source_sandbox_path || ''}`;
        return `file:${asset.source_file_id || ''}`;
    }

    function chInspectAttachmentCompleteness(convData, record = null) {
        const refs = collectVisibleAttachments(convData || {});
        if (refs.length === 0) return { state: 'none', detected: 0, missing: 0 };
        const assets = Array.isArray(record?.assets) ? record.assets : [];
        const assetKeys = new Set(assets.map(chAssetReferenceKey).filter(Boolean));
        const refKeys = refs.map(chAttachmentReferenceKey).filter(Boolean);
        const missing = refKeys.filter(key => !assetKeys.has(key)).length;
        const failed = Number(record?.attachment_failed || 0);
        if (record && missing === 0 && failed === 0 && refKeys.length > 0) {
            return { state: 'complete', detected: refs.length, missing: 0 };
        }
        if (!record || assets.length === 0) return { state: 'not_downloaded', detected: refs.length, missing: refs.length };
        return { state: 'partial', detected: refs.length, missing };
    }

    async function chCollectPreflightRemoteUniverse(mode, workspaceId, currentList) {
        const base = Array.isArray(currentList) ? currentList.slice() : [];
        try {
            if (mode === 'team' || (mode === 'personal' && workspaceId)) {
                return { remoteList: base, complete: true, note: null };
            }
            if (mode === 'personal') {
                const projectList = await listProjectSpaceConversations(workspaceId);
                return {
                    remoteList: chMergeRemoteEntries(base.concat(projectList)),
                    complete: true,
                    note: `combined personal/root list (${base.length}) + project list (${projectList.length})`
                };
            }
            if (mode === 'project') {
                if (workspaceId) {
                    const fullList = await listConversations(workspaceId);
                    return {
                        remoteList: fullList,
                        complete: true,
                        note: `resolved full workspace list (${fullList.length})`
                    };
                }
                const rootList = await listConversations(null);
                return {
                    remoteList: chMergeRemoteEntries(rootList.concat(base)),
                    complete: true,
                    note: `combined personal/root list (${rootList.length}) + project list (${base.length})`
                };
            }
            return { remoteList: base, complete: false, note: `unknown picker mode: ${mode}` };
        } catch (err) {
            return {
                remoteList: base,
                complete: false,
                note: `complementary remote-list scan failed: ${err?.message || String(err)}`
            };
        }
    }

    function chLooksLikeConversationJson(data) {
        return Boolean(
            data &&
            typeof data === 'object' &&
            !Array.isArray(data) &&
            (data.conversation_id || data.id) &&
            data.mapping &&
            typeof data.mapping === 'object' &&
            !Array.isArray(data.mapping)
        );
    }

    async function chReadJsonHandle(fileHandle) {
        const file = await fileHandle.getFile();
        return JSON.parse(await file.text());
    }

    async function chReadManifestForScan(rootHandle) {
        try {
            const handle = await rootHandle.getFileHandle(CH_MANIFEST_NAME);
            const manifest = await chReadJsonHandle(handle);
            chValidateManifestCompatibility(manifest);
            return { exists: true, manifest, error: null };
        } catch (err) {
            if (err?.name === 'NotFoundError') {
                return { exists: false, manifest: null, error: null };
            }
            return {
                exists: true,
                manifest: null,
                error: err?.message || String(err)
            };
        }
    }

    async function chRelativeFileMeta(rootHandle, relativePath) {
        const parts = chSplitPath(relativePath);
        if (!parts.length) return { exists: false, size: null };
        try {
            let dir = rootHandle;
            for (let i = 0; i < parts.length - 1; i++) dir = await dir.getDirectoryHandle(parts[i]);
            const handle = await dir.getFileHandle(parts[parts.length - 1]);
            const file = await handle.getFile();
            return { exists: true, size: Number.isFinite(file?.size) ? file.size : null };
        } catch (err) {
            if (err?.name === 'NotFoundError') return { exists: false, size: null };
            throw err;
        }
    }

    async function chScanLocalArchiveReadOnly(rootHandle, onProgress = null, options = {}) {
        const checkAssets = Boolean(options?.checkAssets);
        if (!rootHandle) throw new Error('Directory handle is required');

        const manifestResult = await chReadManifestForScan(rootHandle);
        const rawById = new Map();
        const rawByPath = new Map();
        const manifestById = new Map();
        const errors = [];
        let jsonFilesSeen = 0;
        let conversationJsonFiles = 0;
        let ignoredJsonFiles = 0;
        let skippedAssetDirs = 0;
        let trackedFastChecked = 0;
        let assetFastChecked = 0;
        let assetIntegrityIssues = 0;

        if (manifestResult.error) errors.push({ type:'MANIFEST_ERROR', id:null, path:CH_MANIFEST_NAME, message:manifestResult.error });

        const trackedJsonPathToId = new Map();
        if (manifestResult.manifest) {
            for (const [key, record] of Object.entries(manifestResult.manifest.conversations || {})) {
                const id = String(key || '');
                if (!id) { errors.push({type:'MANIFEST_EMPTY_ID',id:null,path:CH_MANIFEST_NAME,message:'manifest contains an empty conversation_id key'}); continue; }
                if (record?.conversation_id && String(record.conversation_id) !== id) {
                    errors.push({type:'MANIFEST_ID_MISMATCH',id,path:CH_MANIFEST_NAME,message:`record conversation_id ${record.conversation_id} does not match manifest key`});
                }
                const normalized = { ...(record || {}), conversation_id:id, tracking:'manifest' };
                manifestById.set(id, normalized);
                if (normalized.json_path) trackedJsonPathToId.set(String(normalized.json_path), id);
            }
        }

        const seenTrackedPaths = new Set();
        const walk = async (dirHandle, relativeDir = '') => {
            for await (const [name, handle] of dirHandle.entries()) {
                const relativePath = chJoinRelativePath(relativeDir, name);
                if (handle.kind === 'directory') {
                    if (/_files$/i.test(name)) { skippedAssetDirs++; continue; }
                    await walk(handle, relativePath);
                    continue;
                }
                if (!/\.json$/i.test(name) || name === CH_MANIFEST_NAME) continue;
                jsonFilesSeen++;
                if (onProgress && jsonFilesSeen % 25 === 0) onProgress({jsonFilesSeen,conversationJsonFiles,path:relativePath});

                const trackedId = trackedJsonPathToId.get(relativePath);
                if (trackedId) {
                    seenTrackedPaths.add(relativePath);
                    trackedFastChecked++;
                    const record = manifestById.get(trackedId);
                    try {
                        const file = await handle.getFile();
                        if (Number(record?.json_bytes || 0) > 0 && Number.isFinite(file?.size) && file.size !== Number(record.json_bytes)) {
                            errors.push({type:'MANIFEST_JSON_SIZE_MISMATCH',id:trackedId,path:relativePath,message:`tracked JSON size ${file.size} != manifest ${record.json_bytes}`});
                        }
                    } catch (err) {
                        errors.push({type:'MANIFEST_JSON_STAT_FAILED',id:trackedId,path:relativePath,message:err?.message || String(err)});
                    }
                    continue;
                }

                let data;
                try { data = await chReadJsonHandle(handle); }
                catch (_) { ignoredJsonFiles++; continue; }
                if (!chLooksLikeConversationJson(data)) { ignoredJsonFiles++; continue; }
                const id = String(data.conversation_id || data.id || '');
                if (!id) { errors.push({type:'RAW_CONVERSATION_ID_MISSING',id:null,path:relativePath,message:'conversation-shaped JSON has no conversation_id'}); continue; }
                conversationJsonFiles++;
                const rawRecord = {
                    conversation_id:id,title:data.title||'',create_time:data.create_time??null,
                    remote_update_time:data.update_time??null,is_archived:data.is_archived??false,
                    json_path:relativePath,tracking:'raw_only'
                };
                if (!rawById.has(id)) rawById.set(id,[]);
                rawById.get(id).push(rawRecord); rawByPath.set(relativePath,rawRecord);
            }
        };
        await walk(rootHandle,'');

        const blockedIds = new Set();
        for (const [id, record] of manifestById.entries()) {
            const trackedPath = String(record?.json_path || '');
            if (!trackedPath) { errors.push({type:'MANIFEST_JSON_PATH_MISSING',id,path:CH_MANIFEST_NAME,message:'tracked conversation has no json_path'}); blockedIds.add(id); continue; }
            if (!seenTrackedPaths.has(trackedPath)) { errors.push({type:'MANIFEST_JSON_NOT_FOUND',id,path:trackedPath,message:'manifest json_path was not found during archive scan'}); blockedIds.add(id); }
            if (record?.markdown_path) {
                const meta = await chRelativeFileMeta(rootHandle, record.markdown_path);
                if (!meta.exists) { errors.push({type:'MANIFEST_MARKDOWN_NOT_FOUND',id,path:record.markdown_path,message:'manifest markdown_path was not found during archive scan'}); blockedIds.add(id); }
                else if (Number(record?.markdown_bytes || 0)>0 && meta.size != null && meta.size !== Number(record.markdown_bytes)) {
                    errors.push({type:'MANIFEST_MARKDOWN_SIZE_MISMATCH',id,path:record.markdown_path,message:`tracked Markdown size ${meta.size} != manifest ${record.markdown_bytes}`});
                }
            }
            if (checkAssets && Array.isArray(record?.assets) && record.assets.length) {
                let missing = 0, sizeMismatch = 0;
                for (const asset of record.assets) {
                    if (!asset?.path) { missing++; assetIntegrityIssues++; continue; }
                    assetFastChecked++;
                    const meta = await chRelativeFileMeta(rootHandle, asset.path);
                    if (!meta.exists) { missing++; assetIntegrityIssues++; continue; }
                    const expectedSize = Number(asset?.size_bytes || 0);
                    if (expectedSize > 0 && meta.size != null && meta.size !== expectedSize) { sizeMismatch++; assetIntegrityIssues++; }
                }
                if (missing || sizeMismatch) {
                    record.__chAssetIntegrity = { missing, sizeMismatch };
                    record.attachment_state = 'partial';
                }
            }
        }

        const duplicateIds = new Set(); const duplicates=[];
        for (const [id, records] of rawById.entries()) if (records.length>1) { duplicateIds.add(id); duplicates.push({id,source:'local',paths:records.map(r=>r.json_path)}); blockedIds.add(id); }

        // A raw untracked copy with the same identity as a manifest-tracked conversation is not
        // silently adopted. Preserve it and block that identity until the duplicate is resolved.
        for (const [id, records] of rawById.entries()) {
            if (manifestById.has(id) && records.length) {
                duplicateIds.add(id); blockedIds.add(id);
                duplicates.push({id,source:'local-manifest+untracked',paths:[manifestById.get(id)?.json_path,...records.map(r=>r.json_path)].filter(Boolean)});
            }
        }

        const recordsById = new Map(manifestById);
        for (const [id, records] of rawById.entries()) {
            if (manifestById.has(id)) continue;
            if (records.length===1) recordsById.set(id,records[0]);
            else if (records.length>1) recordsById.set(id,{conversation_id:id,title:records[0]?.title||'',remote_update_time:records[0]?.remote_update_time??null,tracking:'duplicate_raw'});
        }

        const errorsById = new Map();
        for (const error of errors) { if (!error.id) continue; if (!errorsById.has(error.id)) errorsById.set(error.id,[]); errorsById.get(error.id).push(error); }
        for (const error of errors) if (error.id && /_NOT_FOUND|_SIZE_MISMATCH|_STAT_FAILED|_PATH_MISSING|_ID_MISMATCH/.test(error.type)) blockedIds.add(error.id);
        if (onProgress) onProgress({jsonFilesSeen,conversationJsonFiles,done:true});

        return {
            manifestExists:manifestResult.exists, manifestReadable:Boolean(manifestResult.manifest), manifest:manifestResult.manifest,
            recordsById,manifestById,rawById,duplicateIds,duplicates,blockedIds,errors,errorsById,
            stats:{
                local:recordsById.size,manifestTracked:manifestById.size,
                manifestProject:Array.from(manifestById.values()).filter(r=>r.project_id||r.project_title).length,
                manifestRoot:Array.from(manifestById.values()).filter(r=>!(r.project_id||r.project_title)).length,
                rawConversationFiles:conversationJsonFiles,rawUniqueIds:rawById.size,
                rawOnlyIds:Array.from(recordsById.values()).filter(r=>r.tracking==='raw_only').length,
                archiveLayoutVersion:manifestResult.manifest?chManifestLayoutVersion(manifestResult.manifest):CH_ARCHIVE_LAYOUT_VERSION,
                provider:manifestResult.manifest?(chManifestProvider(manifestResult.manifest)||CH_PROVIDER):CH_PROVIDER,
                migrationRequired:Boolean(manifestResult.manifest&&chManifestRequiresLayoutMigration(manifestResult.manifest)),
                jsonFilesSeen,ignoredJsonFiles,skippedAssetDirs,trackedFastChecked,assetFastChecked,assetIntegrityIssues
            }
        };
    }

    function chBuildPreflightPlan(remoteList, localScan, selectedIds = null, options = {}) {
        const allRemote = Array.isArray(remoteList) ? remoteList : [];
        const remoteUniverseComplete = options.remoteUniverseComplete !== false;
        const remoteUniverseNote = options.remoteUniverseNote || null;
        const includeAttachments = Boolean(options.includeAttachments);
        const selected = selectedIds instanceof Set && selectedIds.size > 0 ? selectedIds : null;

        const remoteById = new Map(); const remoteErrors=[];
        for (const entry of allRemote) {
            const id=chRemoteConversationId(entry);
            if(!id){remoteErrors.push({type:'REMOTE_ID_MISSING',id:null,title:entry?.title||'',message:'remote list entry has no conversation_id'});continue;}
            if(!remoteById.has(id))remoteById.set(id,[]); remoteById.get(id).push(entry);
        }
        const remoteDuplicateIds=new Set(),remoteDuplicates=[];
        for(const [id,entries] of remoteById.entries()) if(entries.length>1){remoteDuplicateIds.add(id);remoteDuplicates.push({id,source:'remote',count:entries.length,titles:entries.map(e=>e?.title||'')});}
        const duplicateIds=new Set([...localScan.duplicateIds,...remoteDuplicateIds]);
        const globalRemoteIds=new Set(remoteById.keys());
        const scopeIds=selected?new Set(Array.from(selected).filter(id=>globalRemoteIds.has(id))):new Set(globalRemoteIds);

        const items=[]; let newCount=0,remoteUpdateCandidateCount=0,renameCandidateCount=0,unchangedCount=0,metadataCandidateCount=0,rawOnlyVerifyCount=0,errorCount=0,maximumFetchRequired=0,attachmentCandidateCount=0;
        for(const id of scopeIds){
            const remoteEntries=remoteById.get(id)||[]; const remote=remoteEntries[0]||null; const local=localScan.recordsById.get(id)||null;
            if(duplicateIds.has(id)){items.push({id,action:'DUPLICATE',remote,local,needs_detail_fetch:false,reasons:[...(remoteDuplicateIds.has(id)?['REMOTE_DUPLICATE_ID']:[]),...(localScan.duplicateIds.has(id)?['LOCAL_DUPLICATE_ID']:[])]});continue;}
            if(localScan.blockedIds.has(id)){errorCount++;items.push({id,action:'ERROR',remote,local,needs_detail_fetch:false,reasons:(localScan.errorsById.get(id)||[]).map(e=>e.type)});continue;}
            if(!local){newCount++;maximumFetchRequired++;items.push({id,action:'NEW',remote,local:null,needs_detail_fetch:true,remote_update_candidate:false,rename_candidate:false,metadata_candidate:false,attachment_candidate:includeAttachments,reasons:['NOT_IN_LOCAL_ARCHIVE']});continue;}
            if(local.tracking!=='manifest'){
                const timeRelation=chTimeRelation(remote?.update_time,local?.remote_update_time);
                const updateCandidate=timeRelation!=='same'; const titleChanged=String(remote?.title||'')!==String(local?.title||'');
                rawOnlyVerifyCount++; if(updateCandidate)remoteUpdateCandidateCount++; if(titleChanged)renameCandidateCount++;
                items.push({id,action:'LOCAL_UNTRACKED',remote,local,needs_detail_fetch:false,requires_user_confirmation:true,remote_update_candidate:updateCandidate,rename_candidate:titleChanged,metadata_candidate:false,attachment_candidate:false,reasons:['LOCAL_RAW_NOT_MANIFEST_TRACKED',...(timeRelation==='different'?['REMOTE_UPDATE_TIME_DIFF']:timeRelation==='unknown'?['REMOTE_UPDATE_TIME_UNKNOWN']:[]),...(titleChanged?['TITLE_DIFF']:[])]});continue;
            }

            const baselineTitle=chRecordListTitle(local);
            const titleChanged=String(remote?.title||'')!==baselineTitle;
            const timeRelation=chTimeRelation(remote?.update_time,chRecordListUpdateTime(local));
            const unknownRecentlyVerified = timeRelation==='unknown' && Object.prototype.hasOwnProperty.call(local||{},'remote_list_update_time') && !normalizeEpochSeconds(remote?.update_time||0) && !normalizeEpochSeconds(local?.remote_list_update_time||0) && local?.remote_observed_at && (Date.now()-Date.parse(local.remote_observed_at)) < CH_REMOTE_FULL_REFRESH_MS;
            const updateCandidate=timeRelation==='different' || (timeRelation==='unknown' && !unknownRecentlyVerified);
            const metadataReasons=[];
            const archiveKnown=(remote?.__chArchiveState||'known')!=='unknown';
            const projectKnown=(remote?.__chProjectState||'known')!=='unknown';
            if(archiveKnown && Object.prototype.hasOwnProperty.call(remote||{},'is_archived') && Boolean(remote?.is_archived)!==Boolean(chRecordListArchiveState(local))) metadataReasons.push('ARCHIVE_STATE_DIFF');
            if(projectKnown && String(remote?.projectId??'')!==String(chRecordListProjectId(local)??'')) metadataReasons.push('PROJECT_ID_DIFF');
            if(projectKnown && String(remote?.projectTitle??'')!==String(chRecordListProjectTitle(local)??'')) metadataReasons.push('PROJECT_TITLE_DIFF');
            const metadataCandidate=metadataReasons.length>0;
            const attachmentState=chRecordAttachmentState(local);
            const attachmentCandidate=includeAttachments && !['complete','none'].includes(attachmentState);

            if(updateCandidate)remoteUpdateCandidateCount++; if(titleChanged)renameCandidateCount++; if(metadataCandidate)metadataCandidateCount++; if(attachmentCandidate)attachmentCandidateCount++;
            if(updateCandidate||titleChanged||metadataCandidate||attachmentCandidate){
                maximumFetchRequired++;
                items.push({id,action:(updateCandidate||metadataCandidate||attachmentCandidate)?'VERIFY_CHANGED':'VERIFY_RENAMED',remote,local,needs_detail_fetch:true,remote_update_candidate:updateCandidate,rename_candidate:titleChanged,metadata_candidate:metadataCandidate,attachment_candidate:attachmentCandidate,reasons:[...(timeRelation==='different'?['REMOTE_UPDATE_TIME_DIFF']:timeRelation==='unknown'?['REMOTE_UPDATE_TIME_UNKNOWN']:[]),...(titleChanged?['TITLE_DIFF']:[]),...metadataReasons,...(attachmentCandidate?[`ATTACHMENT_${attachmentState.toUpperCase()}`]:[])]});
            }else{
                unchangedCount++; items.push({id,action:'UNCHANGED',remote,local,needs_detail_fetch:false,remote_update_candidate:false,rename_candidate:false,metadata_candidate:false,attachment_candidate:false,reasons:[]});
            }
        }

        const localOnly=[];
        if(remoteUniverseComplete) for(const [id,local] of localScan.recordsById.entries()) if(!globalRemoteIds.has(id)&&!duplicateIds.has(id)&&!localScan.blockedIds.has(id))localOnly.push({id,local,action:'LOCAL_ONLY'});
        return {items,localOnly,duplicateIds:Array.from(duplicateIds),duplicateDetails:[...localScan.duplicates,...remoteDuplicates],errors:[...localScan.errors,...remoteErrors],summary:{
            remote:allRemote.length,remoteUnique:remoteById.size,scopeRemote:scopeIds.size,local:localScan.recordsById.size,newCount,remoteUpdateCandidateCount,renameCandidateCount,unchangedCount,metadataCandidateCount,attachmentCandidateCount,rawOnlyVerifyCount,
            localOnlyCount:remoteUniverseComplete?localOnly.length:null,localOnlyReliable:remoteUniverseComplete,remoteUniverseComplete,remoteUniverseNote,duplicateIdCount:duplicateIds.size,
            errorCount:errorCount+remoteErrors.length+localScan.errors.filter(e=>!e.id).length,maximumFetchRequired,manifestTracked:localScan.stats.manifestTracked,localProjectCount:localScan.stats.manifestProject||0,localRootCount:localScan.stats.manifestRoot||0,archiveLayoutVersion:localScan.stats.archiveLayoutVersion,provider:localScan.stats.provider,migrationRequired:Boolean(localScan.stats.migrationRequired),rawConversationFiles:localScan.stats.rawConversationFiles,rawOnlyIds:localScan.stats.rawOnlyIds,trackedFastChecked:localScan.stats.trackedFastChecked||0,assetFastChecked:localScan.stats.assetFastChecked||0,assetIntegrityIssues:localScan.stats.assetIntegrityIssues||0
        }};
    }

    function chPreflightReportText(plan) {
        const s = plan.summary;
        const lines = [
            'ChatHarbor | Archive Scan + Preflight Planner',
            'DRY-RUN / READ-ONLY',
            '',
            `Remote: ${s.remote} (${s.remoteUnique} unique IDs)`,
            `Remote universe: ${s.remoteUniverseComplete ? 'COMPLETE' : 'INCOMPLETE'}`,
            ...(s.remoteUniverseNote ? [`Remote note: ${s.remoteUniverseNote}`] : []),
            `Scope: ${s.scopeRemote}`,
            `Local: ${s.local}`,
            `NEW: ${s.newCount}`,
            `remote-update candidates: ${s.remoteUpdateCandidateCount}`,
            `rename candidates: ${s.renameCandidateCount}`,
            `UNCHANGED: ${s.unchangedCount}`,
            `metadata candidates: ${s.metadataCandidateCount}`,
            `raw-only verify candidates: ${s.rawOnlyVerifyCount}`,
            `LOCAL_ONLY: ${s.localOnlyReliable ? s.localOnlyCount : 'UNKNOWN (remote universe incomplete)'}`,
            `duplicate IDs: ${s.duplicateIdCount}`,
            `ERROR: ${s.errorCount}`,
            `maximum fetch required: ${s.maximumFetchRequired}`,
            '',
            `Manifest tracked: ${s.manifestTracked}`,
            `Raw conversation JSON files: ${s.rawConversationFiles}`,
            `Raw-only IDs: ${s.rawOnlyIds}`,
            '',
            'No detail fetch was performed. No file or manifest was written.'
        ];

        const grouped = new Map();
        for (const item of plan.items) {
            if (!grouped.has(item.action)) grouped.set(item.action, []);
            grouped.get(item.action).push(item);
        }

        const appendItems = (label, items, formatter) => {
            if (!items || items.length === 0) return;
            lines.push('', `=== ${label} (${items.length}) ===`);
            for (const item of items.slice(0, 80)) lines.push(formatter(item));
            if (items.length > 80) lines.push(`... ${items.length - 80} more`);
        };

        appendItems('DUPLICATE', grouped.get('DUPLICATE'), item =>
            `[DUPLICATE] ${item.remote?.title || item.local?.title || item.id} | ${item.id} | ${item.reasons.join(', ')}`
        );
        appendItems('ERROR', grouped.get('ERROR'), item =>
            `[ERROR] ${item.remote?.title || item.local?.title || item.id} | ${item.id} | ${item.reasons.join(', ')}`
        );
        appendItems('NEW', grouped.get('NEW'), item =>
            `[NEW] ${item.remote?.title || item.id} | ${item.id}`
        );
        appendItems('VERIFY', plan.items.filter(item => item.action === 'VERIFY_CHANGED' || item.action === 'VERIFY_RENAMED'), item =>
            `[${item.action}] ${item.remote?.title || item.local?.title || item.id} | ${item.id} | time=${item.remote_update_candidate ? 'DIFF' : 'SAME'} | title=${item.rename_candidate ? 'DIFF' : 'SAME'}`
        );
        appendItems('LOCAL_ONLY', plan.localOnly, item =>
            `[LOCAL_ONLY] ${item.local?.title || item.id} | ${item.id}`
        );

        if (plan.errors.length) {
            lines.push('', `=== SCAN ERRORS (${plan.errors.length}) ===`);
            for (const error of plan.errors.slice(0, 80)) {
                lines.push(`[${error.type}] ${error.id || '-'} | ${error.path || '-'} | ${error.message || ''}`);
            }
            if (plan.errors.length > 80) lines.push(`... ${plan.errors.length - 80} more`);
        }

        return lines.join('\n');
    }

    function chShowPreflightReport(plan) {
        const existing = document.getElementById('ch-preflight-report-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'ch-preflight-report-overlay';
        Object.assign(overlay.style, {
            position: 'fixed', inset: '0', zIndex: '2147483647',
            background: 'rgba(0,0,0,.42)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', padding: '24px'
        });

        const panel = document.createElement('div');
        Object.assign(panel.style, {
            width: 'min(880px, 94vw)', maxHeight: '86vh', overflow: 'hidden',
            background: '#fff', color: '#111827', borderRadius: '12px',
            boxShadow: '0 20px 60px rgba(0,0,0,.28)', display: 'flex',
            flexDirection: 'column'
        });

        const header = document.createElement('div');
        Object.assign(header.style, {
            padding: '14px 16px', borderBottom: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        });
        header.innerHTML = '<strong>ChatHarbor · Archive Scan + Preflight Planner</strong><span style="font-size:12px;color:#047857;">DRY-RUN / READ-ONLY</span>';

        const body = document.createElement('pre');
        body.textContent = chPreflightReportText(plan);
        Object.assign(body.style, {
            margin: '0', padding: '16px', overflow: 'auto', whiteSpace: 'pre-wrap',
            wordBreak: 'break-word', fontSize: '12px', lineHeight: '1.55',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
            background: '#f9fafb', flex: '1'
        });

        const footer = document.createElement('div');
        Object.assign(footer.style, {
            padding: '12px 16px', borderTop: '1px solid #e5e7eb',
            display: 'flex', justifyContent: 'flex-end', gap: '8px'
        });
        const close = document.createElement('button');
        close.textContent = '关闭';
        Object.assign(close.style, {
            padding: '8px 14px', border: '1px solid #d1d5db', borderRadius: '6px',
            background: '#fff', cursor: 'pointer'
        });
        close.onclick = () => overlay.remove();
        footer.appendChild(close);

        panel.appendChild(header);
        panel.appendChild(body);
        panel.appendChild(footer);
        overlay.appendChild(panel);
        overlay.addEventListener('click', event => {
            if (event.target === overlay) overlay.remove();
        });
        document.body.appendChild(overlay);
    }

    async function chRunPreflightPlanner({ rootHandle, remoteList, selectedIds = null, remoteUniverseComplete = true, remoteUniverseNote = null, includeAttachments = false }) {
        chSetProgress('快速检查', '只读检查本地文件…', 0);
        const localScan = await chScanLocalArchiveReadOnly(rootHandle, info => {
            const seen = info.jsonFilesSeen || 0;
            const found = info.conversationJsonFiles || 0;
            chSetProgress(
                '快速检查 · 本地扫描',
                `已检查 JSON ${seen} · 识别对话 ${found}${info.path ? ` · ${info.path}` : ''}`,
                null
            );
        }, { checkAssets: true });
        if (localScan.manifest && chManifestRequiresLayoutMigration(localScan.manifest)) {
            throw new Error('Archive Layout v1 需要先执行纯本地 Layout v2 升级。');
        }

        chSetProgress('快速检查', '生成同步计划（不抓取详情、不写盘）…', 70);
        const plan = chBuildPreflightPlan(remoteList, localScan, selectedIds, {
            remoteUniverseComplete,
            remoteUniverseNote,
            includeAttachments
        });
        const s = plan.summary;
        chSetProgress(
            '快速检查完成',
            `NEW ${s.newCount} · 待核验 ${s.maximumFetchRequired - s.newCount} · UNCHANGED ${s.unchangedCount} · LOCAL_ONLY ${s.localOnlyReliable ? s.localOnlyCount : 'UNKNOWN'}`,
            100
        );
        chShowPreflightReport(plan);
        console.log('[ChatHarbor Integrated Sync] Preflight plan (read-only):', { localScan, plan });
        return { localScan, plan };
    }

    // ======================== ChatHarbor Integrated Version-aware Sync ========================
    // Clean-lineage ChatHarbor layer. Reuses huhusmang discovery/detail/Markdown/assets and
    // the validated directory writer/manifest baseline above.

    const CH_FINAL_SYNC_ACTIONS = new Set([
        'NEW',
        'UPDATED',
        'RENAMED_ONLY',
        'UPDATED_AND_RENAMED',
        'METADATA_ONLY',
        'ATTACHMENT_BACKFILL',
        'OBSERVATION_ONLY'
    ]);

    function chMergeRemoteEntries(entries) {
        const merged=new Map();
        for(const entry of Array.isArray(entries)?entries:[]){
            const id=chRemoteConversationId(entry); if(!id)continue;
            const normalized={...entry,id}; const existing=merged.get(id);
            if(!existing){merged.set(id,normalized);continue;}
            const existingTime=normalizeEpochSeconds(existing.update_time||0), incomingTime=normalizeEpochSeconds(normalized.update_time||0);
            const newer=incomingTime>existingTime?normalized:incomingTime<existingTime?existing:normalized;
            const older=newer===normalized?existing:normalized;
            const archiveA=existing.__chArchiveState||'known',archiveB=normalized.__chArchiveState||'known';
            const archiveConflict=archiveA==='known'&&archiveB==='known'&&Boolean(existing.is_archived)!==Boolean(normalized.is_archived)&&existingTime===incomingTime;
            const projectStateA=existing.__chProjectState||((existing.projectId||existing.projectTitle)?'known':'unknown');
            const projectStateB=normalized.__chProjectState||((normalized.projectId||normalized.projectTitle)?'known':'unknown');
            const projectKnownA=projectStateA==='known',projectKnownB=projectStateB==='known';
            const projectConflict=projectKnownA&&projectKnownB&&String(existing.projectId??'')!==String(normalized.projectId??'');
            const resolvedProject=projectConflict
                ? {id:null,title:null,state:'unknown'}
                : projectKnownB
                    ? {id:normalized.projectId??null,title:normalized.projectTitle??null,state:'known'}
                    : projectKnownA
                        ? {id:existing.projectId??null,title:existing.projectTitle??null,state:'known'}
                        : (projectStateA==='none'||projectStateB==='none')
                            ? {id:null,title:null,state:'none'}
                            : {id:null,title:null,state:'unknown'};
            merged.set(id,{
                ...older,...newer,id,
                projectId:resolvedProject.id,
                projectTitle:resolvedProject.title,
                __chProjectState:resolvedProject.state,
                is_archived:archiveConflict?Boolean(newer.is_archived):Boolean(newer.is_archived),
                __chArchiveState:archiveConflict?'unknown':((newer.__chArchiveState||'known')==='unknown'?(older.__chArchiveState||'unknown'):'known'),
                create_time:newer.create_time||older.create_time||0,
                update_time:Math.max(existingTime,incomingTime)||newer.update_time||older.update_time||0
            });
        }
        return Array.from(merged.values());
    }

    const chRemoteRefreshFlights = new Map();

    function chRemoteCacheIdentity(workspaceId = null) {
        // Persistent cache must never guess across accounts. An explicit workspace is safe;
        // otherwise prefer the active account cookie and only fall back when exactly one
        // workspace identity is detectable. Ambiguous identity disables persistence.
        if (workspaceId) {
            const explicit = resolveWorkspaceId(workspaceId);
            return explicit ? `${CH_PROVIDER}:${explicit}` : null;
        }
        const cookieMatch = document.cookie.match(/(?:^|; )_account=([^;]+)/);
        if (cookieMatch?.[1]) return `${CH_PROVIDER}:${cookieMatch[1]}`;
        const detected = detectAllWorkspaceIds();
        return detected.length === 1 ? `${CH_PROVIDER}:${detected[0]}` : null;
    }

    function chOpenRemoteCacheDb() {
        return new Promise((resolve,reject)=>{
            if(typeof indexedDB==='undefined'){resolve(null);return;}
            const req=indexedDB.open(CH_REMOTE_CACHE_DB,1);
            req.onupgradeneeded=()=>{const db=req.result;if(!db.objectStoreNames.contains(CH_REMOTE_CACHE_STORE))db.createObjectStore(CH_REMOTE_CACHE_STORE,{keyPath:'key'});};
            req.onsuccess=()=>resolve(req.result); req.onerror=()=>reject(req.error||new Error('IndexedDB open failed'));
        });
    }

    async function chRemoteCacheGet(workspaceId = null) {
        const key=chRemoteCacheIdentity(workspaceId); if(!key)return null;
        try{const db=await chOpenRemoteCacheDb();if(!db)return null;return await new Promise((resolve,reject)=>{const tx=db.transaction(CH_REMOTE_CACHE_STORE,'readonly');const req=tx.objectStore(CH_REMOTE_CACHE_STORE).get(key);req.onsuccess=()=>resolve(req.result||null);req.onerror=()=>reject(req.error);});}catch(err){console.warn('[ChatHarbor] remote cache read failed',err);return null;}
    }

    async function chRemoteCachePut(workspaceId, snapshot) {
        const key=chRemoteCacheIdentity(workspaceId); if(!key)return false;
        try{const db=await chOpenRemoteCacheDb();if(!db)return false;const value={...snapshot,key,schema:CH_REMOTE_CACHE_SCHEMA,provider:CH_PROVIDER};await new Promise((resolve,reject)=>{const tx=db.transaction(CH_REMOTE_CACHE_STORE,'readwrite');tx.objectStore(CH_REMOTE_CACHE_STORE).put(value);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('cache transaction aborted'));});return true;}catch(err){console.warn('[ChatHarbor] remote cache write failed',err);return false;}
    }

    function chHeadFingerprintEntry(entry) {
        return [entry.__chSourceKey||'',chRemoteConversationId(entry),String(entry.title||''),normalizeEpochSeconds(entry.update_time||0),entry.__chArchiveState||'unknown',entry.is_archived===true?'1':entry.is_archived===false?'0':'?',entry.__chProjectState||'unknown',String(entry.projectId??''),String(entry.projectTitle??'')].join('|');
    }

    function chHeadFingerprint(entries) {
        return (entries||[]).map(chHeadFingerprintEntry).sort().join('\n');
    }

    async function chRemoteHeaders(workspaceId = null) {
        if(!await ensureAccessToken())throw new Error('无法获取 Access Token。');
        const deviceId=getOaiDeviceId(); if(!deviceId)throw new Error('无法获取 oai-device-id。');
        const headers={'Authorization':`Bearer ${accessToken}`,'oai-device-id':deviceId};
        const resolved=resolveWorkspaceId(workspaceId); if(resolved)headers['ChatGPT-Account-Id']=resolved;
        return headers;
    }

    async function chFetchRootHead(workspaceId = null, limit = CH_REMOTE_HEAD_LIMIT, options = {}) {
        const headers=await chRemoteHeaders(workspaceId); const entries=[];
        for(const archived of [false,true]){
            options.onProgress?.({stage:'head-root',message:`快速核对${archived?'已归档':'未归档'}列表…`});
            const r=await fetch(`/backend-api/conversations?offset=0&limit=${limit}&order=updated${archived?'&is_archived=true':''}`,{headers});
            if(!r.ok)throw new Error(`远端列表快速刷新失败 (${r.status})`);
            const j=await r.json();
            for(const item of j.items||[])entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:archived,projectId:null,projectTitle:null,__chArchiveState:'known',__chProjectState:'unknown',__chSourceKey:`root:${archived?'archived':'active'}`});
        }
        return entries;
    }

    async function chFetchProjectHead(workspaceId = null, limit = CH_REMOTE_HEAD_LIMIT, options = {}) {
        const resolved=resolveWorkspaceId(workspaceId); if(!resolved)return [];
        options.onProgress?.({stage:'head-project',message:'快速核对项目列表…'});
        const projects=await getProjectSpaces(resolved,{conversationsPerGizmo:limit,ownedOnly:true}); const entries=[];
        for(const project of projects)for(const item of project.conversations||[])entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:item.is_archived??false,projectId:project.id,projectTitle:project.title,__chArchiveState:Object.prototype.hasOwnProperty.call(item||{},'is_archived')?'known':'unknown',__chProjectState:'known',__chSourceKey:`project:${project.id}`});
        return entries;
    }

    async function chFetchRemoteHeadSnapshot(workspaceId = null, options = {}) {
        const entries=[...(await chFetchRootHead(workspaceId,CH_REMOTE_HEAD_LIMIT,options)),...(await chFetchProjectHead(workspaceId,CH_REMOTE_HEAD_LIMIT,options))];
        return {entries,fingerprint:chHeadFingerprint(entries),validatedAt:Date.now()};
    }

    async function chFetchRootFull(workspaceId = null, options = {}) {
        const headers=await chRemoteHeaders(workspaceId); const entries=[];
        for(const archived of [false,true]){
            let offset=0,hasMore=true,page=0;
            while(hasMore){
                page+=1;
                options.onProgress?.({stage:'root',archived,page,message:`读取${archived?'已归档':'未归档'}对话 · 第 ${page} 页…`});
                const r=await fetch(`/backend-api/conversations?offset=${offset}&limit=${PAGE_LIMIT}&order=updated${archived?'&is_archived=true':''}`,{headers});
                if(!r.ok)throw new Error(`远端列表完整刷新失败 (${r.status})`);
                const j=await r.json(); const items=Array.isArray(j.items)?j.items:[];
                for(const item of items)entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:archived,projectId:null,projectTitle:null,__chArchiveState:'known',__chProjectState:'unknown',__chSourceKey:`root:${archived?'archived':'active'}`});
                hasMore=items.length===PAGE_LIMIT; offset+=items.length;
                options.onPartial?.({list:chMergeRemoteEntries(entries),complete:false,note:`root ${entries.length} · project complement pending`,validatedAt:0,refreshMode:'partial-root'});
            }
        }
        return chMergeRemoteEntries(entries);
    }

    async function chFetchProjectFull(workspaceId = null, options = {}) {
        const resolved=resolveWorkspaceId(workspaceId); if(!resolved)return [];
        const headers=await chRemoteHeaders(resolved);
        options.onProgress?.({stage:'projects',message:'读取项目列表…'});
        const projects=await getProjectSpaces(resolved,{conversationsPerGizmo:PROJECT_SIDEBAR_PREVIEW,ownedOnly:true});
        const entries=[];
        for(let projectIndex=0;projectIndex<projects.length;projectIndex++){
            const project=projects[projectIndex];
            let cursor='0'; let fetched=false;
            options.onProgress?.({stage:'projects',current:projectIndex+1,total:projects.length,message:`读取项目 ${projectIndex+1}/${projects.length} · ${project.title}`});
            do{
                const r=await fetch(`/backend-api/gizmos/${project.id}/conversations?cursor=${cursor}`,{headers});
                if(!r.ok){
                    if(!fetched&&Array.isArray(project.conversations)&&project.conversations.length){
                        project.conversations.forEach(item=>entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:item.is_archived??false,projectId:project.id,projectTitle:project.title,__chArchiveState:Object.prototype.hasOwnProperty.call(item||{},'is_archived')?'known':'unknown',__chProjectState:'known',__chSourceKey:`project:${project.id}`}));
                        cursor=null; break;
                    }
                    throw new Error(`列举项目对话列表失败 (${r.status})`);
                }
                const j=await r.json();
                for(const item of j.items||[])entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:item.is_archived??false,projectId:project.id,projectTitle:project.title,__chArchiveState:Object.prototype.hasOwnProperty.call(item||{},'is_archived')?'known':'unknown',__chProjectState:'known',__chSourceKey:`project:${project.id}`});
                cursor=j.cursor||null; fetched=true;
            }while(cursor);
            options.onProjectPartial?.(entries.slice(),{current:projectIndex+1,total:projects.length,project});
        }
        return chMergeRemoteEntries(entries);
    }

    async function chFetchFullRemoteUniverse(workspaceId = null, options = {}) {
        const rootList=await chFetchRootFull(workspaceId,{
            onProgress:options.onProgress,
            onPartial:partial=>options.onPartial?.(partial)
        });
        options.onPartial?.({list:rootList,complete:false,note:`root complete ${rootList.length} · project complement pending`,validatedAt:0,refreshMode:'partial-root-complete'});
        let projectList=[]; let complete=true; let note=null;
        try{
            projectList=await chFetchProjectFull(workspaceId,{
                onProgress:options.onProgress,
                onProjectPartial:(partialProjects,meta)=>{
                    const merged=chMergeRemoteEntries(rootList.concat(partialProjects)).map(item=>({...item,__chProjectState:(item.projectId||item.projectTitle)?'known':'unknown',__chArchiveState:item.__chArchiveState||'unknown'}));
                    options.onPartial?.({list:merged,complete:false,note:`root ${rootList.length} · projects ${meta.current}/${meta.total}`,validatedAt:0,refreshMode:'partial-projects'});
                }
            });
        }catch(err){complete=false;note=`project complement failed: ${err?.message||String(err)}`;}
        const merged=chMergeRemoteEntries(rootList.concat(projectList)).map(item=>({...item,__chProjectState:(item.projectId||item.projectTitle)?'known':complete?'none':'unknown',__chArchiveState:item.__chArchiveState||'unknown'}));
        return {list:merged,complete,note:note||`full remote index ${merged.length}`};
    }

    async function chRefreshRemoteIndex(workspaceId = null, { forceFull = false, onProgress = null, onPartial = null } = {}) {
        const flightKey=chRemoteCacheIdentity(workspaceId)||`volatile:${workspaceId||'default'}`;
        if(chRemoteRefreshFlights.has(flightKey))return chRemoteRefreshFlights.get(flightKey);
        const callbacks={onProgress,onPartial};
        const promise=(async()=>{
            const cached=await chRemoteCacheGet(workspaceId); const now=Date.now();
            const needsPeriodicFull=!cached||cached.schema!==CH_REMOTE_CACHE_SCHEMA||cached.provider!==CH_PROVIDER||cached.complete!==true||!cached.fullFetchedAt||(now-cached.fullFetchedAt)>=CH_REMOTE_FULL_REFRESH_MS;
            if(forceFull||needsPeriodicFull){
                callbacks.onProgress?.({stage:'full',message:'完整刷新云端对话…'});
                const progressiveCallbacks={...callbacks,onPartial:partial=>{
                    callbacks.onPartial?.(partial);
                    if(!cached?.complete && partial?.list?.length){
                        void chRemoteCachePut(workspaceId,{...partial,complete:false,fullFetchedAt:Number(cached?.fullFetchedAt||0),validatedAt:Number(cached?.validatedAt||0),headFingerprint:cached?.headFingerprint||null,note:partial.note||'progressive incomplete remote index'});
                    }
                }};
                const full=await chFetchFullRemoteUniverse(workspaceId,progressiveCallbacks);
                let head={validatedAt:Date.now(),fingerprint:null};
                try{head=await chFetchRemoteHeadSnapshot(workspaceId,callbacks);}catch(err){console.warn('[ChatHarbor] head fingerprint refresh failed after full snapshot',err);}
                const snapshot={list:full.list,complete:full.complete,note:full.note,fullFetchedAt:now,validatedAt:head.validatedAt||Date.now(),headFingerprint:head.fingerprint||null};
                // Incomplete snapshots are still useful UI/discovery cache, but never prove LOCAL_ONLY.
                await chRemoteCachePut(workspaceId,snapshot);
                return {...snapshot,refreshMode:full.complete?'full':'full-incomplete'};
            }
            callbacks.onProgress?.({stage:'fast',message:`快速核对最新 ${CH_REMOTE_HEAD_LIMIT} 条…`});
            const head=await chFetchRemoteHeadSnapshot(workspaceId,callbacks);
            if(head.fingerprint===cached.headFingerprint){
                const snapshot={...cached,validatedAt:head.validatedAt,note:`fast refresh stable · head ${CH_REMOTE_HEAD_LIMIT}`};
                await chRemoteCachePut(workspaceId,snapshot); return {...snapshot,refreshMode:'fast-stable'};
            }
            callbacks.onProgress?.({stage:'full-after-change',message:'发现远端索引变化，转完整刷新…'});
            const full=await chFetchFullRemoteUniverse(workspaceId,callbacks); const refreshedHead=await chFetchRemoteHeadSnapshot(workspaceId,callbacks);
            const snapshot={list:full.list,complete:full.complete,note:full.note,fullFetchedAt:Date.now(),validatedAt:refreshedHead.validatedAt,headFingerprint:refreshedHead.fingerprint};
            await chRemoteCachePut(workspaceId,snapshot);
            return {...snapshot,refreshMode:full.complete?'full-after-change':'full-after-change-incomplete'};
        })().finally(()=>chRemoteRefreshFlights.delete(flightKey));
        chRemoteRefreshFlights.set(flightKey,promise); return promise;
    }

    function chTargetRelativePrefix(entry) {
        if (!entry?.projectTitle) return `${CH_LAYOUT_CONVERSATIONS_DIR}/`;
        const projectDirName = sanitizeFilename(entry.projectTitle) || 'Untitled Project';
        return `${CH_LAYOUT_PROJECTS_DIR}/${projectDirName}/`;
    }

    function chTargetRelativePrefixForRecord(record) {
        return chTargetRelativePrefix({ projectTitle: record?.project_title || null });
    }

    function chSplitPath(path) {
        return String(path || '').split('/').filter(Boolean);
    }

    function chPathBasename(path) {
        const parts = chSplitPath(path);
        return parts.length ? parts[parts.length - 1] : '';
    }

    function chPathDirname(path) {
        const parts = chSplitPath(path);
        parts.pop();
        return parts.join('/');
    }

    async function chEnsureRelativeDirectory(rootHandle, relativeDir = '') {
        let dir = rootHandle;
        for (const segment of chSplitPath(relativeDir)) {
            dir = await dir.getDirectoryHandle(segment, { create: true });
        }
        return dir;
    }

    async function chGetFileAtRelativePath(rootHandle, relativePath) {
        const parts = chSplitPath(relativePath);
        if (!parts.length) throw new Error('file path missing');
        let dir = rootHandle;
        for (let i = 0; i < parts.length - 1; i++) dir = await dir.getDirectoryHandle(parts[i]);
        const handle = await dir.getFileHandle(parts[parts.length - 1]);
        return { handle, file: await handle.getFile() };
    }

    async function chRelativeFileExists(rootHandle, relativePath) {
        if (!relativePath) return false;
        try { await chGetFileAtRelativePath(rootHandle, relativePath); return true; }
        catch (err) { if (err?.name === 'NotFoundError') return false; throw err; }
    }

    async function chSha256Bytes(data) {
        const buffer = data instanceof ArrayBuffer
            ? data
            : ArrayBuffer.isView(data)
                ? data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength)
                : await data.arrayBuffer();
        return chHex(await crypto.subtle.digest('SHA-256', buffer));
    }

    async function chCopyRelativeFileVerified(rootHandle, sourcePath, targetPath) {
        if (!sourcePath || !targetPath) throw new Error('migration source/target path missing');
        if (sourcePath === targetPath) {
            if (!await chRelativeFileExists(rootHandle, sourcePath)) throw new Error(`migration source missing: ${sourcePath}`);
            return { copied: false, reused: true, bytes: (await chGetFileAtRelativePath(rootHandle, sourcePath)).file.size };
        }
        const source = await chGetFileAtRelativePath(rootHandle, sourcePath);
        const sourceBytes = await source.file.arrayBuffer();
        const sourceHash = await chSha256Bytes(sourceBytes);
        const targetParts = chSplitPath(targetPath);
        const targetName = targetParts.pop();
        const targetDir = await chEnsureRelativeDirectory(rootHandle, targetParts.join('/'));
        let targetExists = false;
        try {
            const existingHandle = await targetDir.getFileHandle(targetName);
            const existingFile = await existingHandle.getFile();
            targetExists = true;
            if (existingFile.size === source.file.size && await chSha256Bytes(existingFile) === sourceHash) {
                return { copied: false, reused: true, bytes: existingFile.size };
            }
            throw new Error(`migration target collision: ${targetPath}`);
        } catch (err) {
            if (targetExists || err?.name !== 'NotFoundError') throw err;
        }
        await chVerifiedDirectoryWrite(targetDir, targetName, sourceBytes);
        const written = await targetDir.getFileHandle(targetName);
        const writtenFile = await written.getFile();
        if (writtenFile.size !== source.file.size || await chSha256Bytes(writtenFile) !== sourceHash) {
            throw new Error(`migration verification failed: ${targetPath}`);
        }
        return { copied: true, reused: false, bytes: writtenFile.size };
    }

    function chMigrationExpectedRecord(record) {
        const prefix = chTargetRelativePrefixForRecord(record);
        const jsonName = chPathBasename(record?.json_path || '');
        const markdownName = chPathBasename(record?.markdown_path || '');
        if (!jsonName || !markdownName) throw new Error(`tracked conversation ${record?.conversation_id || ''} is missing JSON/Markdown path`);
        const oldAssets = Array.isArray(record?.assets) ? record.assets : [];
        const oldAssetDir = record?.asset_dir || (oldAssets.length ? chPathDirname(oldAssets[0]?.path || '') : null);
        const assetFolderName = oldAssetDir ? chPathBasename(oldAssetDir) : null;
        const newAssetDir = assetFolderName ? `${prefix}${assetFolderName}` : null;
        const assets = oldAssets.map(asset => {
            const name = chPathBasename(asset?.path || '') || asset?.name;
            if (!name || !newAssetDir) throw new Error(`tracked asset path is incomplete for ${record?.conversation_id || ''}`);
            return {
                ...asset,
                path: `${newAssetDir}/${name}`,
                markdown_path: encodeRelativePath(`${assetFolderName}/${name}`)
            };
        });
        return {
            ...record,
            json_path: `${prefix}${jsonName}`,
            markdown_path: `${prefix}${markdownName}`,
            asset_dir: newAssetDir,
            assets
        };
    }

    function chMigrationPreviousPaths(record) {
        return {
            json_path: record?.json_path || null,
            markdown_path: record?.markdown_path || null,
            asset_dir: record?.asset_dir || null,
            assets: (record?.assets || []).map(asset => ({ path: asset?.path || null })).filter(asset => asset.path)
        };
    }

    function chMigrationOldRecordFromMarker(currentRecord) {
        const previous = currentRecord?.migration_previous_paths;
        if (!previous) return null;
        return {
            json_path: previous.json_path || null,
            markdown_path: previous.markdown_path || null,
            asset_dir: previous.asset_dir || null,
            assets: Array.isArray(previous.assets) ? previous.assets : []
        };
    }

    async function chArchiveLayoutState(rootHandle) {
        const result = await chReadManifestForScan(rootHandle);
        if (result.error) throw new Error(result.error);
        if (!result.exists || !result.manifest) {
            return {
                manifestExists: false,
                provider: CH_PROVIDER,
                layoutVersion: CH_ARCHIVE_LAYOUT_VERSION,
                requiresMigration: false,
                migrationInProgress: false,
                total: 0,
                project: 0,
                root: 0
            };
        }
        const manifest = result.manifest;
        const records = Object.values(manifest.conversations || {});
        return {
            manifestExists: true,
            provider: chManifestProvider(manifest) || CH_PROVIDER,
            layoutVersion: chManifestLayoutVersion(manifest),
            requiresMigration: chManifestRequiresLayoutMigration(manifest),
            migrationInProgress: Boolean(manifest.migration_state?.type === 'archive_layout'),
            total: records.length,
            project: records.filter(record => record?.project_id || record?.project_title).length,
            root: records.filter(record => !(record?.project_id || record?.project_title)).length,
            manifest
        };
    }

    async function chMigrateArchiveLayoutV1ToV2(rootHandle, onProgress = null) {
        if (!rootHandle) throw new Error('Directory handle is required');
        const manifest = await chReadManifest(rootHandle);
        const layout = chManifestLayoutVersion(manifest);
        if (layout > CH_ARCHIVE_LAYOUT_VERSION) throw new Error(`unsupported archive layout: ${layout}`);
        if (layout === CH_ARCHIVE_LAYOUT_VERSION && !manifest.migration_state) {
            return { migrated: 0, alreadyCurrent: true, cleanupWarnings: [], total: Object.keys(manifest.conversations || {}).length };
        }

        const entries = Object.entries(manifest.conversations || {});
        const cleanupWarnings = [];
        const legacyTopDirs = new Set();
        let migrated = 0;

        // Full local-only preflight: every tracked JSON/Markdown must exist before any new
        // conversation is committed. This migration never fetches remote conversation detail.
        for (const [id, record] of entries) {
            const previous = record?.migration_previous_paths || chMigrationPreviousPaths(record);
            for (const requiredPath of [previous.json_path, previous.markdown_path]) {
                if (requiredPath && !await chRelativeFileExists(rootHandle, requiredPath) && !await chRelativeFileExists(rootHandle, chMigrationExpectedRecord(record)[requiredPath === previous.json_path ? 'json_path' : 'markdown_path'])) {
                    throw new Error(`migration source missing for ${id}: ${requiredPath}`);
                }
            }
            const first = chSplitPath(previous.json_path || '')[0];
            if (record?.project_title && first && ![CH_LAYOUT_PROJECTS_DIR, CH_LAYOUT_CONVERSATIONS_DIR].includes(first)) legacyTopDirs.add(first);
        }

        manifest.provider = CH_PROVIDER;
        manifest.source = CH_PROVIDER_LABEL;
        manifest.migration_state = manifest.migration_state || {
            type: 'archive_layout',
            from: layout,
            to: CH_ARCHIVE_LAYOUT_VERSION,
            status: 'in_progress',
            started_at: new Date().toISOString()
        };
        await chWriteManifest(rootHandle, manifest);

        for (let index = 0; index < entries.length; index++) {
            const [id] = entries[index];
            let record = manifest.conversations[id];
            if (!record) continue;
            if (onProgress) onProgress({ index, total: entries.length, id, title: record.title || id, phase: 'prepare' });

            // Resume-safe cleanup if a prior run committed the v2 paths but was interrupted before cleanup.
            if (record.migration_previous_paths) {
                const oldRecord = chMigrationOldRecordFromMarker(record);
                const cleanup = await chCleanupTrackedOldPaths({ rootHandle, oldRecord, newRecord: record, manifest, currentId: id });
                cleanupWarnings.push(...(cleanup.warnings || []).map(w => `${id}: ${w}`));
                delete record.migration_previous_paths;
                manifest.conversations[id] = record;
                await chWriteManifest(rootHandle, manifest);
                migrated++;
                if (onProgress) onProgress({ index: index + 1, total: entries.length, id, title: record.title || id, phase: 'resumed' });
                continue;
            }

            const oldRecord = JSON.parse(JSON.stringify(record));
            const expected = chMigrationExpectedRecord(record);
            const copies = [
                [record.json_path, expected.json_path],
                [record.markdown_path, expected.markdown_path]
            ];
            const oldAssets = Array.isArray(record.assets) ? record.assets : [];
            for (let i = 0; i < oldAssets.length; i++) copies.push([oldAssets[i]?.path, expected.assets[i]?.path]);

            for (const [sourcePath, targetPath] of copies) {
                if (!sourcePath || !targetPath) continue;
                await chCopyRelativeFileVerified(rootHandle, sourcePath, targetPath);
            }

            const committed = {
                ...expected,
                migration_previous_paths: chMigrationPreviousPaths(oldRecord)
            };
            manifest.conversations[id] = committed;
            await chWriteManifest(rootHandle, manifest);

            const cleanup = await chCleanupTrackedOldPaths({ rootHandle, oldRecord, newRecord: committed, manifest, currentId: id });
            cleanupWarnings.push(...(cleanup.warnings || []).map(w => `${id}: ${w}`));
            delete committed.migration_previous_paths;
            manifest.conversations[id] = committed;
            await chWriteManifest(rootHandle, manifest);
            migrated++;
            if (onProgress) onProgress({ index: index + 1, total: entries.length, id, title: committed.title || id, phase: 'committed' });
        }

        // Verify every canonical v2 JSON/Markdown before declaring the archive upgraded.
        for (const [id, record] of Object.entries(manifest.conversations || {})) {
            const expected = chMigrationExpectedRecord(record);
            if (record.json_path !== expected.json_path || record.markdown_path !== expected.markdown_path) {
                throw new Error(`layout verification failed for ${id}`);
            }
            if (!await chRelativeFileExists(rootHandle, record.json_path) || !await chRelativeFileExists(rootHandle, record.markdown_path)) {
                throw new Error(`migrated files missing for ${id}`);
            }
        }

        manifest.provider = CH_PROVIDER;
        manifest.source = CH_PROVIDER_LABEL;
        manifest.archive_layout_version = CH_ARCHIVE_LAYOUT_VERSION;
        delete manifest.migration_state;
        await chWriteManifest(rootHandle, manifest);

        // Best-effort removal of now-empty legacy project containers only. Anything untracked
        // prevents removal and is deliberately preserved.
        for (const name of legacyTopDirs) {
            try { await rootHandle.removeEntry(name, { recursive: false }); }
            catch (err) { if (err?.name !== 'NotFoundError') cleanupWarnings.push(`legacy directory preserved: ${name}`); }
        }

        return {
            migrated,
            alreadyCurrent: false,
            total: entries.length,
            cleanupWarnings,
            provider: CH_PROVIDER,
            archiveLayoutVersion: CH_ARCHIVE_LAYOUT_VERSION
        };
    }

    function chEncodeRelativeSegments(segments) {
        return segments.map(segment => segment === '..' ? '..' : encodeURIComponent(segment)).join('/');
    }

    function chRelativeMarkdownPath(fromPrefix, targetRootRelativePath) {
        const from = chSplitPath(fromPrefix);
        const to = chSplitPath(targetRootRelativePath);
        let common = 0;
        while (common < from.length && common < to.length && from[common] === to[common]) common++;
        const parts = [
            ...Array(Math.max(0, from.length - common)).fill('..'),
            ...to.slice(common)
        ];
        return chEncodeRelativeSegments(parts);
    }

    function chExistingAttachmentResultForPrefix(existingRecord, targetPrefix) {
        const base = chExistingAttachmentResult(existingRecord);
        if (!base) return null;
        const assets = Array.isArray(existingRecord?.assets) ? existingRecord.assets : [];
        const sandboxPaths = new Map();
        let sandboxSourceComplete = true;
        const files = assets.map(asset => {
            const relativeLink = chRelativeMarkdownPath(targetPrefix, asset.path || '');
            if (asset?.kind === 'sandbox') {
                if (asset.message_id && asset.source_sandbox_path) {
                    sandboxPaths.set(`${asset.message_id}|${asset.source_sandbox_path}`, relativeLink);
                } else {
                    sandboxSourceComplete = false;
                }
            }
            return {
                name: asset.name,
                path: relativeLink,
                disk_path: asset.path,
                kind: asset.kind,
                isImage: Boolean(asset.is_image),
                messageId: asset.message_id || null,
                ownerRole: asset.owner_role || null,
                size_bytes: asset.size_bytes || 0,
                source_file_id: asset.source_file_id || null,
                source_sandbox_path: asset.source_sandbox_path || null
            };
        });
        return {
            ...base,
            files,
            sandboxPaths,
            sandboxSourceComplete
        };
    }

    function chFinalMetadataDiffs(remote, local) {
        const reasons=[];
        const archiveKnown=(remote?.__chArchiveState||'known')!=='unknown';
        const projectKnown=(remote?.__chProjectState||'known')!=='unknown';
        if(archiveKnown&&Object.prototype.hasOwnProperty.call(remote||{},'is_archived')&&Boolean(remote?.is_archived)!==Boolean(chRecordListArchiveState(local)))reasons.push('ARCHIVE_STATE_DIFF');
        if(projectKnown&&String(remote?.projectId??'')!==String(chRecordListProjectId(local)??''))reasons.push('PROJECT_ID_DIFF');
        if(projectKnown&&String(remote?.projectTitle??'')!==String(chRecordListProjectTitle(local)??''))reasons.push('PROJECT_TITLE_DIFF');
        return reasons;
    }

    async function chClassifyFetchedConversation(preflightItem, convData, options = {}) {
        const includeAttachments=Boolean(options.includeAttachments);
        const remote=preflightItem?.remote||{}; const local=preflightItem?.local||null;
        const id=chGetConversationId(remote,convData); const detailTitle=String(convData?.title||remote?.title||'');
        const remoteUpdateTime=convData?.update_time??remote?.update_time??null; const newSignature=await chContentSignature(convData);
        const attachmentInspection=chInspectAttachmentCompleteness(convData,local);
        if(!local)return {...preflightItem,id,finalAction:'NEW',convData,newSignature,contentChanged:true,titleChanged:false,metadataChanged:false,timestampChanged:false,attachmentInspection,needs_sync:true,finalReasons:['NOT_IN_LOCAL_ARCHIVE']};
        if(local.tracking!=='manifest')return {...preflightItem,id,finalAction:'LOCAL_UNTRACKED',convData,newSignature,contentChanged:null,titleChanged:detailTitle!==String(local?.title||''),metadataChanged:false,timestampChanged:chTimeRelation(remoteUpdateTime,local?.remote_update_time)!=='same',attachmentInspection,needs_sync:true,finalReasons:['LOCAL_RAW_NOT_MANIFEST_TRACKED','NO_AUTHORITATIVE_LOCAL_SIGNATURE']};
        const oldSignature=String(local?.content_signature||'');
        if(!oldSignature)return {...preflightItem,id,finalAction:'ERROR',convData,newSignature,contentChanged:null,titleChanged:detailTitle!==String(local?.title||''),metadataChanged:null,timestampChanged:null,attachmentInspection,needs_sync:false,finalReasons:['LOCAL_SIGNATURE_MISSING'],error:'Tracked manifest record has no content_signature'};

        const contentChanged=newSignature!==oldSignature;
        const titleChanged=detailTitle!==String(local?.title||'');
        const metadataReasons=chFinalMetadataDiffs(remote,local); const metadataChanged=metadataReasons.length>0;
        const timestampChanged=chTimeRelation(remoteUpdateTime,local?.remote_update_time)==='different';
        const attachmentBackfill=includeAttachments&&!['complete','none'].includes(attachmentInspection.state);
        let finalAction='OBSERVATION_ONLY';
        if(contentChanged&&titleChanged)finalAction='UPDATED_AND_RENAMED';
        else if(contentChanged)finalAction='UPDATED';
        else if(titleChanged)finalAction='RENAMED_ONLY';
        else if(attachmentBackfill)finalAction='ATTACHMENT_BACKFILL';
        else if(metadataChanged)finalAction='METADATA_ONLY';
        return {...preflightItem,id,finalAction,convData,newSignature,contentChanged,titleChanged,metadataChanged,timestampChanged,attachmentInspection,attachmentBackfill,needs_sync:true,finalReasons:[...(contentChanged?['CONTENT_SIGNATURE_DIFF']:[]),...(titleChanged?['TITLE_DIFF']:[]),...metadataReasons,...(timestampChanged?['DETAIL_UPDATE_TIME_DIFF']:[]),...(attachmentBackfill?[`ATTACHMENT_${attachmentInspection.state.toUpperCase()}`]:[]),...(finalAction==='OBSERVATION_ONLY'?['REMOTE_OBSERVATION_ADVANCE']:[])]};
    }

    async function chVerifyPreflightCandidates({ plan, workspaceId = null }) {
        const resultItems = [];
        const fetchItems = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE');
        const fetchTotal = fetchItems.length;

        if (fetchTotal > 0 && !await ensureAccessToken()) {
            throw new Error('当前登录信息不可用。请刷新 ChatGPT 页面后再试。');
        }

        let fetchIndex = 0;
        for (const item of plan.items) {
            if (!item.needs_detail_fetch || item.action === 'ERROR' || item.action === 'DUPLICATE') {
                resultItems.push({
                    ...item,
                    finalAction: item.action,
                    needs_sync: false,
                    finalReasons: item.reasons || []
                });
                continue;
            }

            const title = item.remote?.title || item.local?.title || item.id;
            chSetProgress(
                '核验远端详情',
                `${fetchIndex + 1}/${fetchTotal} · ${String(title).slice(0, 60)}`,
                fetchTotal ? Math.round((fetchIndex / fetchTotal) * 45) : 45
            );
            try {
                await chControlCheckpoint('detail-verification');
                const convData = await chGetConversationConservative(item.id, workspaceId, title);
                resultItems.push(await chClassifyFetchedConversation(item, convData, { includeAttachments: false }));
            } catch (err) {
                if (chIsCancellation(err)) throw err;
                resultItems.push({
                    ...item,
                    finalAction: 'ERROR',
                    needs_sync: false,
                    finalReasons: ['DETAIL_FETCH_OR_CLASSIFICATION_FAILED'],
                    error: err?.message || String(err)
                });
            }
            fetchIndex++;
        }

        const counts = {};
        for (const item of resultItems) counts[item.finalAction] = (counts[item.finalAction] || 0) + 1;
        return {
            items: resultItems,
            counts,
            detailFetchCount: fetchTotal
        };
    }

    function chExpectedStoragePaths(entry, convData) {
        const prefix = chTargetRelativePrefix(entry);
        return {
            prefix,
            json_path: `${prefix}${generateUniqueFilename(convData)}`,
            markdown_path: `${prefix}${generateMarkdownFilename(convData)}`
        };
    }

    function chMetadataOnlyRecord(existingRecord, classifiedItem) {
        const remote=classifiedItem.remote||{}; const convData=classifiedItem.convData||{};
        const observed=chRemoteObservation(remote,existingRecord);
        const inspection=classifiedItem.attachmentInspection||null;
        const projectKnown=(remote?.__chProjectState||'known')!=='unknown';
        const archiveKnown=(remote?.__chArchiveState||'known')!=='unknown';
        return {
            ...existingRecord,
            title: convData.title || existingRecord.title,
            create_time: convData.create_time ?? remote.create_time ?? existingRecord.create_time ?? null,
            remote_update_time: convData.update_time ?? existingRecord.remote_update_time ?? null,
            is_archived: archiveKnown ? Boolean(remote?.is_archived) : (existingRecord.is_archived ?? false),
            project_id: projectKnown ? (remote?.projectId ?? null) : (existingRecord.project_id ?? null),
            project_title: projectKnown ? (remote?.projectTitle ?? null) : (existingRecord.project_title ?? null),
            ...observed,
            provider:CH_PROVIDER,archive_layout_version:CH_ARCHIVE_LAYOUT_VERSION,
            content_signature:classifiedItem.newSignature||existingRecord.content_signature,signature_version:CH_SIGNATURE_VERSION,
            attachment_state:inspection?.state||chRecordAttachmentState(existingRecord),
            attachments_checked_at:inspection?new Date().toISOString():(existingRecord.attachments_checked_at||null),
            attachment_detected:inspection?.detected??existingRecord.attachment_detected,
            // synced_at intentionally remains the last content/file commit time.
            synced_at: existingRecord.synced_at || null
        };
    }

    function chManifestPathReferencedElsewhere(manifest, currentId, path) {
        if (!path) return false;
        for (const [id, record] of Object.entries(manifest?.conversations || {})) {
            if (id === currentId) continue;
            if (record?.json_path === path || record?.markdown_path === path || record?.asset_dir === path) return true;
            if ((record?.assets || []).some(asset => asset?.path === path)) return true;
        }
        return false;
    }

    async function chRemoveTrackedEntry(rootHandle, relativePath, isDirectory = false) {
        if (!relativePath) return { removed: false, reason: 'EMPTY_PATH' };
        const parts = chSplitPath(relativePath);
        if (parts.length === 0) return { removed: false, reason: 'EMPTY_PATH' };
        try {
            let dir = rootHandle;
            for (let i = 0; i < parts.length - 1; i++) {
                dir = await dir.getDirectoryHandle(parts[i]);
            }
            if (isDirectory) await dir.removeEntry(parts[parts.length - 1], { recursive: false });
            else await dir.removeEntry(parts[parts.length - 1]);
            return { removed: true, reason: null };
        } catch (err) {
            if (err?.name === 'NotFoundError') return { removed: false, reason: 'ALREADY_MISSING' };
            return { removed: false, reason: err?.message || String(err) };
        }
    }

    async function chCleanupTrackedOldPaths({ rootHandle, oldRecord, newRecord, manifest, currentId }) {
        if (!oldRecord) return { removed: [], warnings: [] };
        const removed = [];
        const warnings = [];
        const newAssetPaths = new Set((newRecord?.assets || []).map(asset => asset?.path).filter(Boolean));
        const candidates = [];

        if (oldRecord.json_path && oldRecord.json_path !== newRecord.json_path) {
            candidates.push({ path: oldRecord.json_path, kind: 'json' });
        }
        if (oldRecord.markdown_path && oldRecord.markdown_path !== newRecord.markdown_path) {
            candidates.push({ path: oldRecord.markdown_path, kind: 'markdown' });
        }
        for (const asset of oldRecord.assets || []) {
            if (asset?.path && !newAssetPaths.has(asset.path)) {
                candidates.push({ path: asset.path, kind: 'asset' });
            }
        }

        for (const candidate of candidates) {
            if (chManifestPathReferencedElsewhere(manifest, currentId, candidate.path)) {
                warnings.push(`${candidate.kind}: shared path preserved: ${candidate.path}`);
                continue;
            }
            const outcome = await chRemoveTrackedEntry(rootHandle, candidate.path, false);
            if (outcome.removed) removed.push(candidate.path);
            else if (outcome.reason !== 'ALREADY_MISSING') warnings.push(`${candidate.kind}: ${candidate.path}: ${outcome.reason}`);
        }

        if (oldRecord.asset_dir && oldRecord.asset_dir !== newRecord.asset_dir &&
            !chManifestPathReferencedElsewhere(manifest, currentId, oldRecord.asset_dir)) {
            // Non-recursive on purpose. If any untracked legacy asset remains, the directory stays.
            const outcome = await chRemoveTrackedEntry(rootHandle, oldRecord.asset_dir, true);
            if (outcome.removed) removed.push(oldRecord.asset_dir);
            else if (!['ALREADY_MISSING', 'Directory not empty'].includes(outcome.reason)) {
                // Browser error text is implementation-specific; any failure is safe because cleanup is best-effort.
                warnings.push(`asset_dir preserved: ${oldRecord.asset_dir}: ${outcome.reason}`);
            }
        }

        return { removed, warnings };
    }

    async function chApplyClassifiedSyncItem({
        rootHandle,
        classifiedItem,
        manifest,
        workspaceId = null,
        includeAttachments = false,
        btn = null,
        conversationIndex = 0,
        conversationTotal = 1,
        deps = {}
    }) {
        const action = classifiedItem.finalAction;
        if (!CH_FINAL_SYNC_ACTIONS.has(action)) {
            return { status: 'SKIPPED', action, id: classifiedItem.id, reason: 'NOT_ACTIONABLE' };
        }

        const id = classifiedItem.id;
        const remote = classifiedItem.remote || {};
        const convData = classifiedItem.convData;
        if (!convData) throw new Error(`Missing fetched conversation detail for ${id}`);

        const writeConversation = deps.writeConversation || chWriteConversationToDirectory;
        const writeManifest = deps.writeManifest || chWriteManifest;
        const cleanup = deps.cleanup || chCleanupTrackedOldPaths;
        const oldRecord = manifest.conversations?.[id] || null;
        const expected = chExpectedStoragePaths(remote, convData);

        const metadataOnlyInPlace = ['METADATA_ONLY','OBSERVATION_ONLY'].includes(action) && oldRecord &&
            oldRecord.json_path === expected.json_path &&
            oldRecord.markdown_path === expected.markdown_path;

        if (metadataOnlyInPlace) {
            const updatedRecord = chMetadataOnlyRecord(oldRecord, classifiedItem);
            manifest.conversations[id] = updatedRecord;
            await writeManifest(rootHandle, manifest);
            return {
                status: 'SYNCED',
                mode: 'MANIFEST_ONLY',
                action,
                id,
                record: updatedRecord,
                cleanup: { removed: [], warnings: [] }
            };
        }

        const existingRecord = oldRecord || null;
        const existingAttachmentResultOverride = !includeAttachments && existingRecord
            ? chExistingAttachmentResultForPrefix(existingRecord, expected.prefix)
            : null;

        const record = await writeConversation({
            rootHandle,
            entry: remote,
            convData,
            workspaceId,
            includeAttachments,
            existingRecord,
            existingAttachmentResultOverride,
            btn: btn || getExportButton(),
            conversationIndex,
            conversationTotal
        });

        const newAssetPaths = Array.isArray(record.__ch_new_asset_paths) ? [...record.__ch_new_asset_paths] : [];
        delete record.__ch_new_asset_paths;
        const priorManifestRecord = manifest.conversations?.[record.conversation_id] || null;
        manifest.conversations[record.conversation_id] = record;
        try {
            await writeManifest(rootHandle, manifest);
        } catch (err) {
            if (priorManifestRecord) manifest.conversations[record.conversation_id] = priorManifestRecord;
            else delete manifest.conversations[record.conversation_id];
            for (const path of newAssetPaths) {
                try { await chRemoveTrackedEntry(rootHandle, path, false); } catch (_) {}
            }
            throw err;
        }

        const cleanupResult = oldRecord
            ? await cleanup({
                rootHandle,
                oldRecord,
                newRecord: record,
                manifest,
                currentId: record.conversation_id
            })
            : { removed: [], warnings: [] };

        return {
            status: 'SYNCED',
            mode: 'FILES_AND_MANIFEST',
            action,
            id: record.conversation_id,
            record,
            cleanup: cleanupResult
        };
    }

    function chIntegratedSyncReportText(result) {
        const c = result.verification.counts || {};
        const lines = [
            'ChatHarbor | Version-aware Selective Sync',
            'INTEGRATED BUILD',
            '',
            `Scope remote IDs: ${result.plan.summary.scopeRemote}`,
            `Detail fetched: ${result.verification.detailFetchCount}`,
            `NEW: ${c.NEW || 0}`,
            `UPDATED: ${c.UPDATED || 0}`,
            `RENAMED_ONLY: ${c.RENAMED_ONLY || 0}`,
            `UPDATED_AND_RENAMED: ${c.UPDATED_AND_RENAMED || 0}`,
            `METADATA_ONLY: ${c.METADATA_ONLY || 0}`,
            `UNCHANGED: ${c.UNCHANGED || 0}`,
            `LOCAL_UNTRACKED: ${c.LOCAL_UNTRACKED || 0}`,
            `LOCAL_ONLY: ${result.plan.summary.localOnlyReliable ? result.plan.summary.localOnlyCount : 'UNKNOWN'}`,
            `DUPLICATE: ${c.DUPLICATE || 0}`,
            `ERROR: ${c.ERROR || 0}`,
            '',
            `Sync attempted: ${result.sync.attempted}`,
            `Sync succeeded: ${result.sync.succeeded}`,
            `Sync failed: ${result.sync.failed}`,
            `Manifest-only commits: ${result.sync.manifestOnly}`,
            `File+manifest commits: ${result.sync.fileCommits}`,
            `Cleanup warnings: ${result.sync.cleanupWarnings.length}`,
            `Cancelled: ${result.sync.cancelled ? 'YES' : 'NO'}`,
            '',
            'LOCAL_ONLY was never deleted.',
            'Cleanup only touched paths explicitly tracked by the prior manifest.'
        ];

        if (!result.plan.summary.remoteUniverseComplete) {
            lines.push('', `Remote universe incomplete: ${result.plan.summary.remoteUniverseNote || 'unknown reason'}`);
        }
        if (result.sync.failures.length) {
            lines.push('', '=== SYNC FAILURES ===');
            for (const failure of result.sync.failures.slice(0, 50)) {
                lines.push(`[${failure.action}] ${failure.id}: ${failure.error}`);
            }
        }
        if (result.sync.cleanupWarnings.length) {
            lines.push('', '=== CLEANUP WARNINGS (safe leftovers preserved) ===');
            for (const warning of result.sync.cleanupWarnings.slice(0, 50)) lines.push(warning);
        }
        return lines.join('\n');
    }

    function chShowIntegratedSyncReport(result) {
        const existing = document.getElementById('ch-integrated-sync-report-overlay');
        if (existing) existing.remove();
        const overlay = document.createElement('div');
        overlay.id = 'ch-integrated-sync-report-overlay';
        Object.assign(overlay.style, {
            position: 'fixed', inset: '0', background: 'rgba(0,0,0,.52)', zIndex: '100001',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px'
        });
        const panel = document.createElement('div');
        Object.assign(panel.style, {
            width: 'min(860px, 95vw)', maxHeight: '86vh', overflow: 'auto', background: '#fff',
            color: '#111827', borderRadius: '12px', padding: '18px', boxShadow: '0 12px 36px rgba(0,0,0,.28)'
        });
        const title = document.createElement('div');
        title.textContent = 'ChatHarbor · Version-aware Sync';
        title.style.fontWeight = '700';
        title.style.marginBottom = '10px';
        const pre = document.createElement('pre');
        pre.textContent = chIntegratedSyncReportText(result);
        Object.assign(pre.style, {
            whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '12px', lineHeight: '1.55',
            background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '12px'
        });
        const close = document.createElement('button');
        close.textContent = '关闭';
        Object.assign(close.style, {
            marginTop: '12px', padding: '8px 14px', border: '1px solid #d1d5db', borderRadius: '6px',
            background: '#fff', cursor: 'pointer'
        });
        close.onclick = () => overlay.remove();
        panel.appendChild(title);
        panel.appendChild(pre);
        panel.appendChild(close);
        overlay.appendChild(panel);
        overlay.addEventListener('click', event => { if (event.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
    }

    async function chRunIntegratedDirectorySync({
        rootHandle,
        remoteList,
        selectedIds = null,
        workspaceId = null,
        includeAttachments = false,
        remoteUniverseComplete = true,
        remoteUniverseNote = null,
        networkPolicy = null,
        onItemClassified = null,
        onItemCommitted = null,
        onItemFailed = null
    }) {
        const selected = selectedIds instanceof Set && selectedIds.size > 0 ? selectedIds : null;
        if (!selected && !remoteUniverseComplete) {
            throw new Error('云端对话列表还没有加载完整。为避免漏同步，本轮不会写入，请稍后刷新重试。');
        }
        const ownsRun = !chSyncRun.active;
        if (ownsRun) chBeginControlledRun(networkPolicy || chLoadNetworkPolicy());
        else if (networkPolicy) chSyncRun.policy = chSaveNetworkPolicy(networkPolicy);

        chSetProgress('同步', `检查本地文件… · ${chNetworkPolicySummary(chSyncRun.policy)}`, 0);
        await chControlCheckpoint('local-scan');
        const localScan = await chScanLocalArchiveReadOnly(rootHandle, null, { checkAssets: true });
        if (localScan.manifestExists && !localScan.manifestReadable) {
            throw new Error('本地保存记录无法读取。为避免覆盖现有文件，本轮同步已停止。');
        }
        if (localScan.manifest && chManifestRequiresLayoutMigration(localScan.manifest)) {
            throw new Error('本地保存结构需要升级。请先完成升级，再开始同步。');
        }
        const plan = chBuildPreflightPlan(remoteList, localScan, selected, {
            remoteUniverseComplete,
            remoteUniverseNote,
            includeAttachments
        });
        const fetchTotal = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE').length;
        if (fetchTotal > 0 && !await ensureAccessToken()) {
            throw new Error('当前登录信息不可用。请刷新 ChatGPT 页面后再试。');
        }

        const manifest = await chReadManifest(rootHandle);
        const btn = getExportButton();
        const verification = { items: [], counts: {}, detailFetchCount: 0, cancelled: false };
        const sync = {
            attempted: 0,
            succeeded: 0,
            failed: 0,
            manifestOnly: 0,
            fileCommits: 0,
            cleanupWarnings: [],
            results: [],
            failures: [],
            cancelled: false
        };
        let fetchIndex = 0;
        const fastItems = plan.items.filter(item => !item.needs_detail_fetch || item.action === 'ERROR' || item.action === 'DUPLICATE');
        const workItems = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE');
        for (const item of fastItems) {
            const classified = { ...item, finalAction: item.action, needs_sync: false, finalReasons: item.reasons || [] };
            verification.items.push(classified);
            verification.counts[classified.finalAction] = (verification.counts[classified.finalAction] || 0) + 1;
        }
        const totalItems = Math.max(1, workItems.length);
        chSetRuntimeProgress({ active: workItems.length > 0, processed: 0, total: workItems.length, currentTitle: '' });
        if (workItems.length) chSetProgress('正在开始', '', 0);

        for (let i = 0; i < workItems.length; i++) {
            let classified = null;
            const item = workItems[i];
            const currentTitle = item.remote?.title || item.local?.title || item.id;
            chSetRuntimeProgress({ currentTitle: String(currentTitle || '').slice(0, 58) });
            try {
                await chControlCheckpoint('stream-sync');
                if (!item.needs_detail_fetch || item.action === 'ERROR' || item.action === 'DUPLICATE') {
                    classified = {
                        ...item,
                        finalAction: item.action,
                        needs_sync: false,
                        finalReasons: item.reasons || []
                    };
                } else {
                    const title = item.remote?.title || item.local?.title || item.id;
                    chSetProgress('正在获取对话', '', null);
                    try {
                        const convData = await chGetConversationConservative(item.id, workspaceId, title);
                        verification.detailFetchCount++;
                        fetchIndex++;
                        classified = await chClassifyFetchedConversation(item, convData, { includeAttachments });
                    } catch (err) {
                        if (chIsCancellation(err)) throw err;
                        verification.detailFetchCount++;
                        fetchIndex++;
                        classified = {
                            ...item,
                            finalAction: 'ERROR',
                            needs_sync: false,
                            finalReasons: ['DETAIL_FETCH_OR_CLASSIFICATION_FAILED'],
                            error: err?.message || String(err)
                        };
                    }
                }

                verification.items.push(classified);
                verification.counts[classified.finalAction] = (verification.counts[classified.finalAction] || 0) + 1;
                if (typeof onItemClassified === 'function') {
                    try { onItemClassified(classified, { processed: i + 1, total: workItems.length }); } catch (_) {}
                }

                if (CH_FINAL_SYNC_ACTIONS.has(classified.finalAction)) {
                    sync.attempted++;
                    try {
                        const applied = await chApplyClassifiedSyncItem({
                            rootHandle,
                            classifiedItem: classified,
                            manifest,
                            workspaceId,
                            includeAttachments,
                            btn,
                            conversationIndex: i,
                            conversationTotal: totalItems
                        });
                        sync.succeeded++;
                        if (applied.mode === 'MANIFEST_ONLY') sync.manifestOnly++;
                        if (applied.mode === 'FILES_AND_MANIFEST') sync.fileCommits++;
                        sync.cleanupWarnings.push(...(applied.cleanup?.warnings || []).map(w => `${classified.id}: ${w}`));
                        sync.results.push(applied);
                        if (typeof onItemCommitted === 'function') {
                            try { onItemCommitted(classified, applied); } catch (_) {}
                        }
                    } catch (err) {
                        if (chIsCancellation(err)) throw err;
                        sync.failed++;
                        sync.failures.push({
                            id: classified.id,
                            action: classified.finalAction,
                            error: err?.message || String(err)
                        });
                        if (typeof onItemFailed === 'function') {
                            try { onItemFailed(classified, err); } catch (_) {}
                        }
                    }
                }
                chSetRuntimeProgress({ processed: i + 1, currentTitle: String(currentTitle || '').slice(0, 58) });
                chSetProgress('', '', null);

            } catch (err) {
                if (chIsCancellation(err)) {
                    verification.cancelled = true;
                    sync.cancelled = true;
                    break;
                }
                throw err;
            }
        }

        chSetRuntimeProgress({ active:false });
        chSetProgress(
            sync.cancelled ? '同步已取消' : (sync.failed ? '同步完成（有异常）' : '同步完成'),
            sync.cancelled
                ? `已安全提交 ${sync.succeeded} 个会话；未开始的会话保持不变，下次可继续。`
                : `写入成功 ${sync.succeeded} · 未变化 ${verification.counts.UNCHANGED || 0} · 异常 ${(verification.counts.ERROR || 0) + (verification.counts.DUPLICATE || 0)}`,
            100
        );

        const result = { localScan, plan, verification, sync };
        chShowIntegratedSyncReport(result);
        console.log('[ChatHarbor Integrated Sync]', result);
        return result;
    }


'''
text = text.replace(anchor, directory_writer + anchor, 1)

old_buttons = '''                        <button id="back-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">返回</button>
                        <button id="export-selected-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;" disabled>导出选中 (0)</button>'''
new_buttons = '''                        <button id="back-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">返回</button>
                        <button id="preflight-plan-btn" style="padding: 8px 12px; border: 1px solid #6366f1; border-radius: 6px; background: #fff; color: #4338ca; cursor: pointer; font-weight: bold;" disabled>快速检查（全部）</button>
                        <button id="sync-directory-btn" style="padding: 8px 12px; border: 1px solid #10a37f; border-radius: 6px; background: #fff; color: #0f766e; cursor: pointer; font-weight: bold;" disabled>同步（全部）</button>
                        <button id="export-selected-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;" disabled>导出选中 (0)</button>'''
if old_buttons not in text:
    raise SystemExit("Picker button anchor not found")
text = text.replace(old_buttons, new_buttons, 1)

first_query = "            const exportBtn = dialog.querySelector('#export-selected-btn');\n"
if first_query not in text:
    raise SystemExit("Picker query anchor not found")
text = text.replace(
    first_query,
    "            const preflightBtn = dialog.querySelector('#preflight-plan-btn');\n" +
    "            const syncDirBtn = dialog.querySelector('#sync-directory-btn');\n" + first_query,
    1
)

handler_anchor = '''            exportBtn.onclick = async () => {
                if (state.selected.size === 0) return;
                const selectedList = state.list.filter(item => state.selected.has(item.id));
                closeDialog();
                await startSelectiveExportProcess(mode, workspaceId, selectedList, state.includeAttachments);
            };
'''
if handler_anchor not in text:
    raise SystemExit("Picker export handler anchor not found")

preflight_handler = r'''            preflightBtn.onclick = async () => {
                if (!window.showDirectoryPicker) {
                    alert('当前浏览器不支持 File System Access API。请使用新版 Edge / Chromium。');
                    return;
                }

                const rootHandle = await window.showDirectoryPicker({ mode: 'read' });
                const selectedIds = state.selected.size > 0 ? new Set(state.selected) : null;

                preflightBtn.disabled = true;
                syncDirBtn.disabled = true;
                exportBtn.disabled = true;
                try {
                    chSetProgress('快速检查', '补全远端列表范围…', 0);
                    const remoteUniverse = await chCollectPreflightRemoteUniverse(mode, workspaceId, state.list);
                    await chRunPreflightPlanner({
                        rootHandle,
                        remoteList: remoteUniverse.remoteList,
                        selectedIds,
                        remoteUniverseComplete: remoteUniverse.complete,
                        remoteUniverseNote: remoteUniverse.note
                    });
                } catch (err) {
                    console.error('[ChatHarbor Integrated Sync] Preflight failed:', err);
                    chSetProgress('快速检查失败', err?.message || String(err), 100);
                } finally {
                    preflightBtn.disabled = state.loading;
                    syncDirBtn.disabled = state.loading;
                    exportBtn.disabled = state.loading || state.selected.size === 0;
                }
            };

'''

sync_handler = r'''            syncDirBtn.onclick = async () => {
                if (!window.showDirectoryPicker) {
                    alert('当前浏览器不支持 File System Access API。请使用新版 Edge / Chromium。');
                    return;
                }

                const rootHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
                const selectedIds = state.selected.size > 0 ? new Set(state.selected) : null;

                preflightBtn.disabled = true;
                syncDirBtn.disabled = true;
                exportBtn.disabled = true;
                try {
                    chBeginControlledRun(state.networkPolicy);
                    chSetProgress('同步', `补全远端列表范围… · ${chNetworkPolicySummary(chSyncRun.policy)}`, 0);
                    const remoteUniverse = await chCollectPreflightRemoteUniverse(mode, workspaceId, state.list);
                    await chControlCheckpoint('remote-universe-ready');
                    await chRunIntegratedDirectorySync({
                        rootHandle,
                        remoteList: remoteUniverse.remoteList,
                        selectedIds,
                        workspaceId,
                        includeAttachments: state.includeAttachments,
                        remoteUniverseComplete: remoteUniverse.complete,
                        remoteUniverseNote: remoteUniverse.note,
                        networkPolicy: state.networkPolicy
                    });
                } catch (err) {
                    if (chIsCancellation(err)) {
                        chSetProgress('同步已取消', '已在安全边界停止；已提交会话保留，下次同步可继续。', 100);
                    } else {
                        console.error('[ChatHarbor Integrated Sync] failed:', err);
                        chSetProgress('同步失败', err?.message || String(err), 100);
                    }
                } finally {
                    chEndControlledRun();
                    preflightBtn.disabled = state.loading;
                    syncDirBtn.disabled = state.loading;
                    exportBtn.disabled = state.loading || state.selected.size === 0;
                    renderList();
                }
            };

'''


# Run controls are bound in the existing picker; no second execution dialog is introduced.
control_binding = r'''            const pauseSyncBtn = dialog.querySelector('#ch-pause-sync-btn');
            const cancelSyncBtn = dialog.querySelector('#ch-cancel-sync-btn');
            if (pauseSyncBtn) pauseSyncBtn.onclick = () => {
                if (!chSyncRun.active) return;
                if (chSyncRun.paused) chResumeRun();
                else chRequestPause();
            };
            if (cancelSyncBtn) cancelSyncBtn.onclick = () => {
                if (!chSyncRun.active) return;
                chRequestCancel('USER_CANCELLED');
                chSetProgress('正在取消同步', '不会开始新的详情请求或新的会话事务；若当前会话正在提交，将先完成该原子事务。', null);
            };
            chUpdateRunControlUi();

'''
text = text.replace(handler_anchor, control_binding + preflight_handler + sync_handler + handler_anchor, 1)


# Add conservative policy state to the existing picker state object.
state_anchor = "            includeAttachments: Boolean(includeAttachments)\n        };"
state_replacement = "            includeAttachments: Boolean(includeAttachments),\n            networkPolicy: chLoadNetworkPolicy()\n        };"
if state_anchor not in text:
    raise SystemExit("Picker state anchor not found")
text = text.replace(state_anchor, state_replacement, 1)

# Compact network-policy controls under the existing attachment toggle.
attachment_panel_anchor = '''                </label>
                <div id="conv-status" style="margin-bottom: 8px; font-size: 12px; color: #666;">正在加载列表...</div>'''
attachment_panel_replacement = '''                </label>
                <details id="ch-network-policy-panel" style="margin-bottom:10px; padding:8px 10px; border:1px solid #d1d5db; border-radius:8px; background:#fff;">
                    <summary id="ch-network-policy-summary" style="cursor:pointer; font-size:12px; font-weight:600;">网络策略：${chNetworkPolicySummary(state.networkPolicy)}</summary>
                    <div style="display:grid; grid-template-columns:1.6fr .7fr .8fr .8fr; gap:8px; margin-top:8px; align-items:end;">
                        <label style="font-size:11px; color:#666;">速度
                            <select id="ch-speed-level" style="width:100%; margin-top:3px; padding:6px; border:1px solid #ccc; border-radius:6px;">${CH_SPEED_LEVELS.map((x,i)=>`<option value="${i}" ${i===state.networkPolicy.speedIndex?'selected':''}>${x.name}</option>`).join('')}</select>
                        </label>
                        <label style="font-size:11px; color:#666;">每批
                            <input id="ch-batch-size" type="number" min="1" max="200" value="${state.networkPolicy.batchSize}" style="width:100%; box-sizing:border-box; margin-top:3px; padding:6px; border:1px solid #ccc; border-radius:6px;">
                        </label>
                        <label style="font-size:11px; color:#666;">暂停最小(秒)
                            <input id="ch-pause-min" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMinSec}" style="width:100%; box-sizing:border-box; margin-top:3px; padding:6px; border:1px solid #ccc; border-radius:6px;">
                        </label>
                        <label style="font-size:11px; color:#666;">暂停最大(秒)
                            <input id="ch-pause-max" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMaxSec}" style="width:100%; box-sizing:border-box; margin-top:3px; padding:6px; border:1px solid #ccc; border-radius:6px;">
                        </label>
                    </div>
                    <div style="margin-top:6px; font-size:11px; color:#777;">默认沿用超保守策略：较慢 6–10 秒/会话详情；20 条/批；批间随机 3–5 分钟。设置只影响后续新任务。</div>
                </details>
                <div id="conv-status" style="margin-bottom: 8px; font-size: 12px; color: #666;">正在加载列表...</div>'''
if attachment_panel_anchor not in text:
    raise SystemExit("Network policy UI anchor not found")
text = text.replace(attachment_panel_anchor, attachment_panel_replacement, 1)

policy_query_anchor = "            const includeAttachmentsInput = dialog.querySelector('#include-attachments-picker');\n"
policy_query_replacement = policy_query_anchor + (
    "            const speedLevelInput = dialog.querySelector('#ch-speed-level');\n"
    "            const batchSizeInput = dialog.querySelector('#ch-batch-size');\n"
    "            const pauseMinInput = dialog.querySelector('#ch-pause-min');\n"
    "            const pauseMaxInput = dialog.querySelector('#ch-pause-max');\n"
    "            const networkSummary = dialog.querySelector('#ch-network-policy-summary');\n"
)
if policy_query_anchor not in text:
    raise SystemExit("Network policy query anchor not found")
text = text.replace(policy_query_anchor, policy_query_replacement, 1)

policy_handler_anchor = '''            includeAttachmentsInput.onchange = (e) => {
                state.includeAttachments = e.target.checked;
            };
'''
policy_handler_replacement = policy_handler_anchor + '''            const persistPolicyFromUi = () => {
                state.networkPolicy = chSaveNetworkPolicy({
                    ...state.networkPolicy,
                    speedIndex: Number(speedLevelInput?.value),
                    batchSize: Number(batchSizeInput?.value),
                    batchPauseMinSec: Number(pauseMinInput?.value),
                    batchPauseMaxSec: Number(pauseMaxInput?.value)
                });
                if (batchSizeInput) batchSizeInput.value = String(state.networkPolicy.batchSize);
                if (pauseMinInput) pauseMinInput.value = String(state.networkPolicy.batchPauseMinSec);
                if (pauseMaxInput) pauseMaxInput.value = String(state.networkPolicy.batchPauseMaxSec);
                if (networkSummary) networkSummary.textContent = `网络策略：${chNetworkPolicySummary(state.networkPolicy)}`;
            };
            if (speedLevelInput) speedLevelInput.onchange = persistPolicyFromUi;
            if (batchSizeInput) batchSizeInput.onchange = persistPolicyFromUi;
            if (pauseMinInput) pauseMinInput.onchange = persistPolicyFromUi;
            if (pauseMaxInput) pauseMaxInput.onchange = persistPolicyFromUi;
'''
if policy_handler_anchor not in text:
    raise SystemExit("Network policy handler anchor not found")
text = text.replace(policy_handler_anchor, policy_handler_replacement, 1)

back_handler_anchor = '''            backBtn.onclick = () => {
                closeDialog();
                showExportDialog({ includeAttachments: state.includeAttachments });
            };
'''
back_handler_replacement = '''            backBtn.onclick = () => {
                if (chSyncRun.active) {
                    chSetProgress('同步仍在运行', '请使用“暂停”或“取消同步”。返回只负责导航，不再隐式隐藏后台任务。', null);
                    return;
                }
                closeDialog();
                showExportDialog({ includeAttachments: state.includeAttachments });
            };
'''
if back_handler_anchor not in text:
    raise SystemExit("Back handler anchor not found")
text = text.replace(back_handler_anchor, back_handler_replacement, 1)

picker_overlay_anchor = "        overlay.onclick = (e) => { if (e.target === overlay) closeDialog(); };\n\n        const listPromise = mode === 'project'\n"
picker_overlay_replacement = "        overlay.onclick = (e) => {\n            if (e.target !== overlay) return;\n            if (chSyncRun.active) {\n                chSetProgress('同步仍在运行', '请使用“暂停”或“取消同步”；运行期间不会通过点击背景退出。', null);\n                return;\n            }\n            closeDialog();\n        };\n\n        const listPromise = mode === 'project'\n"
if picker_overlay_anchor not in text:
    raise SystemExit("Picker overlay anchor not found")
text = text.replace(picker_overlay_anchor, picker_overlay_replacement, 1)

# ChatHarbor UI hotfix 0.0.6.1:
# Upstream v1.5 auto-collapses the right-edge launcher after 2.5 seconds. For ChatHarbor,
# discoverability is more important than the half-hidden handle, so keep it fully visible.
old_collapse = '''    function fabScheduleCollapse(btn) {
        clearTimeout(fabCollapseTimer);
        if (!fabState.docked) return;
        fabCollapseTimer = setTimeout(() => {
            if (!btn.classList.contains('gre-busy') && !btn.classList.contains('gre-progress') && !btn.matches(':hover')) {
                fabCollapse(btn);
            }
        }, 2500);
    }
'''
new_collapse = '''    function fabScheduleCollapse(btn) {
        clearTimeout(fabCollapseTimer);
        // ChatHarbor: keep the primary launcher fully visible.
        // Dragging and edge snapping remain available; only automatic half-hide is disabled.
        if (fabIsCollapsed(btn)) fabExpand(btn);
    }
'''
if old_collapse not in text:
    raise SystemExit("Launcher visibility anchor not found")
text = text.replace(old_collapse, new_collapse, 1)

# Make the sync path visible from the first dialog without introducing a second selector.
text = text.replace('选择要导出的空间', 'ChatHarbor｜选择空间', 1)
text = text.replace('选择要导出的对话', '选择对话｜导出 / 本地同步', 1)
text = text.replace('>选择对话导出</button>', '>选择对话 / 同步</button>')


render_query_anchor = '''            const exportBtn = dialog.querySelector('#export-selected-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');'''
render_query_repl = '''            const preflightBtn = dialog.querySelector('#preflight-plan-btn');
            const syncDirBtn = dialog.querySelector('#sync-directory-btn');
            const exportBtn = dialog.querySelector('#export-selected-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');'''
if render_query_anchor not in text:
    raise SystemExit("renderList query anchor not found")
text = text.replace(render_query_anchor, render_query_repl, 1)

controls_anchor = "            const controlsDisabled = state.loading;\n"
controls_replacement = "            const controlsDisabled = state.loading || chSyncRun.active;\n"
if controls_anchor not in text:
    raise SystemExit("controlsDisabled anchor not found")
text = text.replace(controls_anchor, controls_replacement, 1)

disabled_anchor = '''            if (clearAllBtn) clearAllBtn.disabled = controlsDisabled;
            if (exportBtn) exportBtn.disabled = controlsDisabled || state.selected.size === 0;'''
disabled_repl = '''            if (clearAllBtn) clearAllBtn.disabled = controlsDisabled;
            if (preflightBtn) preflightBtn.disabled = controlsDisabled;
            if (syncDirBtn) syncDirBtn.disabled = controlsDisabled;
            if (exportBtn) exportBtn.disabled = controlsDisabled || state.selected.size === 0;'''
if disabled_anchor not in text:
    raise SystemExit("renderList disabled anchor not found")
text = text.replace(disabled_anchor, disabled_repl, 1)

text_anchor = "            exportBtn.textContent = `导出选中 (${state.selected.size})`;\n"
if text_anchor not in text:
    raise SystemExit("renderList text anchor not found")
text = text.replace(
    text_anchor,
    "            if (preflightBtn) preflightBtn.textContent = state.selected.size > 0 ? `快速检查（选中 ${state.selected.size}）` : `快速检查（全部 ${state.list.length}）`;\n" +
    "            if (syncDirBtn) syncDirBtn.textContent = state.selected.size > 0 ? `同步（选中 ${state.selected.size}）` : `同步（全部 ${state.list.length}）`;\n" + text_anchor,
    1
)


progress_anchor = '                <div id="conv-status" style="margin-bottom: 8px; font-size: 12px; color: #666;">正在加载列表...</div>\n                <div id="conv-list" style="max-height: 360px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fff;"></div>'
progress_replacement = '                <div id="conv-status" style="margin-bottom: 8px; font-size: 12px; color: #666;">正在加载列表...</div>\n                <div id="ch-sync-progress" style="display:none; margin-bottom: 10px; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px; background: #f9fafb;">\n                    <div style="display:flex; justify-content:space-between; gap:12px; align-items:center; font-size:12px;">\n                        <strong id="ch-sync-progress-primary" style="font-size:12px;">准备同步</strong>\n                        <span id="ch-sync-progress-pct" style="color:#666; min-width:36px; text-align:right;"></span>\n                    </div>\n                    <div style="height:6px; margin-top:7px; background:#e5e7eb; border-radius:999px; overflow:hidden;">\n                        <div id="ch-sync-progress-bar" style="width:0%; height:100%; background:#10a37f; border-radius:999px; transition:width .18s ease;"></div>\n                    </div>\n                    <div id="ch-sync-progress-secondary" style="margin-top:6px; font-size:11px; color:#666; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>\n                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">\n                        <button id="ch-pause-sync-btn" style="display:none; padding:5px 10px; border:1px solid #6366f1; border-radius:6px; background:#fff; color:#4338ca; cursor:pointer;">暂停</button>\n                        <button id="ch-cancel-sync-btn" style="display:none; padding:5px 10px; border:1px solid #dc2626; border-radius:6px; background:#fff; color:#b91c1c; cursor:pointer;">取消同步</button>\n                    </div>\n                </div>\n                <div id="conv-list" style="max-height: 360px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fff;"></div>'
if progress_anchor not in text:
    raise SystemExit("Progress UI anchor not found")
text = text.replace(progress_anchor, progress_replacement, 1)

attachment_hint_old = "默认关闭；开启后导出时间和 ZIP 体积可能明显增加。"
attachment_hint_new = "默认关闭；开启后处理时间与本地占用可能明显增加。"
text = text.replace(attachment_hint_old, attachment_hint_new)


# ======================== ChatHarbor 0.0.14.0 Typed Failure + Observable Retry Release ========================
# This release closes cross-cutting runtime gaps across network scheduling, remote refresh
# snapshot freezing, physical attachment integrity, commit-accurate status and presentation.

# Locale helper for ChatHarbor-owned UI/report strings.
locale_anchor = "    const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';\n"
locale_replacement = locale_anchor + "    const CH_UI_LANG = /^zh(?:-|$)/i.test(String(navigator.language || '')) ? 'zh-CN' : 'en-US';\n    const chT = (zh, en) => CH_UI_LANG === 'zh-CN' ? zh : en;\n"
if locale_anchor not in text:
    raise SystemExit("UI locale anchor not found")
text = text.replace(locale_anchor, locale_replacement, 1)

# Launcher: use a ChatHarbor-specific persisted position, green surface, right-edge default,
# and automatic half-hide. Changing the storage key intentionally discards stale upstream
# positions such as the top-left location observed during migration tests.
text = text.replace("const FAB_STORAGE_KEY = 'chatgpt-exporter-fab-v1';", "const FAB_STORAGE_KEY = 'chatharbor-fab-v2';", 1)
text = text.replace(
    "    background: rgba(255, 255, 255, .88);\n    color: #0d0d0d;",
    "    background: #10a37f;\n    color: #ffffff;",
    1
)
text = text.replace(
    "html.dark #gpt-rescue-btn {\n    background: rgba(52, 53, 65, .92);\n    border-color: rgba(255, 255, 255, .14);\n    color: #ececec;\n}",
    "html.dark #gpt-rescue-btn {\n    background: #10a37f;\n    border-color: rgba(255, 255, 255, .22);\n    color: #ffffff;\n}",
    1
)
text = text.replace(
    "#gpt-rescue-btn:hover { box-shadow: 0 4px 16px rgba(0, 0, 0, .24); }",
    "#gpt-rescue-btn:hover { background:#0d8f70; box-shadow: 0 4px 16px rgba(0, 0, 0, .24); }",
    1
)
old_disabled_collapse = '''    function fabScheduleCollapse(btn) {
        clearTimeout(fabCollapseTimer);
        // ChatHarbor: keep the primary launcher fully visible.
        // Dragging and edge snapping remain available; only automatic half-hide is disabled.
        if (fabIsCollapsed(btn)) fabExpand(btn);
    }
'''
new_half_hide = '''    function fabScheduleCollapse(btn) {
        clearTimeout(fabCollapseTimer);
        if (!fabState.docked) return;
        fabCollapseTimer = setTimeout(() => {
            if (!btn.classList.contains('gre-busy') && !btn.classList.contains('gre-progress') && !btn.matches(':hover')) {
                fabCollapse(btn);
            }
        }, 1800);
    }
'''
if old_disabled_collapse not in text:
    raise SystemExit("0.0.7 launcher override not found")
text = text.replace(old_disabled_collapse, new_half_hide, 1)
old_fab_init = '''            fabApply(btn, fabSnap(fabClamp(saved ? { x: saved.x, y: saved.y } : fabDefaultPosition())));
            if (saved && saved.collapsed && fabState.docked) fabCollapse(btn);'''
new_fab_init = '''            fabApply(btn, fabSnap(fabClamp(saved ? { x: saved.x, y: saved.y } : fabDefaultPosition())));
            if ((saved && saved.collapsed && fabState.docked) || (!saved && fabState.docked)) fabCollapse(btn);'''
if old_fab_init not in text:
    raise SystemExit("FAB initialization anchor not found")
text = text.replace(old_fab_init, new_fab_init, 1)
text = text.replace("btn.setAttribute('aria-label', 'ChatGPT Exporter：导出对话');", "btn.setAttribute('aria-label', 'ChatHarbor：本地归档同步');", 1)
text = text.replace("btn.title = `ChatGPT Exporter v${ATTACHMENT_EXPORT_VERSION} · 点击导出 · 拖动移动 · 右键重置位置`;", "btn.title = `ChatHarbor · 点击打开 · 拖动移动 · 右键重置位置`;", 1)

single_page_picker = r'''    function showConversationPicker(options = {}) {
        const initialMode = options.mode || 'personal';
        const initialWorkspaceId = options.workspaceId || null;
        const initialAttachments = Boolean(options.includeAttachments);
        const existing = document.getElementById('export-dialog-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'export-dialog-overlay';
        Object.assign(overlay.style, {
            position: 'fixed', inset: '0', backgroundColor: 'rgba(0,0,0,.46)', zIndex: '99998',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', boxSizing: 'border-box'
        });

        const dialog = document.createElement('div');
        dialog.id = 'export-dialog';
        Object.assign(dialog.style, {
            background: '#fff', borderRadius: '12px', boxShadow: '0 18px 56px rgba(0,0,0,.30)',
            width: 'min(1240px, calc(100vw - 48px))', height: 'min(820px, calc(100vh - 48px))',
            minHeight: '560px', fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
            color: '#1f2937', boxSizing: 'border-box', overflow: 'hidden', display: 'flex', flexDirection: 'column'
        });

        const state = {
            mode: initialMode,
            workspaceId: initialWorkspaceId,
            list: [], filtered: [], selected: new Set(), query: '',
            projectFilter: 'all', archived: 'all', syncStatus: 'all',
            timeField: 'update', timeRange: 'all', sort: 'desc', startDate: '', endDate: '',
            loading: true, pageSize: 100, visibleCount: 100, includeAttachments: initialAttachments,
            networkPolicy: chLoadNetworkPolicy(), runSettings: null, rootHandle: null, savedRootHandle: null, localScan: null, lastPlan: null,
            layoutState: null, migrationActive: false, migrationReport: null,
            lastResult: null, syncStatusById: new Map(), lastSelectedIndex: null,
            remoteUniverse: [], remoteUniverseComplete: false, remoteUniverseNote: null,
            accountUniverse: null, accountUniverseComplete: false, accountUniverseNote: null,
            accountLoadedAt: null, teamUniverseCache: new Map(), remoteCacheMeta: null,
            remoteRefreshPromise: null, pendingRemoteSnapshot: null, remoteRefreshGeneration: 0, remoteAppliedValidatedAt: 0,
            loadingMessage: chT('正在加载云端对话…','Loading cloud conversations…')
        };

        const userStatus = value => {
            if (['UNCHANGED','OBSERVATION_ONLY'].includes(value)) return 'SYNCED';
            if (['LOCAL_UNTRACKED','LOCAL_ONLY'].includes(value)) return 'CONFIRM';
            if (['ERROR','DUPLICATE'].includes(value)) return 'ERROR';
            if (value) return 'PENDING';
            return null;
        };
        const statusLabel = value => ({
            SYNCED: chT('已同步','Synced'), PENDING: chT('待同步','To sync'),
            CONFIRM: chT('需确认','Check'), ERROR: chT('异常','Error')
        }[userStatus(value) || value] || '');
        const statusColor = value => ({
            SYNCED:['#f0fdf4','#166534'], PENDING:['#eff6ff','#1d4ed8'],
            CONFIRM:['#fff7ed','#c2410c'], ERROR:['#fef2f2','#b91c1c']
        }[userStatus(value) || value] || ['#f3f4f6','#6b7280']);

        const closeDialog = () => {
            if (chSyncRun.active || state.migrationActive) {
                chSetProgress(
                    state.migrationActive ? chT('本地保存升级仍在运行','Local save upgrade is still running') : chT('同步仍在运行','Sync is still running'),
                    state.migrationActive ? chT('请等待当前整理步骤完成。','Wait for the current reorganization step to finish.') : chT('请先暂停或取消同步。','Pause or cancel sync first.'),
                    null
                );
                return;
            }
            overlay.remove();
        };

        dialog.innerHTML = `
            <div style="height:52px; padding:0 18px; border-bottom:1px solid #e5e7eb; display:flex; align-items:center; justify-content:space-between; flex:0 0 auto;">
                <div style="display:flex; align-items:baseline; gap:10px; min-width:0;">
                    <strong style="font-size:18px;">ChatHarbor</strong>
                    <span id="ch-header-summary" style="font-size:12px; color:#6b7280; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></span>
                </div>
                <div style="display:flex;gap:7px;"><button id="ch-refresh-btn" style="padding:7px 11px; border:1px solid #d1d5db; border-radius:7px; background:#fff; cursor:pointer;">${chT('刷新','Refresh')}</button><button id="back-btn" style="padding:7px 11px; border:1px solid #d1d5db; border-radius:7px; background:#fff; cursor:pointer;">${chT('关闭','Close')}</button></div>
            </div>
            <div style="padding:10px 14px; border-bottom:1px solid #e5e7eb; display:grid; grid-template-columns:minmax(260px,1fr) 118px 150px 120px 150px 118px; gap:8px; align-items:center; flex:0 0 auto;">
                <input id="conv-search" type="text" placeholder="${chT('搜索对话或项目','Search conversations or projects')}" style="min-width:0; padding:8px 10px; border:1px solid #d1d5db; border-radius:7px;">
                <select id="ch-space-select" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="personal">${chT('全部对话','All conversations')}</option><option value="project">${chT('项目对话','Project conversations')}</option><option value="team">${chT('团队空间','Team')}</option>
                </select>
                <select id="filter-project" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;"><option value="all">${chT('项目：全部','Project: all')}</option></select>
                <select id="filter-archived" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="all">${chT('归档：全部','Archive: all')}</option><option value="active">${chT('未归档','Active')}</option><option value="archived">${chT('已归档','Archived')}</option>
                </select>
                <select id="filter-sync-status" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="all">${chT('状态：全部','Status: all')}</option>
                </select>
                <details id="ch-time-menu" style="position:relative;">
                    <summary id="ch-time-summary" style="list-style:none; padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff; cursor:pointer; text-align:center;">${chT('时间：不限','Time: all')}</summary>
                    <div style="position:absolute; right:0; top:40px; z-index:20; width:280px; padding:12px; background:#fff; border:1px solid #d1d5db; border-radius:9px; box-shadow:0 10px 28px rgba(0,0,0,.16);">
                        <label style="display:block; font-size:12px; color:#6b7280; margin-bottom:4px;">${chT('时间依据','Time field')}</label>
                        <select id="filter-time-field" style="width:100%; padding:7px; border:1px solid #d1d5db; border-radius:6px;"><option value="update">${chT('更新时间','Updated')}</option><option value="create">${chT('创建时间','Created')}</option></select>
                        <label style="display:block; font-size:12px; color:#6b7280; margin:10px 0 4px;">${chT('范围','Range')}</label>
                        <select id="filter-time-range" style="width:100%; padding:7px; border:1px solid #d1d5db; border-radius:6px;"><option value="all">${chT('不限','All')}</option><option value="7d">${chT('最近7天','Last 7 days')}</option><option value="30d">${chT('最近30天','Last 30 days')}</option><option value="custom">${chT('自定义','Custom')}</option></select>
                        <div id="ch-custom-date-row" style="display:none; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;"><input id="filter-start-date" type="date" style="min-width:0; padding:6px; border:1px solid #d1d5db; border-radius:6px;"><input id="filter-end-date" type="date" style="min-width:0; padding:6px; border:1px solid #d1d5db; border-radius:6px;"></div>
                        <label style="display:block; font-size:12px; color:#6b7280; margin:10px 0 4px;">${chT('排序','Sort')}</label>
                        <select id="filter-sort" style="width:100%; padding:7px; border:1px solid #d1d5db; border-radius:6px;"><option value="desc">${chT('最新优先','Newest first')}</option><option value="asc">${chT('最早优先','Oldest first')}</option></select>
                    </div>
                </details>
            </div>
            <div style="display:grid; grid-template-columns:minmax(0,1fr) 310px; gap:12px; padding:12px 14px 14px; flex:1 1 auto; min-height:0; background:#f8fafc;">
                <section style="min-width:0; min-height:0; display:flex; flex-direction:column;">
                    <div style="display:flex; justify-content:flex-start; align-items:center; gap:0; margin-bottom:8px; flex:0 0 auto; min-height:22px;">
                        <label style="display:flex;align-items:center;gap:6px;min-width:72px;font-size:12px;color:#374151;cursor:pointer;white-space:nowrap;"><input id="select-all-checkbox" type="checkbox"><span>${chT('全选','Select all')}</span></label>
                        <div id="conv-status" style="margin-left:24px;font-size:12px;color:#6b7280;white-space:nowrap;">${chT('正在加载列表…','Loading…')}</div>
                    </div>
                    <div id="conv-list" style="flex:1 1 auto; min-height:0; overflow:auto; border:1px solid #e5e7eb; border-radius:9px; padding:8px; background:#fff;"></div>
                </section>
                <aside style="min-height:0; overflow:hidden; display:flex; flex-direction:column; gap:9px;">
                    <div id="ch-right-scroll" style="min-height:0; flex:1 1 auto; overflow:auto; display:flex; flex-direction:column; gap:9px; padding-right:1px;">
                        <div style="padding:10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;"><strong style="font-size:13px;">${chT('本地保存','Local save')}</strong><button id="ch-archive-copy-report-btn" style="display:none;padding:3px 7px;border:1px solid #d1d5db;border-radius:6px;background:#fff;color:#6b7280;cursor:pointer;font-size:11px;">${chT('详情','Details')}</button></div>
                            <div id="ch-archive-path" style="margin-top:6px; font-size:12px; color:#6b7280; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${chT('尚未选择目录','No directory selected')}</div>
                            <div id="ch-archive-summary" style="margin-top:6px; font-size:12px; line-height:1.55; color:#4b5563;">${chT('等待选择目录','Waiting for directory')}</div>
                            <div style="display:flex; gap:6px; margin-top:8px;"><button id="ch-choose-directory-btn" style="flex:1; padding:7px 8px; border:1px solid #d1d5db; border-radius:6px; background:#fff; cursor:pointer;">${chT('选择目录','Choose')}</button><button id="preflight-plan-btn" style="flex:1; padding:7px 8px; border:1px solid #6366f1; border-radius:6px; background:#fff; color:#4338ca; cursor:pointer; font-weight:600;">${chT('重新检查','Check again')}</button></div>
                            <button id="ch-migrate-layout-btn" style="display:none;width:100%;margin-top:7px;padding:8px 10px;border:1px solid #d97706;border-radius:7px;background:#fffbeb;color:#92400e;cursor:pointer;font-weight:700;">${chT('升级本地保存结构','Upgrade local save structure')}</button>
                        </div>
                        <details style="padding:9px 10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <summary id="ch-network-policy-summary" style="cursor:pointer; font-size:13px; font-weight:600;">${chT('请求速度','Request speed')} · ${chNetworkPolicySummary(state.networkPolicy)}</summary>
                            <div id="ch-network-policy-lock-note" style="display:none;margin-top:7px;font-size:11px;color:#6b7280;">${chT('本次同步期间不可修改','Locked during this sync')}</div>
                            <label style="display:block;font-size:11px;color:#6b7280;margin-top:8px;">${chT('使用场景','Use case')}<select id="ch-speed-level" style="width:100%;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;">${CH_SPEED_LEVELS.map((x,i)=>`<option value="${i}" ${i===state.networkPolicy.speedIndex?'selected':''}>${x.name}</option>`).join('')}</select></label>
                            <div id="ch-network-policy-detail" style="margin-top:6px;font-size:11px;color:#6b7280;line-height:1.45;">${chNetworkPolicyDetail(state.networkPolicy)}</div>
                            <div style="margin-top:5px;font-size:10.5px;color:#9ca3af;line-height:1.45;">${chT('出现“请求过多”时，建议改用“保守模式（最稳）”。','After a “too many requests” warning, use “Conservative mode (safest)”.')}</div>
                            <details style="margin-top:7px;">
                                <summary style="cursor:pointer;font-size:11px;color:#6b7280;">${chT('高级设置','Advanced settings')}</summary>
                                <div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px;">
                                    <label style="font-size:11px;color:#6b7280;">${chT('每批会话数','Conversations per batch')}<input id="ch-batch-size" type="number" min="1" max="200" value="${state.networkPolicy.batchSize}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                                    <span></span>
                                    <label style="font-size:11px;color:#6b7280;">${chT('最短休息(秒)','Minimum break (s)')}<input id="ch-pause-min" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMinSec}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                                    <label style="font-size:11px;color:#6b7280;">${chT('最长休息(秒)','Maximum break (s)')}<input id="ch-pause-max" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMaxSec}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                                </div>
                            </details>
                        </details>
                        <details style="padding:9px 10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <summary id="ch-sync-content-summary" style="cursor:pointer; font-size:13px; font-weight:600;">${chT('附件','Attachments')} · ${state.includeAttachments?chT('下载','Download'):chT('不下载','Do not download')}</summary>
                            <div id="ch-sync-content-lock-note" style="display:none;margin-top:7px;font-size:11px;color:#6b7280;">${chT('本次同步期间不可修改','Locked during this sync')}</div>
                            <label style="display:flex; gap:7px; align-items:flex-start; margin-top:8px; font-size:12px; cursor:pointer;"><input id="include-attachments-picker" type="checkbox" ${state.includeAttachments?'checked':''}><span>${chT('同时下载上传和生成的附件','Download uploads and generated files')}<small style="display:block;color:#6b7280;margin-top:2px;">${chT('默认关闭；开启后处理时间与本地占用可能明显增加。','Off by default; increases processing time and local storage.')}</small></span></label>
                        </details>
                        <div id="ch-sync-progress" style="display:none; padding:10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:12px;"><strong id="ch-sync-progress-primary"></strong><span id="ch-sync-progress-pct" style="color:#6b7280;"></span></div>
                            <div style="height:6px;margin-top:7px;background:#e5e7eb;border-radius:999px;overflow:hidden;"><div id="ch-sync-progress-bar" style="width:0%;height:100%;background:#10a37f;border-radius:999px;transition:width .18s ease;"></div></div>
                            <div id="ch-sync-progress-secondary" style="margin-top:6px;font-size:11px;color:#6b7280;line-height:1.45;"></div>
                            <div style="display:flex;justify-content:flex-end;gap:6px;margin-top:8px;"><button id="ch-pause-sync-btn" style="display:none;padding:5px 9px;border:1px solid #6366f1;border-radius:6px;background:#fff;color:#4338ca;cursor:pointer;">${chT('暂停','Pause')}</button><button id="ch-cancel-sync-btn" style="display:none;padding:5px 9px;border:1px solid #dc2626;border-radius:6px;background:#fff;color:#b91c1c;cursor:pointer;">${chT('取消同步','Cancel sync')}</button></div>
                        </div>
                        <div id="ch-result-panel" style="display:none; padding:9px 10px; border:1px solid #bbf7d0; border-radius:9px; background:#f0fdf4;">
                            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;"><strong id="ch-result-title" style="font-size:13px;"></strong><button id="ch-copy-report-btn" style="padding:3px 7px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;font-size:11px;">${chT('复制详细报告','Copy details')}</button></div><pre id="ch-result-summary" style="margin:6px 0 0;white-space:pre-wrap;font:11px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#374151;"></pre>
                        </div>
                    </div>
                    <div id="ch-action-bar" style="flex:0 0 auto; padding:9px; border:1px solid #d1d5db; border-radius:9px; background:#fff; box-shadow:0 -4px 16px rgba(15,23,42,.04);">
                        <button id="sync-directory-btn" style="width:100%;padding:12px 14px;border:none;border-radius:7px;background:#10a37f;color:#fff;cursor:pointer;font-weight:700;white-space:nowrap;">${chT('同步选中','Sync selected')}</button>
                    </div>
                </aside>
            </div>`;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        const $ = id => dialog.querySelector(`#${id}`);
        const searchInput = $('conv-search');
        const spaceSelect = $('ch-space-select');
        const projectSelect = $('filter-project');
        const archivedSelect = $('filter-archived');
        const syncStatusSelect = $('filter-sync-status');
        const timeFieldSelect = $('filter-time-field');
        const timeRangeSelect = $('filter-time-range');
        const sortSelect = $('filter-sort');
        const startDateInput = $('filter-start-date');
        const endDateInput = $('filter-end-date');
        const customDateRow = $('ch-custom-date-row');
        const timeSummary = $('ch-time-summary');
        const includeAttachmentsInput = $('include-attachments-picker');
        const chooseDirBtn = $('ch-choose-directory-btn');
        const preflightBtn = $('preflight-plan-btn');
        const migrateLayoutBtn = $('ch-migrate-layout-btn');
        const syncSelectedBtn = $('sync-directory-btn');
        const selectAllCheckbox = $('select-all-checkbox');
        const refreshBtn = $('ch-refresh-btn');
        const closeBtn = $('back-btn');
        const pauseSyncBtn = $('ch-pause-sync-btn');
        const cancelSyncBtn = $('ch-cancel-sync-btn');
        const speedLevelInput = $('ch-speed-level');
        const batchSizeInput = $('ch-batch-size');
        const pauseMinInput = $('ch-pause-min');
        const pauseMaxInput = $('ch-pause-max');
        const networkSummary = $('ch-network-policy-summary');
        const networkDetail = $('ch-network-policy-detail');
        const networkLockNote = $('ch-network-policy-lock-note');
        const syncContentSummary = $('ch-sync-content-summary');
        const syncContentLockNote = $('ch-sync-content-lock-note');
        const archiveCopyReportBtn = $('ch-archive-copy-report-btn');

        spaceSelect.value = state.mode;
        archivedSelect.value = state.archived;

        const updateHeader = () => {
            $('ch-header-summary').textContent = CH_PROVIDER_LABEL;
        };
        const updateTimeSummary = () => {
            const range = state.timeRange === '7d' ? chT('最近7天','7 days') : state.timeRange === '30d' ? chT('最近30天','30 days') : state.timeRange === 'custom' ? chT('自定义','Custom') : chT('不限','All');
            timeSummary.textContent = `${chT('时间','Time')}：${range}`;
            customDateRow.style.display = state.timeRange === 'custom' ? 'grid' : 'none';
        };
        const statusMatches = status => {
            if (state.syncStatus === 'all') return true;
            return userStatus(status) === state.syncStatus;
        };
        const projectKey = item => item.projectId ? `id:${item.projectId}` : item.projectTitle ? `title:${item.projectTitle}` : item.__chProjectState === 'unknown' ? 'unknown' : 'none';

        const rebuildProjectOptions = () => {
            const current = state.projectFilter;
            const map = new Map();
            for (const item of state.list) if (item.projectTitle) map.set(projectKey(item), item.projectTitle);
            projectSelect.innerHTML = '';
            const add = (value, label) => { const o=document.createElement('option');o.value=value;o.textContent=label;projectSelect.appendChild(o); };
            add('all', chT('项目：全部','Project: all'));
            add('none', chT('无项目','No project'));
            if (state.list.some(item => projectKey(item) === 'unknown')) add('unknown', chT('归属未知','Unknown project'));
            [...map.entries()].sort((a,b)=>a[1].localeCompare(b[1])).forEach(([value,label])=>add(value,label));
            state.projectFilter = [...projectSelect.options].some(o=>o.value===current) ? current : 'all';
            projectSelect.value = state.projectFilter;
        };
        const rebuildSyncOptions = () => {
            const current = state.syncStatus;
            const counts = {SYNCED:0,PENDING:0,CONFIRM:0,ERROR:0};
            state.list.forEach(item => { const u=userStatus(state.syncStatusById.get(item.id)); if(u) counts[u]++; });
            const options = [
                ['all', `${chT('状态：全部','Status: all')} (${state.list.length})`],
                ['SYNCED', `${chT('已同步','Synced')} (${counts.SYNCED})`],
                ['PENDING', `${chT('待同步','To sync')} (${counts.PENDING})`],
                ['CONFIRM', `${chT('需确认','Check')} (${counts.CONFIRM})`],
                ['ERROR', `${chT('异常','Error')} (${counts.ERROR})`]
            ];
            syncStatusSelect.innerHTML='';
            options.forEach(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;syncStatusSelect.appendChild(o);});
            state.syncStatus = options.some(x=>x[0]===current) ? current : 'all';
            syncStatusSelect.value = state.syncStatus;
        };
        const applyFilters = () => {
            const query = state.query.trim().toLowerCase();
            const now = Date.now()/1000;
            let startBound = null, endBound = null;
            if (state.timeRange === '7d') startBound = now - 7*86400;
            else if (state.timeRange === '30d') startBound = now - 30*86400;
            else if (state.timeRange === 'custom') { startBound=parseDateInputToEpoch(state.startDate,false); endBound=parseDateInputToEpoch(state.endDate,true); }
            state.filtered = state.list.filter(item => {
                const hay = `${item.title||''} ${item.projectTitle||''} ${item.id||''}`.toLowerCase();
                if (query && !hay.includes(query)) return false;
                if (state.projectFilter !== 'all' && projectKey(item) !== state.projectFilter) return false;
                if (state.archived === 'active' && item.is_archived) return false;
                if (state.archived === 'archived' && !item.is_archived) return false;
                if (!statusMatches(state.syncStatusById.get(item.id))) return false;
                const ts = normalizeEpochSeconds(state.timeField === 'create' ? item.create_time : item.update_time);
                if (startBound && (!ts || ts < startBound)) return false;
                if (endBound && (!ts || ts > endBound)) return false;
                return true;
            }).sort((a,b)=>{
                const ta=normalizeEpochSeconds(state.timeField==='create'?a.create_time:a.update_time)||0;
                const tb=normalizeEpochSeconds(state.timeField==='create'?b.create_time:b.update_time)||0;
                return state.sort==='asc' ? ta-tb : tb-ta;
            });
            state.visibleCount = state.pageSize;
        };
        const updateArchiveSummary = () => {
            $('ch-archive-path').textContent = state.rootHandle?.name ? `${chT('保存到','Save to')}：${state.rootHandle.name}` : state.savedRootHandle ? chT('上次保存位置需要重新授权','Previous save location needs permission') : chT('尚未选择保存位置','No save location selected');
            const layout = state.layoutState;
            if (!state.rootHandle) {
                $('ch-archive-summary').textContent = state.savedRootHandle ? chT('点击“继续使用”恢复上次位置','Click “Continue” to restore the previous location') : chT('选择后会自动检查本地文件','Local files are checked automatically after selection');
            } else if (layout?.requiresMigration) {
                $('ch-archive-summary').textContent = `${chT('本地保存结构需要升级','Local save structure needs an upgrade')} · ${chT('共','Total')} ${layout.total || 0}`;
            } else if (!state.lastPlan) {
                $('ch-archive-summary').textContent = `${chT('已选择保存位置','Save location selected')} · ${chT('等待检查','waiting to check')}`;
            } else {
                const s = state.lastPlan.summary;
                const pending = Math.max(0, Number(s.maximumFetchRequired || 0));
                const confirm = Math.max(0, Number(s.rawOnlyVerifyCount || 0)) + (s.localOnlyReliable ? Math.max(0, Number(s.localOnlyCount || 0)) : 0);
                const issues = Math.max(0, Number(s.errorCount || 0) + Number(s.duplicateIdCount || 0));
                const parts = [`${chT('已保存','Saved')} ${s.local || 0}`];
                if (s.unchangedCount) parts.push(`${chT('已同步','Synced')} ${s.unchangedCount}`);
                if (pending) parts.push(`${chT('待同步','To sync')} ${pending}`);
                if (confirm) parts.push(`${chT('需确认','Check')} ${confirm}`);
                if (issues) parts.push(`${chT('异常','Error')} ${issues}`);
                $('ch-archive-summary').textContent = parts.join(' · ');
            }
            if (migrateLayoutBtn) {
                migrateLayoutBtn.style.display = layout?.requiresMigration ? '' : 'none';
                migrateLayoutBtn.textContent = layout?.migrationInProgress ? chT('继续升级本地保存结构','Continue upgrade') : chT('升级本地保存结构','Upgrade local save');
            }
            if (archiveCopyReportBtn) archiveCopyReportBtn.style.display = state.lastPlan ? '' : 'none';
            updateHeader();
        };
        const updateSettingsSummary = () => {
            const runLocked = Boolean(chSyncRun.active && state.runSettings);
            const policy = runLocked ? chSyncRun.policy : state.networkPolicy;
            const includeAttachments = runLocked ? Boolean(state.runSettings.includeAttachments) : Boolean(state.includeAttachments);
            if (networkSummary) networkSummary.textContent = `${chT('请求速度','Request speed')} · ${chNetworkPolicySummary(policy)}`;
            if (networkDetail) networkDetail.textContent = chNetworkPolicyDetail(policy);
            if (syncContentSummary) syncContentSummary.textContent = `${chT('附件','Attachments')} · ${includeAttachments ? chT('下载','Download') : chT('不下载','Do not download')}`;
            if (networkLockNote) networkLockNote.style.display = runLocked ? '' : 'none';
            if (syncContentLockNote) syncContentLockNote.style.display = runLocked ? '' : 'none';
        };
        const updateControls = () => {
            const disabled = state.loading || chSyncRun.active || state.migrationActive;
            const migrationRequired = Boolean(state.layoutState?.requiresMigration);
            [searchInput,spaceSelect,projectSelect,archivedSelect,syncStatusSelect,timeFieldSelect,timeRangeSelect,sortSelect,startDateInput,endDateInput,refreshBtn].forEach(el=>{if(el)el.disabled=disabled;});
            const runLocked = Boolean(chSyncRun.active);
            [speedLevelInput,batchSizeInput,pauseMinInput,pauseMaxInput,includeAttachmentsInput].forEach(el=>{if(el)el.disabled=runLocked;});
            updateSettingsSummary();
            chooseDirBtn.disabled = chSyncRun.active || state.migrationActive;
            chooseDirBtn.textContent = state.rootHandle ? chT('更换目录','Change location') : state.savedRootHandle ? chT('继续使用','Continue') : chT('选择位置','Choose location');
            chooseDirBtn.title = state.rootHandle ? chT('切换本地保存位置。','Change the local save location.') : '';
            preflightBtn.disabled = chSyncRun.active || state.migrationActive || !state.rootHandle;
            if (migrateLayoutBtn) migrateLayoutBtn.disabled = disabled || !migrationRequired;
            if (selectAllCheckbox) selectAllCheckbox.disabled = disabled || state.filtered.length===0 || migrationRequired;
            syncSelectedBtn.disabled = disabled || migrationRequired || !state.rootHandle || state.selected.size===0;
            syncSelectedBtn.style.opacity = syncSelectedBtn.disabled ? '.45' : '1';
            syncSelectedBtn.textContent = migrationRequired
                ? chT('请先升级本地保存','Upgrade local save first')
                : state.selected.size ? `${chT('同步选中','Sync selected')} ${state.selected.size}` : chT('请选择对话','Select conversations');
        };
        const renderList = () => {
            const listEl=$('conv-list'), statusEl=$('conv-status');
            listEl.innerHTML='';
            updateControls(); updateArchiveSummary();
            if(state.loading && !state.list.length){statusEl.textContent=state.loadingMessage||chT('正在加载云端对话…','Loading cloud conversations…');if(selectAllCheckbox){selectAllCheckbox.checked=false;selectAllCheckbox.indeterminate=false;}return;}
            const matchedSelected = state.filtered.reduce((n,item)=>n+(state.selected.has(item.id)?1:0),0);
            if(selectAllCheckbox){selectAllCheckbox.checked=state.filtered.length>0&&matchedSelected===state.filtered.length;selectAllCheckbox.indeterminate=matchedSelected>0&&matchedSelected<state.filtered.length;}
            const providerTotal = state.remoteUniverse.length || state.list.length;
            const countParts=[`${chT('已选','Selected')} ${state.selected.size}`];
            if(state.filtered.length!==providerTotal) countParts.push(`${chT('当前','Current')} ${state.filtered.length} / ${chT('共','Total')} ${providerTotal}`);
            else countParts.push(`${chT('共','Total')} ${providerTotal}`);
            statusEl.textContent=state.loading ? `${state.loadingMessage||chT('云端对话加载中','Remote index loading')} · ${countParts.join(' · ')}` : countParts.join(' · ');
            if(!state.filtered.length){const e=document.createElement('div');e.textContent=chT('没有匹配的对话。','No matching conversations.');e.style.cssText='color:#9ca3af;padding:12px 8px;';listEl.appendChild(e);return;}
            state.filtered.slice(0,state.visibleCount).forEach((item,index)=>{
                const row=document.createElement('label');
                row.style.cssText='display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 9px;border:1px solid #e5e7eb;border-radius:7px;margin-bottom:6px;cursor:pointer;background:#fff;';
                const cb=document.createElement('input');cb.type='checkbox';cb.checked=state.selected.has(item.id);cb.disabled=state.loading||chSyncRun.active||state.migrationActive||Boolean(state.layoutState?.requiresMigration);
                cb.onclick=e=>{const checked=cb.checked;if(e.shiftKey && state.lastSelectedIndex!=null){const a=Math.min(state.lastSelectedIndex,index),b=Math.max(state.lastSelectedIndex,index);for(let i=a;i<=b;i++){const id=state.filtered[i]?.id;if(!id)continue;if(checked)state.selected.add(id);else state.selected.delete(id);}}else{if(checked)state.selected.add(item.id);else state.selected.delete(item.id);}state.lastSelectedIndex=index;renderList();};
                const content=document.createElement('div');content.style.minWidth='0';
                const title=document.createElement('div');title.textContent=item.title||'Untitled Conversation';title.style.cssText='font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                const meta=document.createElement('div');const time=formatTimestamp(state.timeField==='create'?item.create_time:item.update_time)||chT('未知','Unknown');const timeText=`${state.timeField==='create'?chT('创建','Created'):chT('更新','Updated')} ${time}`;meta.textContent=item.projectTitle?`${item.projectTitle} · ${timeText}`:timeText;meta.style.cssText='font-size:11px;color:#6b7280;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                content.append(title,meta);row.append(cb,content);
                const badges=document.createElement('div');badges.style.cssText='display:flex;gap:5px;align-items:center;justify-content:flex-end;flex-wrap:wrap;';
                const s=state.syncStatusById.get(item.id);if(s){const [bg,fg]=statusColor(s);const badge=document.createElement('span');badge.textContent=statusLabel(s);badge.style.cssText=`font-size:11px;padding:3px 7px;border-radius:999px;background:${bg};color:${fg};white-space:nowrap;`;badges.appendChild(badge);}
                if(item.is_archived){const archiveBadge=document.createElement('span');archiveBadge.textContent=chT('已归档','Archived');archiveBadge.style.cssText='font-size:11px;padding:3px 7px;border-radius:999px;background:#fef3c7;color:#92400e;white-space:nowrap;';badges.appendChild(archiveBadge);}
                row.appendChild(badges);listEl.appendChild(row);
            });
            if(state.filtered.length>state.visibleCount){const more=document.createElement('button');more.textContent=`${chT('加载更多','Load more')} (${state.filtered.length-state.visibleCount})`;more.style.cssText='width:100%;padding:7px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;';more.onclick=()=>{state.visibleCount=Math.min(state.visibleCount+state.pageSize,state.filtered.length);renderList();};listEl.appendChild(more);}
        };
        const renderAll = () => { rebuildProjectOptions(); rebuildSyncOptions(); applyFilters(); updateTimeSummary(); renderList(); };

        const persistPolicy = () => {
            if (chSyncRun.active) { updateSettingsSummary(); return; }
            state.networkPolicy=chSaveNetworkPolicy({...state.networkPolicy,speedIndex:Number(speedLevelInput.value),batchSize:Number(batchSizeInput.value),batchPauseMinSec:Number(pauseMinInput.value),batchPauseMaxSec:Number(pauseMaxInput.value)});
            batchSizeInput.value=String(state.networkPolicy.batchSize);pauseMinInput.value=String(state.networkPolicy.batchPauseMinSec);pauseMaxInput.value=String(state.networkPolicy.batchPauseMaxSec);
            updateSettingsSummary();
        };
        const applySpeedPreset = () => {
            if (chSyncRun.active) { updateSettingsSummary(); return; }
            const speedIndex = Math.max(0, Math.min(CH_SPEED_LEVELS.length - 1, Number(speedLevelInput.value) || 0));
            const preset = CH_SPEED_LEVELS[speedIndex];
            state.networkPolicy=chSaveNetworkPolicy({...state.networkPolicy,speedIndex,batchSize:preset.batchSize,batchPauseMinSec:preset.pauseMinSec,batchPauseMaxSec:preset.pauseMaxSec});
            batchSizeInput.value=String(state.networkPolicy.batchSize);pauseMinInput.value=String(state.networkPolicy.batchPauseMinSec);pauseMaxInput.value=String(state.networkPolicy.batchPauseMaxSec);
            updateSettingsSummary();
        };
        const applyPreflightStatuses = plan => {
            state.syncStatusById.clear();
            for(const item of plan.items){let s=item.action;if(s==='VERIFY_CHANGED'||s==='VERIFY_RENAMED')s='VERIFY';state.syncStatusById.set(item.id,s);}
            state.lastPlan=plan;
        };
        const applyFinalStatuses = result => {
            const failedIds=new Set((result.sync?.failures||[]).map(x=>x.id));
            const committedIds=new Set((result.sync?.results||[]).map(x=>x.id));
            for(const item of result.verification.items||[]){
                if(!item.id||!item.finalAction)continue;
                if(failedIds.has(item.id)){state.syncStatusById.set(item.id,'ERROR');continue;}
                if(CH_FINAL_SYNC_ACTIONS.has(item.finalAction)&&!committedIds.has(item.id))continue;
                state.syncStatusById.set(item.id,item.finalAction==='OBSERVATION_ONLY'?'UNCHANGED':item.finalAction==='ATTACHMENT_BACKFILL'?'UNCHANGED':item.finalAction);
            }
            state.lastPlan=result.plan;state.lastResult=result;
        };
        const ensureRoot = async () => {
            if(state.rootHandle)return state.rootHandle;
            throw new Error(chT('请先选择本地保存位置。','Choose a local save location first.'));
        };
        const chooseRoot = async () => {
            if(!window.showDirectoryPicker)throw new Error(chT('当前浏览器不支持选择本地目录。','Directory selection is unavailable in this browser.'));
            const handle=await window.showDirectoryPicker({mode:'readwrite'});
            state.rootHandle=handle; state.savedRootHandle=handle;
            await chDirectoryHandleSave(handle);
            updateArchiveSummary();
            return handle;
        };
        const restoreSavedRoot = async () => {
            const handle=await chDirectoryHandleLoad();
            if(!handle)return false;
            state.savedRootHandle=handle;
            const permission=await chDirectoryHandlePermission(handle,false);
            if(permission==='granted'){
                state.rootHandle=handle;
                state.layoutState=await chArchiveLayoutState(handle).catch(()=>null);
                updateArchiveSummary(); updateControls();
                if(state.list.length) await runPreflight(true);
                return true;
            }
            updateArchiveSummary(); updateControls();
            return false;
        };
        const decorateProjectKnowledge = (items, complete) => (items||[]).map(item=>({...item,__chProjectState:item.__chProjectState||((item.projectId||item.projectTitle)?'known':complete?'none':'unknown'),__chArchiveState:item.__chArchiveState||'known'}));
        const currentWorkspaceForRemote = () => state.mode==='team' ? state.workspaceId : null;
        const applyRemoteSnapshot = snapshot => {
            const list=decorateProjectKnowledge(snapshot?.list||[],snapshot?.complete===true);
            state.remoteUniverse=list;state.remoteUniverseComplete=snapshot?.complete===true;state.remoteUniverseNote=snapshot?.note||null;state.remoteCacheMeta={validatedAt:snapshot?.validatedAt||0,fullFetchedAt:snapshot?.fullFetchedAt||0,refreshMode:snapshot?.refreshMode||'cache'};state.remoteAppliedValidatedAt=Math.max(Number(state.remoteAppliedValidatedAt||0),Number(snapshot?.validatedAt||0));
            if(state.mode==='team'){state.list=list;return;}
            state.accountUniverse=list;state.accountUniverseComplete=state.remoteUniverseComplete;state.accountUniverseNote=state.remoteUniverseNote;state.accountLoadedAt=state.remoteCacheMeta.validatedAt||Date.now();
            state.list=state.mode==='project'?list.filter(item=>item.projectId||item.projectTitle):list;
        };
        const applyRemoteSnapshotSafely = async snapshot => {
            if(Number(snapshot?.validatedAt||0)<=Number(state.remoteAppliedValidatedAt||0))return false;
            if(chSyncRun.active){state.pendingRemoteSnapshot=snapshot;return false;}
            applyRemoteSnapshot(snapshot);renderAll();if(state.rootHandle)await runPreflight(true);return true;
        };
        const ensureTeamWorkspace = () => {
            if(state.mode!=='team')return;
            if(!state.workspaceId){const ids=detectAllWorkspaceIds();if(ids.length===0)throw new Error(chT('未检测到 Team Workspace ID，请先打开一个团队对话后再试。','No Team Workspace ID detected. Open a team conversation first.'));state.workspaceId=ids[0];}
        };
        const remoteProgressText = info => {
            if(!info)return chT('正在加载云端对话…','Loading cloud conversations…');
            if(info.message)return info.message;
            return chT('正在加载云端对话…','Loading cloud conversations…');
        };
        const startRemoteRefresh = async (ws, options={}) => {
            if(state.remoteRefreshPromise)return state.remoteRefreshPromise;
            const generation=++state.remoteRefreshGeneration;
            const userProgress=options.onProgress;
            const userPartial=options.onPartial;
            const task=(async()=>{
                const snapshot=await chRefreshRemoteIndex(ws,{
                    ...options,
                    onProgress:info=>{
                        state.loadingMessage=remoteProgressText(info);
                        try{userProgress?.(info);}catch(_){}
                        if(state.loading)renderList();
                    },
                    onPartial:partial=>{
                        try{userPartial?.(partial);}catch(_){}
                        if(generation!==state.remoteRefreshGeneration||chSyncRun.active)return;
                        if(partial?.list?.length){applyRemoteSnapshot(partial);renderAll();}
                    }
                });
                if(generation!==state.remoteRefreshGeneration)return snapshot;
                return snapshot;
            })();
            state.remoteRefreshPromise=task;
            try{return await task;}finally{if(state.remoteRefreshPromise===task)state.remoteRefreshPromise=null;}
        };
        chSetNetworkStatusHook(info=>{
            if(chSyncRun.active||!state.loading||!info)return;
            const remaining=Number(info.remainingMs||0);
            const suffix=info.countdown&&remaining>0?` · ${chFormatRemainingDuration(remaining)}`:'';
            state.loadingMessage=`${info.primary||chT('网络等待','Network wait')}${suffix}${info.secondary?` · ${info.secondary}`:''}`;
            renderList();
        });
        const loadRemoteList = async (force=false, forceFull=false) => {
            state.loading=true;state.loadingMessage=chT('正在加载云端对话…','Loading cloud conversations…');state.syncStatusById.clear();state.lastPlan=null;renderList();
            try{
                ensureTeamWorkspace(); const ws=currentWorkspaceForRemote();
                if(!force){
                    const cached=await chRemoteCacheGet(ws);
                    // Complete or incomplete cache is useful for immediate display. Incomplete
                    // cache never proves LOCAL_ONLY and is always refreshed in the background.
                    if(cached&&Array.isArray(cached.list)&&cached.list.length){
                        applyRemoteSnapshot({...cached,refreshMode:cached.complete?'persistent-cache':'persistent-cache-incomplete'}); state.loading=false; renderAll(); if(state.rootHandle)await runPreflight(true);
                        void (async()=>{try{const fresh=await startRemoteRefresh(ws);await applyRemoteSnapshotSafely(fresh);}catch(err){console.warn('[ChatHarbor] background remote refresh failed',err);}})();
                        return;
                    }
                }
                const snapshot=await startRemoteRefresh(ws,{forceFull:Boolean(forceFull)}); applyRemoteSnapshot(snapshot); state.loading=false;state.loadingMessage=''; renderAll(); if(state.rootHandle)await runPreflight(true);
            }catch(err){state.loading=false;state.loadingMessage='';if(!state.remoteUniverse.length){state.list=[];state.filtered=[];state.remoteUniverse=[];}$('conv-status').textContent=`${chT('加载失败','Load failed')}: ${err.message}`;renderList();}
        };
        const ensureRemoteFreshForSync = async () => {
            ensureTeamWorkspace(); const ws=currentWorkspaceForRemote();
            if(state.remoteRefreshPromise){
                chSetProgress(chT('刷新云端对话','Refreshing remote index'),chT('等待正在进行的远端快速刷新完成…','Waiting for the active remote refresh…'),0);
                const snapshot=await state.remoteRefreshPromise;if(Number(snapshot?.validatedAt||0)>Number(state.remoteAppliedValidatedAt||0)){applyRemoteSnapshot(snapshot);renderAll();if(state.rootHandle)await runPreflight(true);}
            }
            const age=Date.now()-Number(state.remoteCacheMeta?.validatedAt||0);
            if(state.remoteUniverseComplete&&age>=0&&age<=CH_REMOTE_SYNC_FRESH_MS)return;
            chSetProgress(chT('刷新云端对话','Refreshing remote index'),chT('同步前确认最新列表；无变化时只检查最新窗口。','Confirming the latest remote index; stable heads stop early.'),0);
            const keep=new Set(state.selected); const snapshot=await startRemoteRefresh(ws); applyRemoteSnapshot(snapshot);
            state.selected.clear(); for(const id of keep)if(state.remoteUniverse.some(item=>item.id===id))state.selected.add(id); renderAll(); if(state.rootHandle)await runPreflight(true);
            if(!state.remoteUniverseComplete)throw new Error(chT('云端对话列表还没有加载完整。为避免漏同步，本轮不会写入，请稍后刷新重试。','The cloud conversation list is not fully loaded yet. To avoid missing conversations, this sync will not write; refresh and try again later.'));
        };
        const runPreflight = async (automatic=false) => {
            if(!state.rootHandle)return;
            const root=state.rootHandle;
            preflightBtn.disabled=true;
            try{
                state.layoutState=await chArchiveLayoutState(root);
                if(state.layoutState.requiresMigration){
                    state.lastPlan=null;state.localScan=null;state.syncStatusById.clear();state.syncStatus='all';
                    chSetProgress(chT('需要升级本地保存结构','Local save upgrade required'),`${chT('发现旧的保存结构','An older save structure was found')} · ${state.layoutState.total} ${chT('条记录','records')}`,100);
                    renderAll();return;
                }
                chSetProgress(automatic?chT('检查本地文件','Checking local files'):chT('重新检查','Checking again'),chT('正在检查本地文件…','Checking local files…'),0);
                const {localScan,plan}=await chRunPreflightPlanner({rootHandle:root,remoteList:state.remoteUniverse.length?state.remoteUniverse:state.list,selectedIds:null,remoteUniverseComplete:state.remoteUniverseComplete,remoteUniverseNote:state.remoteUniverseNote,includeAttachments:state.includeAttachments});
                state.localScan=localScan;
                state.layoutState=await chArchiveLayoutState(root);
                applyPreflightStatuses(plan);renderAll();
            }catch(err){console.error('[ChatHarbor] preflight failed',err);chSetProgress(chT('检查本地文件失败','Local scan failed'),err?.message||String(err),100);}finally{updateControls();}
        };
        const runLayoutMigration = async () => {
            if(!state.rootHandle || !state.layoutState?.requiresMigration || state.migrationActive)return;
            const ok = window.confirm(chT(
                '检测到旧的保存结构，需要升级后才能继续同步。升级只整理本地文件，不会重新下载对话，也不会删除未识别的文件。现在升级吗？',
                'An older save structure was found and must be upgraded before syncing. The upgrade only reorganizes local files; it will not re-download conversations or delete unrecognized files. Upgrade now?'
            ));
            if(!ok)return;
            state.migrationActive=true;updateControls();renderList();
            try{
                chSetProgress(chT('正在升级本地保存结构','Upgrading local save structure'),chT('只整理本地文件，不会下载对话','Reorganizing local files only; conversations will not be downloaded'),0);
                const result=await chMigrateArchiveLayoutV1ToV2(state.rootHandle,info=>{
                    const pct=info.total?Math.round((info.index/info.total)*100):0;
                    chSetProgress(chT('正在升级本地保存结构','Upgrading local save structure'),`${info.index}/${info.total} · ${String(info.title||info.id||'').slice(0,42)}`,pct);
                });
                state.migrationReport=result;
                state.layoutState=await chArchiveLayoutState(state.rootHandle);
                chRenderInlineReport(
                    chT('本地保存结构升级完成','Local save structure upgraded'),
                    [
                        `${chT('已整理','Reorganized')}: ${result.migrated}/${result.total}`,
                        `${chT('来源','Source')}: ${result.provider || CH_PROVIDER}`,
                        `${chT('保存结构已升级','Save structure upgraded')}`,
                        `${chT('需要注意','Needs attention')}: ${(result.cleanupWarnings||[]).length}`,
                        chT('未重新下载任何会话。','No conversation was re-downloaded.')
                    ],
                    JSON.stringify(result,null,2),
                    (result.cleanupWarnings||[]).length?'warn':'success'
                );
                await runPreflight(true);
            }catch(err){
                console.error('[ChatHarbor] layout migration failed',err);
                state.layoutState=await chArchiveLayoutState(state.rootHandle).catch(()=>state.layoutState);
                chSetProgress(chT('本地保存结构升级未完成','Local save upgrade incomplete'),err?.message||String(err),100);
                chRenderInlineReport(chT('本地保存结构升级未完成','Local save upgrade incomplete'),[err?.message||String(err),chT('已完成的逐会话提交保持有效；下次可继续升级。','Completed per-conversation commits remain valid; migration can be resumed.')],err?.stack||err?.message||String(err),'error');
            }finally{
                state.migrationActive=false;updateArchiveSummary();updateControls();renderList();
            }
        };
        const runSync = async () => {
            const root=await ensureRoot();
            if(state.layoutState?.requiresMigration){chSetProgress(chT('需要升级本地保存结构','Local save upgrade required'),chT('请先完成升级，再开始同步。','Finish the upgrade before syncing.'),100);return;}
            try{
                await ensureRemoteFreshForSync();
                const selectedIds=new Set(state.selected);
                if(selectedIds.size===0)return;
                chBeginControlledRun(state.networkPolicy);
                state.runSettings={includeAttachments:Boolean(state.includeAttachments),networkPolicy:{...chSyncRun.policy}};
                const launcher=getExportButton(); launcher.classList.add('gre-busy'); const launcherPill=document.getElementById('gre-fab-status'); if(launcherPill)launcherPill.classList.remove('gre-visible');
                renderList();chSetProgress(chT('同步','Directory sync'),`${chT('正在准备同步…','Preparing sync…')} · ${chNetworkPolicySummary(chSyncRun.policy)}`,0);
                const remote=state.remoteUniverse.length?state.remoteUniverse:state.list;
                const result=await chRunIntegratedDirectorySync({rootHandle:root,remoteList:remote,selectedIds,workspaceId:state.workspaceId,includeAttachments:state.runSettings.includeAttachments,remoteUniverseComplete:state.remoteUniverseComplete,remoteUniverseNote:state.remoteUniverseNote,networkPolicy:chSyncRun.policy,onItemClassified:(item)=>{if(item.id&&item.finalAction==='ERROR'){state.syncStatusById.set(item.id,'ERROR');renderList();}},onItemCommitted:(item)=>{if(item.id&&item.finalAction)state.syncStatusById.set(item.id,item.finalAction==='OBSERVATION_ONLY'?'UNCHANGED':item.finalAction==='ATTACHMENT_BACKFILL'?'UNCHANGED':item.finalAction);renderList();},onItemFailed:(item)=>{if(item.id){state.syncStatusById.set(item.id,'ERROR');renderList();}}});
                applyFinalStatuses(result);renderAll();
            }catch(err){if(chIsCancellation(err))chSetProgress(chT('同步已取消','Sync cancelled'),chT('已在安全边界停止；已提交会话保留。','Stopped at a safe boundary; committed conversations were kept.'),100);else{console.error('[ChatHarbor] sync failed',err);chSetProgress(chT('同步失败','Sync failed'),err?.message||String(err),100);}}finally{const launcher=getExportButton();launcher.classList.remove('gre-busy','gre-progress');const launcherPill=document.getElementById('gre-fab-status');if(launcherPill)launcherPill.classList.remove('gre-visible');fabScheduleCollapse(launcher);chEndControlledRun();state.runSettings=null;const deferred=state.pendingRemoteSnapshot;state.pendingRemoteSnapshot=null;if(deferred){applyRemoteSnapshot(deferred);renderAll();if(state.rootHandle)await runPreflight(true);}else{renderList();}}
        };

        searchInput.oninput=e=>{state.query=e.target.value||'';applyFilters();renderList();};
        spaceSelect.onchange=async e=>{const next=e.target.value;state.projectFilter='all';state.syncStatus='all';state.mode=next;state.workspaceId=null;await loadRemoteList(false);};
        projectSelect.onchange=e=>{state.projectFilter=e.target.value;applyFilters();renderList();};
        archivedSelect.onchange=e=>{state.archived=e.target.value;applyFilters();renderList();};
        syncStatusSelect.onchange=e=>{state.syncStatus=e.target.value;applyFilters();renderList();};
        timeFieldSelect.onchange=e=>{state.timeField=e.target.value;applyFilters();renderList();};
        timeRangeSelect.onchange=e=>{state.timeRange=e.target.value;updateTimeSummary();applyFilters();renderList();};
        sortSelect.onchange=e=>{state.sort=e.target.value;applyFilters();renderList();};
        startDateInput.onchange=e=>{state.startDate=e.target.value||'';applyFilters();renderList();};
        endDateInput.onchange=e=>{state.endDate=e.target.value||'';applyFilters();renderList();};
        includeAttachmentsInput.onchange=async e=>{if(chSyncRun.active){e.target.checked=Boolean(state.runSettings?.includeAttachments);updateSettingsSummary();return;}state.includeAttachments=e.target.checked;updateSettingsSummary();if(state.rootHandle)await runPreflight(true);};
        selectAllCheckbox.onchange=()=>{const allSelected=state.filtered.length>0&&state.filtered.every(item=>state.selected.has(item.id));if(allSelected){state.filtered.forEach(item=>state.selected.delete(item.id));}else{state.filtered.forEach(item=>state.selected.add(item.id));}renderList();};
        refreshBtn.title=chT('更新云端对话列表。','Update the cloud conversation list.');
        preflightBtn.title=chT('重新检查当前保存位置。','Check the current save location again.');refreshBtn.onclick=async(e)=>{const keep=new Set(state.selected);await loadRemoteList(true,Boolean(e?.shiftKey));state.selected.clear();for(const id of keep)if(state.list.some(item=>item.id===id))state.selected.add(id);renderList();};
        closeBtn.onclick=closeDialog;
        chooseDirBtn.onclick=async()=>{try{
            state.lastPlan=null;
            if(!state.rootHandle && state.savedRootHandle){
                const permission=await chDirectoryHandlePermission(state.savedRootHandle,true);
                if(permission==='granted') state.rootHandle=state.savedRootHandle;
                else return;
            } else {
                await chooseRoot();
            }
            state.layoutState=await chArchiveLayoutState(state.rootHandle).catch(()=>null);
            await runPreflight(true);
        }catch(err){if(err?.name!=='AbortError')chSetProgress(chT('选择保存位置失败','Could not choose save location'),err?.message||String(err),null);}};
        preflightBtn.onclick=()=>runPreflight(false);
        migrateLayoutBtn.onclick=runLayoutMigration;
        syncSelectedBtn.onclick=runSync;
        speedLevelInput.onchange=applySpeedPreset;
        [batchSizeInput,pauseMinInput,pauseMaxInput].forEach(el=>el.onchange=persistPolicy);
        pauseSyncBtn.onclick=()=>{if(!chSyncRun.active)return;if(chSyncRun.paused)chResumeRun();else chRequestPause();};
        cancelSyncBtn.onclick=()=>{if(!chSyncRun.active)return;chRequestCancel('USER_CANCELLED');chSetProgress(chT('正在取消同步','Cancelling sync'),chT('不会开始新的详情请求或新的会话事务；当前原子事务会先完成。','No new detail fetch or conversation transaction will start; the current atomic transaction will finish first.'),null);};
        overlay.onclick=e=>{if(e.target===overlay)closeDialog();};
        document.addEventListener('keydown',function esc(ev){if(ev.key==='Escape'&&document.body.contains(overlay)&&!chSyncRun.active&&!state.migrationActive){document.removeEventListener('keydown',esc);closeDialog();}});
        chUpdateRunControlUi();updateTimeSummary();updateSettingsSummary();restoreSavedRoot();loadRemoteList();
    }

'''

picker_start = text.find("    function showConversationPicker(options = {}) {")
picker_end = text.find("    /**\n     * [重构] 多步骤、用户主导的导出对话框", picker_start)
if picker_start < 0 or picker_end < 0:
    raise SystemExit("Single-page picker replacement boundaries not found")
text = text[:picker_start] + single_page_picker + text[picker_end:]

# FAB/API opens the single desktop workspace directly; the old space chooser remains only as
# inherited compatibility code and is no longer the primary user path.
text = text.replace("            showExportDialog();", "            showConversationPicker({ mode: 'personal', workspaceId: null, includeAttachments: false });", 1)
text = text.replace("        showDialog: showExportDialog,", "        showDialog: () => showConversationPicker({ mode: 'personal', workspaceId: null, includeAttachments: false }),", 1)

# Inline report renderer: results stay in the right rail instead of opening a third modal layer.
inline_report_helpers = r'''    function chRenderInlineReport(title, summaryLines, detailText, tone = 'success') {
        const panel = document.getElementById('ch-result-panel');
        const titleEl = document.getElementById('ch-result-title');
        const summaryEl = document.getElementById('ch-result-summary');
        const copyBtn = document.getElementById('ch-copy-report-btn');
        if (!panel || !titleEl || !summaryEl) {
            console.log(`[ChatHarbor] ${title}\n${detailText || summaryLines.join('\n')}`);
            return;
        }
        panel.style.display = 'block';
        panel.style.background = tone === 'error' ? '#fef2f2' : tone === 'warn' ? '#fffbeb' : '#f0fdf4';
        panel.style.borderColor = tone === 'error' ? '#fecaca' : tone === 'warn' ? '#fde68a' : '#bbf7d0';
        titleEl.textContent = title;
        summaryEl.textContent = summaryLines.join('\n');
        if (copyBtn) copyBtn.onclick = async () => {
            const payload = detailText || summaryLines.join('\n');
            try { await navigator.clipboard.writeText(payload); copyBtn.textContent = chT('已复制','Copied'); setTimeout(()=>copyBtn.textContent=chT('复制详细报告','Copy details'),1200); }
            catch (_) { console.log(payload); }
        };
    }

'''
insert_before = "    function chPreflightReportText(plan) {"
pos = text.find(insert_before)
if pos < 0:
    raise SystemExit("Preflight report anchor not found")
text = text[:pos] + inline_report_helpers + text[pos:]

# Localize the detailed preflight report and render its summary inline.
preflight_text_start = text.find("    function chPreflightReportText(plan) {")
preflight_show_start = text.find("    function chShowPreflightReport(plan) {", preflight_text_start)
preflight_run_start = text.find("    async function chRunPreflightPlanner", preflight_show_start)
if min(preflight_text_start, preflight_show_start, preflight_run_start) < 0:
    raise SystemExit("Preflight report replacement boundaries missing")
preflight_report_block = r'''    function chPreflightReportText(plan) {
        const s = plan.summary;
        const lines = [
            chT('ChatHarbor｜目录扫描 + 同步预检','ChatHarbor | Archive Scan + Preflight'),
            chT('只读：未抓取对话详情，未写入任何文件或 Manifest。','Read-only: no conversation detail fetch and no disk/manifest write.'), '',
            `Remote: ${s.remote} (${s.remoteUnique} unique IDs)`,
            `${chT('远端全集','Remote universe')}: ${s.remoteUniverseComplete ? chT('完整','COMPLETE') : chT('不完整','INCOMPLETE')}`,
            ...(s.remoteUniverseNote ? [`${chT('远端备注','Remote note')}: ${s.remoteUniverseNote}`] : []),
            `${chT('本地','Local')}: ${s.local}`,
            `${chT('新增','NEW')}: ${s.newCount}`,
            `${chT('远端更新时间候选','remote-update candidates')}: ${s.remoteUpdateCandidateCount}`,
            `${chT('改名候选','rename candidates')}: ${s.renameCandidateCount}`,
            `${chT('已同步','UNCHANGED')}: ${s.unchangedCount}`,
            `${chT('元数据候选','metadata candidates')}: ${s.metadataCandidateCount}`,
            `${chT('附件候选','attachment candidates')}: ${s.attachmentCandidateCount||0}`,
            `${chT('本地未跟踪待核验','raw-only verify candidates')}: ${s.rawOnlyVerifyCount}`,
            `${chT('仅本地','LOCAL_ONLY')}: ${s.localOnlyReliable ? s.localOnlyCount : chT('未知（远端全集不完整）','UNKNOWN (remote universe incomplete)')}`,
            `${chT('重复ID','duplicate IDs')}: ${s.duplicateIdCount}`,
            `${chT('错误','ERROR')}: ${s.errorCount}`,
            `${chT('最多需要抓取详情','maximum fetch required')}: ${s.maximumFetchRequired}`,
            '', `${chT('Manifest 跟踪','Manifest tracked')}: ${s.manifestTracked}`, `${chT('Manifest 快检','Manifest fast-checked')}: ${s.trackedFastChecked||0}`, `${chT('附件路径快检','Asset fast-check')}: ${s.assetFastChecked||0}`, `${chT('附件缺失/异常','Attachment issues')}: ${s.assetIntegrityIssues||0}`, `${chT('原始对话 JSON','Raw conversation JSON files')}: ${s.rawConversationFiles}`, `${chT('仅原始文件 ID','Raw-only IDs')}: ${s.rawOnlyIds}`
        ];
        if (plan.errors.length) {
            lines.push('', `=== ${chT('扫描错误','SCAN ERRORS')} (${plan.errors.length}) ===`);
            for (const error of plan.errors.slice(0,80)) lines.push(`[${error.type}] ${error.id||'-'} | ${error.path||'-'} | ${error.message||''}`);
        }
        return lines.join('\n');
    }

    function chShowPreflightReport(plan) {
        const detail = chPreflightReportText(plan);
        const btn = document.getElementById('ch-archive-copy-report-btn');
        if (btn) btn.onclick = () => {
            const s = plan.summary;
            const pending = Math.max(0, Number(s.maximumFetchRequired || 0));
            const confirm = Math.max(0, Number(s.rawOnlyVerifyCount || 0)) + (s.localOnlyReliable ? Math.max(0, Number(s.localOnlyCount || 0)) : 0);
            const issues = Math.max(0, Number(s.errorCount || 0) + Number(s.duplicateIdCount || 0));
            chRenderInlineReport(chT('本地检查详情','Local check details'),[
                `${chT('已保存','Saved')} ${s.local || 0} · ${chT('已同步','Synced')} ${s.unchangedCount || 0}`,
                `${chT('待同步','To sync')} ${pending} · ${chT('需确认','Check')} ${confirm} · ${chT('异常','Error')} ${issues}`
            ],detail,issues?'warn':'success');
        };
        const resultPanel = document.getElementById('ch-result-panel');
        if (resultPanel && !chSyncRun.active) resultPanel.style.display = 'none';
    }

'''
text = text[:preflight_text_start] + preflight_report_block + text[preflight_run_start:]

# Localize integrated detail text and keep completion report in the sidebar.
integrated_text_start = text.find("    function chIntegratedSyncReportText(result) {")
integrated_run_start = text.find("    async function chRunIntegratedDirectorySync", integrated_text_start)
if integrated_text_start < 0 or integrated_run_start < 0:
    raise SystemExit("Integrated report replacement boundaries missing")
integrated_report_block = r'''    function chIntegratedSyncReportText(result) {
        const c = result.verification.counts || {};
        const lines = [
            chT('ChatHarbor｜版本感知选择性同步','ChatHarbor | Version-aware Selective Sync'), '',
            `${chT('范围内远端ID','Scope remote IDs')}: ${result.plan.summary.scopeRemote}`,
            `${chT('实际抓取详情','Detail fetched')}: ${result.verification.detailFetchCount}`,
            `${chT('新增','NEW')}: ${c.NEW||0}`, `${chT('内容更新','UPDATED')}: ${c.UPDATED||0}`, `${chT('仅改名','RENAMED_ONLY')}: ${c.RENAMED_ONLY||0}`,
            `${chT('更新+改名','UPDATED_AND_RENAMED')}: ${c.UPDATED_AND_RENAMED||0}`, `${chT('仅元数据','METADATA_ONLY')}: ${c.METADATA_ONLY||0}`,
            `${chT('已同步','UNCHANGED')}: ${(c.UNCHANGED||0)+(c.OBSERVATION_ONLY||0)}`, `${chT('附件补齐','Attachment backfill')}: ${c.ATTACHMENT_BACKFILL||0}`, `${chT('本地未跟踪','LOCAL_UNTRACKED')}: ${c.LOCAL_UNTRACKED||0}`,
            `${chT('仅本地','LOCAL_ONLY')}: ${result.plan.summary.localOnlyReliable?result.plan.summary.localOnlyCount:chT('未知','UNKNOWN')}`,
            `${chT('重复ID','DUPLICATE')}: ${c.DUPLICATE||0}`, `${chT('错误','ERROR')}: ${c.ERROR||0}`, '',
            `${chT('尝试同步','Sync attempted')}: ${result.sync.attempted}`, `${chT('同步成功','Sync succeeded')}: ${result.sync.succeeded}`, `${chT('同步失败','Sync failed')}: ${result.sync.failed}`,
            `${chT('仅Manifest提交','Manifest-only commits')}: ${result.sync.manifestOnly}`, `${chT('文件+Manifest提交','File+manifest commits')}: ${result.sync.fileCommits}`,
            `${chT('清理警告','Cleanup warnings')}: ${result.sync.cleanupWarnings.length}`, `${chT('已取消','Cancelled')}: ${result.sync.cancelled?chT('是','YES'):chT('否','NO')}`, '',
            chT('LOCAL_ONLY 从未自动删除。','LOCAL_ONLY was never deleted.'), chT('清理只触碰旧 Manifest 明确跟踪的路径。','Cleanup only touched paths explicitly tracked by the prior manifest.')
        ];
        if(result.sync.failures.length){lines.push('',`=== ${chT('同步失败项','SYNC FAILURES')} ===`);for(const f of result.sync.failures.slice(0,50))lines.push(`[${f.action}] ${f.id}: ${f.error}`);}
        if(result.sync.cleanupWarnings.length){lines.push('',`=== ${chT('清理警告（安全保留残留）','CLEANUP WARNINGS (safe leftovers preserved)')} ===`);result.sync.cleanupWarnings.slice(0,50).forEach(x=>lines.push(x));}
        return lines.join('\n');
    }

    function chShowIntegratedSyncReport(result) {
        const c = result.verification.counts || {};
        const tone = result.sync.failed || (c.ERROR||0) || (c.DUPLICATE||0) ? 'warn' : 'success';
        chRenderInlineReport(
            result.sync.cancelled ? chT('同步已取消','Sync cancelled') : result.sync.failed ? chT('同步完成（存在失败）','Sync completed with failures') : chT('同步完成','Sync complete'),
            [
                `${chT('选择','Selected')} ${result.plan.summary.scopeRemote} · ${chT('实际处理','Processed')} ${result.verification.detailFetchCount}`,
                `${chT('同步成功','Synced successfully')} ${result.sync.succeeded} · ${chT('无需更新','No update needed')} ${(c.UNCHANGED||0)+(c.OBSERVATION_ONLY||0)}`,
                `${chT('需确认','Check')} ${(c.LOCAL_UNTRACKED||0)+(result.plan.summary.localOnlyReliable?(result.plan.summary.localOnlyCount||0):0)} · ${chT('异常','Error')} ${(c.ERROR||0)+(c.DUPLICATE||0)+result.sync.failed}`
            ],
            chIntegratedSyncReportText(result), tone
        );
    }

'''
text = text[:integrated_text_start] + integrated_report_block + text[integrated_run_start:]

# Route every ChatHarbor/upstream control-plane /backend-api/ fetch through the shared scheduler.
# Signed binary fetches use parsedUrl.href and intentionally remain direct data-transfer requests.
text = text.replace("await fetch(`/backend-api/", "await chBackendFetch(`/backend-api/")
text = text.replace("await fetch(metadataUrl, { credentials: 'include', headers })", "await chBackendFetch(metadataUrl, { credentials: 'include', headers })")
text = text.replace("await fetch(parsedUrl.href, sameOrigin", "await chDataTransferFetch(parsedUrl.href, sameOrigin")
text = text.replace("if(hasMore)await sleep(jitter());", "")

# Runtime markers for the desktop workspace must be present in the generated userscript.

# Build-time UI/runtime invariants: fail closed instead of generating a script with no visible entry.
required_runtime_markers = [
    "function initFab()",
    "getExportButton();",
    "document.addEventListener('DOMContentLoaded', initFab);",
    "#gpt-rescue-btn",
    "showDialog: () => showConversationPicker",
    "id=\"preflight-plan-btn\"",
    "id=\"sync-directory-btn\"",
    "id=\"ch-pause-sync-btn\"",
    "id=\"ch-cancel-sync-btn\"",
    "CH_SPEED_LEVELS",
    "大量任务（更稳）",
    "保守模式（最稳）",
    "id=\"ch-network-policy-detail\"",
    "会话进度 ${done} / ${chRuntimeProgress.total}",
    "chatharbor-directory-handle-v1",
    "chBeginControlledRun",
    "chGetConversationConservative",
    "async function chBackendFetch",
    "async function chDataTransferFetch",
    "const chBackendScheduler",
    "CH_BACKEND_LANE_DISCOVERY",
    "CH_BACKEND_LANE_ATTACHMENT",
    "chSetNetworkStatusHook",
    "function chBackendRequestDescriptor",
    "function chRetryDelayForFailure",
    "服务器暂时出错（",
    "partial-root",
    "remoteRefreshPromise",
    "pendingRemoteSnapshot",
    "assetFastChecked",
    "onItemFailed",
    "id=\"ch-space-select\"",
    "id=\"select-all-checkbox\"",
    "id=\"ch-result-panel\"",
    "id=\"ch-action-bar\"",
    "id=\"ch-archive-copy-report-btn\"",
    "grid-template-columns:minmax(0,1fr) 310px",
    "const FAB_STORAGE_KEY = 'chatharbor-fab-v2';",
    "chReconcileRuntimeState",
    "正在准备同步",
    "accountUniverse",
    "待同步",
    "function chInferLegacyAttachmentState",
    "function chPlanAttachmentBackfill",
    "Progress is completion-based and monotonic",
    "Reuse only assets whose Manifest identity and physical file both remain valid",
]
missing_runtime_markers = [marker for marker in required_runtime_markers if marker not in text]
if missing_runtime_markers:
    raise SystemExit("Generated runtime invariant failed; missing: " + ", ".join(missing_runtime_markers))
forbidden_runtime_markers = [
    "fetch(`/backend-api/",
    "fetch(metadataUrl, { credentials: 'include', headers })",
    "fetch(parsedUrl.href, sameOrigin",
    "ch-integrated-sync-report-overlay",
    "ch-preflight-report-overlay",
    "id=\"sync-filtered-btn\"",
    "id=\"sync-all-btn\"",
    "id=\"clear-all-btn\"",
]
remaining_forbidden = [marker for marker in forbidden_runtime_markers if marker in text]
if remaining_forbidden:
    raise SystemExit("Desktop workspace invariant failed; obsolete modal remains: " + ", ".join(remaining_forbidden))

out.write_text(text, encoding="utf-8")
print(f"Wrote: {out}")
print(f"Source git blob: {actual_blob}")
print(f"Output SHA-256: {hashlib.sha256(out.read_bytes()).hexdigest()}")
