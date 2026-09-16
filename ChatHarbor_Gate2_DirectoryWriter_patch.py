#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_GIT_BLOB = "3a5dfe6a696e03db7028232d45b136104e67b51f"

def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

if len(sys.argv) < 2:
    print("Usage: python ChatHarbor_Gate2_DirectoryWriter_patch.py <Tampermonkey.js> [output.user.js]")
    raise SystemExit(2)

src = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name("ChatHarbor-Gate2.user.js")
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
    "// @name         ChatHarbor Gate 2 (Clean Lineage)\n"
    "// @name:zh-CN   ChatHarbor Gate 2（干净来源测试版）\n"
    "// @version      0.0.2-gate2\n"
    "// @description  Clean-lineage directory-writer test based on huhusmang/ChatGPT-Exporter.\n"
    "// @description:zh-CN 基于 huhusmang/ChatGPT-Exporter 的干净来源目录写入测试版。\n"
    "// @author       huhu; ChatHarbor contributors\n"
)

anchor = "    async function exportConversations(options = {}) {\n"
if anchor not in text:
    raise SystemExit("Insertion anchor not found: exportConversations")

directory_writer = r'''
    // ======================== ChatHarbor Gate 2: Directory Writer ========================
    // Clean-lineage implementation. Uses huhusmang's conversation/attachment parsing,
    // but writes derived archive files directly to a user-selected directory.

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

    async function chWriteAttachmentsToDirectory(targetDir, convData, workspaceId) {
        const references = collectVisibleAttachments(convData);
        const failures = [];
        const files = [];
        const sandboxPaths = new Map();
        const usedNames = new Set();

        const folderName = generateUniqueFilename(convData).replace(/\.json$/i, '') + '_files';
        const assetDir = await targetDir.getDirectoryHandle(folderName, { create: true });

        for (const reference of references) {
            try {
                const downloaded = await fetchAttachmentBinary(reference, convData, workspaceId);
                const filename = uniqueAttachmentName(downloaded.filename, usedNames);
                await chVerifiedDirectoryWrite(assetDir, filename, downloaded.data);

                const relativePath = encodeRelativePath(`${folderName}/${filename}`);
                files.push({
                    name: filename,
                    path: relativePath,
                    kind: reference.kind,
                    isImage: reference.isImage,
                    messageId: reference.messageId,
                    ownerRole: reference.ownerRole
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
            await sleep(150);
        }

        return { detected: references.length, files, failures, sandboxPaths };
    }

    async function chWriteConversationToDirectory(rootHandle, entry, convData, workspaceId, includeAttachments) {
        let targetDir = rootHandle;
        let relativePrefix = '';

        if (entry?.projectTitle) {
            const projectDirName = sanitizeFilename(entry.projectTitle) || 'Untitled Project';
            targetDir = await rootHandle.getDirectoryHandle(projectDirName, { create: true });
            relativePrefix = `${projectDirName}/`;
        }

        const attachmentResult = includeAttachments
            ? await chWriteAttachmentsToDirectory(targetDir, convData, workspaceId)
            : null;

        const jsonFilename = generateUniqueFilename(convData);
        const markdownFilename = generateMarkdownFilename(convData);
        const jsonText = JSON.stringify(convData, null, 2);
        const markdownText = convertConversationToMarkdown(convData, attachmentResult);

        await chVerifiedDirectoryWrite(targetDir, jsonFilename, jsonText);
        await chVerifiedDirectoryWrite(targetDir, markdownFilename, markdownText);

        return {
            conversation_id: convData?.conversation_id || convData?.id || entry?.id || null,
            title: convData?.title || entry?.title || 'Untitled Conversation',
            json_path: `${relativePrefix}${jsonFilename}`,
            markdown_path: `${relativePrefix}${markdownFilename}`,
            attachment_detected: attachmentResult?.detected || 0,
            attachment_downloaded: attachmentResult?.files?.length || 0,
            attachment_failed: attachmentResult?.failures?.length || 0
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

        if (!await ensureAccessToken()) {
            btn.disabled = false;
            setFabStatus(btn, EXPORT_BUTTON_LABEL);
            return;
        }

        const results = [];
        let failed = 0;

        try {
            for (let i = 0; i < conversationEntries.length; i++) {
                const entry = conversationEntries[i];
                const label = entry?.title ? entry.title.slice(0, 12) : '对话';
                setFabStatus(btn, `💾 ${label} (${i + 1}/${conversationEntries.length})`);

                try {
                    const convData = await getConversation(entry.id, workspaceId);
                    const result = await chWriteConversationToDirectory(
                        rootHandle, entry, convData, workspaceId, includeAttachments
                    );
                    results.push(result);
                } catch (err) {
                    failed++;
                    console.error('[ChatHarbor Gate 2] Directory write failed:', entry?.id, err);
                }

                if (i + 1 < conversationEntries.length) await sleep(jitter());
            }

            const downloadedAttachments = results.reduce((n, item) => n + item.attachment_downloaded, 0);
            const failedAttachments = results.reduce((n, item) => n + item.attachment_failed, 0);

            alert(
                `ChatHarbor Gate 2 目录写入完成。\n\n` +
                `计划：${conversationEntries.length}\n` +
                `成功：${results.length}\n` +
                `失败：${failed}\n` +
                `附件成功：${downloadedAttachments}\n` +
                `附件失败：${failedAttachments}\n\n` +
                `本阶段尚未写入 manifest，也尚未进行版本判断。`
            );
            setFabStatus(btn, failed ? '⚠️ Gate 2 完成' : '✅ Gate 2 完成');

            return { planned: conversationEntries.length, succeeded: results.length, failed, results };
        } finally {
            setTimeout(() => {
                btn.disabled = false;
                setFabStatus(btn, EXPORT_BUTTON_LABEL);
            }, 1500);
        }
    }

'''
text = text.replace(anchor, directory_writer + anchor, 1)

