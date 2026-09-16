# ChatHarbor 历史版本恢复清单（Git Reconstruction Inventory）

**日期：** 2026-09-16  
**性质：** 只读恢复审计；未修改任何历史源码，未初始化 Git。

## 结论

- 已找到并实际读取 **19 个编号发布包**：`0.0.6.1` ～ `0.0.14.1`。
- 19 个编号发布包的 `CHECKSUMS.sha256` **全部内部校验通过**。
- 其中 **18 个版本**的 ZIP SHA-256 已与历史开发记录中的发布 SHA 逐字节匹配。
- `0.0.14.1` 的发布 ZIP、README、CHANGELOG、TEST_REPORT 和当前实际 userscript 均保存；当前导出的开发会话中未找到该 ZIP 的历史 SHA 文本，因此标为“保留工件已核验，但缺历史聊天 SHA 交叉证据”，不是失败。
- 所有编号发布 ZIP 都是**源码/构建包**，不内嵌最终 `.user.js`；历史最终 userscript 需要未来通过固定 upstream + 当版 patcher 重建。当前 `0.0.14.1.user.js` 单独保存。
- `v0.5.0` 应保留为历史/行为参考，但根据 provenance audit **不能作为 clean-lineage 公共 Git 主线祖先**。clean-lineage 应从固定 huhusmang 基线与 Gate 快照开始。

## 当前运行件

- `ChatHarbor-IntegratedSync-0.0.14.1.user.js`
- `@version = 0.0.14.1`
- bytes = 311505
- SHA-256 = `0f74da1b51dbf6e3ef393e0c04372adb90fb07a0d3899ed1dc645ded4bf0191e`

## 编号发布版本

| 版本 | 日期 | ZIP SHA 历史交叉核验 | 包内 checksum | README | Test | CHANGELOG | Git 恢复判断 |
|---|---|---|---|---|---|---|---|
| 0.0.6.1 | 2026-09-14 | MATCH | PASS (7) | ✓ | ✓ | — | COMMIT_CANDIDATE |
| 0.0.7.0 | 2026-09-14 | MATCH | PASS (8) | ✓ | ✓ | — | COMMIT_CANDIDATE |
| 0.0.8.0 | 2026-09-14 | MATCH | PASS (10) | ✓ | ✓ | — | COMMIT_CANDIDATE |
| 0.0.9.0 | 2026-09-14 | MATCH | PASS (12) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.9.1 | 2026-09-14 | MATCH | PASS (12) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.9.2 | 2026-09-14 | MATCH | FAIL (12) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.9.3 | 2026-09-14 | MATCH | PASS (12) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.10.0 | 2026-09-14 | MATCH | PASS (15) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.10.1 | 2026-09-14 | MATCH | PASS (15) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.11.0 | 2026-09-14 | MATCH | PASS (16) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.11.1 | 2026-09-14 | MATCH | PASS (7) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.11.2 | 2026-09-15 | MATCH | PASS (15) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.11.3 | 2026-09-15 | MATCH | PASS (16) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.11.4 | 2026-09-15 | MATCH | PASS (16) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.12.0 | 2026-09-15 | MATCH | PASS (17) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.13.0 | 2026-09-15 | MATCH | PASS (18) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.13.1 | 2026-09-15 | MATCH | PASS (18) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.14.0 | 2026-09-15 | MATCH | PASS (18) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |
| 0.0.14.1 | 2026-09-16 | NO_HISTORICAL_SHA_FOUND | PASS (18) | ✓ | ✓ | ✓ | COMMIT_CANDIDATE |

### ZIP SHA-256

