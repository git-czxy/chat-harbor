// ==UserScript==
// @name         ChatHarbor
// @name:zh-Hans ChatHarbor
// @name:zh-Hant ChatHarbor
// @namespace    chatharbor.local
// @version      0.5.0
// @description  Local-first ChatGPT archive with conservative export, version-aware scan and direct directory sync.
// @description:zh-Hans 本地优先的 ChatGPT 对话归档工具：保守导出、版本识别与目录增量同步。
// @description:zh-Hant 本地優先的 ChatGPT 對話歸檔工具：保守匯出、版本識別與目錄增量同步。
// @author       ChatHarbor contributors; derived from OwlCt/ChatGPT-Export
// @license      MIT
// @match        https://chatgpt.com/*
// @match        https://chat.openai.com/*
// @require      https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js#sha256=acc7e41455a80765b5fd9c7ee1b8078a6d160bbbca455aeae854de65c947d59e
// @grant        none
// ==/UserScript==

// ChatHarbor v0.5.0
//  - Version-aware Scan + Directory Sync（File System Access API）
//  - conversation_id 作为唯一身份；识别 NEW / RENAMED_ONLY / UPDATED / UPDATED_AND_RENAMED / METADATA_ONLY / UNCHANGED
//  - 同步模式取消 ZIP 中间层，但保留原有安全批次、随机暂停、重试与 ZIP 导出能力
//  - 目录写入按 conversation 粒度提交；标题变化按“先写新文件，再移除旧文件”处理
//
// Direct upstream / 直接来源：
//   OwlCt/ChatGPT-Export — https://github.com/OwlCt/ChatGPT-Export
// ChatHarbor retains the upstream MIT provenance and acknowledges OwlCt and earlier upstream contributors.

