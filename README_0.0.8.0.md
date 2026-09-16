# ChatHarbor Clean-lineage Integrated Sync 0.0.8.0

本构建在 `0.0.7.0` 已验证的同步/Manifest/保守网络策略基础上，仅重构 ChatHarbor-owned UI 层。

## 固定上游

- Repository: `huhusmang/ChatGPT-Exporter`
- Commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream version: `1.5.0`

Patcher 会先核验 Git blob，不匹配则拒绝生成。

## 0.0.8.0 UI 改造

1. **单一 Desktop-first 主窗口**
   - 悬浮球点击后直接打开 ChatHarbor 工作区，不再先进入“选择空间”首页。
   - 个人 / 项目 / Team 改为主窗口顶部的空间切换维度。

2. **宽屏双栏**
   - 宽度：`min(1240px, calc(100vw - 48px))`
   - 高度：`min(820px, calc(100vh - 48px))`
   - 左侧会话列表独立滚动；右侧控制栏独立、固定存在。

3. **顶部压缩工具栏**
   - 搜索
   - 空间
   - 项目
   - 归档
   - 同步状态
   - 时间（更新时间/创建时间、范围、排序收进一个菜单）

4. **右侧控制栏**
   - 本地归档：选择目录、目录预检、Remote/Local/待核验/LOCAL_ONLY 摘要
   - 网络策略：速度、每批、批间暂停；继续持久化
   - 同步内容：附件下载开关
   - 主操作：同步选中 / 同步当前筛选 / 同步全部
   - 运行状态：进度、暂停/继续、安全取消
   - 完成摘要：原地展示，不再弹第三层报告框

5. **同步状态展示**
   - 新增
   - 待核验
   - 内容更新
   - 仅改名
   - 更新+改名
   - 仅元数据
   - 已同步
   - 异常 / 重复ID

   预检只能给出列表级 `待核验`；真正 `UPDATED / RENAMED_ONLY / ...` 仍由 detail fetch + content signature 最终确认。

6. **选择体验**
   - 全选当前匹配集合
   - 清空选择
   - Shift + Click 连续选择
   - 筛选变化不主动清空既有选择

7. **悬浮球**
   - 44px
   - 与主操作一致的 `#10a37f` 绿色
   - 新 storage key：`chatharbor-fab-v1`
   - 首次默认贴右边、约视口 45% 高度
   - 空闲时半隐藏；hover 展开；拖动后吸附；位置持久化
   - 新 key 会避开此前迁移测试留下的左上角旧位置

8. **报告**
   - 预检和同步完成摘要均在右栏原地展示
   - ChatHarbor-owned 报告支持 `zh-CN / en-US`
   - 提供“复制详细报告”
   - 不再创建 `ch-preflight-report-overlay` / `ch-integrated-sync-report-overlay`

## 未改变的 Core

`directory_writer` / Planner / final classifier / transaction / cleanup / conservative network core 与 0.0.7.0 **字节级一致**：

`SHA-256 = f4c01a1e3c2f94e3572fe76d1263f0c4ab3ea29a3c64b121482b6b2eab6122cc`

因此本轮不是重新实现同步逻辑。

## 构建

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

生成：

```text
ChatHarbor-IntegratedSync-0.0.8.0.user.js
```

安装时建议只启用这一版 ChatHarbor userscript，停用 0.0.6.x / 0.0.7.0 测试版本，避免两个 runtime 同时存在。

## 建议真实 smoke check

自动测试无法替代浏览器实际 CSS / File System Access 行为。安装后只需要一次整体检查，不拆 Gate：

- 悬浮球首次是否出现在右侧中部并半隐藏；
- 点击是否直接进入宽屏单主窗口；
- 右栏、列表独立滚动是否正常；
- 选择一个测试目录执行一次“目录预检”；
- 选 1–3 条执行一次同步，确认暂停/继续/取消与中文完成摘要；
- 不需要重新验收已经冻结的 raw JSON / Markdown / Manifest 基线。