old_buttons = '''                        <button id="back-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">返回</button>
                        <button id="export-selected-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;" disabled>导出选中 (0)</button>'''
new_buttons = '''                        <button id="back-btn" style="padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; background: #fff; cursor: pointer;">返回</button>
                        <button id="sync-selected-test-btn" style="padding: 8px 12px; border: 1px solid #10a37f; border-radius: 6px; background: #fff; color: #0f766e; cursor: pointer; font-weight: bold;" disabled>写入选中到目录 (0)</button>
                        <button id="export-selected-btn" style="padding: 8px 12px; border: none; border-radius: 6px; background: #10a37f; color: #fff; cursor: pointer; font-weight: bold;" disabled>导出选中 (0)</button>'''
if old_buttons not in text:
    raise SystemExit("Picker button anchor not found")
text = text.replace(old_buttons, new_buttons, 1)

first_query = "            const exportBtn = dialog.querySelector('#export-selected-btn');\n"
if first_query not in text:
    raise SystemExit("Picker query anchor not found")
text = text.replace(
    first_query,
    "            const syncTestBtn = dialog.querySelector('#sync-selected-test-btn');\n" + first_query,
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

sync_handler = r'''            syncTestBtn.onclick = async () => {
                if (state.selected.size === 0) return;
                if (!window.showDirectoryPicker) {
                    alert('当前浏览器不支持 File System Access API。请使用新版 Edge / Chromium。');
                    return;
                }

                const rootHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
                const selectedList = state.list.filter(item => state.selected.has(item.id));

                syncTestBtn.disabled = true;
                exportBtn.disabled = true;
                try {
                    await chDirectoryWriteSelected({
                        rootHandle,
                        mode,
                        workspaceId,
                        conversationEntries: selectedList,
                        includeAttachments: state.includeAttachments
                    });
                } finally {
                    syncTestBtn.disabled = state.loading || state.selected.size === 0;
                    exportBtn.disabled = state.loading || state.selected.size === 0;
                }
            };

'''
text = text.replace(handler_anchor, sync_handler + handler_anchor, 1)

render_query_anchor = '''            const exportBtn = dialog.querySelector('#export-selected-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');'''
render_query_repl = '''            const syncTestBtn = dialog.querySelector('#sync-selected-test-btn');
            const exportBtn = dialog.querySelector('#export-selected-btn');
            const selectAllBtn = dialog.querySelector('#select-all-btn');'''
if render_query_anchor not in text:
    raise SystemExit("renderList query anchor not found")
text = text.replace(render_query_anchor, render_query_repl, 1)

disabled_anchor = '''            if (clearAllBtn) clearAllBtn.disabled = controlsDisabled;
            if (exportBtn) exportBtn.disabled = controlsDisabled || state.selected.size === 0;'''
disabled_repl = '''            if (clearAllBtn) clearAllBtn.disabled = controlsDisabled;
            if (syncTestBtn) syncTestBtn.disabled = controlsDisabled || state.selected.size === 0;
            if (exportBtn) exportBtn.disabled = controlsDisabled || state.selected.size === 0;'''
if disabled_anchor not in text:
    raise SystemExit("renderList disabled anchor not found")
text = text.replace(disabled_anchor, disabled_repl, 1)

text_anchor = "            exportBtn.textContent = `导出选中 (${state.selected.size})`;\n"
if text_anchor not in text:
    raise SystemExit("renderList text anchor not found")
text = text.replace(
    text_anchor,
    "            if (syncTestBtn) syncTestBtn.textContent = `写入选中到目录 (${state.selected.size})`;\n" + text_anchor,
    1
)

out.write_text(text, encoding="utf-8")
print(f"Wrote: {out}")
print(f"Source git blob: {actual_blob}")
print(f"Output SHA-256: {hashlib.sha256(out.read_bytes()).hexdigest()}")