- `0.0.6.1` `49e9ffd15de4d108d4f7ec207988fd91c5c15b0ea7be670af9d414c1ecfc8b6a` — `ChatHarbor_clean_lineage_integrated_sync_0.0.6.1_hotfix.zip`
- `0.0.7.0` `710e44a6d62b53f9b73f12186de25922d44392043b9c9c21665384f9429f964e` — `ChatHarbor_clean_lineage_integrated_sync_0.0.7.0_conservative.zip`
- `0.0.8.0` `8e78c83c20d8332ce4cd3ccd36ab99cefa79466cdae7ba3d9d2485cb2122814b` — `ChatHarbor_clean_lineage_integrated_sync_0.0.8.0_desktop_workspace.zip`
- `0.0.9.0` `b27aacd20abcbc18a34c74d05cbf9deedb4817af68c82a9c94aa4a3bcf45a655` — `ChatHarbor_clean_lineage_integrated_sync_0.0.9.0_streaming_sync.zip`
- `0.0.9.1` `4f3727951bb961597b190a2d2e8556dd30db001fc61f8188e40480a663c61753` — `ChatHarbor_clean_lineage_integrated_sync_0.0.9.1_batch_countdown.zip`
- `0.0.9.2` `d0d01a55e727a759d67cfc8246bd58409d47f48b4ea803515078a18b154295ca` — `ChatHarbor_clean_lineage_integrated_sync_0.0.9.2_cached_index_compact_rail.zip`
- `0.0.9.3` `a4da3489128be896ab593ccce21d22b993baf53639b4f873b97d5e014b3ddb3c` — `ChatHarbor_clean_lineage_integrated_sync_0.0.9.3_ui_clarity.zip`
- `0.0.10.0` `f8dbb2bec49d68ba22e4d46086a2ae05096a648200950a7552182a8a2b3d17fd` — `ChatHarbor_clean_lineage_integrated_sync_0.0.10.0_layout_v2.zip`
- `0.0.10.1` `ce8ea65cd28304b21378b0322127ffe44dca4264488053f238e84dfde098fe7e` — `ChatHarbor_clean_lineage_integrated_sync_0.0.10.1_ui_state_lock.zip`
- `0.0.11.0` `c7692fbcd3d5869fad231ede450fc2fdd1bd0d18c829b5b9c57032db31408542` — `ChatHarbor_clean_lineage_integrated_sync_0.0.11.0_incremental_convergence_cache.zip`
- `0.0.11.1` `e86d7fcfd517ad7f92824559f37b4a19861b3f9af2b7490e9ec7f2b5072eec01` — `ChatHarbor_clean_lineage_integrated_sync_0.0.11.1_runtime_ux_hotfix.zip`
- `0.0.11.2` `c3dca909a7843174892496b8fe0f17d3f88cb6b7872cca6abe51a7520bdfcd10` — `ChatHarbor_clean_lineage_integrated_sync_0.0.11.2_installation_hotfix.zip`
- `0.0.11.3` `cf2b76231a644e57b007badc2583ba72c6618dfd79276767111316799e9b16e5` — `ChatHarbor_clean_lineage_integrated_sync_0.0.11.3_build_invariant_hotfix.zip`
- `0.0.11.4` `baf46faeef267ea44142f872fb07dcfb61c4189dff6d7f9f3f5a581641379556` — `ChatHarbor_clean_lineage_integrated_sync_0.0.11.4_attachment_incremental_hotfix.zip`
- `0.0.12.0` `62fe635d582350edf0a33470f7d271e7b8024c8208b106dc4566965e0edecc46` — `ChatHarbor_clean_lineage_integrated_sync_0.0.12.0_runtime_convergence.zip`
- `0.0.13.0` `9dca4b132f97335cdc2e0e489949500add928abe58b8873f843fa6a7d13ca1bb` — `ChatHarbor_clean_lineage_integrated_sync_0.0.13.0_lane_aware_discovery.zip`
- `0.0.13.1` `9ef98369c4065a228ddc5e3204e095125d59afe4327978fb56e371271d73adb7` — `ChatHarbor_clean_lineage_integrated_sync_0.0.13.1_typed_failure_observable_retry.zip`
- `0.0.14.0` `283166a6845b7f18eba8731dd4a5b203f1ff2949700f861d48f1f4bbb043f81a` — `ChatHarbor_clean_lineage_integrated_sync_0.0.14.0_user_facing_ux_convergence.zip`
- `0.0.14.1` `6a325066cd27d83120de3cdce37d54acae445178ef0f05f32654d32a47094768` — `ChatHarbor_clean_lineage_integrated_sync_0.0.14.1_first_use_selection_ux.zip`

## Clean-lineage 前置快照

