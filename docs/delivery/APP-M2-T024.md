# APP-M2-T024：A-03 字典配置页交付报告

为什么有这个文件：记录 APP-M2-T024 A-03 字典配置与元数据管理页的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 依据 PRD MVP v1.8 §5.10.3、§6.9 规范，落地 A-03 字典配置与元数据调阅管理页，提供跨 6 大业务状态码表与全量业务字段元数据的集中化调阅与管理控制；
2. 深度复用 `StatusTag` 组件提供真实的状态标签预览，保障 WCAG AA 4.5:1 对比度规范；
3. 严格落实“已使用代码只能停用，不可直接硬删除”核心安全红线，杜绝业务历史数据被破坏；
4. 实现标准 8 大角色的精细化权限感知，非管理员角色严格处于只读安全态；
5. 贯彻 **Layout First** 原则，以直观的分类 Tabs、多维检索、状态开关与侧边详情抽屉清晰组织功能，杜绝说明书式冗余文字堆叠。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T024 |
| 代码解释 | [APP-M2-T024 代码说明](../code/APP-M2-T024.md) |
| 文档登记 | [D-788](../DOCUMENT_INDEX.md) |
| 验收 | 1. **A-03 字典配置中心完整落地**：在 `frontend/web/src/admin/DictConfigPage.tsx` 与 `dict-config-core.ts` 落地字典配置页，并通过 `lazy-routes.tsx` 与 `GlobalPagesContent.tsx` 装配至全局规则导航 `admin.rules` 的【A-03 字典配置】页签；<br>2. **6 大核心业务状态码表与字段元数据全收口**：收录 `status_project` (5项)、`status_chapter` (5项)、`status_job` (5项)、`status_check` (3项)、`status_export` (4项)、`status_lock` (4项) 及项目、招标、资料、SLA 核心字段元数据；<br>3. **深度复用 StatusTag 组件**：列表与抽屉预览统一通过 `<StatusTag type={domain} status={code} showIcon />` 渲染真实视觉效果；<br>4. **核心红线“已使用代码只能停用，不可直接硬删除”**：在用（`isInUse: true`）或系统内置代码硬删除按钮严格禁用并拦截，仅允许通过弹窗确认安全切换【启用/停用】状态；<br>5. **角色感知与只读安全保护**：仅 `platform_admin` 与 `company_admin` 具备状态控制权限；普通编写人、项目负责人与审计角色呈现只读查看态（只读 Badge，操作按钮禁用）；<br>6. **测试与质量门禁全绿**：专属单测 6 项全绿，全量 420 项前端单元测试 100% 保持全绿，TypeScript 0 error，Vite 生产构建 1.13s 成功（产物 29.57 kB），工程治理检查通过。 |
| 项目进度 | 本地已完成实现与多维质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 业务背景与规范遵从

根据 PRD MVP v1.8 §5.10.3、§6.9 与系统交接规范 M1-P09-F2：
- 投标编制系统需要统一的字典代码管理中心，负责收录与运维各业务模块所依赖的状态码与业务属性；
- 原交接验收核心约束明确指出：**“已使用代码只能停用”**，防止物理删除已在项目历史、章节、任务或检查中引用的状态导致系统级数据不一致或崩溃；
- 本任务结合前期 `APP-M2-T023`（StatusTag 状态字典）与 `INT-STATUS-TAG-METADATA-GLUE`（元数据接口联调）成果，在前端 `frontend/web/src/admin/` 落地完整的 A-03 字典配置页。

---

## 2. 核心交付内容清单

### 2.1 纯逻辑层 (`frontend/web/src/admin/dict-config-core.ts`)
1. **数据模型与初始数据集**：
   - 定义 `DictItem` 与 `DictCategorySummary`；
   - `buildInitialDictItems()`：聚合 6 大业务状态码表（26 项核心状态）及 9 项关键业务字段元数据；
