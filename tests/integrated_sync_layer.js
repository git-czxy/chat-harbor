
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
        // Runtime progress is intentionally shown only in the workspace progress card.
        // Keep the launcher free of duplicate percentage/status pills.
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

    function chRecordAttachmentState(record) {
        const value = String(record?.attachment_state || '').toLowerCase();
        if (['unknown','none','complete','partial','not_downloaded'].includes(value)) return value;
        return 'unknown';
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
        let trackedFastChecked = 0;

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
                jsonFilesSeen,ignoredJsonFiles,skippedAssetDirs,trackedFastChecked
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
                rawOnlyVerifyCount++; if(updateCandidate)remoteUpdateCandidateCount++; if(titleChanged)renameCandidateCount++; maximumFetchRequired++;
                items.push({id,action:'VERIFY_CHANGED',remote,local,needs_detail_fetch:true,remote_update_candidate:updateCandidate,rename_candidate:titleChanged,metadata_candidate:false,attachment_candidate:includeAttachments,reasons:['LOCAL_RAW_NOT_MANIFEST_TRACKED',...(timeRelation==='different'?['REMOTE_UPDATE_TIME_DIFF']:timeRelation==='unknown'?['REMOTE_UPDATE_TIME_UNKNOWN']:[]),...(titleChanged?['TITLE_DIFF']:[])]});continue;
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
            errorCount:errorCount+remoteErrors.length+localScan.errors.filter(e=>!e.id).length,maximumFetchRequired,manifestTracked:localScan.stats.manifestTracked,localProjectCount:localScan.stats.manifestProject||0,localRootCount:localScan.stats.manifestRoot||0,archiveLayoutVersion:localScan.stats.archiveLayoutVersion,provider:localScan.stats.provider,migrationRequired:Boolean(localScan.stats.migrationRequired),rawConversationFiles:localScan.stats.rawConversationFiles,rawOnlyIds:localScan.stats.rawOnlyIds,trackedFastChecked:localScan.stats.trackedFastChecked||0
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
            remoteUniverseNote,
            includeAttachments
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
        'ATTACHMENT_BACKFILL',
        'OBSERVATION_ONLY',
        'LOCAL_UNTRACKED'
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

    async function chFetchRootHead(workspaceId = null, limit = CH_REMOTE_HEAD_LIMIT) {
        const headers=await chRemoteHeaders(workspaceId); const entries=[];
        for(const archived of [false,true]){
            const r=await fetch(`/backend-api/conversations?offset=0&limit=${limit}&order=updated${archived?'&is_archived=true':''}`,{headers});
            if(!r.ok)throw new Error(`远端列表快速刷新失败 (${r.status})`);
            const j=await r.json();
            for(const item of j.items||[])entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:archived,projectId:null,projectTitle:null,__chArchiveState:'known',__chProjectState:'unknown',__chSourceKey:`root:${archived?'archived':'active'}`});
        }
        return entries;
    }

    async function chFetchProjectHead(workspaceId = null, limit = CH_REMOTE_HEAD_LIMIT) {
        const resolved=resolveWorkspaceId(workspaceId); if(!resolved)return [];
        const projects=await getProjectSpaces(resolved,{conversationsPerGizmo:limit,ownedOnly:true}); const entries=[];
        for(const project of projects)for(const item of project.conversations||[])entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:item.is_archived??false,projectId:project.id,projectTitle:project.title,__chArchiveState:Object.prototype.hasOwnProperty.call(item||{},'is_archived')?'known':'unknown',__chProjectState:'known',__chSourceKey:`project:${project.id}`});
        return entries;
    }

    async function chFetchRemoteHeadSnapshot(workspaceId = null) {
        const entries=[...(await chFetchRootHead(workspaceId)),...(await chFetchProjectHead(workspaceId))];
        return {entries,fingerprint:chHeadFingerprint(entries),validatedAt:Date.now()};
    }

    async function chFetchRootFull(workspaceId = null) {
        const headers=await chRemoteHeaders(workspaceId); const entries=[];
        for(const archived of [false,true]){
            let offset=0,hasMore=true;
            while(hasMore){
                const r=await fetch(`/backend-api/conversations?offset=${offset}&limit=${PAGE_LIMIT}&order=updated${archived?'&is_archived=true':''}`,{headers});
                if(!r.ok)throw new Error(`远端列表完整刷新失败 (${r.status})`);
                const j=await r.json(); const items=Array.isArray(j.items)?j.items:[];
                for(const item of items)entries.push({id:item.id,title:item.title||'Untitled Conversation',create_time:normalizeEpochSeconds(item.create_time||0),update_time:normalizeEpochSeconds(item.update_time||item.create_time||0),is_archived:archived,projectId:null,projectTitle:null,__chArchiveState:'known',__chProjectState:'unknown',__chSourceKey:`root:${archived?'archived':'active'}`});
                hasMore=items.length===PAGE_LIMIT; offset+=items.length;
                if(hasMore)await sleep(jitter());
            }
        }
        return chMergeRemoteEntries(entries);
    }

    async function chFetchFullRemoteUniverse(workspaceId = null) {
        const rootList=await chFetchRootFull(workspaceId);
        let projectList=[]; let complete=true; let note=null;
        try{
            projectList=(await listProjectSpaceConversations(workspaceId)).map(item=>({...item,__chProjectState:'known',__chArchiveState:Object.prototype.hasOwnProperty.call(item||{},'is_archived')?'known':'unknown',__chSourceKey:`project:${item.projectId||'unknown'}`}));
        }catch(err){complete=false;note=`project complement failed: ${err?.message||String(err)}`;}
        const merged=chMergeRemoteEntries(rootList.concat(projectList)).map(item=>({...item,__chProjectState:(item.projectId||item.projectTitle)?'known':complete?'none':'unknown',__chArchiveState:item.__chArchiveState||'unknown'}));
        return {list:merged,complete,note:note||`full remote index ${merged.length}`};
    }

    async function chRefreshRemoteIndex(workspaceId = null, { forceFull = false } = {}) {
        const flightKey=chRemoteCacheIdentity(workspaceId)||`volatile:${workspaceId||'default'}`;
        if(chRemoteRefreshFlights.has(flightKey))return chRemoteRefreshFlights.get(flightKey);
        const promise=(async()=>{
            const cached=await chRemoteCacheGet(workspaceId); const now=Date.now();
            const needsPeriodicFull=!cached||cached.schema!==CH_REMOTE_CACHE_SCHEMA||cached.provider!==CH_PROVIDER||cached.complete!==true||!cached.fullFetchedAt||(now-cached.fullFetchedAt)>=CH_REMOTE_FULL_REFRESH_MS;
            if(forceFull||needsPeriodicFull){
                const full=await chFetchFullRemoteUniverse(workspaceId); const head=await chFetchRemoteHeadSnapshot(workspaceId);
                const snapshot={list:full.list,complete:full.complete,note:full.note,fullFetchedAt:now,validatedAt:head.validatedAt,headFingerprint:head.fingerprint};
                if(full.complete)await chRemoteCachePut(workspaceId,snapshot);
                return {...snapshot,refreshMode:'full'};
            }
            const head=await chFetchRemoteHeadSnapshot(workspaceId);
            if(head.fingerprint===cached.headFingerprint){
                const snapshot={...cached,validatedAt:head.validatedAt,note:`fast refresh stable · head ${CH_REMOTE_HEAD_LIMIT}`};
                await chRemoteCachePut(workspaceId,snapshot); return {...snapshot,refreshMode:'fast-stable'};
            }
            const full=await chFetchFullRemoteUniverse(workspaceId); const refreshedHead=await chFetchRemoteHeadSnapshot(workspaceId);
            const snapshot={list:full.list,complete:full.complete,note:full.note,fullFetchedAt:Date.now(),validatedAt:refreshedHead.validatedAt,headFingerprint:refreshedHead.fingerprint};
            if(full.complete)await chRemoteCachePut(workspaceId,snapshot);
            return {...snapshot,refreshMode:'full-after-change'};
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
            remoteUniverseNote,
            includeAttachments
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
        const fastItems = plan.items.filter(item => !item.needs_detail_fetch || item.action === 'ERROR' || item.action === 'DUPLICATE');
        const workItems = plan.items.filter(item => item.needs_detail_fetch && item.action !== 'ERROR' && item.action !== 'DUPLICATE');
        for (const item of fastItems) {
            const classified = { ...item, finalAction: item.action, needs_sync: false, finalReasons: item.reasons || [] };
            verification.items.push(classified);
            verification.counts[classified.finalAction] = (verification.counts[classified.finalAction] || 0) + 1;
        }
        if (workItems.length && fastItems.length) {
            chSetProgress('目录同步', `快速跳过 ${fastItems.length} 条已由 Manifest/预检确认的记录；待处理 ${workItems.length} 条`, 0);
        }
        const totalItems = Math.max(1, workItems.length);

        for (let i = 0; i < workItems.length; i++) {
            let classified = null;
            const item = workItems[i];
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