- **clean-gate2** — `ChatHarbor_clean_gate2.zip` — SHA-256 `b18fc9341551c1aec66aad6c4dbd5cfd1cb9f6fc5998b4ab17f7d2e81fc43ae7` — internal checksum `PASS` — **PRE_RELEASE_COMMIT_CANDIDATE**
  - Clean-lineage gate snapshot; package preserved and internal checksums verified.
- **clean-gate3** — `ChatHarbor_clean_gate3.zip` — SHA-256 `8c9f371a1994a14f1a06eae21ac655a89c9ecf0ce5e3e10a44d37e2d34b622c3` — internal checksum `PASS` — **PRE_RELEASE_COMMIT_CANDIDATE**
  - Clean-lineage gate snapshot; package preserved and internal checksums verified.
- **clean-gate3_1** — `ChatHarbor_clean_gate3_1.zip` — SHA-256 `987efd0a172a91350de2159766448886494b3175e80eae33bbb77f05589e7546` — internal checksum `PASS` — **PRE_RELEASE_COMMIT_CANDIDATE**
  - Clean-lineage gate snapshot; package preserved and internal checksums verified.
- **clean-gate4a** — `ChatHarbor_clean_gate4a_preflight.zip` — SHA-256 `7b2531ff8ccff0d875bd7aca38041e4aa609557d617f26c5b91fd6b8cde4bbf7` — internal checksum `PASS` — **PRE_RELEASE_COMMIT_CANDIDATE**
  - Clean-lineage pre-release gate snapshot.
- **clean-integrated** — `ChatHarbor_clean_lineage_integrated_sync_2026-09-14.zip` — SHA-256 `f108c070764855c957a75ddf455a60ae1018c33a0ebb0440c0c9e4345d7a8d41` — internal checksum `PASS` — **PRE_RELEASE_COMMIT_CANDIDATE**
  - Clean-lineage integrated snapshot immediately before numbered releases.
- **legacy-v0.5.0** — `ChatHarbor_v0.5.0.zip` — SHA-256 `1c748351c1152d3d45f0f72e668c650e5b7e187d845977833edbf49f84ffadbe` — internal checksum `PASS` — **LEGACY_REFERENCE_ONLY**
  - Historical/reference artifact with direct OwlCt-linked provenance; preserve, but do not make it an ancestor of the clean-lineage public branch.

## 共同上游事实

- repository: `huhusmang/ChatGPT-Exporter`
- pinned commit(s): `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- pinned Tampermonkey Git blob(s): `3a5dfe6a696e03db7028232d45b136104e67b51f`

## 推荐的 Git 重建边界

```text
legacy/reference (not ancestor): v0.4 / v0.5.0

clean upstream: huhusmang/ChatGPT-Exporter @ efa1f0f...
    ↓
Gate 2 → Gate 3 → Gate 3.1 → Gate 4A → integrated snapshot
    ↓
v0.0.6.1 → v0.0.7.0 → ... → v0.0.14.1
    ↓
future normal Git development
```

## 下一阶段（尚未执行）

1. 从每个 ZIP 解出**完整源码树快照**，统一去掉包裹目录名，但不修改文件内容。
2. 用固定上游 commit/blob 验证每版 patcher 的输入基线。
3. 能确定原始历史时间的节点，用原始时间作为 Git commit author/committer date；提交说明明确标注 `reconstructed history`。
4. 每个编号版本建立 tag `v0.0.x.y`；Gate 节点使用 `gate/*` tag 或 annotated tag。
5. `v0.5.0` 放在 orphan `legacy-reference` 分支或 `history/legacy` 目录，不并入 clean-lineage 主线。
6. 生成 `docs/history/RECONSTRUCTION.md`，永久声明：工件是历史原件，Git commit 对象为后期重建，不能伪装成原始 commit hash。

## 证据限制

- 此清单证明的是**保存的发布包/文档/测试工件完整性**，不是证明每个版本都曾在浏览器真实环境完成 smoke test。
- 编号发布 ZIP 本身不包含最终生成 userscript；因此历史 runtime 字节级恢复需要下一阶段重跑 deterministic build，并与任何已保存 userscript（若存在）再做交叉比对。
- `0.0.14.1` 当前 userscript 已保存，可作为该版本 runtime 的直接字节级参照。
