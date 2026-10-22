为什么有这个文件：记录 APP-M2-T018 掩码规则读取与查看留痕提示的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现公司级高敏脱敏规则（sensitive_mask_rules）动态读取与清洗、规则变动全表响应式自适应刷新、PRD §6.9 不可关闭掩码合规防线、查看留痕合规警示组件（MaskNoticeBanner / AuditTraceHint）、首屏 Bundle 体积控制（<= 295 kB）与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T018：掩码规则读取与查看留痕提示交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T018 |
| 代码解释 | [docs/code/APP-M2-T018.md](../code/APP-M2-T018.md) |
| 验收 | 10 项专属自动化单测通过；全量 253 项前端单测通过；生产构建首屏产物 294.86 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T018 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T018](../tasks/APP-M2.md#app-m2-t018)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T017](../tasks/APP-M2.md#app-m2-t017)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **公司掩码配置动态解析与合规清洗 (`frontend/web/src/company-mask-settings.ts`)**：
   - 实现了纯函数 `extractMaskRulesFromCompanySettings(rawSettings)`，支持从公司整体设置对象或 JSON 中提取 `sensitive_mask_rules` 节点；
   - 实现了 `sanitizeMaskRule(type, customRule)`：严格落实 PRD §6.9 “每类保留的前后位数可调，但不能设为‘不掩码’，不提供关闭掩码的开关”，拦截负数、空白 `maskChar` 及企图通过超大前缀绕过脱敏的非法配置；
   - 定义标准留痕文案常量 `DEFAULT_AUDIT_TRACE_NOTICE` 与 `DEFAULT_AUDIT_TRACE_DETAIL`。
2. **React 掩码上下文与动态 Hook 封装 (`frontend/web/src/company-mask-context.ts`, `frontend/web/src/useCompanyMaskSettings.ts`)**：
   - `<CompanyMaskProvider>`：上下文容器组件，维护当前生效规则并支持在运行时通过 `updateRules` 动态切换规则（如由标准 6+4 切换至严格 3+4）；
   - `useCompanyMaskSettings()`：消费上下文并提供便捷查询函数 `getRule(type)` 与当前来源 `source`，未包裹时安全兜底至平台安全默认值。
3. **查看留痕合规警示组件 (`frontend/web/src/MaskNoticeBanner.tsx`)**：
   - `<MaskNoticeBanner>`：提供 `banner`（常规横幅）、`inline`（内联行提示）与 `compact`（带 Tooltip 紧凑图标）三种呈现模式；
   - `<AuditTraceHint>`：以行内紧凑模式暴露的快捷别名组件，便于在敏感数据表头或卡片标题右侧灵活插入；
   - 配色完全满足 WCAG AA 4.5:1 对比度标准（背景 `#fffbe6`、边框 `#ffe58f`、文字 `#613400`）。
4. **掩码展示组件响应式联动 (`frontend/web/src/MaskedField.tsx`)**：
   - 接入 `useCompanyMaskSettings()`，在未指定特定 `maskRule` 属性时自适应消费公司上下文规则；
   - 达成原交接约束与验收标准：“规则变化后显示随之变化”。

### 2. 变更文件清单
- `frontend/web/src/company-mask-settings.ts` (新增): 公司规则提取、合规安全清洗与留痕文案常量
- `frontend/web/src/company-mask-context.ts` (新增): React 上下文实例与契约类型定义
- `frontend/web/src/useCompanyMaskSettings.ts` (新增): CompanyMaskProvider 容器与 useCompanyMaskSettings Hook
- `frontend/web/src/MaskNoticeBanner.tsx` (新增): MaskNoticeBanner 横幅与 AuditTraceHint 组件
- `frontend/web/src/MaskedField.tsx` (修改): 接入动态公司规则，实现自适应联动刷新
- `tests/frontend/company-mask-settings.test.mjs` (新增): 6 项规则提取、合规清洗、自适应表格驱动与防泄露单测
- `frontend/web/tests/company-mask-settings.test.mjs` (新增): 4 项 AST 静态契约与零 storage 写入断言测试
- `docs/code/APP-M2-T018.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T018.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单元测试（100% 通过）
运行命令：
```powershell
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
测试输出：
```text
ℹ tests 253
ℹ suites 0
ℹ pass 253
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2587.1765
```
全量 253 项测试全部绿色通过（包含新增的 10 项公司动态规则与留痕提示专属测试）。

### 2. 构建产物体积审计（<= 295 kB 门禁达标）
运行命令：
```powershell
pnpm --dir frontend/web build
```
构建输出：
```text
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-DxiuVLoO.css                30.10 kB │ gzip:   6.82 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/popover-Dy7Y8T45.js                5.30 kB │ gzip:   2.18 kB
dist/assets/collapse-BH52iPNU.js              10.50 kB │ gzip:   3.85 kB
dist/assets/SupportPages-DqWKE_n6.js          11.32 kB │ gzip:   4.52 kB
dist/assets/ProjectSettingsPage--1v7SuLB.js   22.57 kB │ gzip:   8.92 kB
dist/assets/result-BJ4tHomv.js                33.86 kB │ gzip:  10.39 kB
dist/assets/SlaPages-Aj8HgBbd.js              36.52 kB │ gzip:  12.05 kB
dist/assets/zh_CN-vK_Yfa8y.js                 39.18 kB │ gzip:  11.28 kB
dist/assets/EditorPage-Dqyc6Hf0.js            98.74 kB │ gzip:  32.03 kB
dist/assets/ProjectPages-fK2lnAZv.js         116.10 kB │ gzip:  34.97 kB
dist/assets/AppShell-5zcXhWSv.js             223.69 kB │ gzip:  73.43 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip:  90.01 kB
dist/assets/index-fu3kmuVM.js                294.86 kB │ gzip:  93.90 kB
dist/assets/jsx-runtime-DNp14iXa.js          437.98 kB │ gzip: 144.54 kB
✓ built in 889ms
```
首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（gzip 93.90 kB），严格保持在 **295.00 kB 红线以内**，体积 0 字节膨胀。

### 3. 工程治理检查
运行命令：
```powershell
node scripts/check-project-governance.cjs
```
检查确保文档索引、链接与任务记录 100% 契合。

---

## 结论与待决事项
- `APP-M2-T018` 前端公司掩码动态读取、留痕告警提示与自适应联动全部完成，提交代码审查；
- 状态更新为 **in-review**，关联 ISSUE-007 保持开启，等待 QA 与主 Agent 联合评审。
