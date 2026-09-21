# ChatHarbor v0.0.14.5 — Greasy Fork Publication Package

Date: **2026-09-21**  
Status: **Published / Human-confirmed**  
Runtime baseline: **ChatHarbor v0.0.14.5**  
Distribution policy: GitHub is authoritative; Greasy Fork is a secondary distribution channel.

## Publication result

- Greasy Fork page: https://greasyfork.org/scripts/596705-chatharbor
- Published by the maintainer through the maintainer's Greasy Fork account on 2026-09-21.
- Publication status is Human-confirmed from the maintainer's completed submission and returned public page URL.
- Automated external verification was attempted immediately after publication, but the current retrieval environment could not fetch the Greasy Fork page directly and search indexing had not yet surfaced the new script. Those checks therefore remain unverified rather than inferred.

## 1. Publication decision

Publish the existing `ChatHarbor.user.js` for v0.0.14.5 as an ordinary **user script**, not as a library.

For the first Greasy Fork release:

- use the exact v0.0.14.5 runtime code currently on `main`;
- do not change `@version`;
- do not change `@downloadURL` / `@updateURL` in the GitHub source;
- do not enable GitHub webhook / automatic external-source synchronization yet;
- do not maintain Greasy-Fork-only code changes;
- future Greasy Fork versions are published only after the corresponding GitHub-authoritative release is complete.

Greasy Fork may rewrite update/download metadata in its hosted copy. That is expected platform behavior and does not change the GitHub source.

## 2. Pre-publication compliance check

Current script facts:

- Script size: approximately 349 KB, below Greasy Fork's 2 MB limit.
- Required metadata present: `@name`, localized name, `@description`, localized description, `@namespace`, `@version`, `@match`, `@license`.
- `@supportURL` points to the GitHub issue tracker.
- `@homepageURL` / `@source` point to the authoritative GitHub repository.
- External executable dependency: JSZip 3.10.1 through `cdnjs.cloudflare.com`.
- cdnjs is an allowed Greasy Fork CDN.
- Repository scan found no direct matches for `eval(`, dynamic script-element injection, `GM_xmlhttpRequest`, analytics, tracking, or `sendBeacon`.
- Metadata uses `@grant none`.
- No ads, tracking, mining, or other known author-benefit antifeature was identified.
- Script is readable source, not minified/obfuscated.

Assessment: no obvious Greasy Fork code-rule blocker was identified for the v0.0.14.5 publication candidate.

## 3. Source to submit

Submit the exact contents of:

`ChatHarbor.user.js`

from the authoritative ChatHarbor GitHub repository on `main`.

Expected metadata identity:

```text
@name         ChatHarbor
@version      0.0.14.5
@namespace    https://github.com/git-czxy/chat-harbor
@license      MIT
```

Do not publish the historical provenance backfill tool as part of the main ChatHarbor Greasy Fork script.

## 4. Recommended Greasy Fork settings

- Type: User script
- Adult content: No
- Default publication language for additional info: English
- Add localized additional info: Simplified Chinese (`zh-CN`)
- Automatic external-source/webhook synchronization: Off for the first release
- Install/update authority for Greasy Fork users: Greasy Fork-hosted copy, as rewritten by Greasy Fork
- Source/repository/support authority: GitHub

If the form exposes options not covered here and they affect code ownership, automatic synchronization, permissions, monetization, or publication visibility, stop before submission and treat them as a human gate.

## 5. English additional information

### ChatHarbor

ChatHarbor is a **local-first ChatGPT conversation archive and integrity-audit userscript**.

It continuously saves your own ChatGPT conversations to a local directory you choose and makes archive gaps explicit rather than hiding them.

Main capabilities include:

- incremental synchronization using stable conversation identity and content signatures;
- local JSON, Markdown, attachment assets, and Manifest records;
- project and archived-conversation awareness;
- attachment provenance and integrity status;
- transparent diagnostics for attachment failures such as 403 / 404 / 415 / 500 or expired download URLs;
- links back to the original ChatGPT conversation for manual verification;
- conservative request pacing, bounded retry, pause/resume, and safe cancellation;
- transactional local writes and auditable preflight/sync-completion reports.