2. **安全红线校验**：
   - `validateCodeDeactivation(item)`：判断代码是否在用（`isInUse`）或内置（`isBuiltin`），若在用严禁硬删除（`canHardDelete: false`），明确返回理由：“已使用代码只能停用，不可直接硬删除”；
   - `toggleDictItemActive(items, itemId, targetActive)`：提供不可变的数据更新与停用状态变更；
3. **角色感知与权限判定**：
   - `checkDictPermission(role)`：区分平台管理员、公司管理员与只读人员；
4. **分类统计与多维检索**：
   - `computeCategorySummaries(items)`：按分类聚合统计总项数、启用项数与在用项数；
   - `filterDictItems(items, params)`：支持分类精确过滤、启用状态过滤与关键字（代码、显示名、描述）模糊搜索。

### 2.2 呈现层组件 (`frontend/web/src/admin/DictConfigPage.tsx`)
1. **Layout First 架构布局**：
   - 顶部概览卡片：呈现标题、角色权限徽标、代码总数、启用数、在用受保护数与状态码表数；
   - 告警横幅：醒目呈现“数据完整性与防篡改红线：已使用代码只能停用不可硬删除”；
   - 筛选控制栏：搜索输入框 + 状态单选过滤按钮组（全部 / 仅启用 / 已停用）；
   - 分类选项卡（Tabs）：支持在全部代码与各业务分类间一键切换；
   - 字典表格：展示代码 Key、StatusTag 预览、显示名称（含关键★与废标标签）、所属分类、在用保护徽标、启用状态及操作按钮；
2. **操作与交互控制**：
   - 停用/启用气泡确认（Popconfirm）；
   - 硬删除保护拦截（尝试删除在用代码触发警告 Modal 阻断）；
   - 侧边抽屉（Drawer）：查阅代码完整元信息与全站统一标签渲染效果（default/solid/outline 三变体实景）。

### 2.3 应用路由集成
- `frontend/web/src/app/route-loaders.ts`：导出 `loadDictConfig` 动态分包加载器；
- `frontend/web/src/app/lazy-routes.tsx`：导出 `LazyDictConfigPage`；
- `frontend/web/src/app/GlobalPagesContent.tsx`：在 `nav === 'admin.rules'` 下装配 `key: 'dict'` 页签（【A-03 字典配置】）。

---

## 3. 测试与质量门禁证据

### 3.1 专属单元测试（6 passed, 0 failed）
运行命令：
```bash
node --test frontend/web/tests/unit/dict-config-page.test.mjs
```

测试执行结果：
```
✔ 1. 字典项初始化加载：涵盖 6 大核心业务状态码表与字段元数据 (1.2154ms)
✔ 2. 角色感知与权限判定：区分平台管理员、公司管理员与只读人员 (0.3206ms)
✔ 3. 核心红线：“已使用代码只能停用，不可直接硬删除” (0.5144ms)
✔ 4. 分类汇总与多维检索过滤逻辑验证 (0.7455ms)
✔ 5. DictConfigPage.tsx AST 静态契约与组件规范断言 (26.373ms)
✔ 6. GlobalPagesContent.tsx 路由装配断言 (4.7826ms)
ℹ tests 6
ℹ suites 0
ℹ pass 6
ℹ fail 0
```

### 3.2 全量前端单测保持 100% 全绿（420 passed, 0 failed）
运行命令：
```bash
pnpm --dir frontend/web test
```
执行结果：420 项单元测试全部通过（420 passed, 0 failed, 0 error）。

### 3.3 TypeScript 严格类型检查
运行命令：
```bash
pnpm --dir frontend/web lint
```
执行结果：`$ tsc -b --noEmit` 顺利退出，0 error, 0 warning。

### 3.4 生产构建验证
运行命令：
```bash
pnpm --dir frontend/web build
```
执行结果：`dist/assets/DictConfigPage-B_AypwDI.js 29.57 kB` 独立动态分包，全站构建耗时 1.13s，分包体积健康受控。

---

## 4. 建议与流转

本卡所有核心页面与纯逻辑已全面交付并通过严格测试，按规范将状态推至 `in-review`。建议 PM 在 QA/PD 复核签署后标为 `done`。
