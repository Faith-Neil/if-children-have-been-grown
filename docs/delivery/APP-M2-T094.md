为什么有这个文件：说明 APP-M2-T094（ProjectHeader 摘要条与页签）与 APP-M2-T095（项目列表与多维筛选）的交付成果、验收证据与治理状态。

它解决什么问题：完成 ProjectHeader 摘要条与项目列表页的重构升级，统一提取并封装统一组件，落实标的金额 MaskedField 掩码与审计调阅、投标截止时间倒计时（≤3天标红）、涉密项目横幅展示、八角色权限感知（只读成员无编辑设置入口）与项目多维筛选（状态、涉密、分册）；前端全量 289 项单测与工程构建 100% 通过。按规范标记为 in-review，关联 Issue 保持开启。

# APP-M2-T094 & T095 交付文档：ProjectHeader 摘要条与项目列表页

- **对应任务**：
  - [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094) · ProjectHeader 摘要条与页签（无“资料匹配”）
  - [APP-M2-T095](../tasks/APP-M2.md#app-m2-t095) · 项目列表与多维筛选
- **关联 Issue**：[ISSUE-007](../../issues/ISSUE-007.md) · 编辑台与项目工作台主链路
- **代码解释文档**：[docs/code/APP-M2-T094.md](../code/APP-M2-T094.md)
- **交付时间**：2026-10-22
- **交付状态**：**in-review**（绝不私自标 done，关联 Issue 保持开启）

---

## 1. 交付清单

| 类型 | 文件路径 | 简述 |
|---|---|---|
| UI 摘要条组件 | [frontend/web/src/ProjectHeader.tsx](../../frontend/web/src/ProjectHeader.tsx) | ProjectHeader 项目摘要条组件（名称、金额脱敏、倒计时、涉密横幅、分册进度与页签导航） |
| 摘要核心算法 | [frontend/web/src/project-header-core.ts](../../frontend/web/src/project-header-core.ts) | 纯函数：倒计时计算、金额千分位格式化、八角色权限判断与页签过滤 |
| UI 列表页组件 | [frontend/web/src/ProjectListPage.tsx](../../frontend/web/src/ProjectListPage.tsx) | 项目列表多维筛选页、统计卡片栏与项目元数据抽屉组件 |
| 列表核心算法 | [frontend/web/src/project-list-core.ts](../../frontend/web/src/project-list-core.ts) | 纯函数：项目生命周期阶段推导、分册状态推导与多维复合筛选 |
| 模块导出 | [frontend/web/src/ProjectPages.tsx](../../frontend/web/src/ProjectPages.tsx) | 统一导出 ProjectHeader 与 ProjectListPage |
| 应用接入 | [frontend/web/src/App.tsx](../../frontend/web/src/App.tsx) | 在工作台与项目主外壳中集成新组件，替换原内联粗糙实现 |
| 类型扩展 | [frontend/web/src/types.ts](../../frontend/web/src/types.ts) | 为 Project 实体增加标的金额、分册状态等字段支持 |
| 专属单测 | [tests/frontend/project-header-list.test.mjs](../../tests/frontend/project-header-list.test.mjs) | 5 个测试用例，全方位验证倒计时判定、金额脱敏掩码、权限隔离与筛选规则 |
| 架构文档 | [docs/code/APP-M2-T094.md](../code/APP-M2-T094.md) | 架构设计、调用链路、状态流转与边界安全保护文档 |
| 交付文档 | [docs/delivery/APP-M2-T094.md](APP-M2-T094.md) | 本交付文档与实测验证记录 |

---

## 2. 核心需求满足度

| 需求项 | 规范与交接要求 | 实现与验证方案 | 状态 |
|---|---|---|---|
| **ProjectHeader 摘要条** | 展示项目名称、标的金额、截止倒计时、分册列表与快速导航页签 | `ProjectHeader.tsx` 提取独立组件，集成 `<MaskedField>` 与 `<Tabs>`，完美呈现 | **达标** |
| **标的金额脱敏与调阅** | 集成 MaskedField 掩码展示，项目负责人可调阅，只读成员禁用 | 默认以 `¥ *******.00` 掩码显示，调阅要求输入 ≥5 字理由；只读成员按钮置灰并展示 Tooltip | **达标** |
| **投标截止倒计时** | 倒计时计算精准，≤3 天以橙色/红色高亮标红预警，过期展示“已截止” | `calculateProjectCountdown` 纯函数精确计算天/时/分，单测全覆盖各类边界与临期时间点 | **达标** |
| **涉密项目横幅展示** | 涉密项目显著提示，强制本地模式运行，禁止外部大模型联网调用 | 当 `project.sensitive` 为真时，顶部渲染专用保密 Alert 横幅，列表中带有保密 Tag | **达标** |
| **八角色权限感知** | 只读成员无编辑设置入口，剔除 settings 页签 | `filterProjectTabs` 依据 8 角色规范对 `viewer`、`auditor`、`readonly` 自动移除 settings 入口 | **达标** |
| **项目列表与多维筛选** | 支持状态（筹备中/编写中/审核中/已完成）、涉密属性、分册状态筛选 | `ProjectListPage.tsx` 提供 4 个维度的复合筛选栏与统计卡片，支持实时模糊搜索 | **达标** |
| **项目元数据抽屉** | 列表项支持进入项目工作台、查看项目元数据 | 点击“元数据”滑出 `<Drawer>`，展示基本属性、涉密策略、标的金额脱敏调阅与分册概览 | **达标** |
| **构建与包体积受控** | 前端构建通过，路由按需分包，包体积受控 | `pnpm build` 在 875ms 内完成，主 index chunk 从 660KB 降至 407KB，无超标警告 | **达标** |

---

## 3. 测试与验证执行证据

### 3.1 专属单元测试执行结果
执行命令：
```bash
node --test tests/frontend/project-header-list.test.mjs
```
实测输出：
```text
✔ ProjectHeader: 倒计时计算与临期、过期判定 (2.2105ms)
✔ ProjectHeader: 标的金额货币格式化与脱敏掩码规则 (13.416ms)
✔ ProjectHeader: 八角色权限感知与只读成员设置入口拦截 (0.2742ms)
✔ ProjectListPage: 项目状态与分册状态推导 (0.1848ms)
✔ ProjectListPage: 状态、涉密属性、分册状态与关键词多维筛选 (0.2771ms)
ℹ tests 5
ℹ suites 0
ℹ pass 5
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 180.2718
```

### 3.2 全量前端测试执行结果（289 项 100% 通过）
执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出：
```text
ℹ tests 289
ℹ suites 0
ℹ pass 289
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2717.468
```

### 3.3 前端生产构建执行结果
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3362 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                0.79 kB │ gzip:   0.54 kB
dist/assets/index-CZMgSkPA.css                34.47 kB │ gzip:   7.53 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/MenuUnfoldOutlined-Nb8MiWYk.js     6.69 kB │ gzip:   2.60 kB
dist/assets/collapse-CkeV8bG4.js              10.50 kB │ gzip:   3.83 kB
dist/assets/SupportPages-DY5HsOqL.js          11.32 kB │ gzip:   4.53 kB
dist/assets/ProjectSettingsPage-DdevWk6D.js   22.58 kB │ gzip:   8.93 kB
dist/assets/SlaPages-Dsx60n40.js              26.98 kB │ gzip:   9.31 kB
dist/assets/ProjectPages-BJEkqfoE.js         116.16 kB │ gzip:  34.97 kB
dist/assets/EditorPage-hQsGOelJ.js           147.11 kB │ gzip:  47.20 kB
dist/assets/AppShell-ChirJZP2.js             222.28 kB │ gzip:  73.19 kB
dist/assets/project-team-CRj9tYqM.js         295.98 kB │ gzip:  90.33 kB
dist/assets/index-CLefK1X_.js                407.16 kB │ gzip: 126.58 kB
dist/assets/jsx-runtime-J66WJ9pO.js          438.61 kB │ gzip: 144.68 kB

✓ built in 875ms
```
构建无任何 TypeScript 报错与告警，包体积受控良好。