(function () {
    'use strict';

    // ======================== 超保守可配置参数 ========================
    const SPEED_LEVELS = [
        { name: '1. 最快（原版）', base: 600, jitter: 400 },
        { name: '2. 较快', base: 1500, jitter: 1000 },
        { name: '3. 中等', base: 3000, jitter: 2000 },
        { name: '4. 较慢（推荐）', base: 6000, jitter: 4000 },
        { name: '5. 很慢', base: 9000, jitter: 6000 },
        { name: '6. 最慢（超慢×2）', base: 12000, jitter: 8000 }
    ];
    let currentSpeedIndex = 3; // 默认「较慢」
    let BASE_DELAY = SPEED_LEVELS[currentSpeedIndex].base;
    let JITTER = SPEED_LEVELS[currentSpeedIndex].jitter;

    let MAX_EXPORT_PER_BATCH = 20;
    let BATCH_PAUSE_MIN = 180; // 3分钟
    let BATCH_PAUSE_MAX = 300; // 5分钟

    const PAGE_LIMIT = 100;
    const PROJECT_SIDEBAR_PREVIEW = 5;
    const PROJECT_SIDEBAR_LIMIT = 50;
    let accessToken = null;
    let capturedWorkspaceIds = new Set();
    let exportRunning = false;        // 是否有导出任务在运行（供按钮切换为取消）
    let exportAbortRequested = false; // 取消导出请求标志

    // ======================== 本地去重（两阶段：待确认/已导出） ========================
    // pending（待确认）：已成功抓取内容、等待 ZIP 下载确认；
    // exported（已导出）：ZIP 已确认下载成功。
    // 中断后可从 pending 续传，且不会把"没拿到文件"的对话误记为已导出。
    const EXPORTED_IDS_KEY = 'chatgpt_exporter_exported_ids_v1';
    const PENDING_IDS_KEY = 'chatgpt_exporter_pending_ids_v1';

    function readIdSet(key) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return new Set();
            const parsed = JSON.parse(raw);
            return new Set(Array.isArray(parsed) ? parsed : []);
        } catch {
            return new Set();
        }
    }

    function writeIdSet(key, set) {
        try {
            localStorage.setItem(key, JSON.stringify([...set]));
            return true;
        } catch (err) {
            console.warn(`[去重] 存储写入失败（可能超出浏览器配额）：`, err);
            alert(t('alert.storageQuotaExceeded'));
            return false;
        }
    }

    function getExportedIds() {
        return readIdSet(EXPORTED_IDS_KEY);
    }

    function getPendingIds() {
        return readIdSet(PENDING_IDS_KEY);
    }

    function markConversationsPending(ids) {
        if (!ids || ids.length === 0) return;
        const set = getPendingIds();
        let changed = false;
        ids.forEach(id => { if (!set.has(id)) { set.add(id); changed = true; } });
        if (changed) writeIdSet(PENDING_IDS_KEY, set);
        console.log(`[续传] 已记录待确认 ${ids.length} 条，累计待确认 ${set.size} 条`);
    }

    function markConversationsExported(ids) {
        if (!ids || ids.length === 0) return;
        const exported = getExportedIds();
        const pending = getPendingIds();
        let changed = false;
        ids.forEach(id => {
            if (!exported.has(id)) { exported.add(id); changed = true; }
            if (pending.delete(id)) changed = true;
        });
        if (changed) {
            writeIdSet(EXPORTED_IDS_KEY, exported);
            writeIdSet(PENDING_IDS_KEY, pending);
        }
        console.log(`[去重] 确认导出 ${ids.length} 条，总计已导出 ${exported.size} 条`);
    }

    function isAlreadyExported(id) {
        return getExportedIds().has(id);
    }

    function isPendingExport(id) {
        return getPendingIds().has(id);
    }

    function clearExportedHistory() {
        localStorage.removeItem(EXPORTED_IDS_KEY);
        localStorage.removeItem(PENDING_IDS_KEY);
        console.log('[去重] 已清空本地导出记录（仅清除记忆，不删除文件）');
        alert(t('alert.exportHistoryCleared'));
    }

    // 备份：把已导出/待确认清单落盘为 JSON，浏览器清理站点数据后可用「导入恢复」还原
    function exportHistoryBackup() {
        const data = {
            app: 'chatgpt-exporter-history',
            version: 1,
            exportedAt: new Date().toISOString(),
            exported: Array.from(getExportedIds()),
            pending: Array.from(getPendingIds())
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const date = new Date().toISOString().slice(0, 10);
        downloadFile(blob, `chatgpt-exporter-history_${date}.json`);
        alert(t('alert.exportHistorySaved'));
    }

    // 导入：读取备份 JSON，与原记录做并集合并（保留现有 + 补回备份），不覆盖既有数据
    function importHistoryBackup(file) {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            try {
                const data = JSON.parse(reader.result);
                if (!data || typeof data !== 'object' || !Array.isArray(data.exported)) {
                    throw new Error('invalid backup');
                }
                const newExported = getExportedIds();
                (Array.isArray(data.exported) ? data.exported : []).forEach(id => id && newExported.add(String(id)));
                const newPending = getPendingIds();
                (Array.isArray(data.pending) ? data.pending : []).forEach(id => id && newPending.add(String(id)));
                writeIdSet(EXPORTED_IDS_KEY, newExported);
                writeIdSet(PENDING_IDS_KEY, newPending);
                alert(t('alert.importHistoryOk', { count: newExported.size, pending: newPending.size }));
            } catch (err) {
                console.warn('[去重] 备份导入失败:', err);
                alert(t('error.importHistoryInvalid'));
            }
        };
        reader.onerror = () => alert(t('error.importHistoryInvalid'));
        reader.readAsText(file);
    }

    // 从已下载的 ZIP 回填已导出清单：无需手动解压，可一次多选多个，串行逐个解析避免内存峰值
    function importHistoryFromZips(fileList, progressBtn) {
        if (!fileList || fileList.length === 0) return;
        const files = Array.from(fileList);
        const uuidLike = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        let handledFiles = 0;
        let handledZips = 0;

        const run = async () => {
            if (progressBtn) progressBtn.disabled = true;
            try {
                for (let i = 0; i < files.length; i++) {
                    if (progressBtn) progressBtn.textContent = `${t('status.parsingZipCount', { current: i + 1, total: files.length })}`;
                    try {
                        const zip = await JSZip.loadAsync(files[i]);
                        const entries = zip.file(/\.json$/i);
                        for (const entry of entries) {
                            try {
                                const obj = JSON.parse(await entry.async('string'));
                                const id = obj && typeof obj === 'object' ? (obj.conversation_id || obj.id) : null;
                                if (typeof id === 'string' && uuidLike.test(id)) {
                                    if (!isAlreadyExported(id)) {
                                        markConversationsExported([id]);
                                        handledFiles++;
                                    }
                                }
                            } catch (_) { /* 单个 JSON 解析失败则忽略 */ }
                        }
                    } catch (err) {
                        console.warn(`[回填] 解析 ZIP ${files[i].name} 失败:`, err.message);
                    }
                    handledZips++;
                }
                alert(t('alert.importZipsOk', { zips: handledZips, count: handledFiles }));
            } finally {
                if (progressBtn) {
                    progressBtn.disabled = false;
                    progressBtn.textContent = t('button.importZips');
                }
            }
        };
        run();
    }

    // ======================== 列表快照（缓存 + 首页指纹探测） ========================
    // 目的：打开选择器时先用本地快照秒开渲染，再用 1 个请求做首页指纹比对，
    // 只有远端确有更新时才全量翻页，从而兼顾速度与风控。
    const LIST_CACHE_KEY = 'chatgpt_exporter_list_cache_v1';
    function readListCache() {
        try { return JSON.parse(localStorage.getItem(LIST_CACHE_KEY) || '{}'); }
        catch (e) { return {}; }
    }
    function writeListCache(cache) {
        try { localStorage.setItem(LIST_CACHE_KEY, JSON.stringify(cache)); return true; }
        catch (err) { console.warn('[列表] 快照写入失败（可能超出配额）:', err); return false; }
    }
    function listCacheKey(mode, workspaceId) {
        return `${mode || 'personal'}:${workspaceId || ''}`;
    }
    function getListSnapshot(cacheKey) {
        const snap = readListCache()[cacheKey];
        return snap && Array.isArray(snap.entries) ? snap : null;
    }
    function saveListSnapshot(cacheKey, entries) {
        if (!entries) return false;
        const cache = readListCache();
        cache[cacheKey] = {
            syncedAt: Date.now(),
            entries: entries.map(e => ({
                id: e.id, title: e.title, create_time: e.create_time || 0,
                update_time: e.update_time || 0, is_archived: !!e.is_archived,
                projectTitle: e.projectTitle || null, projectId: e.projectId || null
            }))
        };
        return writeListCache(cache);
    }

    function setSpeedLevel(index) {
        currentSpeedIndex = Math.max(0, Math.min(SPEED_LEVELS.length - 1, index));
        BASE_DELAY = SPEED_LEVELS[currentSpeedIndex].base;
        JITTER = SPEED_LEVELS[currentSpeedIndex].jitter;
        console.log(`[速度] 切换到：${SPEED_LEVELS[currentSpeedIndex].name}`);
    }

    // ======================== 多语言 ========================
    const SCRIPT_FALLBACK_LOCALE = 'en-US';
    const SCRIPT_LOCALES = {
        'en-US': {
            'button.export': 'Export Conversations',
            'button.exportAll': 'Export all',
            'button.exportAllZip': 'Export all (ZIP)',
            'button.selectConversationsExport': 'Select chats',
            'button.cancel': 'Cancel',
            'button.cancelExport': 'Cancel export',
            'button.back': 'Back',
            'button.clear': 'Clear',
            'button.selectAll': 'Select all',
            'button.clearDates': 'Clear dates',
            'button.exportSelected': 'Export selected ({count})',
            'button.loadMore': 'Load more ({count} remaining)',
            'button.done': 'Done',
            'button.error': 'Error',
            'button.clearExported': 'Clear exported history',
            'button.exportHistory': 'Backup history',
            'button.importHistory': 'Restore backup',
            'button.importZips': 'Import from ZIPs',
            'button.syncDirectory': 'Sync local archive',
            'button.refreshList': 'Refresh',
            'fallback.conversation': 'Conversation',
            'fallback.untitledConversation': 'Untitled Conversation',
            'fallback.unknown': 'Unknown',
            'fallback.untitledProject': 'Untitled Project',
            'fallback.file': 'File',
            'mode.personal': 'Personal space',
            'mode.project': 'Project space',
            'mode.team': 'Team space',
            'dialog.selectSpaceTitle': 'Choose export space',
            'dialog.personalTitle': 'Personal space',
            'dialog.personalCopy': 'Export conversations from your personal account.',
            'dialog.projectTitle': 'Project space',
            'dialog.projectCopy': 'Export project-space conversations, grouped by project.',
            'dialog.teamTitle': 'Team space',
            'dialog.teamCopy': 'Export team-space conversations. The Workspace ID is detected automatically.',
            'dialog.exportTeamTitle': 'Export team space',
            'dialog.multipleWorkspace': 'Multiple workspaces detected. Choose one:',
            'dialog.workspaceDetected': 'Workspace ID detected automatically:',
            'dialog.workspaceMissing': 'Could not detect a Workspace ID.',
            'dialog.workspaceMissingHint': 'Refresh the page, open a team conversation, or enter one manually below.',
            'dialog.manualWorkspaceLabel': 'Team Workspace ID:',
            'dialog.workspacePlaceholder': 'Paste your Workspace ID (ws-...)',
            'dialog.selectConversationsTitle': 'Choose conversations to export',
            'dialog.space': 'Space: {mode}{workspace}',
            'dialog.searchPlaceholder': 'Search title/project/ID',
            'dialog.projectScopeLocked': 'Project space only includes project conversations',
            'filter.scopeAll': 'All scopes',
            'filter.scopeProject': 'Projects only',
            'filter.scopeRoot': 'Root only',
            'filter.statusAll': 'All statuses',
            'filter.statusActive': 'Active only',
            'filter.statusArchived': 'Archived only',
            'filter.timeUpdate': 'By updated time',
            'filter.timeCreate': 'By created time',
            'filter.dateTo': 'to',
            'filter.exportAll': 'All export statuses',
            'filter.exportUnexported': 'Not exported only',
            'filter.exportExported': 'Exported only',
            'status.loadingList': 'Loading list...',
            'status.listSummary': '{total} total, {filtered} filtered, showing {visible}, selected {selected}',
            'status.noMatches': 'No matching conversations.',
            'status.loadFailed': 'Load failed: {message}',
            'status.fetchingOrphanConversations': 'Fetching root conversations...',
            'status.rootProgress': 'Root ({current}/{total})',
            'status.fetchingProjectList': 'Fetching project list...',
            'status.project': 'Project: {title}',
            'status.projectProgress': '{title}... ({current}/{total})',
            'status.generatingZip': 'Generating ZIP...',
            'status.refreshListHint': 'Force a full refresh of the conversation list',
            'status.listFromCache': 'Loaded from local snapshot ({time}); remote unchanged',
            'status.parsingZipCount': 'Parsing ZIP {current}/{total}...',
            'status.scanningLocalArchive': 'Scanning local archive...',
            'status.syncPreparing': 'Preparing directory sync...',
            'status.syncingConversation': 'Syncing {current}/{total}: {title}',
            'status.rootPage': 'Root conversations ({state} p{page})',
            'status.active': 'Active',
            'status.archived': 'Archived',
            'status.batchPause': 'Batch pause: {sec}s remaining...',
            'status.retryPause': 'Network issue, pausing {sec}s...',
            'picker.timeCreated': 'Created',
            'picker.timeUpdated': 'Updated',
            'picker.unknownTime': 'Unknown',
            'picker.projectTag': 'Project: {title}',
            'picker.archivedTag': 'Archived',
            'picker.exportedTag': 'Exported',
            'alert.accessTokenUnavailable': 'Could not get Access Token. Refresh the page or open any conversation and try again.',
            'alert.exportCompletedWithFailures': 'Export complete, but {count} conversations failed and were skipped:\n\n{list}',
            'alert.exportSuccess': 'Export complete.',
            'alert.exportFailed': 'Export failed: {message}. See the console for details (F12 -> Console).',
            'alert.noProjectConversations': 'No project-space conversations found.',
            'alert.projectExportFailed': 'Project-space export failed: {message}',
            'alert.invalidWorkspaceId': 'Choose or enter a valid Team Workspace ID.',
            'alert.batchLimit': 'Selected {total} conversations, exceeds per-batch limit {limit}.\nWill export all in {batches} batches. Continue?',
            'alert.allExported': 'All selected conversations have already been exported.',
            'alert.noSelection': 'No conversations selected.',
            'alert.exportCancelled': 'Export cancelled. Batches already downloaded are marked as exported; the rest can be resumed later.',
            'alert.storageQuotaExceeded': 'Failed to save local export records (storage space exceeded).\nClear old records first under "Clear exported history" to avoid losing progress.',
            'alert.exportHistoryCleared': 'Local exported history cleared.\nNote: this only clears the memory; ZIP files already downloaded to your computer are not deleted.',
            'alert.exportHistorySaved': 'Exported history saved as a JSON file. Keep it somewhere safe, and use "Restore backup" if the records are ever lost.',
            'alert.importHistoryOk': 'Backup restored: {count} exported + {pending} pending records.',
            'alert.importZipsOk': 'Parsed {zips} ZIP(s): registered {count} conversations as exported.',
            'alert.syncUnsupported': 'This browser does not support direct directory sync (File System Access API). Use a recent Chromium/Edge browser.',
            'alert.syncNoChanges': 'No new or changed conversations were found.',
            'error.importHistoryInvalid': 'The backup file is invalid, or not an exported history of this tool.',
            'confirm.clearExportedHistory': 'Clear the exported history? (Only clears the memory, does not delete local ZIP files)',
            'confirm.exportAll': 'About to export all conversations in {mode}.\nThis will run in batches of {limit} with pauses.\nContinue?',
            'confirm.cancelExport': 'Stop exporting? Batches already downloaded will be marked as exported.',
            'confirm.scheduledExport': 'Chrome extension requested exporting {mode} conversations (source: {source}). Start now?',
            'error.deviceIdUnavailable': 'Could not get oai-device-id. Make sure you are signed in and refresh the page.',
            'error.projectSpaceListFailed': 'Failed to fetch project-space list ({status})',
            'error.projectConversationListFailed': 'Failed to list project conversations ({status})',
            'error.rootConversationListFailed': 'Failed to list root conversations ({status})',
            'error.conversationListFailed': 'Failed to list conversations ({status})',
            'error.projectSpaceConversationListFailed': 'Failed to list project-space conversations ({status})',
            'error.conversationDetailFailed': 'Failed to fetch conversation {id} ({status})',
            'error.fileDownloadUrlFailed': 'Failed to get file download URL ({status})',
            'error.imageDownloadFailed': 'Image download failed ({status})',
            'error.fileDownloadFailed': 'File download failed ({status})',
            'error.noDownloadUrl': 'No available download URL',
            'settings.speed': 'Speed',
            'settings.maxBatch': 'Max per batch',
            'settings.pauseRange': 'Batch pause (sec)'
        },
        'zh-Hans': {
            'button.export': '导出对话',
            'button.exportAll': '导出全部',
            'button.exportAllZip': '导出全部 (ZIP)',
            'button.selectConversationsExport': '选择对话导出',
            'button.cancel': '取消',
            'button.cancelExport': '取消导出',
            'button.back': '返回',
            'button.clear': '清空',
            'button.selectAll': '全选',
            'button.clearDates': '清空日期',
            'button.exportSelected': '导出选中 ({count})',
            'button.loadMore': '加载更多（剩余 {count} 条）',
            'button.done': '完成',
            'button.error': '错误',
            'button.clearExported': '清空已导出记录',
            'button.exportHistory': '备份清单',
            'button.importHistory': '导入恢复',
            'button.importZips': '从 ZIP 导入已导出',
            'button.syncDirectory': '同步本地目录',
            'button.refreshList': '刷新列表',
            'fallback.conversation': '对话',
            'fallback.untitledConversation': '未命名对话',
            'fallback.unknown': '未知',
            'fallback.untitledProject': '未命名项目',
            'fallback.file': '文件',
            'mode.personal': '个人空间',
            'mode.project': '项目空间',
            'mode.team': '团队空间',
            'dialog.selectSpaceTitle': '选择要导出的空间',
            'dialog.personalTitle': '个人空间',
            'dialog.personalCopy': '导出您个人账户下的对话。',
            'dialog.projectTitle': '项目空间',
            'dialog.projectCopy': '导出项目空间下的对话，将按项目自动分组。',
            'dialog.teamTitle': '团队空间',
            'dialog.teamCopy': '导出团队空间下的对话，将自动检测 ID。',
            'dialog.exportTeamTitle': '导出团队空间',
            'dialog.multipleWorkspace': '检测到多个 Workspace，请选择一个：',
            'dialog.workspaceDetected': '已自动检测到 Workspace ID：',
            'dialog.workspaceMissing': '未能自动检测到 Workspace ID。',
            'dialog.workspaceMissingHint': '请尝试刷新页面或打开一个团队对话，或在下方手动输入。',
            'dialog.manualWorkspaceLabel': '手动输入 Team Workspace ID：',
            'dialog.workspacePlaceholder': '粘贴您的 Workspace ID (ws-...)',
            'dialog.selectConversationsTitle': '选择要导出的对话',
            'dialog.space': '空间：{mode}{workspace}',
            'dialog.searchPlaceholder': '搜索标题/项目名/ID',
            'dialog.projectScopeLocked': '项目空间仅包含项目对话',
            'filter.scopeAll': '全部范围',
            'filter.scopeProject': '仅项目',
            'filter.scopeRoot': '仅项目外',
            'filter.statusAll': '全部状态',
            'filter.statusActive': '仅未归档',
            'filter.statusArchived': '仅已归档',
            'filter.timeUpdate': '按更新时间',
            'filter.timeCreate': '按创建时间',
            'filter.dateTo': '至',
            'filter.exportAll': '全部导出状态',
            'filter.exportUnexported': '仅未导出',
            'filter.exportExported': '仅已导出',
            'status.loadingList': '正在加载列表...',
            'status.listSummary': '共 {total} 条，当前筛选 {filtered} 条，显示 {visible} 条，已选 {selected} 条',
            'status.noMatches': '没有匹配的对话。',
            'status.loadFailed': '加载失败: {message}',
            'status.fetchingOrphanConversations': '获取项目外对话...',
            'status.rootProgress': '根目录 ({current}/{total})',
            'status.fetchingProjectList': '获取项目列表...',
            'status.project': '项目: {title}',
            'status.projectProgress': '{title}... ({current}/{total})',
            'status.generatingZip': '生成 ZIP 文件...',
            'status.refreshListHint': '强制全量刷新对话列表（忽略本地快照）',
            'status.listFromCache': '列表来自本地快照（{time}），远端未变',
            'status.parsingZipCount': '解析 ZIP {current}/{total}...',
            'status.scanningLocalArchive': '正在扫描本地归档目录...',
            'status.syncPreparing': '正在准备目录同步...',
            'status.syncingConversation': '正在同步 {current}/{total}：{title}',
            'status.rootPage': '项目外对话 ({state} p{page})',
            'status.active': 'Active',
            'status.archived': 'Archived',
            'status.batchPause': '分批暂停中：剩余 {sec} 秒...',
            'status.retryPause': '网络异常，暂停 {sec} 秒后重试...',
            'picker.timeCreated': '创建',
            'picker.timeUpdated': '更新',
            'picker.unknownTime': '未知',
            'picker.projectTag': '项目: {title}',
            'picker.archivedTag': '已归档',
            'picker.exportedTag': '已导出',
            'alert.accessTokenUnavailable': '无法获取 Access Token。请刷新页面或打开任意一个对话后再试。',
            'alert.exportCompletedWithFailures': '导出完成，但有 {count} 个对话失败（已跳过）：\n\n{list}',
            'alert.exportSuccess': '导出完成！',
            'alert.exportFailed': '导出失败: {message}。详情请查看控制台（F12 -> Console）。',
            'alert.noProjectConversations': '未找到项目空间对话。',
            'alert.projectExportFailed': '导出项目空间失败: {message}',
            'alert.invalidWorkspaceId': '请选择或输入一个有效的 Team Workspace ID！',
            'alert.batchLimit': '当前待导出 {total} 条，超过单次上限 {limit} 条。\n将按上限拆分为 {batches} 批全部导出，是否继续？',
            'alert.allExported': '选中的对话全部已经导出过了，无需重复下载。',
            'alert.noSelection': '未选中任何对话。',
            'alert.exportCancelled': '已取消导出。已下载完成的批次会计入已导出记录，其余可稍后续传。',
            'alert.storageQuotaExceeded': '本地导出记录保存失败（存储空间不足）。\n请先到「清空已导出记录」清理旧记录，避免进度丢失。',
            'alert.exportHistoryCleared': '已清空本地已导出记录。\n注意：这只是清除记忆，你电脑里已经下载的 ZIP 文件不会被删除。',
            'alert.exportHistorySaved': '已导出历史清单（JSON）。请妥善保存，记录丢失时用「导入恢复」还原。',
            'alert.importHistoryOk': '已导入备份：{count} 条已导出 + {pending} 条待确认。',
            'alert.importZipsOk': '已解析 {zips} 个 ZIP，累计登记 {count} 条对话为已导出。',
            'alert.syncUnsupported': '当前浏览器不支持直接目录同步（File System Access API）。请使用较新的 Chromium / Edge 浏览器。',
            'alert.syncNoChanges': '没有发现新增或发生变化的对话。',
            'error.importHistoryInvalid': '备份文件无效，不是本工具的已导出清单。',
            'confirm.clearExportedHistory': '确定清空已导出记录？（仅清除记忆，不删除本地 ZIP 文件）',
            'confirm.exportAll': '即将导出 {mode} 下的全部对话。\n将按每批 {limit} 条自动分批，中间随机暂停。\n是否继续？',
            'confirm.cancelExport': '确定要停止导出吗？已成功下载的批次会计入已导出记录。',
            'confirm.scheduledExport': 'Chrome 扩展请求导出 {mode} 对话（来源: {source}）。是否开始？',
            'error.deviceIdUnavailable': '无法获取 oai-device-id，请确保已登录并刷新页面。',
            'error.projectSpaceListFailed': '获取项目空间列表失败 ({status})',
            'error.projectConversationListFailed': '列举项目对话列表失败 ({status})',
            'error.rootConversationListFailed': '列举项目外对话列表失败 ({status})',
            'error.conversationListFailed': '列举对话列表失败 ({status})',
            'error.projectSpaceConversationListFailed': '列举项目空间对话列表失败 ({status})',
            'error.conversationDetailFailed': '获取对话详情失败 conv {id} ({status})',
            'error.fileDownloadUrlFailed': '文件下载链接获取失败 ({status})',
            'error.imageDownloadFailed': '图片下载失败 ({status})',
            'error.fileDownloadFailed': '文件下载失败 ({status})',
            'error.noDownloadUrl': '没有可用下载链接',
            'settings.speed': '速度档位',
            'settings.maxBatch': '单次上限',
            'settings.pauseRange': '分批暂停（秒）'
        }
    };

    function makeTraditionalChineseScriptLocale(source) {
        const replacements = [
            ['导出', '匯出'], ['导入', '匯入'], ['选择', '選擇'], ['对话', '對話'], ['设置', '設定'],
            ['关闭', '關閉'], ['打开', '開啟'], ['边栏', '邊欄'], ['项目', '項目'], ['团队', '團隊'],
            ['空间', '空間'], ['个人', '個人'], ['检测', '偵測'], ['多个', '多個'], ['请输入', '請輸入'],
            ['输入', '輸入'], ['粘贴', '貼上'], ['标题', '標題'], ['范围', '範圍'], ['状态', '狀態'],
            ['归档', '封存'], ['创建', '建立'], ['更新', '更新'], ['清空', '清除'], ['加载', '載入'],
            ['列表', '清單'], ['筛选', '篩選'], ['显示', '顯示'], ['选中', '選取'], ['匹配', '符合'],
            ['时间', '時間'], ['未知', '未知'], ['全部', '全部'], ['取消', '取消'], ['返回', '返回'],
            ['完成', '完成'], ['错误', '錯誤'], ['未命名', '未命名'], ['文件', '檔案'], ['获取', '取得'],
            ['根目录', '根目錄'], ['生成', '產生'], ['失败', '失敗'], ['跳过', '略過'], ['无法', '無法'],
            ['刷新', '重新整理'], ['页面', '頁面'], ['任意', '任一'], ['成功', '成功'], ['图片', '圖片'],
            ['下载', '下載'], ['链接', '連結'], ['没有', '沒有'], ['可用', '可用'], ['详情', '詳細資訊'],
            ['控制台', '主控台'], ['发生', '發生'], ['严重', '嚴重'], ['自动', '自動'], ['列举', '列出'],
            ['有效', '有效'], ['请求', '要求'], ['来源', '來源'], ['开始', '開始'], ['确保', '確保'],
            ['登录', '登入'], ['侧边栏', '側邊欄'], ['预览', '預覽'], ['会话', '對話'], ['浏览器', '瀏覽器'],
            ['当前', '目前'], ['剩余', '剩餘'], ['仅', '僅'], ['按', '依'], ['个', '個'], ['条', '則'],
            ['请', '請'], ['这个', '這個'], ['一个', '一個'], ['已导出', '已匯出'], ['分批', '分批'],
            ['暂停', '暫停'], ['速度', '速度'], ['档位', '檔位'], ['上限', '上限'], ['确定', '確定'], ['吗', '嗎'],
            ['备份', '備份'], ['清单', '清單'], ['恢复', '還原']
        ];
        const converted = {};
        Object.entries(source).forEach(([key, value]) => {
            let text = value;
            replacements.forEach(([from, to]) => {
                text = text.split(from).join(to);
            });
            converted[key] = text;
        });
        return converted;
    }
    SCRIPT_LOCALES['zh-Hant'] = makeTraditionalChineseScriptLocale(SCRIPT_LOCALES['zh-Hans']);

    function normalizeScriptLocale(code) {
        return String(code || '').trim().replace(/_/g, '-');
    }

    function detectScriptLocale(languages = null) {
        const provided = Array.isArray(languages) ? languages : languages ? [languages] : null;
        const nav = window.navigator || (typeof navigator !== 'undefined' ? navigator : null);
        const candidates = provided || [
            ...(Array.isArray(nav?.languages) ? nav.languages : []),
            nav?.language,
            document.documentElement?.lang
        ].filter(Boolean);
        const normalized = candidates.map(normalizeScriptLocale).filter(Boolean);

        // 按浏览器给出的语言优先级逐项归一化。
        // 不能先扫描“精确 key”再扫描映射，否则 ['zh-CN', 'en-US'] 在内部 key
        // 从 zh-CN 改为 zh-Hans 后，会错误地先命中后面的 en-US。
        for (const code of normalized) {
            if (SCRIPT_LOCALES[code]) return code;
            const lower = code.toLowerCase();
            if (['zh-tw', 'zh-hk', 'zh-mo', 'zh-hant'].some(locale => lower === locale || lower.startsWith(`${locale}-`))) return 'zh-Hant';
            if (lower === 'zh' || lower.startsWith('zh-')) return 'zh-Hans';
            if (lower === 'en' || lower.startsWith('en-')) return 'en-US';
        }
        return SCRIPT_FALLBACK_LOCALE;
    }

    const SCRIPT_LOCALE_CODE = detectScriptLocale();
    function getScriptTranslation(key, vars = {}, localeCode = SCRIPT_LOCALE_CODE) {
        const locale = SCRIPT_LOCALES[localeCode] || SCRIPT_LOCALES[SCRIPT_FALLBACK_LOCALE];
        const fallback = SCRIPT_LOCALES[SCRIPT_FALLBACK_LOCALE];
        const template = locale[key] ?? fallback[key] ?? key;
        return String(template).replace(/\{(\w+)\}/g, (_, name) => (
            Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : `{${name}}`
        ));
    }
    const t = getScriptTranslation;

    // ======================== 网络拦截 ========================
    (function interceptNetwork() {
        const rawFetch = window.fetch;
        window.fetch = async function (resource, options) {
            tryCaptureToken(options?.headers);
            if (options?.headers?.['ChatGPT-Account-Id']) {
                const id = options.headers['ChatGPT-Account-Id'];
                if (id && !capturedWorkspaceIds.has(id)) {
                    console.log('🎯 [Fetch] 捕获到 Workspace ID:', id);
                    capturedWorkspaceIds.add(id);
                }
            }
            return rawFetch.apply(this, arguments);
        };
        const rawOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function () {
            this.addEventListener('readystatechange', () => {
                if (this.readyState === 4) {
                    try {
                        tryCaptureToken(this.getRequestHeader('Authorization'));
                        const id = this.getRequestHeader('ChatGPT-Account-Id');
                        if (id && !capturedWorkspaceIds.has(id)) {
                            console.log('🎯 [XHR] 捕获到 Workspace ID:', id);
                            capturedWorkspaceIds.add(id);
                        }
                    } catch (_) {}
                }
            });
            return rawOpen.apply(this, arguments);
        };
    })();

    function tryCaptureToken(header) {
        if (!header) return;
        const h = typeof header === 'string' ? header : header instanceof Headers ? header.get('Authorization') : header.Authorization || header.authorization;
        if (h?.startsWith('Bearer ')) {
            const token = h.slice(7);
            if (token && token.toLowerCase() !== 'dummy') accessToken = token;
        }
    }

    async function ensureAccessToken(force = false) {
        if (!force && accessToken) return accessToken;
        try {
            const session = await (await fetch('/api/auth/session?unstable_client=true')).json();
            if (session.accessToken) {
                accessToken = session.accessToken;
                return accessToken;
            }
        } catch (_) {}
        alert(t('alert.accessTokenUnavailable'));
        return null;
    }

    // 401/403 令牌失效时重新获取（并发去重，只刷新一次）
    let tokenRefreshInFlight = null;
    async function refreshAccessTokenOnce() {
        if (!tokenRefreshInFlight) {
            tokenRefreshInFlight = (async () => {
                accessToken = null;
                const token = await ensureAccessToken(true);
                if (token) console.log('[令牌] 已重新获取 Access Token');
                return token;
            })().finally(() => { tokenRefreshInFlight = null; });
        }
        return tokenRefreshInFlight;
    }

    function isAuthStatus(status) {
        return status === 401 || status === 403;
    }

    // 从错误对象/错误消息中提取 HTTP 状态码（替代脆弱的字符串匹配）
    function errorStatus(err) {
        if (err && typeof err.status === 'number') return err.status;
        const m = String(err && err.message || '').match(/\((\d{3})\)/);
        return m ? Number(m[1]) : 0;
    }

    // 构造携带 HTTP 状态码的错误，便于上层识别 401/403/429 等
    function createStatusError(message, status) {
        const err = new Error(message);
        err.status = status;
        return err;
    }

    function cancelExport() {
        exportAbortRequested = true;
        console.log('[取消] 已请求取消导出，将在当前条目/批次结束后生效');
    }

    // ======================== 通用辅助 ========================
    const MAX_SAFE_NAME_LENGTH = 120;
    const MAX_SAFE_ID_LENGTH = 64;
    const MAX_IMAGE_ID_LENGTH = 80;
    const LOCAL_FILE_REF_PREFIX = 'chatgpt-file:';
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const jitter = () => BASE_DELAY + Math.random() * JITTER;

    const sanitizeFilename = (name, fallback = 'untitled', maxLength = MAX_SAFE_NAME_LENGTH) => {
        const fallbackName = String(fallback || 'untitled').replace(/[\x00-\x1f\x7f]/g, '').replace(/[\/\\?%*:|"<>]/g, '-').trim() || 'untitled';
        let safe = String(name ?? '').replace(/[\x00-\x1f\x7f]/g, '').replace(/[\/\\?%*:|"<>]/g, '-').replace(/\s+/g, ' ').trim().replace(/^[. -]+|[. -]+$/g, '');
        if (!safe) safe = fallbackName;
        if (safe.length > maxLength) safe = safe.slice(0, maxLength).replace(/[. -]+$/g, '');
        return safe || fallbackName;
    };
    const sanitizeImageFilenamePart = (value, fallback = 'image') => {
        const safe = sanitizeFilename(value, fallback, MAX_IMAGE_ID_LENGTH).replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/[-.]{2,}/g, '-').replace(/^[.-]+|[.-]+$/g, '');
        return safe || fallback;
    };
    const splitFilename = (filename) => {
        const idx = filename.lastIndexOf('.');
        if (idx <= 0 || idx === filename.length - 1) return { stem: filename, ext: '' };
        return { stem: filename.slice(0, idx), ext: filename.slice(idx) };
    };
    const makeUniqueZipFilename = (filename, registry, scopeKey = '') => {
        if (!registry) return filename;
        const key = scopeKey || '';
        if (!registry.has(key)) registry.set(key, new Set());
        const used = registry.get(key);
        let candidate = filename;
        if (used.has(candidate)) {
            const { stem, ext } = splitFilename(filename);
            let index = 2;
            do { candidate = `${stem} (${index++})${ext}`; } while (used.has(candidate));
        }
        used.add(candidate);
        return candidate;
    };
    const normalizeEpochSeconds = (value) => {
        if (!value) return 0;
        if (typeof value === 'number' && Number.isFinite(value)) return value > 1e12 ? Math.floor(value / 1000) : value;
        if (typeof value === 'string') {
            const parsed = Date.parse(value);
            if (!Number.isNaN(parsed)) return Math.floor(parsed / 1000);
        }
        return 0;
    };
    const formatTimestamp = (value) => {
        const seconds = normalizeEpochSeconds(value);
        if (!seconds) return '';
        const date = new Date(seconds * 1000);
        return Number.isNaN(date.getTime()) ? '' : date.toLocaleString();
    };
    const parseDateInputToEpoch = (value, isEnd = false) => {
        if (!value) return null;
        const parts = value.split('-').map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
        const [year, month, day] = parts;
        const date = isEnd ? new Date(year, month - 1, day, 23, 59, 59, 999) : new Date(year, month - 1, day, 0, 0, 0, 0);
        const epochMs = date.getTime();
        return Number.isNaN(epochMs) ? null : Math.floor(epochMs / 1000);
    };
    function getOaiDeviceId() {
        const match = document.cookie.match(/oai-did=([^;]+)/);
        return match ? match[1] : null;
    }
    function generateUniqueFilename(convData) {
        const convId = convData.conversation_id || '';
        const shortId = convId.includes('-') ? convId.split('-').pop() : (convId || Date.now().toString(36));
        let baseName = convData.title;
        if (!baseName || baseName.trim().toLowerCase() === 'new chat') baseName = t('fallback.untitledConversation');
        const safeBaseName = sanitizeFilename(baseName, t('fallback.untitledConversation'), MAX_SAFE_NAME_LENGTH);
        const safeShortId = sanitizeImageFilenamePart(shortId, 'conversation').slice(0, MAX_SAFE_ID_LENGTH);
        return `${safeBaseName}_${safeShortId}.json`;
    }
    function generateMarkdownFilename(convData) {
        const jsonName = generateUniqueFilename(convData);
        return jsonName.endsWith('.json') ? `${jsonName.slice(0, -5)}.md` : `${jsonName}.md`;
    }

    // ======================== 消息与资源处理（完整保留原逻辑） ========================
    function cleanMessageContent(text) {
        if (!text) return '';
        return text
            .replace(/\uE200cite(?:\uE202turn\d+[a-z_]+\d+)+\uE201/gi, '')
            .replace(/[\uE200-\uE202]?cite(?:[\uE200-\uE202]?turn\d+[a-z_]+\d+)+[\uE200-\uE202]?/gi, '')
            .trim();
    }

    function processContentReferences(text, contentReferences) {
        if (!text || !Array.isArray(contentReferences) || contentReferences.length === 0) return { text, footnotes: [] };
        const references = contentReferences.filter(ref => ref && typeof ref.matched_text === 'string' && ref.matched_text.length > 0);
        if (references.length === 0) return { text, footnotes: [] };

        const getReferenceInfo = (ref) => {
            const file = inspectReferenceFile(ref);
            if (file) {
                const label = file.label || file.filename || t('fallback.file');
                return { url: `${LOCAL_FILE_REF_PREFIX}${encodeURIComponent(file.key)}`, title: label, label, fileKey: file.key };
            }
            const item = Array.isArray(ref.items) ? ref.items[0] : null;
            const url = item?.url || (Array.isArray(ref.safe_urls) ? ref.safe_urls[0] : '') || '';
            const title = item?.title || '';
            let label = item?.attribution || '';
            if (!label && typeof ref.alt === 'string') {
                const match = ref.alt.match(/\[([^\]]+)\]\([^)]+\)/);
                if (match) label = match[1];
            }
            if (!label) label = title || url;
            return { url, title, label };
        };

        const footnotes = [];
        const footnoteIndexByKey = new Map();
        const citationRefs = references
            .filter(ref => ref.type === 'grouped_webpages' || inspectReferenceFile(ref))
            .sort((a, b) => {
                const aIdx = Number.isFinite(a.start_idx) ? a.start_idx : Number.MAX_SAFE_INTEGER;
                const bIdx = Number.isFinite(b.start_idx) ? b.start_idx : Number.MAX_SAFE_INTEGER;
                return aIdx - bIdx;
            });

        citationRefs.forEach(ref => {
            const info = getReferenceInfo(ref);
            if (!info.url) return;
            const key = `${info.url}|${info.title}`;
            if (footnoteIndexByKey.has(key)) return;
            const index = footnotes.length + 1;
            footnoteIndexByKey.set(key, index);
            footnotes.push({ index, url: info.url, title: info.title, label: info.label });
        });

        const sortedByReplacement = references.slice().sort((a, b) => {
            const aIdx = Number.isFinite(a.start_idx) ? a.start_idx : -1;
            const bIdx = Number.isFinite(b.start_idx) ? b.start_idx : -1;
            if (aIdx !== -1 || bIdx !== -1) return bIdx - aIdx;
            return (b.matched_text?.length || 0) - (a.matched_text?.length || 0);
        });

        let output = text;
        sortedByReplacement.forEach(ref => {
            if (!ref?.matched_text || ref.type === 'sources_footnote') return;
            let replacement = '';
            if (ref.type === 'grouped_webpages' || inspectReferenceFile(ref)) {
                const info = getReferenceInfo(ref);
                if (info.url) {
                    const key = `${info.url}|${info.title}`;
                    const index = footnoteIndexByKey.get(key);
                    replacement = index ? `([${markdownLinkLabel(info.label)}][${index}])` : (ref.alt || '');
                } else replacement = ref.alt || '';
            } else replacement = ref.alt || '';

            if (Number.isFinite(ref.start_idx) && Number.isFinite(ref.end_idx)) {
                if (output.slice(ref.start_idx, ref.end_idx) === ref.matched_text) {
                    output = output.slice(0, ref.start_idx) + replacement + output.slice(ref.end_idx);
                    return;
                }
            }
            output = output.split(ref.matched_text).join(replacement);
        });
        return { text: output, footnotes };
    }

    function inspectImageAsset(asset) {
        if (!asset || typeof asset !== 'object') return null;
        const pointer = asset.asset_pointer || asset.file_id || asset.id || null;
        if (!pointer) return null;
        let label = asset.disposition_label || asset.alt_text || asset.alt || '';
        if (!label && asset.metadata?.dalle?.prompt) label = asset.metadata.dalle.prompt;
        if (!label && asset.metadata?.generation?.serialization_title) label = asset.metadata.generation.serialization_title;
        return {
            asset_pointer: pointer,
            url: asset.url || asset.download_url || asset.dalle_url || null,
            content_type: asset.content_type || asset.mime_type || null,
            file_id: asset.file_id || null,
            dispositionLabel: (typeof label === 'string' ? label : 'image').slice(0, 200)
        };
    }

    function isImageContentType(value) {
        const text = String(value || '').toLowerCase();
        return text === 'image_asset' || text === 'image_asset_pointer' || text.startsWith('image/') || text.includes('image_asset');
    }

    function imageReferenceKeys(image) {
        if (!image || typeof image !== 'object') return [];
        return [image.asset_pointer, image.file_id, image.url, image.download_url, normalizeAssetId(image.asset_pointer || image.file_id || image.url || image.download_url || '')].filter(Boolean);
    }

    function addImageIfMissing(images, image, source) {
        if (!image) return;
        const incoming = { ...image, source };
        const keys = imageReferenceKeys(incoming);
        const existingIndex = images.findIndex(existing => {
            const existingKeys = imageReferenceKeys(existing);
            return existingKeys.some(key => keys.includes(key));
        });
        if (existingIndex >= 0) {
            const existing = images[existingIndex];
            const sources = [existing.source, source].flatMap(v => String(v || '').split(',')).filter(Boolean).filter((v, i, l) => l.indexOf(v) === i);
            images[existingIndex] = { ...existing };
            ['asset_pointer', 'url', 'download_url', 'content_type', 'file_id', 'dispositionLabel', 'localUrl', 'localPath', 'filename'].forEach(field => {
                if (!images[existingIndex][field] && incoming[field]) images[existingIndex][field] = incoming[field];
            });
            images[existingIndex].source = sources.join(',');
            return;
        }
        images.push(incoming);
    }

    function inspectFileAttachment(att) {
        if (!att || typeof att !== 'object') return null;
        const nested = att.file && typeof att.file === 'object' ? att.file : {};
        const contentType = att.mime_type || att.content_type || att.type || nested.mime_type || nested.content_type || nested.type || '';
        if (isImageContentType(contentType) || att.image_asset || nested.image_asset) return null;
        const fileId = att.file_id || nested.file_id || att.id || nested.id || att.asset_pointer || nested.asset_pointer || '';
        const url = att.download_url || att.url || nested.download_url || nested.url || '';
        const rawName = att.name || att.file_name || att.filename || att.title || att.display_name || nested.name || nested.file_name || nested.filename || nested.title || '';
        const contentTypeText = String(contentType || '').toLowerCase();
        const hasFileSignal = contentTypeText.includes('file') || contentTypeText.includes('attachment') || (contentTypeText && contentTypeText !== 'text' && contentTypeText !== 'multimodal_text') || Boolean(att.file || nested.file || rawName);
        if (!fileId && !url && !(rawName && hasFileSignal)) return null;
        const fallbackName = normalizeAssetId(fileId || url) || 'attachment';
        const filename = sanitizeFilename(rawName || fallbackName, fallbackName, MAX_SAFE_NAME_LENGTH);
        return { key: fileId || url || rawName || filename, file_id: fileId, url, download_url: att.download_url || nested.download_url || '', filename, label: rawName || filename, content_type: contentType, size: att.size || nested.size || null };
    }

    function addFileIfMissing(files, file, source) {
        if (!file) return;
        const keys = fileReferenceKeys(file);
        const existingIndex = files.findIndex(existing => {
            const existingKeys = fileReferenceKeys(existing);
            return existingKeys.some(key => keys.includes(key));
        });
        if (existingIndex >= 0) {
            files[existingIndex] = mergeFileAttachment(files[existingIndex], file, source);
            return;
        }
        files.push({ ...file, aliases: keys, source });
    }

    function mergeFileAttachment(existing, incoming, source) {
        const aliases = [...fileReferenceKeys(existing), ...fileReferenceKeys(incoming)].filter(Boolean).filter((v, i, l) => l.indexOf(v) === i);
        const merged = { ...existing, aliases };
        ['key', 'file_id', 'url', 'download_url', 'filename', 'label', 'content_type', 'size', 'path', 'file_path', 'sandbox_path'].forEach(field => {
            if (!merged[field] && incoming[field]) merged[field] = incoming[field];
        });
        merged.source = [existing.source, source].filter(Boolean).filter((v, i, l) => l.indexOf(v) === i).join(',');
        return merged;
    }

    function inspectReferenceFile(ref) {
        if (!ref || typeof ref !== 'object') return null;
        const refType = String(ref.type || ref.content_type || ref.mime_type || '').toLowerCase();
        if (refType === 'grouped_webpages' || refType === 'sources_footnote' || refType.includes('webpage')) return null;
        const nameOnlyFile = (item) => {
            const explicitName = item?.name || item?.file_name || item?.filename || item?.title || item?.display_name || '';
            const pathName = item?.path || item?.file_path || item?.sandbox_path || item?.matched_text || '';
            const rawName = explicitName || String(pathName).split(/[\\/]/).filter(Boolean).pop() || pathName;
            const key = item?.file_id || item?.asset_pointer || item?.url || item?.download_url || item?.path || item?.file_path || item?.sandbox_path || rawName;
            if (!key && !rawName) return null;
            const fallbackName = normalizeAssetId(key) || 'attachment';
            const filename = sanitizeFilename(rawName || fallbackName, fallbackName, MAX_SAFE_NAME_LENGTH);
            return { key: key || filename, file_id: item?.file_id || item?.asset_pointer || '', url: item?.url || '', download_url: item?.download_url || '', filename, label: rawName || filename, content_type: item?.mime_type || item?.content_type || item?.type || '', size: item?.size || null };
        };
        const hasFileSignal = refType.includes('file') || refType.includes('sandbox') || refType.includes('attachment') || Boolean(ref.file_id || ref.asset_pointer || ref.file || ref.file_path || ref.sandbox_path);
        const direct = inspectFileAttachment(ref);
        if (direct && hasFileSignal) return direct;
        const fallback = hasFileSignal ? nameOnlyFile(ref) : null;
        if (fallback) return fallback;
        const items = Array.isArray(ref.items) ? ref.items : [];
        for (const item of items) {
            const itemType = String(item?.type || item?.content_type || item?.mime_type || '').toLowerCase();
            const itemHasFileSignal = itemType.includes('file') || itemType.includes('sandbox') || itemType.includes('attachment') || Boolean(item?.file_id || item?.asset_pointer || item?.file || item?.file_path || item?.sandbox_path);
            const inspected = inspectFileAttachment(item);
            if (inspected && itemHasFileSignal) return inspected;
            const itemFallback = itemHasFileSignal ? nameOnlyFile(item) : null;
            if (itemFallback) return itemFallback;
        }
        return null;
    }

    function extractConversationMessages(convData) {
        const mapping = convData?.mapping;
        if (!mapping) return [];
        const messages = [];
        const mappingKeys = Object.keys(mapping);
        const rootId = mapping['client-created-root'] ? 'client-created-root' : mappingKeys.find(id => !mapping[id]?.parent) || mappingKeys[0];
        const visited = new Set();

        const collectParts = (content) => {
            let textParts = [];
            const images = [];
            const files = [];
            const contentType = content?.content_type;
            const parts = Array.isArray(content?.parts) ? content.parts : [];

            const handleImagePart = (imgAsset, source) => {
                const inspected = inspectImageAsset(imgAsset);
                if (!inspected) return;
                addImageIfMissing(images, inspected, source);
            };
            const handleFilePart = (fileAsset, source) => {
                const inspected = inspectFileAttachment(fileAsset?.file || fileAsset);
                if (!inspected) return;
                addFileIfMissing(files, inspected, source);
                textParts.push(`<!-- file:${encodeURIComponent(inspected.key)} -->`);
            };

            const isImageContentTypeLocal = (ct) => ct === 'image_asset' || ct === 'image_asset_pointer';
            const isFileContentType = (ct) => {
                const text = String(ct || '').toLowerCase();
                return text.includes('file') || text.includes('attachment');
            };

            if (contentType === 'text') {
                parts.forEach(part => collectTextPart(part, textParts, images, files));
            } else if (isImageContentTypeLocal(contentType)) {
                handleImagePart(content.image_asset || content, 'image_asset');
            } else if (isFileContentType(contentType)) {
                handleFilePart(content.file || content, 'file_asset');
            } else if (contentType === 'multimodal_text') {
                parts.forEach(part => {
                    if (typeof part === 'string') collectTextPart(part, textParts, images, files);
                    else if (part && isImageContentTypeLocal(part.content_type || part.type)) handleImagePart(part.image_asset || part, 'multimodal_text');
                    else if (part && isFileContentType(part.content_type || part.type)) handleFilePart(part.file || part, 'multimodal_text');
                    else if (part && typeof part === 'object' && part.text) collectTextPart(part.text, textParts, images, files);
                    else collectTextPart(part, textParts, images, files);
                });
            } else if (contentType && Array.isArray(parts) && parts.length) {
                parts.forEach(part => collectTextPart(part, textParts, images, files));
            }
            const rawText = textParts.filter(Boolean).join('\n');
            return { rawText, images, files };
        };

        const collectTextPart = (part, textParts, images, files) => {
            if (typeof part === 'string') { textParts.push(part); return; }
            if (part && typeof part === 'object') {
                const inspectedFile = inspectFileAttachment(part.file || part);
                if (inspectedFile) {
                    addFileIfMissing(files, inspectedFile, 'text_part');
                    textParts.push(`<!-- file:${encodeURIComponent(inspectedFile.key)} -->`);
                    return;
                }
                if (typeof part.text === 'string') textParts.push(part.text);
                const isImg = part.content_type === 'image_asset' || part.content_type === 'image_asset_pointer' || part.image_asset;
                if (isImg) {
                    const inspected = inspectImageAsset(part.image_asset || part);
                    if (inspected) {
                        textParts.push(`<!-- image:${inspected.asset_pointer} -->`);
                        if (images) addImageIfMissing(images, inspected, 'text_part');
                    }
                }
            }
        };

        const traverse = (nodeId) => {
            if (!nodeId || visited.has(nodeId)) return;
            visited.add(nodeId);
            const node = mapping[nodeId];
            if (!node) return;
            const msg = node.message;
            if (msg) {
                const author = msg.author?.role;
                const isHidden = msg.metadata?.is_visually_hidden_from_conversation || msg.metadata?.is_contextual_answers_system_message;
                if (author && author !== 'system' && !isHidden) {
                    const content = msg.content;
                    const { rawText = '', images = [], files: partFiles = [] } = content ? (collectParts(content) || {}) : {};
                    const files = partFiles.slice();
                    if (Array.isArray(msg.metadata?.attachments)) {
                        msg.metadata.attachments.forEach(att => {
                            if (!att) return;
                            if (isImageContentType(att.content_type || att.type || att.mime_type)) {
                                const inspected = inspectImageAsset(att.image_asset || att);
                                if (inspected) addImageIfMissing(images, inspected, 'attachment');
                                return;
                            }
                            const file = inspectFileAttachment(att);
                            addFileIfMissing(files, file, 'attachment');
                        });
                    }
                    const contentReferences = msg.metadata?.content_references || [];
                    if (Array.isArray(contentReferences)) {
                        contentReferences.forEach(ref => {
                            const file = inspectReferenceFile(ref);
                            if (!file) return;
                            addFileIfMissing(files, file, 'content_reference');
                        });
                    }
                    let processedText = rawText;
                    let footnotes = [];
                    if (Array.isArray(contentReferences) && contentReferences.length > 0) {
                        const processed = processContentReferences(rawText, contentReferences);
                        processedText = processed.text;
                        footnotes = processed.footnotes;
                    }
                    const cleaned = cleanMessageContent(processedText);
                    const hasText = cleaned && cleaned.length > 0;
                    const hasImages = images.length > 0;
                    const hasFiles = files.length > 0;
                    if (hasText || hasImages || hasFiles) {
                        messages.push({
                            messageId: msg.id || nodeId,
                            role: author,
                            content: cleaned || '',
                            create_time: msg.create_time || null,
                            footnotes,
                            images,
                            files
                        });
                    }
                }
            }
            if (Array.isArray(node.children)) node.children.forEach(childId => traverse(childId));
        };

        if (rootId) traverse(rootId);
        else mappingKeys.forEach(traverse);
        return messages;
    }

    function markdownLinkLabel(value) {
        return String(value || 'file').replace(/([\\\[\]])/g, '\\$1');
    }
    function markdownPath(path) {
        return String(path || '').split('/').map(part => encodeURIComponent(part)).join('/');
    }
    function localFileRefKey(url) {
        const value = String(url || '');
        if (!value.startsWith(LOCAL_FILE_REF_PREFIX)) return '';
        try { return decodeURIComponent(value.slice(LOCAL_FILE_REF_PREFIX.length)); } catch (_) { return value.slice(LOCAL_FILE_REF_PREFIX.length); }
    }
    function resolveFootnoteUrl(url, attachmentFiles) {
        const key = localFileRefKey(url);
        if (!key) return url;
        const file = localFileRefCandidates(key).map(candidate => attachmentFiles?.get(candidate)).find(Boolean);
        return file ? markdownPath(`files/${file.filename}`) : '';
    }
    function localFileRefCandidates(key) {
        const candidates = [key, normalizeAssetId(key), sanitizeFilename(key, key, MAX_SAFE_NAME_LENGTH), sanitizeFilename(String(key).split(/[\\/]/).filter(Boolean).pop() || key, key, MAX_SAFE_NAME_LENGTH)].filter(Boolean);
        return candidates.filter((c, i) => candidates.indexOf(c) === i);
    }
    function fileReferenceKeys(file) {
        if (!file || typeof file !== 'object') return [];
        return [file.key, file.file_id, file.url, file.download_url, file.path, file.file_path, file.sandbox_path, file.filename, ...(Array.isArray(file.aliases) ? file.aliases : [])].filter(Boolean);
    }

    function convertConversationToMarkdown(convData) {
        const imageFiles = (arguments.length > 1 && arguments[1] instanceof Map) ? arguments[1] : null;
        const attachmentFiles = (arguments.length > 2 && arguments[2] instanceof Map) ? arguments[2] : null;
        const messages = extractConversationMessages(convData);
        if (messages.length === 0) return '# Conversation\nNo visible user or assistant messages were exported.\n';
        const mdLines = [];
        messages.forEach((msg) => {
            const roleLabel = msg.role === 'user' ? '# User' : '# Assistant';
            mdLines.push(roleLabel);
            let body = msg.content || '';
            const referenced = new Set();
            if (imageFiles && Array.isArray(msg.images) && msg.images.length > 0) {
                msg.images.forEach(img => {
                    const entry = imageFiles.get(img.asset_pointer);
                    if (!entry) return;
                    const placeholder = `<!-- image:${img.asset_pointer} -->`;
                    const mdImg = `\n\n![${entry.dispositionLabel || 'image'}](images/${entry.filename})\n`;
                    if (body.includes(placeholder)) {
                        body = body.split(placeholder).join(mdImg);
                        referenced.add(img.asset_pointer);
                    }
                });
            }
            const referencedFileEntries = new Set();
            if (Array.isArray(msg.files) && msg.files.length > 0) {
                msg.files.forEach(file => {
                    const entry = attachmentFiles ? fileReferenceKeys(file).map(key => attachmentFiles.get(key)).find(Boolean) : null;
                    const replacement = entry ? `\n\n[${markdownLinkLabel(entry.label || entry.filename)}](${markdownPath(`files/${entry.filename}`)})\n\n` : `\n\n${markdownLinkLabel(file.label || file.filename || t('fallback.file'))}\n\n`;
                    fileReferenceKeys(file).forEach(key => {
                        const placeholder = `<!-- file:${encodeURIComponent(key)} -->`;
                        if (body.includes(placeholder)) {
                            body = body.split(placeholder).join(replacement);
                            if (entry) referencedFileEntries.add(entry);
                        }
                    });
                });
            }
            mdLines.push(body);
            if (imageFiles && Array.isArray(msg.images) && msg.images.length > 0) {
                const leftover = msg.images.filter(img => !referenced.has(img.asset_pointer));
                if (leftover.length > 0) {
                    mdLines.push('');
                    mdLines.push(`<!-- 生成图片 (${leftover.length}) -->`);
                    leftover.forEach(img => {
                        const entry = imageFiles.get(img.asset_pointer);
                        if (!entry) return;
                        mdLines.push(`![${entry.dispositionLabel || 'image'}](images/${entry.filename})`);
                    });
                }
            }
            if (attachmentFiles && Array.isArray(msg.files) && msg.files.length > 0) {
                const referencedFiles = new Set((msg.footnotes || []).map(note => localFileRefKey(note.url)).filter(Boolean).flatMap(key => localFileRefCandidates(key)).map(key => attachmentFiles.get(key)).filter(Boolean));
                const linkedFiles = msg.files.map(file => fileReferenceKeys(file).map(key => attachmentFiles.get(key)).find(Boolean)).filter(Boolean).filter(file => !referencedFiles.has(file) && !referencedFileEntries.has(file));
                if (linkedFiles.length > 0) {
                    mdLines.push('');
                    mdLines.push(`<!-- 附件 (${linkedFiles.length}) -->`);
                    linkedFiles.forEach(file => {
                        mdLines.push(`- [${markdownLinkLabel(file.label || file.filename)}](${markdownPath(`files/${file.filename}`)})`);
                    });
                }
            }
            if (Array.isArray(msg.footnotes) && msg.footnotes.length > 0) {
                mdLines.push('');
                msg.footnotes.slice().sort((a, b) => a.index - b.index).forEach(note => {
                    const url = resolveFootnoteUrl(note.url, attachmentFiles);
                    if (!url) return;
                    const title = note.title ? ` "${note.title}"` : '';
                    mdLines.push(`[${note.index}]: ${url}${title}`);
                });
            }
            mdLines.push('');
        });
        return mdLines.join('\n').trim() + '\n';
    }

    function downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        // 延迟释放 URL：大文件下载刚启动就撤销会导致 0 字节或损坏
        setTimeout(() => URL.revokeObjectURL(url), 30000);
    }

    function getExportButton() {
        let btn = document.getElementById('gpt-rescue-btn');
        if (!btn) {
            btn = document.createElement('button');
            btn.id = 'gpt-rescue-btn';
            btn.style.display = 'none';
            btn.textContent = t('button.export');
            document.body.appendChild(btn);
        }
        return btn;
    }

    function makeZipScopeRegistry() {
        return new Map();
    }

    // ======================== 核心导出（自动分批 + 暂停 + 去重） ========================
    async function exportConversations(options = {}) {
        const { mode = 'personal', workspaceId = null, conversationEntries = null, exportType = null, projectTitleForName = null } = options;
        const btn = getExportButton();
        btn.disabled = true;
        exportRunning = true;
        exportAbortRequested = false;

        // 配置快照：导出过程中调整速度/批量不会影响本次运行
        const runCfg = {
            delay: BASE_DELAY,
            jitter: JITTER,
            batch: Math.max(1, MAX_EXPORT_PER_BATCH),
            pauseMin: BATCH_PAUSE_MIN,
            pauseMax: BATCH_PAUSE_MAX
        };
        const runJitter = () => runCfg.delay + Math.random() * runCfg.jitter;
        const randomPauseLocal = () => Math.round((runCfg.pauseMin + Math.random() * (runCfg.pauseMax - runCfg.pauseMin)) * 1000);
        const isAborted = () => exportAbortRequested;

        if (!await ensureAccessToken()) {
            btn.disabled = false;
            btn.textContent = t('button.export');
            exportRunning = false;
            return;
        }

        try {
            let allToProcess = [];

            if (Array.isArray(conversationEntries)) {
                // 空数组不应触发"全量导出"
                if (conversationEntries.length === 0) {
                    alert(t('alert.noSelection'));
                    return;
                }
                const exportedSet = getExportedIds();
                const pendingSet = getPendingIds();
                allToProcess = conversationEntries.filter(entry => !exportedSet.has(entry.id) && !pendingSet.has(entry.id));
                const skipped = conversationEntries.length - allToProcess.length;
                if (skipped > 0) console.log(`[去重] 跳过已导出/待确认 ${skipped} 条，剩余 ${allToProcess.length} 条`);
                if (allToProcess.length === 0) {
                    alert(t('alert.allExported'));
                    return;
                }
            } else {
                btn.textContent = `📂 ${t('status.fetchingOrphanConversations')}`;
                const orphanIds = await collectIds(btn, workspaceId, null);
                const exportedSet = getExportedIds();
                const pendingSet = getPendingIds();
                for (const id of orphanIds) {
                    if (!exportedSet.has(id) && !pendingSet.has(id)) allToProcess.push({ id, title: id });
                }
                btn.textContent = `🔍 ${t('status.fetchingProjectList')}`;
                const projects = await getProjects(workspaceId);
                for (const project of projects) {
                    const projectConvIds = await collectIds(btn, workspaceId, project.id);
                    for (const id of projectConvIds) {
                        if (!exportedSet.has(id) && !pendingSet.has(id)) allToProcess.push({ id, title: id, projectTitle: project.title, projectId: project.id });
                    }
                }
            }

            if (allToProcess.length === 0) {
                alert(t('alert.allExported'));
                return;
            }

            // 自动分批（使用快照中的批次上限）
            const batches = [];
            for (let i = 0; i < allToProcess.length; i += runCfg.batch) {
                batches.push(allToProcess.slice(i, i + runCfg.batch));
            }

            const failedConversations = [];
            let consecutiveFails = 0;
            const selectionType = exportType || (Array.isArray(conversationEntries) && conversationEntries.length > 0 ? 'selected' : 'full');

            for (let b = 0; b < batches.length; b++) {
                if (isAborted()) break;
                const batch = batches[b];
                console.log(`[分批] 开始第 ${b + 1}/${batches.length} 批，共 ${batch.length} 条`);

                // 每批独立 ZIP：避免超大 ZIP 一次性内存打包导致 OOM
                const zip = new JSZip();
                const zipFilenameRegistry = makeZipScopeRegistry();
                const batchOkIds = [];

                for (let i = 0; i < batch.length; i++) {
                    if (isAborted()) break;
                    const entry = batch[i];
                    const label = entry?.title ? String(entry.title).slice(0, 12) : t('fallback.conversation');
                    btn.textContent = `📥 ${label} (${i + 1}/${batch.length}) [批次 ${b + 1}/${batches.length}]`;

                    try {
                        const convData = await getConversation(entry.id, workspaceId);
                        const target = entry?.projectTitle ? zip.folder(sanitizeFilename(entry.projectTitle)) : zip;
                        await exportConversationIntoZip(convData, target, accessToken, zipFilenameRegistry, workspaceId);
                        batchOkIds.push(entry.id);
                        consecutiveFails = 0;
                    } catch (err) {
                        consecutiveFails++;
                        failedConversations.push({ id: entry.id, title: entry.title || t('fallback.unknown'), error: err.message || 'unknown' });
                        console.warn(`⚠️ 对话导出失败 [${entry.title || entry.id}]: ${err.message}`);
                        // 连续失败触发网络保护暂停，时长随失败次数增长
                        if (consecutiveFails >= 3) {
                            const pauseSec = 120 * Math.min(consecutiveFails - 2, 5);
                            console.warn(`[网络保护] 连续失败 ${consecutiveFails} 条，暂停 ${pauseSec} 秒`);
                            for (let s = pauseSec; s > 0 && !isAborted(); s--) {
                                btn.textContent = t('status.retryPause', { sec: s });
                                await sleep(1000);
                            }
                            consecutiveFails = 0;
                        }
                    }
                    await sleep(runJitter());
                }

                // 本批打包下载：先记"待确认"，下载成功后转"已导出"
                if (batchOkIds.length > 0) {
                    markConversationsPending(batchOkIds);
                    let batchDownloaded = false;
                    if (!isAborted()) {
                        btn.textContent = `📦 ${t('status.generatingZip')} [批次 ${b + 1}/${batches.length}]`;
                        for (let genAttempt = 1; genAttempt <= 2 && !batchDownloaded; genAttempt++) {
                            try {
                                const blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
                                const date = new Date().toISOString().slice(0, 10);
                                const time = new Date().toTimeString().slice(0, 5).replace(':', '');
                                downloadFile(blob, buildBatchFilename(mode, workspaceId, projectTitleForName, selectionType, date, time, b + 1, batches.length));
                                batchDownloaded = true;
                            } catch (genErr) {
                                console.warn(`⚠️ 第 ${genAttempt} 次生成/下载批次 ZIP 失败: ${genErr.message}`);
                                if (genAttempt < 2) await sleep(5000);
                            }
                        }
                    }
                    if (batchDownloaded) {
                        markConversationsExported(batchOkIds); // 确认下载成功
                    } else if (isAborted()) {
                        console.log('[取消] 本批已抓取内容保留为"待确认"，下次可续传');
                    } else {
                        batchOkIds.forEach(id => failedConversations.push({ id, title: t('fallback.conversation'), error: 'ZIP 生成/下载失败' }));
                        console.warn('[分批] 批次 ZIP 生成失败，本批对话不会标记为已导出，可重试');
                    }
                }

                if (b < batches.length - 1 && !isAborted()) {
                    const pauseSec = Math.round(randomPauseLocal() / 1000);
                    console.log(`[分批] 暂停 ${pauseSec} 秒后继续下一批`);
                    for (let s = pauseSec; s > 0 && !isAborted(); s--) {
                        btn.textContent = t('status.batchPause', { sec: s });
                        await sleep(1000);
                    }
                }
            }

            if (isAborted()) {
                alert(t('alert.exportCancelled'));
                btn.textContent = `⏹ ${t('button.cancelExport')}`;
                return;
            }

            if (failedConversations.length > 0) {
                const failList = failedConversations.slice(0, 20).map(f => `• ${f.title}: ${f.error}`).join('\n');
                const more = failedConversations.length > 20 ? `\n… 以及另外 ${failedConversations.length - 20} 条` : '';
                alert(`⚠️ ${t('alert.exportCompletedWithFailures', { count: failedConversations.length, list: failList + more })}`);
            } else {
                alert(`✅ ${t('alert.exportSuccess')}`);
            }
            btn.textContent = `✅ ${t('button.done')}`;
        } catch (e) {
            console.error("导出过程中发生严重错误:", e);
            // 列表阶段遇到 401/403：刷新令牌后整体重试一次
            const status = errorStatus(e);
            if (isAuthStatus(status)) {
                console.warn(`[令牌] 列表请求返回 ${status}，重新获取令牌后重试一次...`);
                const refreshed = await refreshAccessTokenOnce();
                if (refreshed && !exportAbortRequested) {
                    exportRunning = false;
                    btn.textContent = t('button.export');
                    await exportConversations(options);
                    return;
                }
            }
            alert(t('alert.exportFailed', { message: e.message }));
            btn.textContent = `⚠️ ${t('button.error')}`;
        } finally {
            exportRunning = false;
            exportAbortRequested = false;
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = t('button.export');
            }, 3000);
        }
    }

    // 分批 ZIP 文件名（多批时带批次号，避免互相覆盖）
    function buildBatchFilename(mode, workspaceId, projectTitleForName, selectionType, date, time, batchIndex, totalBatches) {
        let base = '';
        if (mode === 'project' || projectTitleForName) {
            const pName = sanitizeFilename(projectTitleForName || 'project');
            base = selectionType === 'selected' ? `chatgpt_project_${pName}_selected` : `chatgpt_project_${pName}_backup`;
        } else if (mode === 'team') {
            base = selectionType === 'selected' ? `chatgpt_team_selected_${workspaceId}` : `chatgpt_team_backup_${workspaceId}`;
        } else {
            base = selectionType === 'selected' ? 'chatgpt_personal_selected' : 'chatgpt_personal_backup';
        }
        const batchTag = totalBatches > 1 ? `_batch${batchIndex}of${totalBatches}` : '';
        return `${base}_${date}_${time}${batchTag}.zip`;
    }

    async function startExportProcess(mode, workspaceId, skipConfirm = false) {
        const modeLabel = t(`mode.${mode === 'team' ? 'team' : mode === 'project' ? 'project' : 'personal'}`);
        if (!skipConfirm && !confirm(t('confirm.exportAll', { mode: modeLabel, limit: MAX_EXPORT_PER_BATCH }))) return;
        await exportConversations({ mode, workspaceId });
    }

    async function startProjectSpaceExportProcess(workspaceId = null, skipConfirm = false) {
        try {
            const projectEntries = await listProjectSpaceConversations(workspaceId);
            if (projectEntries.length === 0) {
                alert(t('alert.noProjectConversations'));
                return;
            }
            const modeLabel = t('mode.project');
            if (!skipConfirm && !confirm(t('confirm.exportAll', { mode: modeLabel, limit: MAX_EXPORT_PER_BATCH }))) return;
            await exportConversations({ mode: 'project', workspaceId, conversationEntries: projectEntries, exportType: 'full' });
        } catch (err) {
            console.error('导出项目空间失败:', err);
            alert(t('alert.projectExportFailed', { message: err.message }));
        }
    }

    async function startSelectiveExportProcess(mode, workspaceId, conversationEntries) {
        await exportConversations({ mode, workspaceId, conversationEntries });
    }

    function startScheduledExport(options = {}) {
        const { mode = 'personal', workspaceId = null, autoConfirm = false, source = 'schedule' } = options;
        const proceed = async () => {
            try {
                if (mode === 'project') await startProjectSpaceExportProcess(workspaceId, autoConfirm);
                else await startExportProcess(mode, workspaceId, autoConfirm);
            } catch (err) {
                console.error('[ChatGPT Exporter] 自动导出失败:', err);
            }
        };
        if (autoConfirm) { proceed(); return; }
        const modeLabel = t(`mode.${mode === 'team' ? 'team' : mode === 'project' ? 'project' : 'personal'}`);
        if (confirm(t('confirm.scheduledExport', { mode: modeLabel, source }))) proceed();
    }

    // ======================== API 调用（完整保留） ========================
    function normalizeProjectSpaceItem(item) {
        const rawGizmo = item?.gizmo?.gizmo || item?.gizmo || item;
        const display = rawGizmo?.display || item?.gizmo?.display || item?.display;
        const id = rawGizmo?.id || item?.gizmo?.id || item?.id;
        const title = display?.name || rawGizmo?.name || t('fallback.untitledProject');
        if (!id) return null;
        return { id, title, conversations: item?.conversations?.items || [] };
    }

    function resolveWorkspaceId(workspaceId) {
        if (workspaceId) return workspaceId;
        const match = document.cookie.match(/(?:^|; )_account=([^;]+)/);
        if (match?.[1]) return match[1];
        const detectedIds = detectAllWorkspaceIds();
        return detectedIds.length > 0 ? detectedIds[0] : null;
    }

    async function getProjectSpaces(workspaceId, options = {}) {
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        const resolvedWorkspaceId = resolveWorkspaceId(workspaceId);
        if (resolvedWorkspaceId) headers['ChatGPT-Account-Id'] = resolvedWorkspaceId;
        const projects = new Map();
        let cursor = null;
        do {
            const query = new URLSearchParams();
            query.set('limit', String(PROJECT_SIDEBAR_LIMIT));
            if (options.conversationsPerGizmo !== undefined) query.set('conversations_per_gizmo', String(options.conversationsPerGizmo));
            if (options.ownedOnly !== undefined) query.set('owned_only', options.ownedOnly ? 'true' : 'false');
            if (cursor) query.set('cursor', cursor);
            const r = await fetch(`/backend-api/gizmos/snorlax/sidebar?${query.toString()}`, { headers });
            if (!r.ok) throw createStatusError(t('error.projectSpaceListFailed', { status: r.status }), r.status);
            const data = await r.json();
            data.items?.forEach(item => {
                const project = normalizeProjectSpaceItem(item);
                if (project) projects.set(project.id, project);
            });
            cursor = data.cursor || null;
            if (cursor) await sleep(jitter());
        } while (cursor);
        return Array.from(projects.values());
    }

    async function getProjects(workspaceId) {
        if (!workspaceId) return [];
        try {
            const projects = await getProjectSpaces(workspaceId);
            return projects.map(({ id, title }) => ({ id, title }));
        } catch (err) {
            console.warn(`获取项目(Gizmo)列表失败 (${err?.message || err})`);
            return [];
        }
    }

    async function collectIds(btn, workspaceId, gizmoId) {
        const all = new Set();
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        if (workspaceId) headers['ChatGPT-Account-Id'] = workspaceId;

        if (gizmoId) {
            let cursor = '0';
            do {
                const r = await fetch(`/backend-api/gizmos/${gizmoId}/conversations?cursor=${cursor}`, { headers });
                if (!r.ok) throw createStatusError(t('error.projectConversationListFailed', { status: r.status }), r.status);
                const j = await r.json();
                j.items?.forEach(it => all.add(it.id));
                cursor = j.cursor;
                await sleep(jitter());
            } while (cursor);
        } else {
            // 「导出全部」复用本地快照：首页指纹一致则直接取根对话 id（零全量翻页，省风控）
            const cacheMode = workspaceId ? 'team' : 'personal';
            const snap = getListSnapshot(listCacheKey(cacheMode, workspaceId));
            if (snap && snap.entries.length > 0) {
                const snapshotIds = await trySnapshotIds(snap, workspaceId);
                if (snapshotIds) {
                    // 根导出只需"非项目"对话，避免与下方逐项目遍历重复
                    const rootSet = new Set(snap.entries.filter(e => !e.projectId).map(e => e.id));
                    return snapshotIds.filter(id => rootSet.has(id));
                }
            }
            for (const is_archived of [false, true]) {
                let offset = 0, has_more = true, page = 0;
                do {
                    btn.textContent = `📂 ${t('status.rootPage', { state: is_archived ? t('status.archived') : t('status.active'), page: ++page })}`;
                    const r = await fetch(`/backend-api/conversations?offset=${offset}&limit=${PAGE_LIMIT}&order=updated${is_archived ? '&is_archived=true' : ''}`, { headers });
                    if (!r.ok) throw createStatusError(t('error.rootConversationListFailed', { status: r.status }), r.status);
                    const j = await r.json();
                    if (j.items && j.items.length > 0) {
                        j.items.forEach(it => all.add(it.id));
                        has_more = j.items.length === PAGE_LIMIT;
                        offset += j.items.length;
                    } else has_more = false;
                    await sleep(jitter());
                } while (has_more);
            }
        }
        return Array.from(all);
    }

    function upsertConversationEntry(map, item, extra = {}) {
        if (!item?.id) return;
        const create_time = normalizeEpochSeconds(item.create_time || 0);
        const update_time = normalizeEpochSeconds(item.update_time || item.create_time || 0);
        const entry = {
            id: item.id,
            title: item.title || t('fallback.untitledConversation'),
            create_time,
            update_time,
            is_archived: item.is_archived ?? extra.is_archived ?? false,
            projectId: extra.projectId || null,
            projectTitle: extra.projectTitle || null
        };
        const existing = map.get(entry.id);
        if (!existing) { map.set(entry.id, entry); return; }
        if (!existing.projectTitle && entry.projectTitle) {
            existing.projectTitle = entry.projectTitle;
            existing.projectId = entry.projectId;
        }
        if (!existing.create_time && entry.create_time) existing.create_time = entry.create_time;
        existing.is_archived = existing.is_archived || entry.is_archived;
        if ((entry.update_time || 0) > (existing.update_time || 0)) existing.update_time = entry.update_time;
        if (existing.title === t('fallback.untitledConversation') && entry.title) existing.title = entry.title;
    }

    async function listConversations(workspaceId) {
        if (!await ensureAccessToken()) throw new Error(t('alert.accessTokenUnavailable'));
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        if (workspaceId) headers['ChatGPT-Account-Id'] = workspaceId;
        const map = new Map();
        const addEntry = (item, extra = {}) => upsertConversationEntry(map, item, extra);

        for (const is_archived of [false, true]) {
            let offset = 0, has_more = true;
            do {
                const r = await fetch(`/backend-api/conversations?offset=${offset}&limit=${PAGE_LIMIT}&order=updated${is_archived ? '&is_archived=true' : ''}`, { headers });
                if (!r.ok) throw createStatusError(t('error.conversationListFailed', { status: r.status }), r.status);
                const j = await r.json();
                if (j.items && j.items.length > 0) {
                    j.items.forEach(it => addEntry(it, { is_archived }));
                    has_more = j.items.length === PAGE_LIMIT;
                    offset += j.items.length;
                } else has_more = false;
                await sleep(jitter());
            } while (has_more);
        }

        if (workspaceId) {
            const projects = await getProjects(workspaceId);
            for (const project of projects) {
                let cursor = '0';
                do {
                    const r = await fetch(`/backend-api/gizmos/${project.id}/conversations?cursor=${cursor}`, { headers });
                    if (!r.ok) throw createStatusError(t('error.projectConversationListFailed', { status: r.status }), r.status);
                    const j = await r.json();
                    j.items?.forEach(it => addEntry(it, { projectId: project.id, projectTitle: project.title }));
                    cursor = j.cursor;
                    await sleep(jitter());
                } while (cursor);
            }
        }
        return Array.from(map.values()).sort((a, b) => (b.update_time || 0) - (a.update_time || 0));
    }

    async function listProjectSpaceConversations(workspaceId) {
        if (!await ensureAccessToken()) throw new Error(t('alert.accessTokenUnavailable'));
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        const resolvedWorkspaceId = resolveWorkspaceId(workspaceId);
        if (resolvedWorkspaceId) headers['ChatGPT-Account-Id'] = resolvedWorkspaceId;
        const map = new Map();
        const projects = await getProjectSpaces(resolvedWorkspaceId, { conversationsPerGizmo: PROJECT_SIDEBAR_PREVIEW, ownedOnly: true });

        for (const project of projects) {
            let cursor = '0';
            let fetched = false;
            do {
                const r = await fetch(`/backend-api/gizmos/${project.id}/conversations?cursor=${cursor}`, { headers });
                if (!r.ok) {
                    if (!fetched && Array.isArray(project.conversations) && project.conversations.length > 0) {
                        console.warn(`项目空间对话列表请求失败 (${r.status})，使用侧边栏返回的预览对话。`);
                        project.conversations.forEach(item => upsertConversationEntry(map, item, { projectId: project.id, projectTitle: project.title }));
                        cursor = null;
                        break;
                    }
                    throw createStatusError(t('error.projectSpaceConversationListFailed', { status: r.status }), r.status);
                }
                const j = await r.json();
                j.items?.forEach(item => upsertConversationEntry(map, item, { projectId: project.id, projectTitle: project.title }));
                cursor = j.cursor;
                fetched = true;
                await sleep(jitter());
            } while (cursor);
        }
        return Array.from(map.values()).sort((a, b) => (b.update_time || 0) - (a.update_time || 0));
    }

    // 远端"首页指纹"：只拉第一页 order=updated，比对首页 id + update_time 序列判断是否有更新。
    // 包含 update_time 后，同一对话哪怕原地更新（相对次序没变）也能被识别。
    async function fetchFirstPageFingerprint(workspaceId, limit) {
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        if (workspaceId) headers['ChatGPT-Account-Id'] = workspaceId;
        const r = await fetch(`/backend-api/conversations?offset=0&limit=${limit}&order=updated`, { headers });
        if (!r.ok) throw createStatusError(t('error.conversationListFailed', { status: r.status }), r.status);
        const j = await r.json();
        return Array.isArray(j.items)
            ? j.items.map(it => ({ id: it.id, update_time: normalizeEpochSeconds(it.update_time || it.create_time || 0) }))
            : [];
    }
    function firstPageFingerprint(entries, limit) {
        return entries.slice().sort((a, b) => (b.update_time || 0) - (a.update_time || 0))
            .slice(0, limit).map(e => ({ id: e.id, update_time: e.update_time || 0 }));
    }
    function fingerprintEqual(a, b) {
        return a.length === b.length && a.every((x, i) => x.id === b[i].id && x.update_time === b[i].update_time);
    }

    // 选择器列表加载：cache-first + 首页指纹探测。无更新返回 null（复用快照），有更新/无快照返回全量并写回快照。
    async function refreshListForPicker(mode, workspaceId, snap, force = false) {
        const cacheKey = listCacheKey(mode, workspaceId);
        if (force || !snap) return await refreshAndCacheList(mode, workspaceId, cacheKey);
        try {
            const remote = await fetchFirstPageFingerprint(workspaceId, MAX_EXPORT_PER_BATCH);
            const local = firstPageFingerprint(snap.entries, MAX_EXPORT_PER_BATCH);
            if (fingerprintEqual(remote, local)) {
                console.log('[列表] 首页指纹一致，判定无更新，复用本地快照');
                return null;
            }
            console.log('[列表] 检测到列表有更新，重新拉取全量');
        } catch (err) {
            console.warn('[列表] 指纹探测失败，保持使用本地快照:', err.message);
            return null;
        }
        return await refreshAndCacheList(mode, workspaceId, cacheKey);
    }

    // 「导出全部」复用快照：首页指纹一致则直接返回快照 id（零全量翻页），否则返回 null 走原全量逻辑
    async function trySnapshotIds(snap, workspaceId) {
        try {
            const remote = await fetchFirstPageFingerprint(workspaceId, MAX_EXPORT_PER_BATCH);
            const local = firstPageFingerprint(snap.entries, MAX_EXPORT_PER_BATCH);
            if (fingerprintEqual(remote, local)) {
                console.log(`[导出全部] 首页指纹一致，复用快照 ${snap.entries.length} 条对话 id`);
                return snap.entries.map(e => e.id);
            }
            console.log('[导出全部] 检测到更新，走全量获取');
        } catch (err) {
            console.warn('[导出全部] 指纹探测失败，走全量获取:', err.message);
        }
        return null;
    }
    async function refreshAndCacheList(mode, workspaceId, cacheKey) {
        const list = mode === 'project' ? await listProjectSpaceConversations(workspaceId) : await listConversations(workspaceId);
        saveListSnapshot(cacheKey, list);
        return list;
    }

    async function getConversation(id, workspaceId, retries = 3) {
        const deviceId = getOaiDeviceId();
        if (!deviceId) throw new Error(t('error.deviceIdUnavailable'));
        const headers = { 'Authorization': `Bearer ${accessToken}`, 'oai-device-id': deviceId };
        const resolvedWorkspaceId = resolveWorkspaceId(workspaceId);
        if (resolvedWorkspaceId) headers['ChatGPT-Account-Id'] = resolvedWorkspaceId;
        let lastError = null;
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                const r = await fetch(`/backend-api/conversation/${id}`, { headers });
                if (r.ok) {
                    const j = await r.json();
                    j.__fetched_at = new Date().toISOString();
                    return j;
                }
                const err = new Error(t('error.conversationDetailFailed', { id, status: r.status }));
                err.status = r.status;
                lastError = err;
                if (isAuthStatus(r.status)) {
                    console.warn(`🔑 令牌可能已失效 (${r.status})，重新获取后重试...`);
                    const refreshed = await refreshAccessTokenOnce();
                    if (refreshed && attempt < retries) {
                        headers['Authorization'] = `Bearer ${accessToken}`;
                        await sleep(Math.pow(2, attempt) * 1000 + Math.random() * 500);
                        continue;
                    }
                }
                if (r.status >= 500 && attempt < retries) {
                    const backoff = Math.pow(2, attempt) * 1000 + Math.random() * 500;
                    console.warn(`⚠️ 第 ${attempt} 次获取对话 ${id} 失败 (${r.status})，${Math.round(backoff / 1000)}s 后重试...`);
                    await sleep(backoff);
                    continue;
                }
                throw lastError;
            } catch (err) {
                lastError = err;
                const status = errorStatus(err);
                if (status && isAuthStatus(status)) {
                    console.warn(`🔑 令牌可能已失效 (${status})，重新获取后重试...`);
                    const refreshed = await refreshAccessTokenOnce();
                    if (refreshed && attempt < retries) {
                        headers['Authorization'] = `Bearer ${accessToken}`;
                        await sleep(Math.pow(2, attempt) * 1000 + Math.random() * 500);
                        continue;
                    }
                }
                if (attempt < retries && !(status >= 400 && status < 500)) {
                    const backoff = Math.pow(2, attempt) * 1000 + Math.random() * 500;
                    console.warn(`⚠️ 第 ${attempt} 次获取对话 ${id} 异常: ${err.message}，${Math.round(backoff / 1000)}s 后重试...`);
                    await sleep(backoff);
                    continue;
                }
                throw err;
            }
        }
        throw lastError;
    }

    // ======================== 图片/文件下载（完整保留） ========================
    function normalizeAssetId(raw) {
        if (!raw) return '';
        if (typeof raw !== 'string') return '';
        const trimmed = raw.trim();
        if (trimmed.startsWith('sediment://')) {
            const path = trimmed.replace('sediment://', '');
            return path || trimmed.replace(/[^\w.-]/g, '_');
        }
        if (trimmed.startsWith('file://') || trimmed.startsWith('file-') || trimmed.startsWith('file_')) {
            const m = trimmed.match(/[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}/i);
            if (m) return m[0];
            const m2 = trimmed.match(/file[_-]([a-f0-9]+)/i);
            if (m2) return `file_${m2[1]}`;
        }
        if (trimmed.startsWith('https://') || trimmed.startsWith('http://')) {
            try {
                const u = new URL(trimmed);
                const path = u.pathname.split('/').filter(Boolean);
                const last = path[path.length - 1];
                if (last) return last.replace(/\.[a-z0-9]+$/i, '');
            } catch (_) {}
        }
        if (/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(trimmed)) return trimmed.toLowerCase();
        return trimmed.replace(/[^\w.-]/g, '_');
    }

    function guessImageExt(contentType, url) {
        if (typeof contentType === 'string') {
            const ct = contentType.toLowerCase();
            if (ct.includes('png')) return 'png';
            if (ct.includes('jpeg') || ct.includes('jpg')) return 'jpg';
            if (ct.includes('webp')) return 'webp';
            if (ct.includes('gif')) return 'gif';
            if (ct.includes('svg')) return 'svg';
            if (ct.includes('bmp')) return 'bmp';
        }
        if (typeof url === 'string') {
            const m = url.toLowerCase().match(/\.(png|jpe?g|webp|gif|svg|bmp)(?:\?|$)/);
            if (m) return m[1] === 'jpg' ? 'jpg' : m[1];
        }
        return 'png';
    }

    function guessFileExt(contentType, url, filename) {
        const byName = String(filename || url || '').toLowerCase().match(/\.([a-z0-9]{1,12})(?:\?|$)/);
        if (byName) return byName[1];
        const ct = String(contentType || '').toLowerCase();
        if (ct.includes('pdf')) return 'pdf';
        if (ct.includes('csv')) return 'csv';
        if (ct.includes('json')) return 'json';
        if (ct.includes('markdown')) return 'md';
        if (ct.includes('plain')) return 'txt';
        if (ct.includes('spreadsheet')) return 'xlsx';
        if (ct.includes('presentation')) return 'pptx';
        if (ct.includes('wordprocessing')) return 'docx';
        if (ct.includes('zip')) return 'zip';
        return '';
    }

    async function resolveFileDownloadUrl(fileId, accessToken, workspaceId) {
        const deviceId = getOaiDeviceId();
        const headers = { 'Authorization': `Bearer ${accessToken}` };
        if (deviceId) headers['oai-device-id'] = deviceId;
        const resolvedWs = workspaceId || resolveWorkspaceId(null);
        if (resolvedWs) headers['ChatGPT-Account-Id'] = resolvedWs;
        const r = await fetch(`/backend-api/files/${fileId}/download`, { headers });
        if (!r.ok) throw createStatusError(t('error.fileDownloadUrlFailed', { status: r.status }), r.status);
        const data = await r.json();
        return data.download_url || null;
    }

    async function resolveImageDownloadUrl(fileId, accessToken, workspaceId) {
        return resolveFileDownloadUrl(fileId, accessToken, workspaceId);
    }

    async function fetchImageBlob(image, accessToken, workspaceId) {
        let url = image.url || image.download_url;
        if (!url && image.asset_pointer) {
            const fileId = normalizeAssetId(image.asset_pointer);
            if (fileId) {
                try {
                    url = await resolveImageDownloadUrl(fileId, accessToken, workspaceId);
                    console.log(`🖼️ 已解析图片下载链接 [${fileId}]`);
                } catch (err) {
                    console.warn(`⚠️ 无法解析图片下载链接 [${fileId}]:`, err.message);
                    return null;
                }
            }
        }
        if (!url) return null;
        const opts = { credentials: 'include' };
        if (accessToken && url.startsWith('/')) opts.headers = { 'Authorization': `Bearer ${accessToken}` };
        const r = await fetch(url, opts);
        if (!r.ok) throw createStatusError(t('error.imageDownloadFailed', { status: r.status }), r.status);
        return await r.blob();
    }

    async function fetchAttachmentBlob(file, accessToken, workspaceId) {
        let url = file.url || file.download_url;
        if (!url && file.file_id) {
            const fileId = normalizeAssetId(file.file_id);
            if (fileId) {
                url = await resolveFileDownloadUrl(fileId, accessToken, workspaceId);
                console.log(`📎 已解析文件下载链接 [${fileId}]`);
            }
        }
        if (!url) return null;
        const opts = { credentials: 'include' };
        if (accessToken && url.startsWith('/')) opts.headers = { 'Authorization': `Bearer ${accessToken}` };
        const r = await fetch(url, opts);
        if (!r.ok) throw createStatusError(t('error.fileDownloadFailed', { status: r.status }), r.status);
        return await r.blob();
    }

    async function downloadConversationAssets(convData, targetZip, generateMarkdown, accessToken, zipFilenameRegistry, workspaceId) {
        const messages = extractConversationMessages(convData);
        const seen = new Set();
        const pending = [];
        const seenFiles = new Set();
        const pendingFiles = [];
        const imageFiles = new Map();
        const attachmentFiles = new Map();

        for (const msg of messages) {
            if (Array.isArray(msg.images)) {
                for (let k = 0; k < msg.images.length; k++) {
                    const img = msg.images[k];
                    const key = img.asset_pointer || img.url || (img.asset_pointer + '_' + k);
                    if (seen.has(key)) continue;
                    seen.add(key);
                    pending.push({ image: img, msgIndex: pending.length, assetId: normalizeAssetId(img.asset_pointer) });
                }
            }
            if (Array.isArray(msg.files)) {
                for (let k = 0; k < msg.files.length; k++) {
                    const file = msg.files[k];
                    const key = file.key || file.file_id || file.url || `${file.filename}_${k}`;
                    if (seenFiles.has(key)) continue;
                    seenFiles.add(key);
                    pendingFiles.push({ file, key, assetId: normalizeAssetId(file.file_id || file.url || key) });
                }
            }
        }

        if (pending.length === 0 && pendingFiles.length === 0) {
            return generateMarkdown ? convertConversationToMarkdown(convData) : null;
        }

        let okCount = 0;
        if (pending.length > 0) {
            const ns = targetZip.folder('images');
            const imageScope = `${targetZip.root || ''}${targetZip.name || ''}images/`;
            for (let i = 0; i < pending.length; i++) {
                const { image, assetId } = pending[i];
                try {
                    const blob = await fetchImageBlob(image, accessToken, workspaceId);
                    const ext = guessImageExt(image.content_type, image.url);
                    const safeAssetId = sanitizeImageFilenamePart(assetId, `image_${i + 1}`);
                    const filename = makeUniqueZipFilename(`img_${String(i + 1).padStart(2, '0')}_${safeAssetId}.${ext}`, zipFilenameRegistry, imageScope);
                    ns.file(filename, blob);
                    imageFiles.set(image.asset_pointer, { filename, dispositionLabel: image.dispositionLabel || 'image' });
                    okCount++;
                } catch (err) {
                    console.warn(`⚠️ 图片下载跳过 [${assetId}]:`, err.message, image);
                }
                await sleep(jitter());
            }
            console.log(`🖼️ 图片导出: ${okCount}/${pending.length} 张成功`);
        }

        let okFileCount = 0;
        if (pendingFiles.length > 0) {
            const ns = targetZip.folder('files');
            const fileScope = `${targetZip.root || ''}${targetZip.name || ''}files/`;
            for (let i = 0; i < pendingFiles.length; i++) {
                const { file, key, assetId } = pendingFiles[i];
                try {
                    const blob = await fetchAttachmentBlob(file, accessToken, workspaceId);
                    if (!blob) throw new Error(t('error.noDownloadUrl'));
                    let safeName = sanitizeFilename(file.filename || file.label || assetId, `file_${i + 1}`, MAX_SAFE_NAME_LENGTH);
                    if (!splitFilename(safeName).ext) {
                        const ext = guessFileExt(file.content_type, file.url, file.filename);
                        if (ext) safeName += `.${ext}`;
                    }
                    const filename = makeUniqueZipFilename(safeName, zipFilenameRegistry, fileScope);
                    ns.file(filename, blob);
                    const entry = { filename, label: file.label || file.filename || filename };
                    fileReferenceKeys({ ...file, key }).forEach(alias => attachmentFiles.set(alias, entry));
                    okFileCount++;
                } catch (err) {
                    console.warn(`⚠️ 文件下载跳过 [${assetId}]:`, err.message, file);
                }
                await sleep(jitter());
            }
            console.log(`📎 文件导出: ${okFileCount}/${pendingFiles.length} 个成功`);
        }

        return generateMarkdown ? convertConversationToMarkdown(convData, imageFiles, attachmentFiles) : null;
    }

    async function exportConversationIntoZip(convData, zip, accessToken, zipFilenameRegistry, workspaceId) {
        const scope = `${zip.root || ''}${zip.name || ''}`;
        const jsonFilename = makeUniqueZipFilename(generateUniqueFilename(convData), zipFilenameRegistry, scope);
        zip.file(jsonFilename, JSON.stringify(convData, null, 2));
        const markdown = await downloadConversationAssets(convData, zip, true, accessToken, zipFilenameRegistry, workspaceId);
        const markdownFilename = makeUniqueZipFilename(
            jsonFilename.endsWith('.json') ? `${jsonFilename.slice(0, -5)}.md` : generateMarkdownFilename(convData),
            zipFilenameRegistry,
            scope
        );
        zip.file(markdownFilename, markdown);
    }

    // ======================== ChatHarbor v0.5：Version-aware Directory Sync ========================
    const CHATHARBOR_VERSION = '0.5.0';
    const CHATHARBOR_MANIFEST = 'ChatHarbor_manifest.json';

    function stableJsonStringify(value) {
        const seen = new WeakSet();
        const normalize = (input) => {
            if (input === null || typeof input !== 'object') return input;
            if (seen.has(input)) return '[Circular]';
            seen.add(input);
            if (Array.isArray(input)) return input.map(normalize);
            const out = {};
            Object.keys(input).sort().forEach(key => { out[key] = normalize(input[key]); });
            return out;
        };
        return JSON.stringify(normalize(value));
    }

    async function sha256Text(text) {
        if (!crypto?.subtle) return `fallback-${String(text).length}-${String(text).slice(0, 32)}`;
        const bytes = new TextEncoder().encode(String(text));
        const digest = await crypto.subtle.digest('SHA-256', bytes);
        return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async function conversationContentSignature(convData) {
        // 标题、update_time 等顶层元数据不进入内容签名；mapping/current_node 变化才视为内容变化。
        const payload = {
            current_node: convData?.current_node || null,
            mapping: convData?.mapping || null
        };
        return await sha256Text(stableJsonStringify(payload));
    }

    function conversationLocalUpdateTime(convData) {
        const direct = normalizeEpochSeconds(convData?.update_time || convData?.create_time || 0);
        if (direct) return direct;
        let maxTs = 0;
        const mapping = convData?.mapping || {};
        Object.values(mapping).forEach(node => {
            const ts = normalizeEpochSeconds(node?.message?.create_time || 0);
            if (ts > maxTs) maxTs = ts;
        });
        return maxTs;
    }

    function conversationIdOf(convData) {
        return String(convData?.conversation_id || convData?.id || '').trim();
    }

    function conversationShortId(convData) {
        const id = conversationIdOf(convData);
        const tail = id.includes('-') ? id.split('-').pop() : id;
        return sanitizeImageFilenamePart(tail || 'conversation', 'conversation').slice(0, 24);
    }

    function splitRelativePath(path) {
        return String(path || '').split('/').filter(Boolean);
    }

    function parentPathOf(path) {
        const parts = splitRelativePath(path);
        parts.pop();
        return parts.join('/');
    }

    function basenameOf(path) {
        const parts = splitRelativePath(path);
        return parts[parts.length - 1] || '';
    }

    function joinRelativePath(...parts) {
        return parts.flatMap(splitRelativePath).join('/');
    }

    async function getDirectoryHandleByPath(root, relativePath, create = false) {
        let dir = root;
        for (const segment of splitRelativePath(relativePath)) {
            dir = await dir.getDirectoryHandle(segment, { create });
        }
        return dir;
    }

    async function readJsonFileFromDirectory(dirHandle, filename) {
        try {
            const handle = await dirHandle.getFileHandle(filename);
            const file = await handle.getFile();
            return JSON.parse(await file.text());
        } catch (_) {
            return null;
        }
    }

    async function writeFileAtomic(dirHandle, filename, data) {
        const suffix = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const tmpName = `.${sanitizeFilename(filename, 'file')}.ch_tmp_${suffix}`;
        let tmpCreated = false;
        try {
            const tmp = await dirHandle.getFileHandle(tmpName, { create: true });
            tmpCreated = true;
            const writer = await tmp.createWritable();
            await writer.write(data);
            await writer.close();

            const tmpFile = await tmp.getFile();
            const finalHandle = await dirHandle.getFileHandle(filename, { create: true });
            const finalWriter = await finalHandle.createWritable();
            await finalWriter.write(tmpFile);
            await finalWriter.close();

            const finalFile = await finalHandle.getFile();
            if (finalFile.size !== tmpFile.size) throw new Error(`写入校验失败：${filename}`);
            return finalFile.size;
        } finally {
            if (tmpCreated) {
                try { await dirHandle.removeEntry(tmpName); } catch (_) {}
            }
        }
    }

    async function removeFileByRelativePath(root, relativePath) {
        if (!relativePath) return;
        try {
            const parent = await getDirectoryHandleByPath(root, parentPathOf(relativePath), false);
            await parent.removeEntry(basenameOf(relativePath));
        } catch (_) { /* 不存在或无权删除时保持保守，不中断同步 */ }
    }

    async function readTextByRelativePath(root, relativePath) {
        if (!relativePath) return null;
        try {
            const parent = await getDirectoryHandleByPath(root, parentPathOf(relativePath), false);
            const handle = await parent.getFileHandle(basenameOf(relativePath));
            return await (await handle.getFile()).text();
        } catch (_) {
            return null;
        }
    }

    async function scanLocalArchive(rootHandle, onProgress = null) {
        const recordsById = new Map();
        const duplicates = [];
        let jsonFilesSeen = 0;
        let conversationsSeen = 0;
        const oldManifest = await readJsonFileFromDirectory(rootHandle, CHATHARBOR_MANIFEST) || null;

        const walk = async (dirHandle, relDir = '') => {
            for await (const [name, handle] of dirHandle.entries()) {
                const relPath = joinRelativePath(relDir, name);
                if (handle.kind === 'directory') {
                    await walk(handle, relPath);
                    continue;
                }
                if (!name.toLowerCase().endsWith('.json') || name === CHATHARBOR_MANIFEST) continue;
                jsonFilesSeen++;
                if (onProgress && jsonFilesSeen % 10 === 0) onProgress({ jsonFilesSeen, conversationsSeen, path: relPath });
                try {
                    const file = await handle.getFile();
                    const obj = JSON.parse(await file.text());
                    const id = conversationIdOf(obj);
                    // 避免把附件 JSON、manifest、普通数据文件误当成会话。
                    if (!id || !obj?.mapping || typeof obj.mapping !== 'object') continue;
                    conversationsSeen++;
                    const updateTime = conversationLocalUpdateTime(obj);
                    const signature = await conversationContentSignature(obj);
                    const base = name.replace(/\.json$/i, '');
                    const candidate = {
                        id,
                        title: obj.title || '',
                        update_time: updateTime,
                        content_signature: signature,
                        json_path: relPath,
                        md_path: joinRelativePath(relDir, `${base}.md`),
                        parent_path: relDir,
                        last_modified: file.lastModified || 0,
                        assets: Array.isArray(oldManifest?.entries?.[id]?.assets) ? oldManifest.entries[id].assets : []
                    };
                    const existing = recordsById.get(id);
                    if (!existing) {
                        recordsById.set(id, candidate);
                    } else {
                        const pickNew = (candidate.update_time > existing.update_time) ||
                            (candidate.update_time === existing.update_time && candidate.last_modified > existing.last_modified);
                        const kept = pickNew ? candidate : existing;
                        const extra = pickNew ? existing : candidate;
                        recordsById.set(id, kept);
                        duplicates.push({ id, kept: kept.json_path, duplicate: extra.json_path });
                    }
                } catch (err) {
                    console.warn(`[同步扫描] 跳过无法解析的 JSON：${relPath}`, err.message);
                }
            }
        };

        await walk(rootHandle, '');
        if (onProgress) onProgress({ jsonFilesSeen, conversationsSeen, done: true });
        return { recordsById, duplicates, oldManifest, jsonFilesSeen, conversationsSeen };
    }

    function buildDirectorySyncPlan(remoteList, localScan) {
        const items = [];
        const remoteIds = new Set();
        let newCount = 0, changedCount = 0, renameOnlyCandidateCount = 0, unchangedCount = 0;
        for (const remote of remoteList || []) {
            remoteIds.add(remote.id);
            const local = localScan.recordsById.get(remote.id);
            if (!local) {
                newCount++;
                items.push({ action: 'NEW', remote, local: null });
                continue;
            }
            const titleChanged = String(remote.title || '') !== String(local.title || '');
            const remoteTime = normalizeEpochSeconds(remote.update_time || 0);
            const localTime = normalizeEpochSeconds(local.update_time || 0);
            if (remoteTime > localTime) {
                changedCount++;
                items.push({ action: 'VERIFY_CHANGED', remote, local, titleChanged });
            } else if (titleChanged) {
                renameOnlyCandidateCount++;
                items.push({ action: 'VERIFY_RENAMED', remote, local, titleChanged: true });
            } else {
                unchangedCount++;
            }
        }
        const localOnly = Array.from(localScan.recordsById.values()).filter(item => !remoteIds.has(item.id));
        return {
            items,
            summary: {
                remote: (remoteList || []).length,
                local: localScan.recordsById.size,
                newCount,
                changedCount,
                renameOnlyCandidateCount,
                unchangedCount,
                localOnlyCount: localOnly.length,
                duplicateCount: localScan.duplicates.length,
                toFetch: items.length
            },
            localOnly
        };
    }

    function syncUiText(zh, en) {
        return SCRIPT_LOCALE_CODE === 'zh-Hans' || SCRIPT_LOCALE_CODE === 'zh-Hant' ? zh : en;
    }

    function directorySyncCandidateLabel(item) {
        if (!item?.local) return 'NEW';
        return item.action === 'VERIFY_RENAMED' ? 'TITLE_DIFF' : 'REMOTE_UPDATED';
    }

    function formatDirectoryCandidateDetail(item) {
        const remote = item?.remote || {};
        const local = item?.local || {};
        const localTime = formatTimestamp(local.update_time) || t('fallback.unknown');
        const remoteTime = formatTimestamp(remote.update_time) || t('fallback.unknown');
        const titleChanged = String(remote.title || '') !== String(local.title || '');
        return [
            `[${directorySyncCandidateLabel(item)}] ${remote.title || local.title || remote.id || t('fallback.conversation')}`,
            `ID: ${remote.id || local.id || ''}`,
            `${syncUiText('本地更新时间', 'Local update')}: ${localTime}`,
            `${syncUiText('远端更新时间', 'Remote update')}: ${remoteTime}`,
            `${syncUiText('标题变化', 'Title changed')}: ${titleChanged ? 'YES' : 'NO'}`,
            ...(titleChanged ? [
                `${syncUiText('本地标题', 'Local title')}: ${local.title || ''}`,
                `${syncUiText('远端标题', 'Remote title')}: ${remote.title || ''}`
            ] : [])
        ].join('\n');
    }

    function formatDirectorySyncPlan(summary) {
        return [
            'ChatHarbor v0.5.0｜目录同步预检',
            '',
            `远端会话：${summary.remote}`,
            `本地会话：${summary.local}`,
            `新增 NEW：${summary.newCount}`,
            `远端更新时间变化（待抓取核验）：${summary.changedCount}`,
            `仅标题差异候选（待抓取核验）：${summary.renameOnlyCandidateCount}`,
            `未变化：${summary.unchangedCount}`,
            `仅本地存在（不会删除）：${summary.localOnlyCount}`,
            `本地重复 conversation_id：${summary.duplicateCount}`,
            '',
            `本次最多需要抓取 ${summary.toFetch} 条。`,
            '已有会话只会在新内容成功抓取并写盘后覆盖/更名；本地仅有记录不会自动删除。',
            '网络请求仍按当前批次上限与随机暂停执行。'
        ].join('\n');
    }

    function showDirectorySyncPlanDialog(plan) {
        return new Promise(resolve => {
            const existingCandidates = plan.items.filter(item => item.local);
            const newSamples = plan.items.filter(item => !item.local).slice(0, 8);
            const overlay = document.createElement('div');
            Object.assign(overlay.style, {
                position: 'fixed', inset: '0', background: 'rgba(0,0,0,.45)', zIndex: '100000',
                display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
            });
            const panel = document.createElement('div');
            Object.assign(panel.style, {
                width: 'min(760px, 96vw)', maxHeight: '88vh', overflow: 'hidden', background: '#fff', color: '#111827',
                borderRadius: '12px', boxShadow: '0 18px 50px rgba(0,0,0,.30)', display: 'flex', flexDirection: 'column'
            });
            const body = document.createElement('div');
            Object.assign(body.style, { padding: '20px 22px 12px', overflowY: 'auto', whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: '1.55' });
            const title = document.createElement('div');
            title.textContent = 'ChatHarbor v0.5.0｜目录同步预检';
            Object.assign(title.style, { fontWeight: '700', fontSize: '17px', marginBottom: '12px' });
            body.appendChild(title);

            const summary = document.createElement('pre');
            summary.textContent = formatDirectorySyncPlan(plan.summary);
            Object.assign(summary.style, { whiteSpace: 'pre-wrap', margin: '0 0 14px', fontFamily: 'inherit' });
            body.appendChild(summary);

            if (existingCandidates.length) {
                const h = document.createElement('div');
                h.textContent = `${syncUiText('已有会话变化候选', 'Existing-change candidates')} (${existingCandidates.length})`;
                Object.assign(h.style, { fontWeight: '700', margin: '10px 0 8px' });
                body.appendChild(h);
                existingCandidates.slice(0, 20).forEach((item, idx) => {
                    const box = document.createElement('pre');
                    box.textContent = formatDirectoryCandidateDetail(item);
                    Object.assign(box.style, {
                        whiteSpace: 'pre-wrap', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: '8px',
                        padding: '9px 10px', margin: '0 0 8px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '12px'
                    });
                    body.appendChild(box);
                });
                if (existingCandidates.length > 20) {
                    const more = document.createElement('div');
                    more.textContent = `${syncUiText('另有', 'Plus')} ${existingCandidates.length - 20} ${syncUiText('条未展开', 'more not expanded')}`;
                    more.style.color = '#6b7280';
                    body.appendChild(more);
                }
            }

            if (newSamples.length) {
                const h = document.createElement('div');
                h.textContent = `${syncUiText('NEW 样例（仅展示前', 'NEW samples (first')} ${newSamples.length}${syncUiText('条）', ')')}`;
                Object.assign(h.style, { fontWeight: '700', margin: '14px 0 6px' });
                body.appendChild(h);
                const ul = document.createElement('ul');
                Object.assign(ul.style, { margin: '0 0 8px', paddingLeft: '22px' });
                newSamples.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = `${item.remote?.title || t('fallback.conversation')} · ${item.remote?.id || ''}`;
                    ul.appendChild(li);
                });
                body.appendChild(ul);
            }

            if (plan.localOnly.length) {
                const h = document.createElement('div');
                h.textContent = `${syncUiText('仅本地存在（不会删除）', 'Local-only (will not be deleted)')} (${plan.localOnly.length})`;
                Object.assign(h.style, { fontWeight: '700', margin: '14px 0 6px' });
                body.appendChild(h);
            }
            if (plan.localScan?.duplicates?.length) {
                const h = document.createElement('div');
                h.textContent = `${syncUiText('重复 conversation_id', 'Duplicate conversation_id')} (${plan.localScan.duplicates.length})`;
                Object.assign(h.style, { fontWeight: '700', margin: '14px 0 6px', color: '#b45309' });
                body.appendChild(h);
            }

            const footer = document.createElement('div');
            Object.assign(footer.style, { display: 'flex', gap: '8px', justifyContent: 'flex-end', padding: '12px 18px 16px', borderTop: '1px solid #e5e7eb', flexWrap: 'wrap' });
            const makeBtn = (label, value, primary = false) => {
                const btn = document.createElement('button');
                btn.textContent = label;
                Object.assign(btn.style, {
                    padding: '9px 13px', borderRadius: '7px', cursor: 'pointer', fontWeight: primary ? '700' : '500',
                    border: primary ? '1px solid #0f766e' : '1px solid #d1d5db',
                    background: primary ? '#0f766e' : '#fff', color: primary ? '#fff' : '#111827'
                });
                btn.onclick = () => { overlay.remove(); resolve(value); };
                return btn;
            };
            if (existingCandidates.length) {
                footer.appendChild(makeBtn(syncUiText('仅核验已有变化项（不写盘）', 'Verify existing changes only (no writes)'), 'verify'));
                footer.appendChild(makeBtn(syncUiText('仅同步已有变化项', 'Sync existing changes only'), 'sync_existing'));
            }
            footer.appendChild(makeBtn(syncUiText('开始全部同步', 'Start full sync'), 'sync', true));
            footer.appendChild(makeBtn(syncUiText('取消', 'Cancel'), 'cancel'));
            panel.appendChild(body);
            panel.appendChild(footer);
            overlay.appendChild(panel);
            overlay.addEventListener('click', e => { if (e.target === overlay) { overlay.remove(); resolve('cancel'); } });
            document.body.appendChild(overlay);
        });
    }

    async function classifyDirectoryFetchedConversation(item, convData) {
        const newSignature = await conversationContentSignature(convData);
        if (!item.local) return { finalAction: 'NEW', newSignature, contentChanged: true, titleChanged: false };
        const oldSignature = item.local?.content_signature || '';
        const contentChanged = newSignature !== oldSignature;
        const remoteTitle = String(convData.title || item.remote?.title || '');
        const localTitle = String(item.local?.title || '');
        const titleChanged = remoteTitle !== localTitle;
        let finalAction;
        if (contentChanged && titleChanged) finalAction = 'UPDATED_AND_RENAMED';
        else if (contentChanged) finalAction = 'UPDATED';
        else if (titleChanged) finalAction = 'RENAMED_ONLY';
        else finalAction = 'METADATA_ONLY';
        return { finalAction, newSignature, contentChanged, titleChanged };
    }

    function formatVerificationResults(results) {
        const lines = [syncUiText('ChatHarbor｜变化项核验完成（未写盘）', 'ChatHarbor | Change verification complete (no writes)'), ''];
        for (const r of results) {
            lines.push(`[${r.finalAction}] ${r.title}`);
            lines.push(`ID: ${r.id}`);
            lines.push(`${syncUiText('本地更新时间', 'Local update')}: ${formatTimestamp(r.local_update_time) || t('fallback.unknown')}`);
            lines.push(`${syncUiText('远端更新时间', 'Remote update')}: ${formatTimestamp(r.remote_update_time) || t('fallback.unknown')}`);
            lines.push(`${syncUiText('内容变化', 'Content changed')}: ${r.contentChanged ? 'YES' : 'NO'}`);
            lines.push(`${syncUiText('标题变化', 'Title changed')}: ${r.titleChanged ? 'YES' : 'NO'}`);
            if (r.titleChanged) {
                lines.push(`${syncUiText('本地标题', 'Local title')}: ${r.local_title}`);
                lines.push(`${syncUiText('远端标题', 'Remote title')}: ${r.remote_title}`);
            }
            lines.push('');
        }
        lines.push(syncUiText('本次仅抓取并分类，没有写入、覆盖、更名、删除文件，也没有更新 manifest / exported 状态。', 'This run only fetched and classified. It did not write, overwrite, rename, delete files, or update manifest/exported state.'));
        return lines.join('\n');
    }

    async function verifyDirectoryChangeCandidates({ plan, workspaceId, statusElement = null }) {
        const candidates = plan.items.filter(item => item.local);
        if (!candidates.length) {
            alert(syncUiText('没有需要核验的已有会话变化项。', 'There are no existing-conversation changes to verify.'));
            return [];
        }
        if (!await ensureAccessToken()) throw new Error(t('alert.accessTokenUnavailable'));
        const runCfg = {
            delay: BASE_DELAY,
            jitter: JITTER,
            batch: Math.max(1, MAX_EXPORT_PER_BATCH),
            pauseMin: BATCH_PAUSE_MIN,
            pauseMax: BATCH_PAUSE_MAX
        };
        const runJitter = () => runCfg.delay + Math.random() * runCfg.jitter;
        const randomPauseLocal = () => Math.round((runCfg.pauseMin + Math.random() * (runCfg.pauseMax - runCfg.pauseMin)) * 1000);
        const results = [];
        exportRunning = true;
        exportAbortRequested = false;
        const btn = getExportButton();
        btn.disabled = false;
        try {
            const batches = [];
            for (let i = 0; i < candidates.length; i += runCfg.batch) batches.push(candidates.slice(i, i + runCfg.batch));
            let index = 0;
            for (let b = 0; b < batches.length; b++) {
                if (exportAbortRequested) break;
                for (const item of batches[b]) {
                    if (exportAbortRequested) break;
                    index++;
                    const label = item.remote?.title || item.remote?.id || t('fallback.conversation');
                    btn.textContent = `🔎 ${String(label).slice(0, 12)} (${index}/${candidates.length})`;
                    if (statusElement) statusElement.textContent = `${syncUiText('正在核验变化项', 'Verifying changes')} ${index}/${candidates.length}: ${label}`;
                    const convData = await getConversation(item.remote.id, workspaceId);
                    const classified = await classifyDirectoryFetchedConversation(item, convData);
                    results.push({
                        id: item.remote.id,
                        title: convData.title || item.remote.title || item.local.title || '',
                        local_title: item.local.title || '',
                        remote_title: convData.title || item.remote.title || '',
                        local_update_time: item.local.update_time || 0,
                        remote_update_time: normalizeEpochSeconds(convData.update_time || item.remote.update_time || 0),
                        finalAction: classified.finalAction,
                        contentChanged: classified.contentChanged,
                        titleChanged: classified.titleChanged
                    });
                    if (!exportAbortRequested) await sleep(runJitter());
                }
                if (b < batches.length - 1 && !exportAbortRequested) {
                    const pauseSec = Math.round(randomPauseLocal() / 1000);
                    for (let sec = pauseSec; sec > 0 && !exportAbortRequested; sec--) {
                        btn.textContent = t('status.batchPause', { sec });
                        await sleep(1000);
                    }
                }
            }
        } finally {
            exportRunning = false;
            exportAbortRequested = false;
            btn.disabled = false;
            btn.textContent = t('button.export');
        }
        return results;
    }

    async function prepareDirectoryAssets(convData, accessToken, workspaceId) {
        const messages = extractConversationMessages(convData);
        const pendingImages = [];
        const pendingFiles = [];
        const seenImages = new Set();
        const seenFiles = new Set();
        const imageFiles = new Map();
        const attachmentFiles = new Map();
        const writes = [];
        const convShort = conversationShortId(convData);
        const usedImageNames = new Set();
        const usedFileNames = new Set();

        const uniqueName = (name, used) => {
            let candidate = name;
            if (!used.has(candidate)) { used.add(candidate); return candidate; }
            const { stem, ext } = splitFilename(candidate);
            let i = 2;
            do { candidate = `${stem} (${i++})${ext}`; } while (used.has(candidate));
            used.add(candidate);
            return candidate;
        };

        for (const msg of messages) {
            for (const img of (Array.isArray(msg.images) ? msg.images : [])) {
                const key = img.asset_pointer || img.url;
                if (!key || seenImages.has(key)) continue;
                seenImages.add(key);
                pendingImages.push(img);
            }
            for (const file of (Array.isArray(msg.files) ? msg.files : [])) {
                const key = file.key || file.file_id || file.url || file.filename;
                if (!key || seenFiles.has(key)) continue;
                seenFiles.add(key);
                pendingFiles.push({ file, key });
            }
        }

        for (let i = 0; i < pendingImages.length; i++) {
            const image = pendingImages[i];
            const assetId = normalizeAssetId(image.asset_pointer || image.url || `image_${i + 1}`);
            try {
                const blob = await fetchImageBlob(image, accessToken, workspaceId);
                if (!blob) continue;
                const ext = guessImageExt(image.content_type, image.url);
                const safeAssetId = sanitizeImageFilenamePart(assetId, `image_${i + 1}`);
                const filename = uniqueName(`${convShort}_img_${String(i + 1).padStart(2, '0')}_${safeAssetId}.${ext}`, usedImageNames);
                writes.push({ subdir: 'images', filename, data: blob, kind: 'image' });
                imageFiles.set(image.asset_pointer, { filename, dispositionLabel: image.dispositionLabel || 'image' });
            } catch (err) {
                console.warn(`⚠️ 目录同步图片跳过 [${assetId}]：`, err.message);
            }
            await sleep(jitter());
        }

        for (let i = 0; i < pendingFiles.length; i++) {
            const { file, key } = pendingFiles[i];
            const assetId = normalizeAssetId(file.file_id || file.url || key);
            try {
                const blob = await fetchAttachmentBlob(file, accessToken, workspaceId);
                if (!blob) throw new Error(t('error.noDownloadUrl'));
                let safeName = sanitizeFilename(file.filename || file.label || assetId, `file_${i + 1}`, MAX_SAFE_NAME_LENGTH);
                if (!splitFilename(safeName).ext) {
                    const ext = guessFileExt(file.content_type, file.url, file.filename);
                    if (ext) safeName += `.${ext}`;
                }
                const filename = uniqueName(`${convShort}_${safeName}`, usedFileNames);
                writes.push({ subdir: 'files', filename, data: blob, kind: 'file' });
                const entry = { filename, label: file.label || file.filename || filename };
                fileReferenceKeys({ ...file, key }).forEach(alias => attachmentFiles.set(alias, entry));
            } catch (err) {
                console.warn(`⚠️ 目录同步附件跳过 [${assetId}]：`, err.message);
            }
            await sleep(jitter());
        }

        const markdown = convertConversationToMarkdown(convData, imageFiles, attachmentFiles);
        return { writes, markdown };
    }

    async function writeConversationToDirectory(rootHandle, remoteEntry, localRecord, convData, contentSignature, assetBundle) {
        // 既有会话优先保持原父目录；新增会话按项目名建目录，和旧 ZIP 目录结构保持接近。
        const parentPath = localRecord?.parent_path || (remoteEntry?.projectTitle ? sanitizeFilename(remoteEntry.projectTitle) : '');
        const parentDir = await getDirectoryHandleByPath(rootHandle, parentPath, true);
        const jsonFilename = generateUniqueFilename(convData);
        const mdFilename = jsonFilename.endsWith('.json') ? `${jsonFilename.slice(0, -5)}.md` : generateMarkdownFilename(convData);
        const jsonPath = joinRelativePath(parentPath, jsonFilename);
        const mdPath = joinRelativePath(parentPath, mdFilename);

        // 先准备并写入资源；文件名带 conversation 短 ID，避免跨会话覆盖同名附件。
        const newAssetPaths = [];
        for (const asset of assetBundle.writes) {
            const assetDir = await parentDir.getDirectoryHandle(asset.subdir, { create: true });
            await writeFileAtomic(assetDir, asset.filename, asset.data);
            newAssetPaths.push(joinRelativePath(parentPath, asset.subdir, asset.filename));
        }

        // JSON/MD 最后写，确保正文不会指向尚未落盘的资源。
        await writeFileAtomic(parentDir, jsonFilename, JSON.stringify(convData, null, 2));
        await writeFileAtomic(parentDir, mdFilename, assetBundle.markdown);

        // 标题变化时，只有新文件确认写入后才移除旧 JSON/MD。
        if (localRecord?.json_path && localRecord.json_path !== jsonPath) await removeFileByRelativePath(rootHandle, localRecord.json_path);
        if (localRecord?.md_path && localRecord.md_path !== mdPath) await removeFileByRelativePath(rootHandle, localRecord.md_path);

        // 只清理由 ChatHarbor v0.5 manifest 明确追踪的旧资源；legacy 未追踪资源不冒险删除。
        const oldAssets = Array.isArray(localRecord?.assets) ? localRecord.assets : [];
        if (assetBundle.preserveExistingAssets) {
            newAssetPaths.push(...oldAssets.filter(path => !newAssetPaths.includes(path)));
        } else {
            for (const oldPath of oldAssets) {
                if (!newAssetPaths.includes(oldPath)) await removeFileByRelativePath(rootHandle, oldPath);
            }
        }

        return {
            id: conversationIdOf(convData),
            title: convData.title || remoteEntry?.title || '',
            remote_update_time: normalizeEpochSeconds(convData.update_time || remoteEntry?.update_time || 0),
            content_signature: contentSignature,
            json_path: jsonPath,
            md_path: mdPath,
            assets: newAssetPaths,
            synced_at: new Date().toISOString(),
            project_title: remoteEntry?.projectTitle || null,
            project_id: remoteEntry?.projectId || null
        };
    }

    async function writeDirectoryManifest(rootHandle, manifest) {
        manifest.app = 'ChatHarbor';
        manifest.schema_version = 1;
        manifest.project_version = CHATHARBOR_VERSION;
        manifest.updated_at = new Date().toISOString();
        await writeFileAtomic(rootHandle, CHATHARBOR_MANIFEST, JSON.stringify(manifest, null, 2));
    }

    async function syncDirectoryArchive({ rootHandle, remoteList, plan, workspaceId, statusCallback = null }) {
        if (!await ensureAccessToken()) throw new Error(t('alert.accessTokenUnavailable'));
        const runCfg = {
            delay: BASE_DELAY,
            jitter: JITTER,
            batch: Math.max(1, MAX_EXPORT_PER_BATCH),
            pauseMin: BATCH_PAUSE_MIN,
            pauseMax: BATCH_PAUSE_MAX
        };
        const runJitter = () => runCfg.delay + Math.random() * runCfg.jitter;
        const randomPauseLocal = () => Math.round((runCfg.pauseMin + Math.random() * (runCfg.pauseMax - runCfg.pauseMin)) * 1000);
        const items = plan.items.slice();
        const manifest = plan.localScan.oldManifest && typeof plan.localScan.oldManifest === 'object'
            ? { ...plan.localScan.oldManifest, entries: { ...(plan.localScan.oldManifest.entries || {}) } }
            : { app: 'ChatHarbor', schema_version: 1, project_version: CHATHARBOR_VERSION, entries: {} };
        const result = {
            total: items.length, success: 0, failed: 0,
            newCount: 0, updatedCount: 0, renamedOnlyCount: 0, updatedAndRenamedCount: 0, metadataOnlyCount: 0,
            failures: []
        };

        exportRunning = true;
        exportAbortRequested = false;
        const btn = getExportButton();
        btn.disabled = false; // 保持可点击用于取消

        try {
            const batches = [];
            for (let i = 0; i < items.length; i += runCfg.batch) batches.push(items.slice(i, i + runCfg.batch));
            let globalIndex = 0;
            for (let b = 0; b < batches.length; b++) {
                if (exportAbortRequested) break;
                for (const item of batches[b]) {
                    if (exportAbortRequested) break;
                    globalIndex++;
                    const label = item.remote?.title || item.remote?.id || t('fallback.conversation');
                    if (statusCallback) statusCallback({ phase: 'sync', current: globalIndex, total: items.length, title: label, batch: b + 1, batches: batches.length });
                    btn.textContent = `🔄 ${String(label).slice(0, 12)} (${globalIndex}/${items.length})`;
                    try {
                        const convData = await getConversation(item.remote.id, workspaceId);
                        const classified = await classifyDirectoryFetchedConversation(item, convData);
                        const newSignature = classified.newSignature;
                        const finalAction = classified.finalAction;

                        let assetBundle;
                        if (finalAction === 'RENAMED_ONLY' || finalAction === 'METADATA_ONLY') {
                            // 内容未变时不重复请求附件/图片；沿用既有 Markdown 与已追踪资源。
                            const existingMarkdown = await readTextByRelativePath(rootHandle, item.local?.md_path);
                            assetBundle = {
                                writes: [],
                                markdown: existingMarkdown ?? convertConversationToMarkdown(convData),
                                preserveExistingAssets: true
                            };
                        } else {
                            assetBundle = await prepareDirectoryAssets(convData, accessToken, workspaceId);
                            assetBundle.preserveExistingAssets = false;
                        }
                        const record = await writeConversationToDirectory(rootHandle, item.remote, item.local, convData, newSignature, assetBundle);
                        manifest.entries[item.remote.id] = record;
                        await writeDirectoryManifest(rootHandle, manifest); // conversation 粒度提交，断点后可重建/续跑
                        markConversationsExported([item.remote.id]);

                        // 更新运行期 local 记录，保证本次结果可继续使用。
                        plan.localScan.recordsById.set(item.remote.id, {
                            id: record.id, title: record.title, update_time: record.remote_update_time,
                            content_signature: record.content_signature, json_path: record.json_path, md_path: record.md_path,
                            parent_path: parentPathOf(record.json_path), last_modified: Date.now(), assets: record.assets
                        });
                        result.success++;
                        if (finalAction === 'NEW') result.newCount++;
                        else if (finalAction === 'UPDATED') result.updatedCount++;
                        else if (finalAction === 'RENAMED_ONLY') result.renamedOnlyCount++;
                        else if (finalAction === 'UPDATED_AND_RENAMED') result.updatedAndRenamedCount++;
                        else result.metadataOnlyCount++;
                    } catch (err) {
                        result.failed++;
                        result.failures.push({ id: item.remote?.id, title: label, error: err.message || String(err) });
                        console.warn(`[目录同步] ${label} 失败：`, err);
                    }
                    if (!exportAbortRequested) await sleep(runJitter());
                }
                if (b < batches.length - 1 && !exportAbortRequested) {
                    const pauseMs = randomPauseLocal();
                    const pauseSec = Math.round(pauseMs / 1000);
                    for (let s = pauseSec; s > 0 && !exportAbortRequested; s--) {
                        btn.textContent = t('status.batchPause', { sec: s });
                        if (statusCallback) statusCallback({ phase: 'pause', sec: s, batch: b + 1, batches: batches.length });
                        await sleep(1000);
                    }
                }
            }
        } finally {
            exportRunning = false;
            exportAbortRequested = false;
            btn.disabled = false;
            btn.textContent = t('button.export');
        }
        return result;
    }

    async function runDirectorySyncFromPicker({ mode, workspaceId, remoteList, closeDialog, statusElement = null }) {
        if (typeof window.showDirectoryPicker !== 'function') {
            alert(t('alert.syncUnsupported'));
            return;
        }
        let rootHandle;
        try {
            // 必须由用户点击直接触发 picker；Edge/Chromium 会在这里请求目录读写授权。
            rootHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        } catch (err) {
            if (err?.name !== 'AbortError') alert(`选择目录失败：${err.message || err}`);
            return;
        }

        try {
            // 目录授权后再强制刷新远端列表，避免用旧快照做版本判断。
            if (statusElement) statusElement.textContent = t('status.syncPreparing');
            remoteList = await refreshAndCacheList(mode, workspaceId, listCacheKey(mode, workspaceId));
            if (statusElement) statusElement.textContent = t('status.scanningLocalArchive');
            const localScan = await scanLocalArchive(rootHandle, progress => {
                if (statusElement && !progress.done) statusElement.textContent = `${t('status.scanningLocalArchive')} JSON ${progress.jsonFilesSeen} / 会话 ${progress.conversationsSeen}`;
            });
            const plan = buildDirectorySyncPlan(remoteList, localScan);
            plan.localScan = localScan;
            if (plan.summary.toFetch === 0) {
                alert(t('alert.syncNoChanges'));
                if (statusElement) statusElement.textContent = t('alert.syncNoChanges');
                return;
            }
            const decision = await showDirectorySyncPlanDialog(plan);
            if (decision === 'cancel') {
                if (statusElement) statusElement.textContent = syncUiText('目录同步已取消。', 'Directory sync cancelled.');
                return;
            }
            if (decision === 'verify') {
                const verification = await verifyDirectoryChangeCandidates({ plan, workspaceId, statusElement });
                if (verification.length) alert(formatVerificationResults(verification));
                if (statusElement) statusElement.textContent = syncUiText('变化项核验完成（未写盘）。', 'Change verification complete (no writes).');
                return;
            }
            if (decision === 'sync_existing') {
                const existingItems = plan.items.filter(item => item.local);
                if (!existingItems.length) {
                    alert(syncUiText('没有需要同步的已有会话变化项。', 'There are no existing-conversation changes to sync.'));
                    return;
                }
                // 仅同步已有变化项属于局部操作：保持主选择窗口打开，
                // 完成提示关闭后用户可继续查看/执行其他操作。
                const existingPlan = { ...plan, items: existingItems };
                const result = await syncDirectoryArchive({
                    rootHandle, remoteList, plan: existingPlan, workspaceId,
                    statusCallback: info => console.log('[目录同步-已有变化项]', info)
                });
                const lines = [
                    syncUiText('ChatHarbor 已有变化项同步完成', 'ChatHarbor existing-change sync complete'), '',
                    `${syncUiText('计划', 'Planned')}：${result.total}`,
                    `${syncUiText('成功', 'Succeeded')}：${result.success}`,
                    `${syncUiText('失败', 'Failed')}：${result.failed}`,
                    `UPDATED：${result.updatedCount}`,
                    `UPDATED + RENAMED：${result.updatedAndRenamedCount}`,
                    `RENAMED ONLY：${result.renamedOnlyCount}`,
                    `METADATA ONLY：${result.metadataOnlyCount}`
                ];
                if (result.failures.length) {
                    lines.push('', `${syncUiText('失败项', 'Failures')}：`);
                    result.failures.slice(0, 10).forEach(x => lines.push(`- ${x.title}: ${x.error}`));
                    if (result.failures.length > 10) lines.push(`...${syncUiText('另有', 'plus')} ${result.failures.length - 10} ${syncUiText('条', 'more')}`);
                }
                alert(lines.join('\n'));
                if (statusElement) statusElement.textContent = syncUiText('已有变化项同步完成。', 'Existing-change sync complete.');
                return;
            }
            if (closeDialog) closeDialog();
            const result = await syncDirectoryArchive({
                rootHandle, remoteList, plan, workspaceId,
                statusCallback: info => console.log('[目录同步]', info)
            });
            const lines = [
                'ChatHarbor 目录同步完成', '',
                `计划：${result.total}`,
                `成功：${result.success}`,
                `失败：${result.failed}`,
                `NEW：${result.newCount}`,
                `UPDATED：${result.updatedCount}`,
                `UPDATED + RENAMED：${result.updatedAndRenamedCount}`,
                `RENAMED ONLY：${result.renamedOnlyCount}`,
                `METADATA ONLY：${result.metadataOnlyCount}`
            ];
            if (result.failures.length) {
                lines.push('', '失败项：');
                result.failures.slice(0, 10).forEach(x => lines.push(`- ${x.title}: ${x.error}`));
                if (result.failures.length > 10) lines.push(`...另有 ${result.failures.length - 10} 条`);
            }
            alert(lines.join('\n'));
        } catch (err) {
            console.error('[目录同步] 失败:', err);
            alert(`目录同步失败：${err.message || err}`);
        }
    }

    // ======================== UI ========================
    function detectAllWorkspaceIds() {
        const foundIds = new Set(capturedWorkspaceIds);
        try {
            const data = JSON.parse(document.getElementById('__NEXT_DATA__').textContent);
            const accounts = data?.props?.pageProps?.user?.accounts;
            if (accounts) {
                Object.values(accounts).forEach(acc => {
                    if (acc?.account?.id) foundIds.add(acc.account.id);
                });
            }
        } catch (e) {}
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && (key.includes('account') || key.includes('workspace'))) {
                    const value = localStorage.getItem(key);
                    if (value && /^[a-z0-9]{2,}-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value.replace(/"/g, ''))) {
                        const extractedId = value.match(/ws-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/i);
                        if (extractedId) foundIds.add(extractedId[0]);
                    } else if (value && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value.replace(/"/g, ''))) {
                        foundIds.add(value.replace(/"/g, ''));
                    }
                }
            }
        } catch (e) {}
        console.log('🔍 检测到以下 Workspace IDs:', Array.from(foundIds));
        return Array.from(foundIds);
    }

    function showConversationPicker(options = {}) {
        const { mode = 'personal', workspaceId = null } = options;
        const existing = document.getElementById('export-dialog-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'export-dialog-overlay';
        Object.assign(overlay.style, {
            position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: '99998',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        });

        const dialog = document.createElement('div');
        dialog.id = 'export-dialog';
        Object.assign(dialog.style, {
            background: '#fff', padding: '24px', borderRadius: '12px',
            boxShadow: '0 5px 15px rgba(0,0,0,.3)', width: '780px', maxHeight: '90vh', overflow: 'auto',
            fontFamily: 'sans-serif', color: '#333', boxSizing: 'border-box'
        });

        const closeDialog = () => document.body.removeChild(overlay);
        const state = {
            list: [], filtered: [], selected: new Set(),
            query: '', scope: mode === 'project' ? 'project' : 'all',
            scopeLocked: mode === 'project', archived: 'all', exportStatus: 'all', timeField: 'update',
            loading: true, pageSize: 100, visibleCount: 100, startDate: '', endDate: ''
        };

        // 选择器列表加载：先快照秒开，再后台指纹探测；force=true 时强制全量刷新
        async function loadPickerListInitial(force) {
            const cacheKey = listCacheKey(mode, workspaceId);
            const snap = getListSnapshot(cacheKey);
            if (snap && snap.entries.length > 0 && !force) {
                state.list = snap.entries.slice();
                state.loading = false;
                applyFilters();
                renderList();
            }
            try {
                const fresh = await refreshListForPicker(mode, workspaceId, snap, force);
                if (fresh) {
                    state.list = fresh;
                    state.loading = false;
                    applyFilters();
                    renderList();
                } else if (snap && !force) {
                    const statusEl = dialog.querySelector('#conv-status');
                    if (statusEl) statusEl.textContent = t('status.listFromCache', { time: formatTimestamp(snap.syncedAt / 1000) || '' });
                }
            } catch (err) {
                const statusEl = dialog.querySelector('#conv-status');
                if (!snap || !state.list || state.list.length === 0) {
                    state.loading = false;
                    state.list = [];
                    state.filtered = [];
                    if (statusEl) statusEl.textContent = t('status.loadFailed', { message: err.message });
                    renderList();
                } else {
                    console.warn('[列表] 后台刷新失败，继续使用缓存:', err.message);
                    if (statusEl) statusEl.textContent = `${t('status.listFromCache', { time: formatTimestamp(snap.syncedAt / 1000) || '' })}（${err.message}）`;
                }
            }
        }

        const renderBase = () => {
            const modeLabel = t(`mode.${mode === 'team' ? 'team' : mode === 'project' ? 'project' : 'personal'}`);
            const workspaceLabel = workspaceId ? ` (${workspaceId})` : '';
            dialog.innerHTML = `
                <h2 style="margin-top:0; margin-bottom: 12px; font-size: 18px;">${t('dialog.selectConversationsTitle')}</h2>
                <div style="margin-bottom: 12px; color: #666; font-size: 12px;">${t('dialog.space', { mode: modeLabel, workspace: workspaceLabel })}</div>
                
                <div style="display:flex; gap:12px; margin-bottom:12px; flex-wrap:wrap; align-items:center; background:#f8fafc; padding:10px; border-radius:8px;">
                    <label style="font-size:13px;">${t('settings.speed')}：
                        <select id="speed-select" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc;">
                            ${SPEED_LEVELS.map((lv, i) => `<option value="${i}" ${i === currentSpeedIndex ? 'selected' : ''}>${lv.name}</option>`).join('')}
                        </select>
                    </label>
                    <label style="font-size:13px;">${t('settings.maxBatch')}：
                        <select id="max-batch-select" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc;">
                            <option value="5">5</option>
                            <option value="10">10</option>
                            <option value="20" selected>20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                        <input id="max-batch-custom" type="number" min="1" max="200" placeholder="自定义" style="width:70px; padding:4px; margin-left:4px; border-radius:4px; border:1px solid #ccc;">
                    </label>
                </div>

                <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                    <input id="conv-search" type="text" placeholder="${t('dialog.searchPlaceholder')}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box;">
                    <select id="filter-scope" style="padding: 8px 28px 8px 8px; border-radius: 6px; border: 1px solid #ccc;">
                        <option value="all">${t('filter.scopeAll')}</option>
                        <option value="project">${t('filter.scopeProject')}</option>
                        <option value="root">${t('filter.scopeRoot')}</option>
                    </select>
                    <select id="filter-archived" style="padding: 8px 28px 8px 8px; border-radius: 6px; border: 1px solid #ccc;">
                        <option value="all">${t('filter.statusAll')}</option>
                        <option value="active">${t('filter.statusActive')}</option>
                        <option value="archived">${t('filter.statusArchived')}</option>
                    </select>
                    <select id="filter-exported" style="padding: 8px 28px 8px 8px; border-radius: 6px; border: 1px solid #ccc;">
                        <option value="all">${t('filter.exportAll')}</option>
                        <option value="unexported">${t('filter.exportUnexported')}</option>
                        <option value="exported">${t('filter.exportExported')}</option>
                    </select>
                </div>
                <div style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center;">
                    <select id="filter-time-field" style="padding: 8px 28px 8px 8px; border-radius: 6px; border: 1px solid #ccc;">
                        <option value="update">${t('filter.timeUpdate')}</option>
                        <option value="create">${t('filter.timeCreate')}</option>
                    </select>
                    <input id="filter-start-date" type="date" style="padding: 8px; border-radius: 6px; border: 1px solid #ccc;">
                    <span style="color: #666; font-size: 12px;">${t('filter.dateTo')}</span>
                    <input id="filter-end-date" type="date" style="padding: 8px; border-radius: 6px; border: 1px solid #ccc;">
                    <button id="clear-date-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.clearDates')}</button>
                </div>
                <div id="conv-status" style="margin-bottom: 8px; font-size: 12px; color: #666;">${t('status.loadingList')}</div>
                <div id="conv-list" style="max-height: 360px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fff;"></div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; flex-wrap:wrap; gap:8px;">
                    <div style="display: flex; gap: 8px;">
                        <button id="select-all-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.selectAll')}</button>
                        <button id="clear-all-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.clear')}</button>
                        <button id="export-history-btn" style="padding: 8px 12px; border: 1px solid #93c5fd; border-radius: 6px; background: #eff6ff; color:#1d4ed8; cursor: pointer; font-size:12px;">${t('button.exportHistory')}</button>
                        <button id="refresh-list-btn" title="${t('status.refreshListHint')}" style="padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color:#475569; cursor: pointer; font-size:12px;">${t('button.refreshList')}</button>
                        <button id="import-history-btn" style="padding: 8px 12px; border: 1px solid #bfdbfe; border-radius: 6px; background: #fff; color:#1d4ed8; cursor: pointer; font-size:12px;">${t('button.importHistory')}</button>
                        <button id="import-zips-btn" style="padding: 8px 12px; border: 1px solid #a7f3d0; border-radius: 6px; background: #ecfdf5; color:#047857; cursor: pointer; font-size:12px;">${t('button.importZips')}</button>
                        <button id="sync-directory-btn" style="padding: 8px 12px; border: 1px solid #67e8f9; border-radius: 6px; background: #ecfeff; color:#0e7490; cursor: pointer; font-size:12px; font-weight:bold;">${t('button.syncDirectory')}</button>
                        <button id="clear-exported-btn" style="padding: 8px 12px; border: 1px solid #fca5a5; border-radius: 6px; background: #fef2f2; color:#b91c1c; cursor: pointer; font-size:12px;">${t('button.clearExported')}</button>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="back-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.back')}</button>
                        <button id="export-selected-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;" disabled>${t('button.exportSelected', { count: 0 })}</button>
                    </div>
                </div>
            `;

            // 绑定设置
            dialog.querySelector('#speed-select').onchange = (e) => setSpeedLevel(Number(e.target.value));
            const maxBatchSelect = dialog.querySelector('#max-batch-select');
            const maxBatchCustom = dialog.querySelector('#max-batch-custom');
            maxBatchSelect.onchange = () => {
                MAX_EXPORT_PER_BATCH = Number(maxBatchSelect.value);
                maxBatchCustom.value = '';
            };
            maxBatchCustom.onchange = () => {
                const v = Number(maxBatchCustom.value);
                if (v > 0 && v <= 200) {
                    MAX_EXPORT_PER_BATCH = v;
                    maxBatchSelect.value = '';
                }
            };

            const searchInput = dialog.querySelector('#conv-search');
            const scopeSelect = dialog.querySelector('#filter-scope');
            const archivedSelect = dialog.querySelector('#filter-archived');
            const exportedSelect = dialog.querySelector('#filter-exported');
            const timeFieldSelect = dialog.querySelector('#filter-time-field');
            const startDateInput = dialog.querySelector('#filter-start-date');
            const endDateInput = dialog.querySelector('#filter-end-date');
            const clearDateBtn = dialog.querySelector('#clear-date-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');
            const clearAllBtn = dialog.querySelector('#clear-all-btn');
            const clearExportedBtn = dialog.querySelector('#clear-exported-btn');
            const refreshListBtn = dialog.querySelector('#refresh-list-btn');
            const exportHistoryBtn = dialog.querySelector('#export-history-btn');
            const importHistoryBtn = dialog.querySelector('#import-history-btn');
            const importZipsBtn = dialog.querySelector('#import-zips-btn');
            const syncDirectoryBtn = dialog.querySelector('#sync-directory-btn');
            const backBtn = dialog.querySelector('#back-btn');
            const exportBtn = dialog.querySelector('#export-selected-btn');

            if (state.scopeLocked && scopeSelect) {
                scopeSelect.value = 'project';
                scopeSelect.disabled = true;
                scopeSelect.style.opacity = '0.7';
                scopeSelect.style.cursor = 'not-allowed';
                scopeSelect.title = t('dialog.projectScopeLocked');
            }

            searchInput.oninput = (e) => { state.query = e.target.value || ''; applyFilters(); renderList(); };
            scopeSelect.onchange = (e) => { state.scope = e.target.value; applyFilters(); renderList(); };
            archivedSelect.onchange = (e) => { state.archived = e.target.value; applyFilters(); renderList(); };
            exportedSelect.onchange = (e) => { state.exportStatus = e.target.value; applyFilters(); renderList(); };
            timeFieldSelect.onchange = (e) => { state.timeField = e.target.value; applyFilters(); renderList(); };
            startDateInput.onchange = (e) => { state.startDate = e.target.value || ''; applyFilters(); renderList(); };
            endDateInput.onchange = (e) => { state.endDate = e.target.value || ''; applyFilters(); renderList(); };
            clearDateBtn.onclick = () => {
                state.startDate = ''; state.endDate = '';
                startDateInput.value = ''; endDateInput.value = '';
                applyFilters(); renderList();
            };
            selectAllBtn.onclick = () => {
                const exportedSet = getExportedIds();
                state.filtered.forEach(item => { if (!exportedSet.has(item.id)) state.selected.add(item.id); });
                renderList();
            };
            clearAllBtn.onclick = () => { state.selected.clear(); renderList(); };
            clearExportedBtn.onclick = () => {
                if (confirm(t('confirm.clearExportedHistory'))) {
                    clearExportedHistory();
                    renderList();
                }
            };
            refreshListBtn.onclick = () => {
                const statusEl = dialog.querySelector('#conv-status');
                if (statusEl) statusEl.textContent = t('status.loadingList');
                loadPickerListInitial(true);
            };
            backBtn.onclick = () => { closeDialog(); showExportDialog(); };
            exportHistoryBtn.onclick = () => exportHistoryBackup();
            importHistoryBtn.onclick = () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'application/json,.json';
                input.onchange = () => {
                    if (input.files && input.files[0]) {
                        importHistoryBackup(input.files[0]);
                        renderList();
                    }
                };
                input.click();
            };
            importZipsBtn.onclick = () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.zip,application/zip';
                input.multiple = true;
                input.onchange = () => {
                    if (input.files && input.files.length > 0) {
                        importHistoryFromZips(input.files, importZipsBtn);
                        renderList();
                    }
                };
                input.click();
            };
            syncDirectoryBtn.onclick = async () => {
                const statusEl = dialog.querySelector('#conv-status');
                await runDirectorySyncFromPicker({ mode, workspaceId, remoteList: state.list, closeDialog, statusElement: statusEl });
            };
            exportBtn.onclick = async () => {
                if (state.selected.size === 0) return;
                const selectedList = state.list.filter(item => state.selected.has(item.id));
                if (selectedList.length > MAX_EXPORT_PER_BATCH) {
                    const batches = Math.ceil(selectedList.length / MAX_EXPORT_PER_BATCH);
                    if (!confirm(t('alert.batchLimit', { total: selectedList.length, limit: MAX_EXPORT_PER_BATCH, batches }))) return;
                }
                closeDialog();
                await startSelectiveExportProcess(mode, workspaceId, selectedList);
            };
        };

        const applyFilters = () => {
            const query = state.query.trim().toLowerCase();
            const startBound = parseDateInputToEpoch(state.startDate, false);
            const endBound = parseDateInputToEpoch(state.endDate, true);
            const exportedSet = getExportedIds();
            state.filtered = state.list.filter(item => {
                const text = `${item.title || ''} ${item.projectTitle || ''} ${item.id || ''}`.toLowerCase();
                if (query && !text.includes(query)) return false;
                if (state.scope === 'project' && !item.projectTitle) return false;
                if (state.scope === 'root' && item.projectTitle) return false;
                if (state.archived === 'active' && item.is_archived) return false;
                if (state.archived === 'archived' && !item.is_archived) return false;
                if (state.exportStatus !== 'all') {
                    const isExported = exportedSet.has(item.id);
                    if (state.exportStatus === 'exported' && !isExported) return false;
                    if (state.exportStatus === 'unexported' && isExported) return false;
                }
                if (startBound || endBound) {
                    const sourceTime = state.timeField === 'create' ? item.create_time : item.update_time;
                    const ts = normalizeEpochSeconds(sourceTime || 0);
                    if (!ts) return false;
                    if (startBound && ts < startBound) return false;
                    if (endBound && ts > endBound) return false;
                }
                return true;
            });
            state.visibleCount = state.pageSize;
        };

        const renderList = () => {
            const statusEl = dialog.querySelector('#conv-status');
            const listEl = dialog.querySelector('#conv-list');
            const exportBtn = dialog.querySelector('#export-selected-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');
            const clearAllBtn = dialog.querySelector('#clear-all-btn');
            const controlsDisabled = state.loading;

            if (selectAllBtn) selectAllBtn.disabled = controlsDisabled;
            if (clearAllBtn) clearAllBtn.disabled = controlsDisabled;
            if (exportBtn) exportBtn.disabled = controlsDisabled || state.selected.size === 0;

            listEl.innerHTML = '';
            if (state.loading) {
                statusEl.textContent = t('status.loadingList');
                return;
            }

            const visibleCount = Math.min(state.visibleCount, state.filtered.length);
            statusEl.textContent = t('status.listSummary', {
                total: state.list.length, filtered: state.filtered.length,
                visible: visibleCount, selected: state.selected.size
            });
            exportBtn.textContent = t('button.exportSelected', { count: state.selected.size });

            if (state.filtered.length === 0) {
                const empty = document.createElement('div');
                empty.textContent = t('status.noMatches');
                empty.style.color = '#999';
                empty.style.padding = '8px 4px';
                listEl.appendChild(empty);
                return;
            }

            const exportedSet = getExportedIds();
            const visibleItems = state.filtered.slice(0, state.visibleCount);
            visibleItems.forEach(item => {
                const isExported = exportedSet.has(item.id);
                const label = document.createElement('label');
                Object.assign(label.style, {
                    display: 'flex', gap: '8px', padding: '8px',
                    border: '1px solid #e5e7eb', borderRadius: '6px',
                    marginBottom: '8px', cursor: 'pointer', alignItems: 'center',
                    ...(isExported ? { opacity: '0.55' } : {})
                });

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = state.selected.has(item.id);
                checkbox.onchange = (e) => {
                    if (e.target.checked) state.selected.add(item.id);
                    else state.selected.delete(item.id);
                    renderList();
                };

                const content = document.createElement('div');
                content.style.flex = '1';
                content.style.minWidth = '0';

                const title = document.createElement('div');
                title.textContent = item.title || t('fallback.untitledConversation');
                title.style.fontWeight = 'bold';
                title.style.fontSize = '14px';

                const meta = document.createElement('div');
                meta.style.fontSize = '12px';
                meta.style.color = '#666';
                const timeLabelPrefix = state.timeField === 'create' ? t('picker.timeCreated') : t('picker.timeUpdated');
                const timeValue = state.timeField === 'create' ? item.create_time : item.update_time;
                const timeLabel = formatTimestamp(timeValue) || t('picker.unknownTime');
                meta.textContent = `${timeLabelPrefix}: ${timeLabel}`;

                const tags = document.createElement('div');
                tags.style.marginTop = '6px';
                tags.style.display = 'flex';
                tags.style.gap = '6px';
                tags.style.flexWrap = 'wrap';

                if (item.projectTitle) {
                    const projectTag = document.createElement('span');
                    projectTag.textContent = t('picker.projectTag', { title: item.projectTitle });
                    Object.assign(projectTag.style, { background: '#eef2ff', color: '#4338ca', padding: '2px 6px', borderRadius: '999px', fontSize: '11px' });
                    tags.appendChild(projectTag);
                }
                if (item.is_archived) {
                    const archivedTag = document.createElement('span');
                    archivedTag.textContent = t('picker.archivedTag');
                    Object.assign(archivedTag.style, { background: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: '999px', fontSize: '11px' });
                    tags.appendChild(archivedTag);
                }

                content.appendChild(title);
                content.appendChild(meta);
                if (tags.childNodes.length > 0) content.appendChild(tags);

                // 右侧独立导出状态列（右对齐），与"已归档"标签彻底分开
                const exportCol = document.createElement('div');
                exportCol.style.flex = 'none';
                exportCol.style.display = 'flex';
                exportCol.style.alignItems = 'center';
                exportCol.style.paddingLeft = '12px';
                if (isExported) {
                    const pill = document.createElement('span');
                    pill.textContent = `✓ ${t('picker.exportedTag')}`;
                    Object.assign(pill.style, { background: '#d1fae5', color: '#065f46', padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 'bold', whiteSpace: 'nowrap' });
                    exportCol.appendChild(pill);
                }

                label.appendChild(checkbox);
                label.appendChild(content);
                label.appendChild(exportCol);
                listEl.appendChild(label);
            });

            if (state.filtered.length > state.visibleCount) {
                const loadMore = document.createElement('button');
                loadMore.textContent = t('button.loadMore', { count: state.filtered.length - state.visibleCount });
                Object.assign(loadMore.style, { width: '100%', padding: '8px 12px', border: '1px solid #ccc', borderRadius: '6px', background: '#fff', cursor: 'pointer' });
                loadMore.onclick = () => {
                    state.visibleCount = Math.min(state.visibleCount + state.pageSize, state.filtered.length);
                    renderList();
                };
                listEl.appendChild(loadMore);
            }
        };

        renderBase();
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        overlay.onclick = (e) => { if (e.target === overlay) closeDialog(); };

        loadPickerListInitial(false);
    }

    function showExportDialog() {
        if (document.getElementById('export-dialog-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'export-dialog-overlay';
        Object.assign(overlay.style, {
            position: 'fixed', top: '0', left: '0', width: '100%', height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: '99998',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        });

        const dialog = document.createElement('div');
        dialog.id = 'export-dialog';
        Object.assign(dialog.style, {
            background: '#fff', padding: '24px', borderRadius: '12px',
            boxShadow: '0 5px 15px rgba(0,0,0,.3)', width: '480px',
            fontFamily: 'sans-serif', color: '#333', boxSizing: 'border-box'
        });

        const closeDialog = () => document.body.removeChild(overlay);

        let pendingTeamAction = null;
        const renderStep = (step, action = null) => {
            pendingTeamAction = action;
            let html = '';
            switch (step) {
                case 'team': {
                    const detectedIds = detectAllWorkspaceIds();
                    html = `<h2 style="margin-top:0; margin-bottom: 20px; font-size: 18px;">${t('dialog.exportTeamTitle')}</h2>`;
                    if (detectedIds.length > 1) {
                        html += `<div style="background: #eef2ff; border: 1px solid #818cf8; border-radius: 8px; padding: 12px; margin-bottom: 20px;">
                                     <p style="margin: 0 0 12px 0; font-weight: bold; color: #4338ca;">🔎 ${t('dialog.multipleWorkspace')}</p>
                                     <div id="workspace-id-list">`;
                        detectedIds.forEach((id, index) => {
                            html += `<label style="display: block; margin-bottom: 8px; padding: 8px; border-radius: 6px; cursor: pointer; border: 1px solid #ddd; background: #fff;">
                                         <input type="radio" name="workspace_id" value="${id}" ${index === 0 ? 'checked' : ''}>
                                         <code style="margin-left: 8px; font-family: monospace; color: #555;">${id}</code>
                                      </label>`;
                        });
                        html += `</div></div>`;
                    } else if (detectedIds.length === 1) {
                        html += `<div style="background: #f0fdf4; border: 1px solid #4ade80; border-radius: 8px; padding: 12px; margin-bottom: 20px;">
                                     <p style="margin: 0 0 8px 0; font-weight: bold; color: #166534;">✅ ${t('dialog.workspaceDetected')}</p>
                                     <code id="workspace-id-code" style="background: #e0e7ff; padding: 4px 8px; border-radius: 4px; font-family: monospace; color: #4338ca; word-break: break-all;">${detectedIds[0]}</code>
                                   </div>`;
                    } else {
                        html += `<div style="background: #fffbeb; border: 1px solid #facc15; border-radius: 8px; padding: 12px; margin-bottom: 20px;">
                                     <p style="margin: 0; color: #92400e;">⚠️ ${t('dialog.workspaceMissing')}</p>
                                     <p style="margin: 8px 0 0 0; font-size: 12px; color: #92400e;">${t('dialog.workspaceMissingHint')}</p>
                                   </div>
                                   <label for="team-id-input" style="display: block; margin-bottom: 8px; font-weight: bold;">${t('dialog.manualWorkspaceLabel')}</label>
                                   <input type="text" id="team-id-input" placeholder="${t('dialog.workspacePlaceholder')}" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box;">`;
                    }

                    let actionButtons = '';
                    if (pendingTeamAction === 'all') {
                        actionButtons = `<button id="start-team-export-btn" style="padding: 10px 16px; border: none; border-radius: 8px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;">${t('button.exportAllZip')}</button>`;
                    } else if (pendingTeamAction === 'select') {
                        actionButtons = `<button id="start-team-picker-btn" style="padding: 10px 16px; border: 1px solid #ccc; border-radius: 8px; background: #fff; cursor: pointer;">${t('button.selectConversationsExport')}</button>`;
                    } else {
                        actionButtons = `<button id="start-team-export-btn" style="padding: 10px 16px; border: none; border-radius: 8px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;">${t('button.exportAllZip')}</button>
                                     <button id="start-team-picker-btn" style="padding: 10px 16px; border: 1px solid #ccc; border-radius: 8px; background: #fff; cursor: pointer;">${t('button.selectConversationsExport')}</button>`;
                    }

                    html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 24px;">
                                 <button id="back-btn" style="padding: 10px 16px; border: 1px solid #ccc; border-radius: 8px; background: #fff; cursor: pointer;">${t('button.back')}</button>
                                 <div style="display: flex; gap: 8px;">${actionButtons}</div>
                               </div>`;
                    break;
                }
                case 'initial':
                default:
                    html = `<h2 style="margin-top:0; margin-bottom: 16px; font-size: 18px;">${t('dialog.selectSpaceTitle')}</h2>
                            
                            <div style="background:#f8fafc; padding:12px; border-radius:8px; margin-bottom:16px; font-size:13px;">
                                <div style="margin-bottom:8px;">
                                    <label>${t('settings.speed')}：
                                        <select id="main-speed-select" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc;">
                                            ${SPEED_LEVELS.map((lv, i) => `<option value="${i}" ${i === currentSpeedIndex ? 'selected' : ''}>${lv.name}</option>`).join('')}
                                        </select>
                                    </label>
                                </div>
                                <div>
                                    <label>${t('settings.maxBatch')}：
                                        <select id="main-max-batch" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc;">
                                            <option value="5">5</option>
                                            <option value="10">10</option>
                                            <option value="20" selected>20</option>
                                            <option value="50">50</option>
                                            <option value="100">100</option>
                                        </select>
                                    </label>
                                </div>
                            </div>

                            <div style="display: flex; flex-direction: column; gap: 16px;">
                                <div style="padding: 16px; border: 1px solid #ccc; border-radius: 8px; background: #f9fafb;">
                                    <strong style="font-size: 16px;">${t('dialog.personalTitle')}</strong>
                                    <p style="margin: 4px 0 12px 0; color: #666;">${t('dialog.personalCopy')}</p>
                                    <div style="display: flex; gap: 8px;">
                                        <button id="select-personal-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;">${t('button.exportAll')}</button>
                                        <button id="select-personal-picker-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.selectConversationsExport')}</button>
                                    </div>
                                </div>
                                <div style="padding: 16px; border: 1px solid #ccc; border-radius: 8px; background: #f9fafb;">
                                    <strong style="font-size: 16px;">${t('dialog.projectTitle')}</strong>
                                    <p style="margin: 4px 0 12px 0; color: #666;">${t('dialog.projectCopy')}</p>
                                    <div style="display: flex; gap: 8px;">
                                        <button id="select-project-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;">${t('button.exportAll')}</button>
                                        <button id="select-project-picker-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.selectConversationsExport')}</button>
                                    </div>
                                </div>
                                <div style="padding: 16px; border: 1px solid #ccc; border-radius: 8px; background: #f9fafb;">
                                    <strong style="font-size: 16px;">${t('dialog.teamTitle')}</strong>
                                    <p style="margin: 4px 0 12px 0; color: #666;">${t('dialog.teamCopy')}</p>
                                    <div style="display: flex; gap: 8px;">
                                        <button id="select-team-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;">${t('button.exportAll')}</button>
                                        <button id="select-team-picker-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">${t('button.selectConversationsExport')}</button>
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
                                <button id="cancel-btn" style="padding: 10px 16px; border: 1px solid #ccc; border-radius: 8px; background: #fff; cursor: pointer;">${t('button.cancel')}</button>
                            </div>`;
                    break;
            }
            dialog.innerHTML = html;
            attachListeners(step);
        };

        const attachListeners = (step) => {
            if (step === 'initial') {
                const speedSel = document.getElementById('main-speed-select');
                if (speedSel) speedSel.onchange = (e) => setSpeedLevel(Number(e.target.value));
                const maxBatchSel = document.getElementById('main-max-batch');
                if (maxBatchSel) maxBatchSel.onchange = (e) => { MAX_EXPORT_PER_BATCH = Number(e.target.value); };

                document.getElementById('select-personal-btn').onclick = () => {
                    closeDialog();
                    startExportProcess('personal', null);
                };
                document.getElementById('select-personal-picker-btn').onclick = () => {
                    closeDialog();
                    showConversationPicker({ mode: 'personal', workspaceId: null });
                };
                document.getElementById('select-project-btn').onclick = () => {
                    closeDialog();
                    startProjectSpaceExportProcess();
                };
                document.getElementById('select-project-picker-btn').onclick = () => {
                    closeDialog();
                    showConversationPicker({ mode: 'project', workspaceId: null });
                };
                const startTeamFlow = (action) => {
                    const detectedIds = detectAllWorkspaceIds();
                    if (detectedIds.length === 1) {
                        const workspaceId = detectedIds[0];
                        closeDialog();
                        if (action === 'all') startExportProcess('team', workspaceId);
                        else showConversationPicker({ mode: 'team', workspaceId });
                        return;
                    }
                    renderStep('team', action);
                };
                document.getElementById('select-team-btn').onclick = () => startTeamFlow('all');
                document.getElementById('select-team-picker-btn').onclick = () => startTeamFlow('select');
                document.getElementById('cancel-btn').onclick = closeDialog;
            } else if (step === 'team') {
                document.getElementById('back-btn').onclick = () => renderStep('initial');
                const resolveWorkspaceIdLocal = () => {
                    let workspaceId = '';
                    const radioChecked = document.querySelector('input[name="workspace_id"]:checked');
                    const codeEl = document.getElementById('workspace-id-code');
                    const inputEl = document.getElementById('team-id-input');
                    if (radioChecked) workspaceId = radioChecked.value;
                    else if (codeEl) workspaceId = codeEl.textContent;
                    else if (inputEl) workspaceId = inputEl.value.trim();
                    if (!workspaceId) {
                        alert(t('alert.invalidWorkspaceId'));
                        return null;
                    }
                    return workspaceId;
                };
                const exportAllBtn = document.getElementById('start-team-export-btn');
                const pickerBtn = document.getElementById('start-team-picker-btn');
                if (exportAllBtn) exportAllBtn.onclick = () => {
                    const workspaceId = resolveWorkspaceIdLocal();
                    if (!workspaceId) return;
                    closeDialog();
                    startExportProcess('team', workspaceId);
                };
                if (pickerBtn) pickerBtn.onclick = () => {
                    const workspaceId = resolveWorkspaceIdLocal();
                    if (!workspaceId) return;
                    closeDialog();
                    showConversationPicker({ mode: 'team', workspaceId });
                };
            }
        };

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        overlay.onclick = (e) => { if (e.target === overlay) closeDialog(); };
        renderStep('initial');
    }

    function addBtn() {
        if (document.getElementById('gpt-rescue-btn')) return;
        const b = document.createElement('button');
        b.id = 'gpt-rescue-btn';
        b.textContent = t('button.export');
        Object.assign(b.style, {
            position: 'fixed', bottom: '24px', right: '24px', zIndex: '99997',
            padding: '10px 14px', borderRadius: '8px', border: 'none', cursor: 'pointer',
            fontWeight: 'bold', background: '#10a37f', color: '#fff', fontSize: '14px',
            boxShadow: '0 3px 12px rgba(0,0,0,.15)', userSelect: 'none'
        });
        b.onclick = () => {
            if (exportRunning) {
                if (confirm(t('confirm.cancelExport'))) cancelExport();
                return;
            }
            showExportDialog();
        };
        document.body.appendChild(b);
    }

    setTimeout(addBtn, 2000);

    window.ChatGPTExporter = window.ChatGPTExporter || {};
    Object.assign(window.ChatGPTExporter, {
        showDialog: showExportDialog,
        startManualExport: (mode = 'personal', workspaceId = null) => {
            if (mode === 'project') return startProjectSpaceExportProcess(workspaceId);
            return startExportProcess(mode, workspaceId);
        },
        startScheduledExport,
        cancelExport
    });

    document.documentElement.setAttribute('data-chatgpt-exporter-ready', '1');
    window.dispatchEvent(new CustomEvent('CHATGPT_EXPORTER_READY'));

    window.addEventListener('message', (event) => {
        if (event.source !== window) return;
        const data = event.data || {};
        if (data?.type !== 'CHATGPT_EXPORTER_COMMAND') return;
        const api = window.ChatGPTExporter;
        if (!api) return;
        try {
            switch (data.action) {
                case 'START_SCHEDULED_EXPORT':
                    api.startScheduledExport(data.payload || {});
                    break;
                case 'OPEN_DIALOG':
                    api.showDialog();
                    break;
                case 'START_MANUAL_EXPORT':
                    api.startManualExport(data.payload?.mode, data.payload?.workspaceId);
                    break;
                default:
                    console.warn('[ChatGPT Exporter] 未知命令:', data.action);
            }
        } catch (err) {
            console.error('[ChatGPT Exporter] 处理命令失败:', err);
        }
    });

})();