### Important limitation

ChatHarbor does **not** promise a 100% complete backup.

Some ChatGPT attachments may no longer be obtainable from the platform. ChatHarbor preserves the known failure evidence and makes the gap visible and traceable instead of presenting an unsupported “complete” result.

### Recommended environment

Desktop Chromium browser, especially Chrome or Edge, with Tampermonkey.

The archive workflow uses browser directory-access capabilities, so behavior may differ in other browsers or userscript managers.

### Privacy

ChatHarbor operates in your existing ChatGPT browser session and writes archive data to the local directory you select.

The project does not operate an upload server for your archived conversations. JSZip is loaded from cdnjs as declared in the userscript metadata.

### Project and support

The GitHub repository is the authoritative source for code, release history, issue tracking, licensing, provenance, and release notes.

## 6. 中文附加信息（zh-CN）

### ChatHarbor

ChatHarbor 是一个**本地优先的 ChatGPT 对话归档与完整性审计 Userscript**。

它把你自己的 ChatGPT 对话持续保存到你选择的本地目录，并明确呈现归档缺口，而不是把失败隐藏成“已完成”。

主要能力包括：

- 以稳定会话身份和内容签名进行增量同步；
- 本地保存 JSON、Markdown、附件资源和 Manifest；
- 识别项目会话与归档状态；
- 记录附件来源和完整性状态；
- 对 403 / 404 / 415 / 500、临时下载 URL 失效等附件失败保留原始证据并提供解释；
- 可从附件缺口返回 ChatGPT 原会话人工核查；
- 保守请求间隔、有限重试、暂停/恢复和安全取消；
- 事务式本地写入，以及可审计的预检和同步完成报告。

### 重要限制

ChatHarbor **不承诺 100% 完整备份**。

部分 ChatGPT 附件可能已经无法从平台取得。ChatHarbor 的目标是保留已知失败证据，让缺口透明、可追溯、可核查，而不是把无法验证的状态宣称为“完整”。

### 推荐环境

桌面 Chromium 浏览器，优先 Edge / Chrome，并配合 Tampermonkey 使用。

归档流程依赖浏览器目录访问能力，因此其他浏览器或 Userscript 管理器的兼容性可能不同。

### 隐私

ChatHarbor 在你现有的 ChatGPT 浏览器登录态中运行，并把归档数据写入你自己选择的本地目录。

本项目不运营用于接收你对话归档的上传服务器。脚本 metadata 中声明的 JSZip 通过 cdnjs 加载。

### 项目与支持

GitHub 仓库是代码、版本发布、问题反馈、许可证、来源说明和 Release Notes 的权威来源。

## 7. Human-only submission steps

The following actions require the maintainer's own Greasy Fork account/session:

1. Sign in to Greasy Fork (create/verify an account if needed).
2. From the user profile, choose **Publish a script you've written**.
3. Paste/submit the exact v0.0.14.5 `ChatHarbor.user.js` code.
4. Keep it as a normal user script, not a library.
5. Add the English additional information above.
6. Add localized additional information for `zh-CN` using the Chinese text above.
7. Do not enable automatic GitHub/webhook synchronization for this first release.
8. Review the Greasy Fork validation result. If Greasy Fork raises a warning/error not covered by this package, do not bypass it; capture the exact message for assessment.
9. Publish only after the preview shows version `0.0.14.5`, the expected ChatGPT matches, MIT license, and the intended description.

## 8. Post-publication verification

After publication, verify:

- script page title is ChatHarbor;
- version is `0.0.14.5`;
- install target is the Greasy Fork-hosted script;
- Greasy Fork has rewritten its hosted `@updateURL` / `@downloadURL` as expected;
- GitHub repository/support links remain visible;
- English and zh-CN additional information render correctly;
- install from Greasy Fork works in Tampermonkey on desktop Chrome/Edge;
- opening ChatGPT exposes the ChatHarbor launcher;
- no unexpected metadata, antifeature, or permission warning appears.

Final Greasy Fork script page URL recorded above. Publication is complete; browser-install smoke verification remains a separate validation step until directly observed.
