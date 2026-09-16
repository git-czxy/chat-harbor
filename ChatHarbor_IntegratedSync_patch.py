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
    "// @version      0.0.10.0\n"
    "// @description  Clean-lineage archive sync with Archive Layout v2, local migration, conservative pacing, and version-aware selective sync.\n"
    "// @description:zh-CN 干净来源的本地档案同步：Archive Layout v2、本地迁移、保守节奏、版本识别与选择性同步。\n"
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
    // - content signature recording (not yet used for classification)
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


    // ======================== ChatHarbor Conservative Network Policy ========================
    // Clean reimplementation of the historical ChatHarbor conservative behavior contract.
    const CH_NETWORK_POLICY_KEY = 'chatharbor_network_policy_v1';
    const CH_SPEED_LEVELS = [
        { name: '1. 最快（上游）', base: 600, jitter: 400 },
        { name: '2. 较快', base: 1500, jitter: 1000 },
        { name: '3. 中等', base: 3000, jitter: 2000 },
        { name: '4. 较慢（推荐）', base: 6000, jitter: 4000 },
        { name: '5. 很慢', base: 9000, jitter: 6000 },
        { name: '6. 最慢', base: 12000, jitter: 8000 }
    ];
    const CH_DEFAULT_NETWORK_POLICY = Object.freeze({
        speedIndex: 3,
        batchSize: 20,
        batchPauseMinSec: 180,
        batchPauseMaxSec: 300,
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
        return `${CH_SPEED_LEVELS[p.speedIndex].name} · 每批 ${p.batchSize} · 批间 ${p.batchPauseMinSec}-${p.batchPauseMaxSec} 秒`;
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
        if (chSyncRun.active) throw new Error('已有目录同步任务正在运行。');
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

    function chCancellationError(message = '目录同步已取消。') {
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
        if (status === 429) return 120000 * Math.max(1, attempt);
        if (status && status >= 500) return 30000 * Math.max(1, attempt);
        if (status === 401 || status === 403) return null;
        return 30000 * Math.max(1, attempt);
    }

    async function chGetConversationConservative(id, workspaceId = null) {
        const policy = chNormalizeNetworkPolicy(chSyncRun.policy);
        const maxAttempts = 1 + policy.maxRetries;
        let lastError = null;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            await chControlCheckpoint('detail-fetch');
            try {
                return await getConversation(id, workspaceId);
            } catch (err) {
                if (chIsCancellation(err)) throw err;
                lastError = err;
                const delay = chRetryDelayMs(err, attempt);
                if (attempt >= maxAttempts || delay == null) break;
                await chControlledSleep(
                    delay,
                    '网络异常，保守重试等待',
                    `${id} · 第 ${attempt}/${policy.maxRetries} 次重试前等待 ${Math.round(delay / 1000)} 秒`
                );
            }
        }
        throw lastError || new Error(`获取对话详情失败: ${id}`);
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

    function chSetProgress(primary, secondary = '', percent = null) {
        const els = chProgressElements();
        if (!els.root) return;

        els.root.style.display = 'block';
        if (els.primary) els.primary.textContent = primary || '';
        if (els.secondary) els.secondary.textContent = secondary || '';

        const normalized = Number.isFinite(percent)
            ? Math.max(0, Math.min(100, Math.round(percent)))
            : null;

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
        const pct = chProgressPercent(conversationIndex, conversationTotal, fraction);
        const shortTitle = String(title || 'Untitled Conversation').slice(0, 42);
        chSetProgress(
            `当前第 ${conversationIndex + 1} / ${conversationTotal} 条 · ${phase}`,
            detail ? `${shortTitle} · ${detail}` : shortTitle,
            pct
        );
        setFabStatus(btn, `💾 ${phase} (${Math.round(pct)}/100)`);
    }

    async function chWriteAttachmentsToDirectory(
        targetDir,
        convData,
        workspaceId,
        progress = null
    ) {
        const references = collectVisibleAttachments(convData);
        const failures = [];
        const files = [];
        const sandboxPaths = new Map();
        const usedNames = new Set();

        if (references.length === 0) {
            return {
                detected: 0,
                files,
                failures,
                sandboxPaths,
                folderName: null
            };
        }

        const folderName = generateUniqueFilename(convData).replace(/\.json$/i, '') + '_files';
        const assetDir = await targetDir.getDirectoryHandle(folderName, { create: true });

        for (let i = 0; i < references.length; i++) {
            const reference = references[i];
            if (progress) {
                progress({
                    assetIndex: i,
                    assetTotal: references.length,
                    name: reference.name || reference.fileId || reference.sandboxPath || 'attachment'
                });
            }

            try {
                const downloaded = await fetchAttachmentBinary(reference, convData, workspaceId);
                const filename = uniqueAttachmentName(downloaded.filename, usedNames);
                await chVerifiedDirectoryWrite(assetDir, filename, downloaded.data);

                const diskPath = `${folderName}/${filename}`;
                const relativePath = encodeRelativePath(diskPath);

                files.push({
                    name: filename,
                    path: relativePath,
                    disk_path: diskPath,
                    kind: reference.kind,
                    isImage: reference.isImage,
                    messageId: reference.messageId,
                    ownerRole: reference.ownerRole,
                    size_bytes: chExpectedByteLength(downloaded.data),
                    source_file_id: reference.fileId || null,
                    source_sandbox_path: reference.sandboxPath || null
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

            if (progress) {
                progress({
                    assetIndex: i + 1,
                    assetTotal: references.length,
                    name: reference.name || reference.fileId || reference.sandboxPath || 'attachment'
                });
            }

            await sleep(150);
        }

        return {
            detected: references.length,
            files,
            failures,
            sandboxPaths,
            folderName
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
                }
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
            : (
                attachmentResult?.folderName
                    ? `${relativePrefix}${attachmentResult.folderName}`
                    : null
            );

        const assets = preserveExistingAssets
            ? (Array.isArray(existingRecord.assets) ? existingRecord.assets : [])
            : (attachmentResult?.files || []).map(file => ({
                path: `${relativePrefix}${file.disk_path}`,
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

        return {
            conversation_id: conversationId,
            title,
            create_time: convData?.create_time ?? entry?.create_time ?? null,
            remote_update_time: convData?.update_time ?? entry?.update_time ?? null,
            is_archived: convData?.is_archived ?? entry?.is_archived ?? false,
            project_id: entry?.projectId || null,
            project_title: entry?.projectTitle || null,
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
            attachment_detected: preserveExistingAssets
                ? (existingRecord.attachment_detected ?? assets.length)
                : (attachmentResult?.detected || 0),
            attachment_downloaded: preserveExistingAssets
                ? (existingRecord.attachment_downloaded ?? assets.length)
                : assets.length,
            attachment_failed: preserveExistingAssets
                ? (existingRecord.attachment_failed ?? 0)
                : (attachmentResult?.failures?.length || 0),
            attachment_failures: preserveExistingAssets
                ? (existingRecord.attachment_failures || [])
                : (attachmentResult?.failures || []),
            attachments_preserved_without_download: Boolean(preserveExistingAssets),
            synced_at: syncedAt
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

    async function chScanLocalArchiveReadOnly(rootHandle, onProgress = null) {
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

        if (manifestResult.error) {
            errors.push({
                type: 'MANIFEST_ERROR',
                id: null,
                path: CH_MANIFEST_NAME,
                message: manifestResult.error
            });
        }

        if (manifestResult.manifest) {
            for (const [key, record] of Object.entries(manifestResult.manifest.conversations)) {
                const id = String(key || '');
                if (!id) {
                    errors.push({
                        type: 'MANIFEST_EMPTY_ID',
                        id: null,
                        path: CH_MANIFEST_NAME,
                        message: 'manifest contains an empty conversation_id key'
                    });
                    continue;
                }
                if (record?.conversation_id && String(record.conversation_id) !== id) {
                    errors.push({
                        type: 'MANIFEST_ID_MISMATCH',
                        id,
                        path: CH_MANIFEST_NAME,
                        message: `record conversation_id ${record.conversation_id} does not match manifest key`
                    });
                }
                manifestById.set(id, {
                    ...(record || {}),
                    conversation_id: id,
                    tracking: 'manifest'
                });
            }
        }

        const walk = async (dirHandle, relativeDir = '') => {
            for await (const [name, handle] of dirHandle.entries()) {
                const relativePath = chJoinRelativePath(relativeDir, name);
                if (handle.kind === 'directory') {
                    if (/_files$/i.test(name)) {
                        skippedAssetDirs++;
                        continue;
                    }
                    await walk(handle, relativePath);
                    continue;
                }
                if (!/\.json$/i.test(name) || name === CH_MANIFEST_NAME) continue;

                jsonFilesSeen++;
                if (onProgress && jsonFilesSeen % 10 === 0) {
                    onProgress({ jsonFilesSeen, conversationJsonFiles, path: relativePath });
                }

                let data;
                try {
                    data = await chReadJsonHandle(handle);
                } catch (_) {
                    // A .json attachment outside a conventional *_files directory may not be a
                    // ChatGPT conversation. Do not treat parse failure as archive corruption here.
                    ignoredJsonFiles++;
                    continue;
                }

                if (!chLooksLikeConversationJson(data)) {
                    ignoredJsonFiles++;
                    continue;
                }

                const id = String(data.conversation_id || data.id || '');
                if (!id) {
                    errors.push({
                        type: 'RAW_CONVERSATION_ID_MISSING',
                        id: null,
                        path: relativePath,
                        message: 'conversation-shaped JSON has no conversation_id'
                    });
                    continue;
                }

                conversationJsonFiles++;
                const rawRecord = {
                    conversation_id: id,
                    title: data.title || '',
                    create_time: data.create_time ?? null,
                    remote_update_time: data.update_time ?? null,
                    is_archived: data.is_archived ?? false,
                    json_path: relativePath,
                    tracking: 'raw_only'
                };
                if (!rawById.has(id)) rawById.set(id, []);
                rawById.get(id).push(rawRecord);
                rawByPath.set(relativePath, rawRecord);
            }
        };

        await walk(rootHandle, '');

        const duplicateIds = new Set();
        const duplicates = [];
        for (const [id, records] of rawById.entries()) {
            if (records.length > 1) {
                duplicateIds.add(id);
                duplicates.push({
                    id,
                    source: 'local',
                    paths: records.map(record => record.json_path)
                });
            }
        }

        const blockedIds = new Set();
        const recordsById = new Map();
        const allIds = new Set([...manifestById.keys(), ...rawById.keys()]);

        for (const id of allIds) {
            const manifestRecord = manifestById.get(id) || null;
            const rawRecords = rawById.get(id) || [];

            if (duplicateIds.has(id)) {
                blockedIds.add(id);
            }

            if (manifestRecord) {
                const trackedPath = String(manifestRecord.json_path || '');
                if (!trackedPath) {
                    errors.push({
                        type: 'MANIFEST_JSON_PATH_MISSING',
                        id,
                        path: CH_MANIFEST_NAME,
                        message: 'tracked conversation has no json_path'
                    });
                    blockedIds.add(id);
                } else {
                    const rawAtTrackedPath = rawByPath.get(trackedPath);
                    if (!rawAtTrackedPath) {
                        errors.push({
                            type: 'MANIFEST_JSON_NOT_FOUND',
                            id,
                            path: trackedPath,
                            message: 'manifest json_path was not found during archive scan'
                        });
                        blockedIds.add(id);
                    } else if (rawAtTrackedPath.conversation_id !== id) {
                        errors.push({
                            type: 'MANIFEST_JSON_ID_MISMATCH',
                            id,
                            path: trackedPath,
                            message: `tracked JSON belongs to ${rawAtTrackedPath.conversation_id}`
                        });
                        blockedIds.add(id);
                    }
                }
                recordsById.set(id, manifestRecord);
            } else if (rawRecords.length === 1) {
                recordsById.set(id, rawRecords[0]);
            } else if (rawRecords.length > 1) {
                // Keep identity visible for counts, but do not choose one duplicate as canonical.
                recordsById.set(id, {
                    conversation_id: id,
                    title: rawRecords[0]?.title || '',
                    remote_update_time: rawRecords[0]?.remote_update_time ?? null,
                    tracking: 'duplicate_raw'
                });
            }
        }

        const errorsById = new Map();
        for (const error of errors) {
            if (!error.id) continue;
            if (!errorsById.has(error.id)) errorsById.set(error.id, []);
            errorsById.get(error.id).push(error);
        }

        if (onProgress) {
            onProgress({ jsonFilesSeen, conversationJsonFiles, done: true });
        }

        return {
            manifestExists: manifestResult.exists,
            manifestReadable: Boolean(manifestResult.manifest),
            manifest: manifestResult.manifest,
            recordsById,
            manifestById,
            rawById,
            duplicateIds,
            duplicates,
            blockedIds,
            errors,
            errorsById,
            stats: {
                local: recordsById.size,
                manifestTracked: manifestById.size,
                manifestProject: Array.from(manifestById.values()).filter(record => record.project_id || record.project_title).length,
                manifestRoot: Array.from(manifestById.values()).filter(record => !(record.project_id || record.project_title)).length,
                rawConversationFiles: conversationJsonFiles,
                rawUniqueIds: rawById.size,
                rawOnlyIds: Array.from(recordsById.values()).filter(record => record.tracking === 'raw_only').length,
                archiveLayoutVersion: manifestResult.manifest ? chManifestLayoutVersion(manifestResult.manifest) : CH_ARCHIVE_LAYOUT_VERSION,
                provider: manifestResult.manifest ? (chManifestProvider(manifestResult.manifest) || CH_PROVIDER) : CH_PROVIDER,
                migrationRequired: Boolean(manifestResult.manifest && chManifestRequiresLayoutMigration(manifestResult.manifest)),
                jsonFilesSeen,
                ignoredJsonFiles,
                skippedAssetDirs
            }
        };
    }

    function chTimeEquivalent(a, b) {
        const aa = normalizeEpochSeconds(a);
        const bb = normalizeEpochSeconds(b);
        if (!aa || !bb) return false;
        return Math.abs(aa - bb) <= 0.001;
    }

    function chBuildPreflightPlan(remoteList, localScan, selectedIds = null, options = {}) {
        const allRemote = Array.isArray(remoteList) ? remoteList : [];
        const remoteUniverseComplete = options.remoteUniverseComplete !== false;
        const remoteUniverseNote = options.remoteUniverseNote || null;
        const selected = selectedIds instanceof Set && selectedIds.size > 0
            ? selectedIds
            : null;

        const remoteById = new Map();
        const remoteErrors = [];
        for (const entry of allRemote) {
            const id = chRemoteConversationId(entry);
            if (!id) {
                remoteErrors.push({
                    type: 'REMOTE_ID_MISSING',
                    id: null,
                    title: entry?.title || '',
                    message: 'remote list entry has no conversation_id'
                });
                continue;
            }
            if (!remoteById.has(id)) remoteById.set(id, []);
            remoteById.get(id).push(entry);
        }

        const remoteDuplicateIds = new Set();
        const remoteDuplicates = [];
        for (const [id, entries] of remoteById.entries()) {
            if (entries.length > 1) {
                remoteDuplicateIds.add(id);
                remoteDuplicates.push({
                    id,
                    source: 'remote',
                    count: entries.length,
                    titles: entries.map(entry => entry?.title || '')
                });
            }
        }

        const duplicateIds = new Set([
            ...localScan.duplicateIds,
            ...remoteDuplicateIds
        ]);

        const globalRemoteIds = new Set(remoteById.keys());
        const scopeIds = selected
            ? new Set(Array.from(selected).filter(id => globalRemoteIds.has(id)))
            : new Set(globalRemoteIds);

        const items = [];
        let newCount = 0;
        let remoteUpdateCandidateCount = 0;
        let renameCandidateCount = 0;
        let unchangedCount = 0;
        let metadataCandidateCount = 0;
        let rawOnlyVerifyCount = 0;
        let errorCount = 0;
        let maximumFetchRequired = 0;

        for (const id of scopeIds) {
            const remoteEntries = remoteById.get(id) || [];
            const remote = remoteEntries[0] || null;
            const local = localScan.recordsById.get(id) || null;

            if (duplicateIds.has(id)) {
                items.push({
                    id,
                    action: 'DUPLICATE',
                    remote,
                    local,
                    needs_detail_fetch: false,
                    reasons: [
                        ...(remoteDuplicateIds.has(id) ? ['REMOTE_DUPLICATE_ID'] : []),
                        ...(localScan.duplicateIds.has(id) ? ['LOCAL_DUPLICATE_ID'] : [])
                    ]
                });
                continue;
            }

            if (localScan.blockedIds.has(id)) {
                errorCount++;
                items.push({
                    id,
                    action: 'ERROR',
                    remote,
                    local,
                    needs_detail_fetch: false,
                    reasons: (localScan.errorsById.get(id) || []).map(error => error.type)
                });
                continue;
            }

            if (!local) {
                newCount++;
                maximumFetchRequired++;
                items.push({
                    id,
                    action: 'NEW',
                    remote,
                    local: null,
                    needs_detail_fetch: true,
                    remote_update_candidate: false,
                    rename_candidate: false,
                    reasons: ['NOT_IN_LOCAL_ARCHIVE']
                });
                continue;
            }

            if (local.tracking !== 'manifest') {
                const titleChanged = String(remote?.title || '') !== String(local?.title || '');
                const updateCandidate = !chTimeEquivalent(remote?.update_time, local?.remote_update_time);
                rawOnlyVerifyCount++;
                if (updateCandidate) remoteUpdateCandidateCount++;
                if (titleChanged) renameCandidateCount++;
                maximumFetchRequired++;
                items.push({
                    id,
                    action: 'VERIFY_CHANGED',
                    remote,
                    local,
                    needs_detail_fetch: true,
                    remote_update_candidate: updateCandidate,
                    rename_candidate: titleChanged,
                    metadata_candidate: false,
                    reasons: [
                        'LOCAL_RAW_NOT_MANIFEST_TRACKED',
                        ...(updateCandidate ? ['REMOTE_UPDATE_TIME_DIFF_OR_UNKNOWN'] : []),
                        ...(titleChanged ? ['TITLE_DIFF'] : [])
                    ]
                });
                continue;
            }

            const titleChanged = String(remote?.title || '') !== String(local?.title || '');
            const timeEquivalent = chTimeEquivalent(
                remote?.update_time,
                local?.remote_update_time
            );
            const updateCandidate = !timeEquivalent;
            const metadataReasons = [];
            if (Object.prototype.hasOwnProperty.call(remote || {}, 'is_archived') &&
                Boolean(remote?.is_archived) !== Boolean(local?.is_archived)) {
                metadataReasons.push('ARCHIVE_STATE_DIFF');
            }
            if (Object.prototype.hasOwnProperty.call(remote || {}, 'projectId') &&
                String(remote?.projectId ?? '') !== String(local?.project_id ?? '')) {
                metadataReasons.push('PROJECT_ID_DIFF');
            }
            if (Object.prototype.hasOwnProperty.call(remote || {}, 'projectTitle') &&
                String(remote?.projectTitle ?? '') !== String(local?.project_title ?? '')) {
                metadataReasons.push('PROJECT_TITLE_DIFF');
            }
            const metadataCandidate = metadataReasons.length > 0;

            if (updateCandidate) remoteUpdateCandidateCount++;
            if (titleChanged) renameCandidateCount++;
            if (metadataCandidate) metadataCandidateCount++;

            if (updateCandidate || titleChanged || metadataCandidate) {
                maximumFetchRequired++;
                items.push({
                    id,
                    action: updateCandidate || metadataCandidate ? 'VERIFY_CHANGED' : 'VERIFY_RENAMED',
                    remote,
                    local,
                    needs_detail_fetch: true,
                    remote_update_candidate: updateCandidate,
                    rename_candidate: titleChanged,
                    metadata_candidate: metadataCandidate,
                    reasons: [
                        ...(updateCandidate ? ['REMOTE_UPDATE_TIME_DIFF_OR_UNKNOWN'] : []),
                        ...(titleChanged ? ['TITLE_DIFF'] : []),
                        ...metadataReasons
                    ]
                });
            } else {
                unchangedCount++;
                items.push({
                    id,
                    action: 'UNCHANGED',
                    remote,
                    local,
                    needs_detail_fetch: false,
                    remote_update_candidate: false,
                    rename_candidate: false,
                    metadata_candidate: false,
                    reasons: []
                });
            }
        }

        const localOnly = [];
        if (remoteUniverseComplete) {
            for (const [id, local] of localScan.recordsById.entries()) {
                if (globalRemoteIds.has(id)) continue;
                if (duplicateIds.has(id) || localScan.blockedIds.has(id)) continue;
                localOnly.push({ id, local, action: 'LOCAL_ONLY' });
            }
        }

        const duplicateDetails = [
            ...localScan.duplicates,
            ...remoteDuplicates
        ];

        return {
            items,
            localOnly,
            duplicateIds: Array.from(duplicateIds),
            duplicateDetails,
            errors: [...localScan.errors, ...remoteErrors],
            summary: {
                remote: allRemote.length,
                remoteUnique: remoteById.size,
                scopeRemote: scopeIds.size,
                local: localScan.recordsById.size,
                newCount,
                remoteUpdateCandidateCount,
                renameCandidateCount,
                unchangedCount,
                metadataCandidateCount,
                rawOnlyVerifyCount,
                localOnlyCount: remoteUniverseComplete ? localOnly.length : null,
                localOnlyReliable: remoteUniverseComplete,
                remoteUniverseComplete,
                remoteUniverseNote,
                duplicateIdCount: duplicateIds.size,
                errorCount: errorCount + remoteErrors.length + localScan.errors.filter(error => !error.id).length,
                maximumFetchRequired,
                manifestTracked: localScan.stats.manifestTracked,
                localProjectCount: localScan.stats.manifestProject || 0,
                localRootCount: localScan.stats.manifestRoot || 0,
                archiveLayoutVersion: localScan.stats.archiveLayoutVersion || CH_ARCHIVE_LAYOUT_VERSION,
                provider: localScan.stats.provider || CH_PROVIDER,
                migrationRequired: Boolean(localScan.stats.migrationRequired),
                rawConversationFiles: localScan.stats.rawConversationFiles,
                rawOnlyIds: localScan.stats.rawOnlyIds
            }
        };
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

    async function chRunPreflightPlanner({ rootHandle, remoteList, selectedIds = null, remoteUniverseComplete = true, remoteUniverseNote = null }) {
        chSetProgress('目录预检', '只读扫描本地档案…', 0);
        const localScan = await chScanLocalArchiveReadOnly(rootHandle, info => {
            const seen = info.jsonFilesSeen || 0;
            const found = info.conversationJsonFiles || 0;
            chSetProgress(
                '目录预检 · 本地扫描',
                `已检查 JSON ${seen} · 识别对话 ${found}${info.path ? ` · ${info.path}` : ''}`,
                null
            );
        });
        if (localScan.manifest && chManifestRequiresLayoutMigration(localScan.manifest)) {
            throw new Error('Archive Layout v1 需要先执行纯本地 Layout v2 升级。');
        }

        chSetProgress('目录预检', '生成同步计划（不抓取详情、不写盘）…', 70);
        const plan = chBuildPreflightPlan(remoteList, localScan, selectedIds, {
            remoteUniverseComplete,
            remoteUniverseNote
        });
        const s = plan.summary;
        chSetProgress(
            '目录预检完成',
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
        'LOCAL_UNTRACKED'
    ]);

    function chMergeRemoteEntries(entries) {
        const merged = new Map();
        for (const entry of Array.isArray(entries) ? entries : []) {
            const id = chRemoteConversationId(entry);
            if (!id) continue;
            const normalized = { ...entry, id };
            const existing = merged.get(id);
            if (!existing) {
                merged.set(id, normalized);
                continue;
            }
            const existingTime = normalizeEpochSeconds(existing.update_time || 0);
            const incomingTime = normalizeEpochSeconds(normalized.update_time || 0);
            const newer = incomingTime >= existingTime ? normalized : existing;
            const older = newer === normalized ? existing : normalized;
            merged.set(id, {
                ...older,
                ...newer,
                id,
                projectId: newer.projectId || older.projectId || null,
                projectTitle: newer.projectTitle || older.projectTitle || null,
                is_archived: Boolean(newer.is_archived || older.is_archived),
                create_time: newer.create_time || older.create_time || 0,
                update_time: Math.max(existingTime, incomingTime) || newer.update_time || older.update_time || 0
            });
        }
        return Array.from(merged.values());
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
        const reasons = [];
        if (Object.prototype.hasOwnProperty.call(remote || {}, 'is_archived') &&
            Boolean(remote?.is_archived) !== Boolean(local?.is_archived)) {
            reasons.push('ARCHIVE_STATE_DIFF');
        }
        if (Object.prototype.hasOwnProperty.call(remote || {}, 'projectId') &&
            String(remote?.projectId ?? '') !== String(local?.project_id ?? '')) {
            reasons.push('PROJECT_ID_DIFF');
        }
        if (Object.prototype.hasOwnProperty.call(remote || {}, 'projectTitle') &&
            String(remote?.projectTitle ?? '') !== String(local?.project_title ?? '')) {
            reasons.push('PROJECT_TITLE_DIFF');
        }
        return reasons;
    }

    async function chClassifyFetchedConversation(preflightItem, convData) {
        const remote = preflightItem?.remote || {};
        const local = preflightItem?.local || null;
        const id = chGetConversationId(remote, convData);
        const remoteTitle = String(convData?.title || remote?.title || '');
        const remoteUpdateTime = convData?.update_time ?? remote?.update_time ?? null;
        const newSignature = await chContentSignature(convData);

        if (!local) {
            return {
                ...preflightItem,
                id,
                finalAction: 'NEW',
                convData,
                newSignature,
                contentChanged: true,
                titleChanged: false,
                metadataChanged: false,
                timestampChanged: false,
                needs_sync: true,
                finalReasons: ['NOT_IN_LOCAL_ARCHIVE']
            };
        }

        if (local.tracking !== 'manifest') {
            return {
                ...preflightItem,
                id,
                finalAction: 'LOCAL_UNTRACKED',
                convData,
                newSignature,
                contentChanged: null,
                titleChanged: remoteTitle !== String(local?.title || ''),
                metadataChanged: false,
                timestampChanged: !chTimeEquivalent(remoteUpdateTime, local?.remote_update_time),
                needs_sync: true,
                finalReasons: ['LOCAL_RAW_NOT_MANIFEST_TRACKED', 'NO_AUTHORITATIVE_LOCAL_SIGNATURE']
            };
        }

        const oldSignature = String(local?.content_signature || '');
        if (!oldSignature) {
            return {
                ...preflightItem,
                id,
                finalAction: 'ERROR',
                convData,
                newSignature,
                contentChanged: null,
                titleChanged: remoteTitle !== String(local?.title || ''),
                metadataChanged: null,
                timestampChanged: null,
                needs_sync: false,
                finalReasons: ['LOCAL_SIGNATURE_MISSING'],
                error: 'Tracked manifest record has no content_signature'
            };
        }

        const contentChanged = newSignature !== oldSignature;
        const titleChanged = remoteTitle !== String(local?.title || '');
        const metadataReasons = chFinalMetadataDiffs(remote, local);
        const metadataChanged = metadataReasons.length > 0;
        const timestampChanged = !chTimeEquivalent(remoteUpdateTime, local?.remote_update_time);

        let finalAction = 'UNCHANGED';
        if (contentChanged && titleChanged) finalAction = 'UPDATED_AND_RENAMED';
        else if (contentChanged) finalAction = 'UPDATED';
        else if (titleChanged) finalAction = 'RENAMED_ONLY';
        else if (metadataChanged || timestampChanged) finalAction = 'METADATA_ONLY';

        return {
            ...preflightItem,
            id,
            finalAction,
            convData,
            newSignature,
            contentChanged,
            titleChanged,
            metadataChanged,
            timestampChanged,
            needs_sync: finalAction !== 'UNCHANGED',
            finalReasons: [
                ...(contentChanged ? ['CONTENT_SIGNATURE_DIFF'] : []),
                ...(titleChanged ? ['TITLE_DIFF'] : []),
                ...metadataReasons,
                ...(timestampChanged ? ['REMOTE_UPDATE_TIME_DIFF'] : [])
            ]
        };
    }

    async function chVerifyPreflightCandidates({ plan, workspaceId = null }) {
        const resultItems = [];
        const fetchItems = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE');
        const fetchTotal = fetchItems.length;

        if (fetchTotal > 0 && !await ensureAccessToken()) {
            throw new Error('无法获取 Access Token，无法执行 detail verification。');
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
                const convData = await chGetConversationConservative(item.id, workspaceId);
                resultItems.push(await chClassifyFetchedConversation(item, convData));
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
            if (fetchIndex < fetchTotal) {
                const policy = chNormalizeNetworkPolicy(chSyncRun.policy);
                if (fetchIndex % policy.batchSize === 0) {
                    const pauseMs = chNetworkBatchPauseMs(policy);
                    await chControlledSleep(
                        pauseMs,
                        '保守批次暂停',
                        `已核验 ${fetchIndex}/${fetchTotal}`,
                        { countdown: true }
                    );
                } else {
                    await chControlledSleep(chNetworkDelayMs(policy), '请求间隔', `已核验 ${fetchIndex}/${fetchTotal}`);
                }
            }
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
        const remote = classifiedItem.remote || {};
        const convData = classifiedItem.convData || {};
        return {
            ...existingRecord,
            title: convData.title || remote.title || existingRecord.title,
            create_time: convData.create_time ?? remote.create_time ?? existingRecord.create_time ?? null,
            remote_update_time: convData.update_time ?? remote.update_time ?? existingRecord.remote_update_time ?? null,
            is_archived: convData.is_archived ?? remote.is_archived ?? existingRecord.is_archived ?? false,
            project_id: remote.projectId ?? existingRecord.project_id ?? null,
            project_title: remote.projectTitle ?? existingRecord.project_title ?? null,
            provider: CH_PROVIDER,
            archive_layout_version: CH_ARCHIVE_LAYOUT_VERSION,
            content_signature: classifiedItem.newSignature || existingRecord.content_signature,
            signature_version: CH_SIGNATURE_VERSION,
            synced_at: new Date().toISOString()
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

        const metadataOnlyInPlace = action === 'METADATA_ONLY' && oldRecord &&
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

        manifest.conversations[record.conversation_id] = record;
        await writeManifest(rootHandle, manifest);

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
        onItemCommitted = null
    }) {
        const selected = selectedIds instanceof Set && selectedIds.size > 0 ? selectedIds : null;
        if (!selected && !remoteUniverseComplete) {
            throw new Error('全范围同步要求完整远端列表；当前 Remote universe 不完整，已停止写入。');
        }
        const ownsRun = !chSyncRun.active;
        if (ownsRun) chBeginControlledRun(networkPolicy || chLoadNetworkPolicy());
        else if (networkPolicy) chSyncRun.policy = chSaveNetworkPolicy(networkPolicy);

        chSetProgress('目录同步', `扫描本地档案… · ${chNetworkPolicySummary(chSyncRun.policy)}`, 0);
        await chControlCheckpoint('local-scan');
        const localScan = await chScanLocalArchiveReadOnly(rootHandle);
        if (localScan.manifestExists && !localScan.manifestReadable) {
            throw new Error(`${CH_MANIFEST_NAME} 不可读或不兼容，已停止同步以避免覆盖。`);
        }
        if (localScan.manifest && chManifestRequiresLayoutMigration(localScan.manifest)) {
            throw new Error('检测到 Archive Layout v1 或未完成的布局迁移；请先完成纯本地 Layout v2 升级。');
        }
        const plan = chBuildPreflightPlan(remoteList, localScan, selected, {
            remoteUniverseComplete,
            remoteUniverseNote
        });
        const fetchTotal = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE').length;
        if (fetchTotal > 0 && !await ensureAccessToken()) {
            throw new Error('无法获取 Access Token，无法执行 detail verification。');
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
        const totalItems = Math.max(1, plan.items.length);

        for (let i = 0; i < plan.items.length; i++) {
            let classified = null;
            const item = plan.items[i];
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
                    chSetProgress(
                        '核验并同步',
                        `${fetchIndex + 1}/${fetchTotal} · ${String(title).slice(0, 58)}`,
                        Math.min(98, Math.round((i / totalItems) * 98))
                    );
                    try {
                        const convData = await chGetConversationConservative(item.id, workspaceId);
                        verification.detailFetchCount++;
                        fetchIndex++;
                        classified = await chClassifyFetchedConversation(item, convData);
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
                    try { onItemClassified(classified, { processed: i + 1, total: plan.items.length }); } catch (_) {}
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
                    }
                }

                // One conservative network cadence governs the next detail request.  This runs
                // after the current conversation has been fully classified and atomically committed.
                if (item.needs_detail_fetch && fetchIndex < fetchTotal) {
                    const policy = chNormalizeNetworkPolicy(chSyncRun.policy);
                    if (fetchIndex % policy.batchSize === 0) {
                        const pauseMs = chNetworkBatchPauseMs(policy);
                        await chControlledSleep(
                            pauseMs,
                            '保守批次暂停',
                            `已处理 ${fetchIndex}/${fetchTotal} 个远端详情`,
                            { countdown: true }
                        );
                    } else {
                        await chControlledSleep(chNetworkDelayMs(policy), '请求间隔', `已处理 ${fetchIndex}/${fetchTotal} 个远端详情`);
                    }
                }
            } catch (err) {
                if (chIsCancellation(err)) {
                    verification.cancelled = true;
                    sync.cancelled = true;
                    break;
                }
                throw err;
            }
        }

        chSetProgress(
            sync.cancelled ? '目录同步已取消' : (sync.failed ? '目录同步完成（存在失败）' : '目录同步完成'),
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
                        <button id="preflight-plan-btn" style="padding: 8px 12px; border: 1px solid #6366f1; border-radius: 6px; background: #fff; color: #4338ca; cursor: pointer; font-weight: bold;" disabled>目录预检（全部）</button>
                        <button id="sync-directory-btn" style="padding: 8px 12px; border: 1px solid #10a37f; border-radius: 6px; background: #fff; color: #0f766e; cursor: pointer; font-weight: bold;" disabled>目录同步（全部）</button>
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
                    chSetProgress('目录预检', '补全远端列表范围…', 0);
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
                    chSetProgress('目录预检失败', err?.message || String(err), 100);
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
                    chSetProgress('目录同步', `补全远端列表范围… · ${chNetworkPolicySummary(chSyncRun.policy)}`, 0);
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
                        chSetProgress('目录同步已取消', '已在安全边界停止；已提交会话保留，下次同步可继续。', 100);
                    } else {
                        console.error('[ChatHarbor Integrated Sync] failed:', err);
                        chSetProgress('目录同步失败', err?.message || String(err), 100);
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
text = text.replace('>选择对话导出</button>', '>选择对话 / 目录同步</button>')


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
    "            if (preflightBtn) preflightBtn.textContent = state.selected.size > 0 ? `目录预检（选中 ${state.selected.size}）` : `目录预检（全部 ${state.list.length}）`;\n" +
    "            if (syncDirBtn) syncDirBtn.textContent = state.selected.size > 0 ? `目录同步（选中 ${state.selected.size}）` : `目录同步（全部 ${state.list.length}）`;\n" + text_anchor,
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


# ======================== ChatHarbor 0.0.10.0 Archive Layout v2 + Migration ========================
# The sync/runtime core above remains unchanged. This final bounded patch replaces only the
# picker presentation, report presentation, and launcher presentation.

# Locale helper for ChatHarbor-owned UI/report strings.
locale_anchor = "    const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';\n"
locale_replacement = locale_anchor + "    const CH_UI_LANG = /^zh(?:-|$)/i.test(String(navigator.language || '')) ? 'zh-CN' : 'en-US';\n    const chT = (zh, en) => CH_UI_LANG === 'zh-CN' ? zh : en;\n"
if locale_anchor not in text:
    raise SystemExit("UI locale anchor not found")
text = text.replace(locale_anchor, locale_replacement, 1)

# Launcher: use a ChatHarbor-specific persisted position, green surface, right-edge default,
# and automatic half-hide. Changing the storage key intentionally discards stale upstream
# positions such as the top-left location observed during migration tests.
text = text.replace("const FAB_STORAGE_KEY = 'chatgpt-exporter-fab-v1';", "const FAB_STORAGE_KEY = 'chatharbor-fab-v1';", 1)
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
            networkPolicy: chLoadNetworkPolicy(), rootHandle: null, localScan: null, lastPlan: null,
            layoutState: null, migrationActive: false, migrationReport: null,
            lastResult: null, syncStatusById: new Map(), lastSelectedIndex: null,
            remoteUniverse: [], remoteUniverseComplete: false, remoteUniverseNote: null,
            accountUniverse: null, accountUniverseComplete: false, accountUniverseNote: null,
            accountLoadedAt: null, teamUniverseCache: new Map()
        };

        const modeLabel = value => value === 'team' ? chT('团队空间','Team workspace') : value === 'project' ? chT('项目对话','Project conversations') : chT('全部对话','All conversations');
        const statusLabel = value => ({
            NEW: chT('新增','New'), VERIFY: chT('待核验','Verify'), UPDATED: chT('内容更新','Updated'),
            RENAMED_ONLY: chT('仅改名','Renamed'), UPDATED_AND_RENAMED: chT('更新+改名','Updated + renamed'),
            METADATA_ONLY: chT('仅元数据','Metadata only'), LOCAL_UNTRACKED: chT('本地未跟踪','Local untracked'),
            UNCHANGED: chT('已同步','Synced'), ERROR: chT('异常','Error'), DUPLICATE: chT('重复ID','Duplicate ID')
        }[value] || '');
        const statusColor = value => ({
            NEW:['#ecfdf5','#047857'], VERIFY:['#eef2ff','#4338ca'], UPDATED:['#eff6ff','#1d4ed8'],
            RENAMED_ONLY:['#f5f3ff','#6d28d9'], UPDATED_AND_RENAMED:['#ede9fe','#5b21b6'],
            METADATA_ONLY:['#f3f4f6','#4b5563'], LOCAL_UNTRACKED:['#fff7ed','#c2410c'],
            UNCHANGED:['#f0fdf4','#166534'], ERROR:['#fef2f2','#b91c1c'], DUPLICATE:['#fff1f2','#be123c']
        }[value] || ['#f3f4f6','#6b7280']);
        const pendingStatus = value => ['NEW','VERIFY','UPDATED','RENAMED_ONLY','UPDATED_AND_RENAMED','METADATA_ONLY','LOCAL_UNTRACKED'].includes(value);

        const closeDialog = () => {
            if (chSyncRun.active || state.migrationActive) {
                chSetProgress(
                    state.migrationActive ? chT('目录结构升级仍在运行','Archive migration is still running') : chT('同步仍在运行','Sync is still running'),
                    state.migrationActive ? chT('请等待当前本地原子迁移步骤完成。','Wait for the current local migration transaction to finish.') : chT('请先暂停或取消同步。','Pause or cancel sync first.'),
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
                <input id="conv-search" type="text" placeholder="${chT('搜索标题/项目名/ID','Search title/project/ID')}" style="min-width:0; padding:8px 10px; border:1px solid #d1d5db; border-radius:7px;">
                <select id="ch-space-select" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="personal">${chT('全部对话','All conversations')}</option><option value="project">${chT('项目对话','Project conversations')}</option><option value="team">${chT('团队空间','Team')}</option>
                </select>
                <select id="filter-project" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;"><option value="all">${chT('项目：全部','Project: all')}</option></select>
                <select id="filter-archived" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="all">${chT('归档：全部','Archive: all')}</option><option value="active">${chT('未归档','Active')}</option><option value="archived">${chT('已归档','Archived')}</option>
                </select>
                <select id="filter-sync-status" style="padding:8px; border:1px solid #d1d5db; border-radius:7px; background:#fff;">
                    <option value="all">${chT('同步状态：全部','Sync: all')}</option>
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
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:8px; flex:0 0 auto;">
                        <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:#374151;cursor:pointer;white-space:nowrap;"><input id="select-all-checkbox" type="checkbox"><span>${chT('全选','Select all')}</span></label>
                        <div id="conv-status" style="font-size:12px; color:#6b7280; text-align:right;">${chT('正在加载列表…','Loading…')}</div>
                    </div>
                    <div id="conv-list" style="flex:1 1 auto; min-height:0; overflow:auto; border:1px solid #e5e7eb; border-radius:9px; padding:8px; background:#fff;"></div>
                </section>
                <aside style="min-height:0; overflow:hidden; display:flex; flex-direction:column; gap:9px;">
                    <div id="ch-right-scroll" style="min-height:0; flex:1 1 auto; overflow:auto; display:flex; flex-direction:column; gap:9px; padding-right:1px;">
                        <div style="padding:10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;"><strong style="font-size:13px;">${chT('本地归档','Local archive')}</strong><button id="ch-archive-copy-report-btn" style="display:none;padding:3px 7px;border:1px solid #d1d5db;border-radius:6px;background:#fff;color:#6b7280;cursor:pointer;font-size:11px;">${chT('详细信息','Details')}</button></div>
                            <div id="ch-archive-path" style="margin-top:6px; font-size:12px; color:#6b7280; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${chT('尚未选择目录','No directory selected')}</div>
                            <div id="ch-archive-summary" style="margin-top:6px; font-size:12px; line-height:1.55; color:#4b5563;">${chT('等待选择目录','Waiting for directory')}</div>
                            <div style="display:flex; gap:6px; margin-top:8px;"><button id="ch-choose-directory-btn" style="flex:1; padding:7px 8px; border:1px solid #d1d5db; border-radius:6px; background:#fff; cursor:pointer;">${chT('选择目录','Choose')}</button><button id="preflight-plan-btn" style="flex:1; padding:7px 8px; border:1px solid #6366f1; border-radius:6px; background:#fff; color:#4338ca; cursor:pointer; font-weight:600;">${chT('重新扫描本地','Rescan local')}</button></div>
                            <button id="ch-migrate-layout-btn" style="display:none;width:100%;margin-top:7px;padding:8px 10px;border:1px solid #d97706;border-radius:7px;background:#fffbeb;color:#92400e;cursor:pointer;font-weight:700;">${chT('升级目录结构到 Layout v2','Upgrade archive to Layout v2')}</button>
                        </div>
                        <details style="padding:9px 10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <summary id="ch-network-policy-summary" style="cursor:pointer; font-size:13px; font-weight:600;">${chT('网络策略','Network policy')} · ${chNetworkPolicySummary(state.networkPolicy)}</summary>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:8px;">
                                <label style="font-size:11px;color:#6b7280;grid-column:1/-1;">${chT('速度','Speed')}<select id="ch-speed-level" style="width:100%;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;">${CH_SPEED_LEVELS.map((x,i)=>`<option value="${i}" ${i===state.networkPolicy.speedIndex?'selected':''}>${x.name}</option>`).join('')}</select></label>
                                <label style="font-size:11px;color:#6b7280;">${chT('每批','Batch')}<input id="ch-batch-size" type="number" min="1" max="200" value="${state.networkPolicy.batchSize}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                                <span></span>
                                <label style="font-size:11px;color:#6b7280;">${chT('暂停最小(秒)','Pause min(s)')}<input id="ch-pause-min" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMinSec}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                                <label style="font-size:11px;color:#6b7280;">${chT('暂停最大(秒)','Pause max(s)')}<input id="ch-pause-max" type="number" min="0" max="3600" value="${state.networkPolicy.batchPauseMaxSec}" style="width:100%;box-sizing:border-box;margin-top:3px;padding:6px;border:1px solid #d1d5db;border-radius:6px;"></label>
                            </div>
                        </details>
                        <details style="padding:9px 10px; border:1px solid #d1d5db; border-radius:9px; background:#fff;">
                            <summary style="cursor:pointer; font-size:13px; font-weight:600;">${chT('同步内容','Sync content')}</summary>
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
        const archiveCopyReportBtn = $('ch-archive-copy-report-btn');

        spaceSelect.value = state.mode;
        archivedSelect.value = state.archived;

        const updateHeader = () => {
            const root = state.rootHandle?.name ? ` · ${state.rootHandle.name}` : '';
            $('ch-header-summary').textContent = `${modeLabel(state.mode)} · ChatGPT${root}`;
        };
        const updateTimeSummary = () => {
            const range = state.timeRange === '7d' ? chT('最近7天','7 days') : state.timeRange === '30d' ? chT('最近30天','30 days') : state.timeRange === 'custom' ? chT('自定义','Custom') : chT('不限','All');
            timeSummary.textContent = `${chT('时间','Time')}：${range}`;
            customDateRow.style.display = state.timeRange === 'custom' ? 'grid' : 'none';
        };
        const statusMatches = status => {
            if (state.syncStatus === 'all') return true;
            if (state.syncStatus === 'pending') return pendingStatus(status);
            if (state.syncStatus === 'error') return status === 'ERROR' || status === 'DUPLICATE';
            return status === state.syncStatus;
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
            const counts = {};
            state.list.forEach(item => { const s=state.syncStatusById.get(item.id); if(s) counts[s]=(counts[s]||0)+1; });
            const pending = [...state.syncStatusById.values()].filter(pendingStatus).length;
            const options = [
                ['all', `${chT('同步状态：全部','Sync: all')} (${state.list.length})`],
                ['pending', `${chT('待处理','To process')} (${pending})`],
                ['NEW', `${chT('新增','New')} (${counts.NEW||0})`],
                ['VERIFY', `${chT('待核验','Verify')} (${counts.VERIFY||0})`],
                ['UPDATED', `${chT('内容更新','Updated')} (${counts.UPDATED||0})`],
                ['RENAMED_ONLY', `${chT('仅改名','Renamed')} (${counts.RENAMED_ONLY||0})`],
                ['UPDATED_AND_RENAMED', `${chT('更新+改名','Updated + renamed')} (${counts.UPDATED_AND_RENAMED||0})`],
                ['METADATA_ONLY', `${chT('仅元数据','Metadata only')} (${counts.METADATA_ONLY||0})`],
                ['UNCHANGED', `${chT('已同步','Synced')} (${counts.UNCHANGED||0})`],
                ['error', `${chT('异常','Error')} (${(counts.ERROR||0)+(counts.DUPLICATE||0)})`]
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
            $('ch-archive-path').textContent = state.rootHandle?.name || chT('尚未选择目录','No directory selected');
            const layout = state.layoutState;
            if (!state.rootHandle) {
                $('ch-archive-summary').textContent = chT('选择目录后将自动执行只读扫描','A read-only scan runs automatically after choosing a directory');
            } else if (layout?.requiresMigration) {
                const prefix = layout.migrationInProgress
                    ? chT('Layout v1 → v2 升级未完成','Layout v1 → v2 migration incomplete')
                    : chT('检测到 Layout v1','Layout v1 detected');
                $('ch-archive-summary').textContent = `${prefix} · ${chT('本地','Local')} ${layout.total || 0}（${chT('项目内','in projects')} ${layout.project || 0} · ${chT('项目外','outside projects')} ${layout.root || 0}） · ${chT('纯本地升级，不重新下载','local-only upgrade; no re-download')}`;
            } else if (!state.lastPlan) {
                const base = layout?.manifestExists
                    ? `${chT('本地','Local')} ${layout.total || 0}（${chT('项目内','in projects')} ${layout.project || 0} · ${chT('项目外','outside projects')} ${layout.root || 0}）`
                    : chT('目录已选择','Directory selected');
                $('ch-archive-summary').textContent = `${base} · ${chT('等待扫描','waiting for scan')}`;
            } else {
                const s = state.lastPlan.summary;
                const verifyCount = Math.max(0, (s.maximumFetchRequired || 0) - (s.newCount || 0));
                const localProject = Number.isFinite(s.localProjectCount) ? s.localProjectCount : (layout?.project || 0);
                const localRoot = Number.isFinite(s.localRootCount) ? s.localRootCount : (layout?.root || 0);
                const first = `${chT('本地','Local')} ${s.local || 0}（${chT('项目内','in projects')} ${localProject} · ${chT('项目外','outside projects')} ${localRoot}）`;
                const second = [`${chT('新增','New')} ${s.newCount || 0}`, `${chT('待核验','Verify')} ${verifyCount}`];
                if (s.unchangedCount) second.push(`${chT('已同步','Synced')} ${s.unchangedCount}`);
                if (s.errorCount || s.duplicateIdCount) second.push(`${chT('异常','Issues')} ${(s.errorCount||0)+(s.duplicateIdCount||0)}`);
                $('ch-archive-summary').textContent = `${first} · ${second.join(' · ')}`;
            }
            if (migrateLayoutBtn) {
                migrateLayoutBtn.style.display = layout?.requiresMigration ? '' : 'none';
                migrateLayoutBtn.textContent = layout?.migrationInProgress
                    ? chT('继续升级目录结构到 Layout v2','Resume Layout v2 migration')
                    : chT('升级目录结构到 Layout v2','Upgrade archive to Layout v2');
            }
            if (archiveCopyReportBtn) archiveCopyReportBtn.style.display = state.lastPlan ? '' : 'none';
            updateHeader();
        };
        const updateControls = () => {
            const disabled = state.loading || chSyncRun.active || state.migrationActive;
            const migrationRequired = Boolean(state.layoutState?.requiresMigration);
            [spaceSelect,projectSelect,archivedSelect,syncStatusSelect,timeFieldSelect,timeRangeSelect,sortSelect,startDateInput,endDateInput,refreshBtn].forEach(el=>{if(el)el.disabled=disabled;});
            chooseDirBtn.disabled = disabled;
            chooseDirBtn.textContent = state.loading ? chT('等待远端列表…','Waiting for remote…') : state.rootHandle ? chT('更换目录','Change directory') : chT('选择目录','Choose directory');
            chooseDirBtn.title = state.loading ? chT('为避免远端/本地状态交叉，远端列表加载完成后再选择目录。','Directory selection is enabled after remote loading to avoid mixed generations.') : '';
            preflightBtn.disabled = disabled || !state.rootHandle;
            if (migrateLayoutBtn) migrateLayoutBtn.disabled = disabled || !migrationRequired;
            if (selectAllCheckbox) selectAllCheckbox.disabled = disabled || state.filtered.length===0 || migrationRequired;
            syncSelectedBtn.disabled = disabled || migrationRequired || state.selected.size===0;
            syncSelectedBtn.style.opacity = syncSelectedBtn.disabled ? '.45' : '1';
            syncSelectedBtn.textContent = migrationRequired
                ? chT('请先升级目录结构','Upgrade archive first')
                : state.selected.size ? `${chT('同步选中','Sync selected')} ${state.selected.size}` : chT('请选择对话','Select conversations');
        };
        const renderList = () => {
            const listEl=$('conv-list'), statusEl=$('conv-status');
            listEl.innerHTML='';
            updateControls(); updateArchiveSummary();
            if(state.loading){statusEl.textContent=chT('正在加载列表…','Loading…');if(selectAllCheckbox){selectAllCheckbox.checked=false;selectAllCheckbox.indeterminate=false;}return;}
            const matchedSelected = state.filtered.reduce((n,item)=>n+(state.selected.has(item.id)?1:0),0);
            const hiddenSelected = Math.max(0,state.selected.size-matchedSelected);
            if(selectAllCheckbox){selectAllCheckbox.checked=state.filtered.length>0&&matchedSelected===state.filtered.length;selectAllCheckbox.indeterminate=matchedSelected>0&&matchedSelected<state.filtered.length;}
            const countParts=[`${chT('已选','Selected')} ${state.selected.size}`];
            if(hiddenSelected>0)countParts.push(`${chT('当前匹配中','in current matches')} ${matchedSelected}`);
            if(state.filtered.length===state.list.length)countParts.push(`${chT('共','Total')} ${state.list.length}`);
            else countParts.push(`${chT('匹配','Matched')} ${state.filtered.length} / ${chT('共','Total')} ${state.list.length}`);
            statusEl.textContent=countParts.join(' · ');
            if(!state.filtered.length){const e=document.createElement('div');e.textContent=chT('没有匹配的对话。','No matching conversations.');e.style.cssText='color:#9ca3af;padding:12px 8px;';listEl.appendChild(e);return;}
            state.filtered.slice(0,state.visibleCount).forEach((item,index)=>{
                const row=document.createElement('label');
                row.style.cssText='display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 9px;border:1px solid #e5e7eb;border-radius:7px;margin-bottom:6px;cursor:pointer;background:#fff;';
                const cb=document.createElement('input');cb.type='checkbox';cb.checked=state.selected.has(item.id);
                cb.onclick=e=>{const checked=cb.checked;if(e.shiftKey && state.lastSelectedIndex!=null){const a=Math.min(state.lastSelectedIndex,index),b=Math.max(state.lastSelectedIndex,index);for(let i=a;i<=b;i++){const id=state.filtered[i]?.id;if(!id)continue;if(checked)state.selected.add(id);else state.selected.delete(id);}}else{if(checked)state.selected.add(item.id);else state.selected.delete(item.id);}state.lastSelectedIndex=index;renderList();};
                const content=document.createElement('div');content.style.minWidth='0';
                const title=document.createElement('div');title.textContent=item.title||'Untitled Conversation';title.style.cssText='font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                const meta=document.createElement('div');const time=formatTimestamp(state.timeField==='create'?item.create_time:item.update_time)||chT('未知','Unknown');const projectText=item.projectTitle|| (item.__chProjectState==='unknown'?chT('归属未知','Project unknown'):chT('无项目','No project'));meta.textContent=`${projectText} · ${state.timeField==='create'?chT('创建','Created'):chT('更新','Updated')} ${time}`;meta.style.cssText='font-size:11px;color:#6b7280;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                content.append(title,meta);row.append(cb,content);
                const badges=document.createElement('div');badges.style.cssText='display:flex;gap:5px;align-items:center;justify-content:flex-end;flex-wrap:wrap;';
                const s=state.syncStatusById.get(item.id);if(s){const [bg,fg]=statusColor(s);const badge=document.createElement('span');badge.textContent=statusLabel(s);badge.style.cssText=`font-size:11px;padding:3px 7px;border-radius:999px;background:${bg};color:${fg};white-space:nowrap;`;badges.appendChild(badge);}
                const archiveBadge=document.createElement('span');archiveBadge.textContent=item.is_archived?chT('已归档','Archived'):chT('未归档','Active');archiveBadge.style.cssText=item.is_archived?'font-size:11px;padding:3px 7px;border-radius:999px;background:#fef3c7;color:#92400e;white-space:nowrap;':'font-size:11px;padding:3px 7px;border-radius:999px;background:#f3f4f6;color:#6b7280;white-space:nowrap;';badges.appendChild(archiveBadge);
                row.appendChild(badges);listEl.appendChild(row);
            });
            if(state.filtered.length>state.visibleCount){const more=document.createElement('button');more.textContent=`${chT('加载更多','Load more')} (${state.filtered.length-state.visibleCount})`;more.style.cssText='width:100%;padding:7px;border:1px solid #d1d5db;border-radius:6px;background:#fff;cursor:pointer;';more.onclick=()=>{state.visibleCount=Math.min(state.visibleCount+state.pageSize,state.filtered.length);renderList();};listEl.appendChild(more);}
        };
        const renderAll = () => { rebuildProjectOptions(); rebuildSyncOptions(); applyFilters(); updateTimeSummary(); renderList(); };

        const persistPolicy = () => {
            state.networkPolicy=chSaveNetworkPolicy({...state.networkPolicy,speedIndex:Number(speedLevelInput.value),batchSize:Number(batchSizeInput.value),batchPauseMinSec:Number(pauseMinInput.value),batchPauseMaxSec:Number(pauseMaxInput.value)});
            batchSizeInput.value=String(state.networkPolicy.batchSize);pauseMinInput.value=String(state.networkPolicy.batchPauseMinSec);pauseMaxInput.value=String(state.networkPolicy.batchPauseMaxSec);
            networkSummary.textContent=`${chT('网络策略','Network policy')} · ${chNetworkPolicySummary(state.networkPolicy)}`;
        };
        const applyPreflightStatuses = plan => {
            state.syncStatusById.clear();
            for(const item of plan.items){let s=item.action;if(s==='VERIFY_CHANGED'||s==='VERIFY_RENAMED')s='VERIFY';if(['NEW','UNCHANGED','DUPLICATE','ERROR'].includes(s)||s==='VERIFY')state.syncStatusById.set(item.id,s);}
            state.lastPlan=plan;state.syncStatus='pending';
        };
        const applyFinalStatuses = result => {
            for(const item of result.verification.items||[]){if(item.id&&item.finalAction)state.syncStatusById.set(item.id,item.finalAction);}
            state.lastPlan=result.plan;state.lastResult=result;
        };
        const ensureRoot = async () => {
            if(state.rootHandle)return state.rootHandle;
            if(!window.showDirectoryPicker)throw new Error(chT('当前浏览器不支持 File System Access API。','File System Access API is unavailable.'));
            state.rootHandle=await window.showDirectoryPicker({mode:'readwrite'});updateArchiveSummary();return state.rootHandle;
        };
        const decorateProjectKnowledge = (items, complete) => (items||[]).map(item=>({...item,__chProjectState:(item.projectId||item.projectTitle)?'known':complete?'none':'unknown'}));
        const applyAccountScopeFromCache = () => {
            const all = Array.isArray(state.accountUniverse) ? state.accountUniverse : [];
            state.remoteUniverse = all;
            state.remoteUniverseComplete = state.accountUniverseComplete;
            state.remoteUniverseNote = state.accountUniverseNote;
            state.list = state.mode === 'project' ? all.filter(item => item.projectId || item.projectTitle) : all;
        };
        const loadAccountUniverse = async (force=false) => {
            if (!force && Array.isArray(state.accountUniverse)) {
                applyAccountScopeFromCache();
                return;
            }
            const base=await listConversations(null);
            const universe=await chCollectPreflightRemoteUniverse('personal',null,base);
            state.accountUniverse=decorateProjectKnowledge(universe.remoteList,universe.complete);
            state.accountUniverseComplete=universe.complete;state.accountUniverseNote=universe.note;state.accountLoadedAt=Date.now();
            applyAccountScopeFromCache();
        };
        const loadTeamUniverse = async (force=false) => {
            if(!state.workspaceId){const ids=detectAllWorkspaceIds();if(ids.length===0)throw new Error(chT('未检测到 Team Workspace ID，请先打开一个团队对话后再试。','No Team Workspace ID detected. Open a team conversation first.'));state.workspaceId=ids[0];}
            const key=String(state.workspaceId);
            if(!force && state.teamUniverseCache.has(key)){
                const cached=state.teamUniverseCache.get(key);state.remoteUniverse=cached.list;state.remoteUniverseComplete=cached.complete;state.remoteUniverseNote=cached.note;state.list=cached.list;return;
            }
            const base=await listConversations(state.workspaceId);
            const universe=await chCollectPreflightRemoteUniverse('team',state.workspaceId,base);
            const list=decorateProjectKnowledge(universe.remoteList,universe.complete);
            state.teamUniverseCache.set(key,{list,complete:universe.complete,note:universe.note,loadedAt:Date.now()});
            state.remoteUniverse=list;state.remoteUniverseComplete=universe.complete;state.remoteUniverseNote=universe.note;state.list=list;
        };
        const loadRemoteList = async (force=false) => {
            state.loading=true;state.syncStatusById.clear();state.lastPlan=null;renderList();
            try{
                if(state.mode==='team') await loadTeamUniverse(force);
                else await loadAccountUniverse(force);
                state.loading=false;renderAll();
                if(state.rootHandle)await runPreflight(true);
            }catch(err){state.loading=false;state.list=[];state.filtered=[];state.remoteUniverse=[];$('conv-status').textContent=`${chT('加载失败','Load failed')}: ${err.message}`;renderList();}
        };
        const runPreflight = async (automatic=false) => {
            if(!state.rootHandle)return;
            const root=state.rootHandle;
            preflightBtn.disabled=true;
            try{
                state.layoutState=await chArchiveLayoutState(root);
                if(state.layoutState.requiresMigration){
                    state.lastPlan=null;state.localScan=null;state.syncStatusById.clear();state.syncStatus='all';
                    chSetProgress(chT('检测到旧目录结构','Legacy archive layout detected'),`${chT('Layout v1 · 本地','Layout v1 · Local')} ${state.layoutState.total} · ${chT('请先执行纯本地 Layout v2 升级','Run the local-only Layout v2 upgrade first')}`,100);
                    renderAll();return;
                }
                chSetProgress(automatic?chT('扫描本地档案','Scanning local archive'):chT('重新扫描本地','Rescanning local'),chT('只读扫描并生成同步计划…','Read-only scan and sync planning…'),0);
                const {localScan,plan}=await chRunPreflightPlanner({rootHandle:root,remoteList:state.remoteUniverse.length?state.remoteUniverse:state.list,selectedIds:null,remoteUniverseComplete:state.remoteUniverseComplete,remoteUniverseNote:state.remoteUniverseNote});
                state.localScan=localScan;
                state.layoutState=await chArchiveLayoutState(root);
                applyPreflightStatuses(plan);renderAll();
            }catch(err){console.error('[ChatHarbor] preflight failed',err);chSetProgress(chT('本地扫描失败','Local scan failed'),err?.message||String(err),100);}finally{updateControls();}
        };
        const runLayoutMigration = async () => {
            if(!state.rootHandle || !state.layoutState?.requiresMigration || state.migrationActive)return;
            const ok = window.confirm(chT(
                '将把当前 ChatGPT Layout v1 档案纯本地迁移到 Layout v2：项目外会话进入 conversations/，项目会话进入 projects/<项目>/。不会重新下载对话；仅删除迁移成功后 Manifest 明确跟踪的旧路径，未跟踪文件保留。继续吗？',
                'Migrate this ChatGPT Layout v1 archive locally to Layout v2: non-project conversations go to conversations/, project conversations to projects/<project>/. No conversations are re-downloaded. Only old manifest-tracked paths are cleaned after verified migration; untracked files are preserved. Continue?'
            ));
            if(!ok)return;
            state.migrationActive=true;updateControls();renderList();
            try{
                chSetProgress(chT('升级目录结构','Upgrading archive layout'),chT('纯本地迁移 · 不访问远端对话详情','Local-only migration · no remote conversation fetch'),0);
                const result=await chMigrateArchiveLayoutV1ToV2(state.rootHandle,info=>{
                    const pct=info.total?Math.round((info.index/info.total)*100):0;
                    chSetProgress(chT('升级目录结构','Upgrading archive layout'),`${info.index}/${info.total} · ${String(info.title||info.id||'').slice(0,42)}`,pct);
                });
                state.migrationReport=result;
                state.layoutState=await chArchiveLayoutState(state.rootHandle);
                chRenderInlineReport(
                    chT('目录结构升级完成','Archive layout upgraded'),
                    [
                        `${chT('本地迁移','Migrated locally')}: ${result.migrated}/${result.total}`,
                        `${chT('Provider','Provider')}: ${result.provider || CH_PROVIDER}`,
                        `Layout v${result.archiveLayoutVersion || CH_ARCHIVE_LAYOUT_VERSION}`,
                        `${chT('清理警告','Cleanup warnings')}: ${(result.cleanupWarnings||[]).length}`,
                        chT('未重新下载任何会话。','No conversation was re-downloaded.')
                    ],
                    JSON.stringify(result,null,2),
                    (result.cleanupWarnings||[]).length?'warn':'success'
                );
                await runPreflight(true);
            }catch(err){
                console.error('[ChatHarbor] layout migration failed',err);
                state.layoutState=await chArchiveLayoutState(state.rootHandle).catch(()=>state.layoutState);
                chSetProgress(chT('目录结构升级未完成','Archive migration incomplete'),err?.message||String(err),100);
                chRenderInlineReport(chT('目录结构升级未完成','Archive migration incomplete'),[err?.message||String(err),chT('已完成的逐会话提交保持有效；下次可继续升级。','Completed per-conversation commits remain valid; migration can be resumed.')],err?.stack||err?.message||String(err),'error');
            }finally{
                state.migrationActive=false;updateArchiveSummary();updateControls();renderList();
            }
        };
        const runSync = async () => {
            const root=await ensureRoot();
            if(state.layoutState?.requiresMigration){chSetProgress(chT('需要升级目录结构','Archive upgrade required'),chT('请先完成纯本地 Layout v2 升级。','Complete the local-only Layout v2 upgrade first.'),100);return;}
            const selectedIds=new Set(state.selected);
            if(selectedIds.size===0)return;
            try{
                chBeginControlledRun(state.networkPolicy);renderList();chSetProgress(chT('目录同步','Directory sync'),`${chT('按选择范围开始流式核验与写入…','Starting streaming verify + commit…')} · ${chNetworkPolicySummary(chSyncRun.policy)}`,0);
                const remote=state.remoteUniverse.length?state.remoteUniverse:state.list;
                const result=await chRunIntegratedDirectorySync({rootHandle:root,remoteList:remote,selectedIds,workspaceId:state.workspaceId,includeAttachments:state.includeAttachments,remoteUniverseComplete:state.remoteUniverseComplete,remoteUniverseNote:state.remoteUniverseNote,networkPolicy:state.networkPolicy,onItemClassified:(item)=>{if(item.id&&item.finalAction)state.syncStatusById.set(item.id,item.finalAction);renderList();},onItemCommitted:(item)=>{if(item.id&&item.finalAction)state.syncStatusById.set(item.id,item.finalAction);}});
                applyFinalStatuses(result);renderAll();
            }catch(err){if(chIsCancellation(err))chSetProgress(chT('目录同步已取消','Sync cancelled'),chT('已在安全边界停止；已提交会话保留。','Stopped at a safe boundary; committed conversations were kept.'),100);else{console.error('[ChatHarbor] sync failed',err);chSetProgress(chT('目录同步失败','Sync failed'),err?.message||String(err),100);}}finally{chEndControlledRun();renderList();}
        };

        searchInput.oninput=e=>{state.query=e.target.value||'';applyFilters();renderList();};
        spaceSelect.onchange=async e=>{const next=e.target.value;state.projectFilter='all';state.syncStatus='all';if(next==='team'){state.mode='team';state.workspaceId=null;await loadRemoteList(false);}else{state.mode=next;state.workspaceId=null;state.loading=true;renderList();await loadAccountUniverse(false);state.loading=false;renderAll();if(state.rootHandle)await runPreflight(true);}};
        projectSelect.onchange=e=>{state.projectFilter=e.target.value;applyFilters();renderList();};
        archivedSelect.onchange=e=>{state.archived=e.target.value;applyFilters();renderList();};
        syncStatusSelect.onchange=e=>{state.syncStatus=e.target.value;applyFilters();renderList();};
        timeFieldSelect.onchange=e=>{state.timeField=e.target.value;applyFilters();renderList();};
        timeRangeSelect.onchange=e=>{state.timeRange=e.target.value;updateTimeSummary();applyFilters();renderList();};
        sortSelect.onchange=e=>{state.sort=e.target.value;applyFilters();renderList();};
        startDateInput.onchange=e=>{state.startDate=e.target.value||'';applyFilters();renderList();};
        endDateInput.onchange=e=>{state.endDate=e.target.value||'';applyFilters();renderList();};
        includeAttachmentsInput.onchange=e=>{state.includeAttachments=e.target.checked;};
        selectAllCheckbox.onchange=()=>{const allSelected=state.filtered.length>0&&state.filtered.every(item=>state.selected.has(item.id));if(allSelected){state.filtered.forEach(item=>state.selected.delete(item.id));}else{state.filtered.forEach(item=>state.selected.add(item.id));}renderList();};
        refreshBtn.onclick=async()=>{const keep=new Set(state.selected);await loadRemoteList(true);state.selected.clear();for(const id of keep)if(state.list.some(item=>item.id===id))state.selected.add(id);renderList();};
        closeBtn.onclick=closeDialog;
        chooseDirBtn.onclick=async()=>{try{state.rootHandle=null;state.lastPlan=null;await ensureRoot();await runPreflight(true);}catch(err){if(err?.name!=='AbortError')chSetProgress(chT('选择目录失败','Directory selection failed'),err?.message||String(err),null);}};
        preflightBtn.onclick=()=>runPreflight(false);
        migrateLayoutBtn.onclick=runLayoutMigration;
        syncSelectedBtn.onclick=runSync;
        [speedLevelInput,batchSizeInput,pauseMinInput,pauseMaxInput].forEach(el=>el.onchange=persistPolicy);
        pauseSyncBtn.onclick=()=>{if(!chSyncRun.active)return;if(chSyncRun.paused)chResumeRun();else chRequestPause();};
        cancelSyncBtn.onclick=()=>{if(!chSyncRun.active)return;chRequestCancel('USER_CANCELLED');chSetProgress(chT('正在取消同步','Cancelling sync'),chT('不会开始新的详情请求或新的会话事务；当前原子事务会先完成。','No new detail fetch or conversation transaction will start; the current atomic transaction will finish first.'),null);};
        overlay.onclick=e=>{if(e.target===overlay)closeDialog();};
        document.addEventListener('keydown',function esc(ev){if(ev.key==='Escape'&&document.body.contains(overlay)&&!chSyncRun.active&&!state.migrationActive){document.removeEventListener('keydown',esc);closeDialog();}});
        chUpdateRunControlUi();updateTimeSummary();loadRemoteList();
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
            `${chT('本地未跟踪待核验','raw-only verify candidates')}: ${s.rawOnlyVerifyCount}`,
            `${chT('仅本地','LOCAL_ONLY')}: ${s.localOnlyReliable ? s.localOnlyCount : chT('未知（远端全集不完整）','UNKNOWN (remote universe incomplete)')}`,
            `${chT('重复ID','duplicate IDs')}: ${s.duplicateIdCount}`,
            `${chT('错误','ERROR')}: ${s.errorCount}`,
            `${chT('最多需要抓取详情','maximum fetch required')}: ${s.maximumFetchRequired}`,
            '', `${chT('Manifest 跟踪','Manifest tracked')}: ${s.manifestTracked}`, `${chT('原始对话 JSON','Raw conversation JSON files')}: ${s.rawConversationFiles}`, `${chT('仅原始文件 ID','Raw-only IDs')}: ${s.rawOnlyIds}`
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
        if (btn) btn.onclick = async () => {
            try { await navigator.clipboard.writeText(detail); const old=btn.textContent; btn.textContent=chT('已复制','Copied'); setTimeout(()=>btn.textContent=old,1200); }
            catch (_) { console.log(detail); }
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
            `${chT('已同步','UNCHANGED')}: ${c.UNCHANGED||0}`, `${chT('本地未跟踪','LOCAL_UNTRACKED')}: ${c.LOCAL_UNTRACKED||0}`,
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
                `${chT('检查','Checked')} ${result.plan.summary.scopeRemote} · ${chT('详情抓取','Detail fetched')} ${result.verification.detailFetchCount}`,
                `${chT('新增','New')} ${c.NEW||0} · ${chT('内容更新','Updated')} ${c.UPDATED||0} · ${chT('仅改名','Renamed')} ${c.RENAMED_ONLY||0}`,
                `${chT('更新+改名','Updated+renamed')} ${c.UPDATED_AND_RENAMED||0} · ${chT('仅元数据','Metadata')} ${c.METADATA_ONLY||0}`,
                `${chT('已同步','Synced')} ${c.UNCHANGED||0} · ${chT('异常','Errors')} ${(c.ERROR||0)+(c.DUPLICATE||0)}`,
                `${chT('写入成功','Committed')} ${result.sync.succeeded} · ${chT('失败','Failed')} ${result.sync.failed}`,
                chT('✓ LOCAL_ONLY 未删除','✓ LOCAL_ONLY was preserved'), chT('✓ 仅清理 Manifest 跟踪路径','✓ Cleanup was limited to manifest-tracked paths')
            ],
            chIntegratedSyncReportText(result), tone
        );
    }

'''
text = text[:integrated_text_start] + integrated_report_block + text[integrated_run_start:]

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
    "chBeginControlledRun",
    "chGetConversationConservative",
    "id=\"ch-space-select\"",
    "id=\"select-all-checkbox\"",
    "id=\"ch-result-panel\"",
    "id=\"ch-action-bar\"",
    "id=\"ch-archive-copy-report-btn\"",
    "grid-template-columns:minmax(0,1fr) 310px",
    "const FAB_STORAGE_KEY = 'chatharbor-fab-v1';",
    "chReconcileRuntimeState",
    "按选择范围开始流式核验与写入",
    "accountUniverse",
    "待处理",
]
missing_runtime_markers = [marker for marker in required_runtime_markers if marker not in text]
if missing_runtime_markers:
    raise SystemExit("Generated runtime invariant failed; missing: " + ", ".join(missing_runtime_markers))
forbidden_runtime_markers = [
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
