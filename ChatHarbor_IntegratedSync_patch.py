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
    "// @version      0.0.7.0\n"
    "// @description  Clean-lineage archive sync with conservative pacing, pause/cancel, and version-aware selective directory sync.\n"
    "// @description:zh-CN 干净来源的本地档案同步：保守节奏、暂停/取消、版本识别与选择性目录同步。\n"
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
    // Integrated Sync preserves the validated Gate 3 / 3.1 writer unchanged, then adds a
    // separate read-only Archive Scan + Preflight Planner below.
    // Final content classification, rename cleanup and selective write execution
    // remain outside this gate.

    const CH_MANIFEST_NAME = 'ChatHarbor_manifest.json';
    const CH_MANIFEST_SCHEMA_VERSION = 1;
    const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';


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
        waiters: []
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

    async function chControlledSleep(ms, primary = '保守网络等待', secondary = '') {
        let remaining = Math.max(0, Math.round(Number(ms) || 0));
        while (remaining > 0) {
            await chControlCheckpoint();
            const chunk = Math.min(1000, remaining);
            if (remaining >= 1000) {
                chSetProgress(primary, secondary || `剩余约 ${Math.ceil(remaining / 1000)} 秒`, null);
            }
            await sleep(chunk);
            remaining -= chunk;
        }
        await chControlCheckpoint();
    }

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
            source: 'ChatGPT',
            created_at: now,
            updated_at: now,
            identity: 'conversation_id',
            signature_version: CH_SIGNATURE_VERSION,
            conversations: {}
        };
    }

    async function chReadManifest(rootHandle) {
        try {
            const handle = await rootHandle.getFileHandle(CH_MANIFEST_NAME);
            const file = await handle.getFile();
            const text = await file.text();
            const manifest = JSON.parse(text);

            if (!manifest || typeof manifest !== 'object') {
                throw new Error('manifest root is not an object');
            }
            if (manifest.schema_version !== CH_MANIFEST_SCHEMA_VERSION) {
                throw new Error(
                    `unsupported manifest schema: ${manifest.schema_version ?? 'missing'}`
                );
            }
            if (!manifest.conversations || typeof manifest.conversations !== 'object' || Array.isArray(manifest.conversations)) {
                throw new Error('manifest.conversations is invalid');
            }
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
            `同步 ${conversationIndex + 1} / ${conversationTotal} · ${phase}`,
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

        let targetDir = rootHandle;
        let relativePrefix = '';

        if (entry?.projectTitle) {
            const projectDirName = sanitizeFilename(entry.projectTitle) || 'Untitled Project';
            targetDir = await rootHandle.getDirectoryHandle(projectDirName, { create: true });
            relativePrefix = `${projectDirName}/`;
        }

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
            if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
                throw new Error('manifest root is not an object');
            }
            if (manifest.schema_version !== CH_MANIFEST_SCHEMA_VERSION) {
                throw new Error(`unsupported manifest schema: ${manifest.schema_version ?? 'missing'}`);
            }
            if (manifest.identity !== 'conversation_id') {
                throw new Error(`unsupported manifest identity: ${manifest.identity ?? 'missing'}`);
            }
            if (manifest.signature_version !== CH_SIGNATURE_VERSION) {
                throw new Error(`unsupported signature version: ${manifest.signature_version ?? 'missing'}`);
            }
            if (!manifest.conversations || typeof manifest.conversations !== 'object' || Array.isArray(manifest.conversations)) {
                throw new Error('manifest.conversations is invalid');
            }
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
                rawConversationFiles: conversationJsonFiles,
                rawUniqueIds: rawById.size,
                rawOnlyIds: Array.from(recordsById.values()).filter(record => record.tracking === 'raw_only').length,
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
        if (!entry?.projectTitle) return '';
        const projectDirName = sanitizeFilename(entry.projectTitle) || 'Untitled Project';
        return `${projectDirName}/`;
    }

    function chSplitPath(path) {
        return String(path || '').split('/').filter(Boolean);
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
                        `已核验 ${fetchIndex}/${fetchTotal} · 下一批前暂停约 ${Math.round(pauseMs / 1000)} 秒`
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
        networkPolicy = null
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
        const plan = chBuildPreflightPlan(remoteList, localScan, selected, {
            remoteUniverseComplete,
            remoteUniverseNote
        });

        chSetProgress('目录同步', `预检完成 · 最多抓取 ${plan.summary.maximumFetchRequired} 条详情`, 5);
        let verification;
        try {
            verification = await chVerifyPreflightCandidates({ plan, workspaceId });
        } catch (err) {
            if (chIsCancellation(err)) {
                chSetProgress('目录同步已取消', '已停止后续详情请求；尚未进入写入阶段。', 100);
                return {
                    localScan,
                    plan,
                    verification: { items: [], counts: {}, detailFetchCount: 0, cancelled: true },
                    sync: { attempted: 0, succeeded: 0, failed: 0, manifestOnly: 0, fileCommits: 0, cleanupWarnings: [], results: [], failures: [], cancelled: true }
                };
            }
            throw err;
        }

        const actionable = verification.items.filter(item => CH_FINAL_SYNC_ACTIONS.has(item.finalAction));
        const manifest = await chReadManifest(rootHandle);
        const btn = getExportButton();
        const sync = {
            attempted: actionable.length,
            succeeded: 0,
            failed: 0,
            manifestOnly: 0,
            fileCommits: 0,
            cleanupWarnings: [],
            results: [],
            failures: [],
            cancelled: false
        };

        for (let i = 0; i < actionable.length; i++) {
            try {
                await chControlCheckpoint('apply-sync');
            } catch (err) {
                if (chIsCancellation(err)) {
                    sync.cancelled = true;
                    break;
                }
                throw err;
            }
            const item = actionable[i];
            const title = item.convData?.title || item.remote?.title || item.id;
            chSetProgress(
                '应用同步计划',
                `${i + 1}/${actionable.length} · [${item.finalAction}] ${String(title).slice(0, 54)}`,
                50 + (actionable.length ? Math.round((i / actionable.length) * 48) : 48)
            );
            try {
                const applied = await chApplyClassifiedSyncItem({
                    rootHandle,
                    classifiedItem: item,
                    manifest,
                    workspaceId,
                    includeAttachments,
                    btn,
                    conversationIndex: i,
                    conversationTotal: actionable.length || 1
                });
                sync.succeeded++;
                if (applied.mode === 'MANIFEST_ONLY') sync.manifestOnly++;
                if (applied.mode === 'FILES_AND_MANIFEST') sync.fileCommits++;
                sync.cleanupWarnings.push(...(applied.cleanup?.warnings || []).map(w => `${item.id}: ${w}`));
                sync.results.push(applied);
                if (includeAttachments && applied?.record?.attachment_detected > 0 && i < actionable.length - 1) {
                    const policy = chNormalizeNetworkPolicy(chSyncRun.policy);
                    const completed = i + 1;
                    if (completed % policy.batchSize === 0) {
                        const pauseMs = chNetworkBatchPauseMs(policy);
                        await chControlledSleep(
                            pauseMs,
                            '附件同步批次暂停',
                            `已完成 ${completed}/${actionable.length} 个会话 · 暂停约 ${Math.round(pauseMs / 1000)} 秒`
                        );
                    } else {
                        await chControlledSleep(chNetworkDelayMs(policy), '附件同步请求间隔', `${completed}/${actionable.length}`);
                    }
                }
            } catch (err) {
                if (chIsCancellation(err)) {
                    sync.cancelled = true;
                    break;
                }
                sync.failed++;
                sync.failures.push({
                    id: item.id,
                    action: item.finalAction,
                    error: err?.message || String(err)
                });
            }
        }

        chSetProgress(
            sync.cancelled ? '目录同步已取消' : (sync.failed ? '目录同步完成（存在失败）' : '目录同步完成'),
            sync.cancelled
                ? `已安全提交 ${sync.succeeded} 个会话；未开始的会话保持不变，下次可继续。`
                : `成功 ${sync.succeeded}/${sync.attempted} · 未变化 ${verification.counts.UNCHANGED || 0} · 异常 ${(verification.counts.ERROR || 0) + (verification.counts.DUPLICATE || 0)}`,
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

# Build-time UI/runtime invariants: fail closed instead of generating a script with no visible entry.
required_runtime_markers = [
    "function initFab()",
    "getExportButton();",
    "document.addEventListener('DOMContentLoaded', initFab);",
    "#gpt-rescue-btn",
    "ChatHarbor｜选择空间",
    "选择对话 / 目录同步",
    "id=\"preflight-plan-btn\"",
    "id=\"sync-directory-btn\"",
    "id=\"ch-pause-sync-btn\"",
    "id=\"ch-cancel-sync-btn\"",
    "CH_SPEED_LEVELS",
    "chBeginControlledRun",
    "chGetConversationConservative",
]
missing_runtime_markers = [marker for marker in required_runtime_markers if marker not in text]
if missing_runtime_markers:
    raise SystemExit("Generated runtime invariant failed; missing: " + ", ".join(missing_runtime_markers))

out.write_text(text, encoding="utf-8")
print(f"Wrote: {out}")
print(f"Source git blob: {actual_blob}")
print(f"Output SHA-256: {hashlib.sha256(out.read_bytes()).hexdigest()}")
