# APP-M2-T046 & APP-M2-T047：企业资料库通用列表页、资料详情通用页与附件槽位交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T046、APP-M2-T047 |
| 代码解释 | [docs/code/APP-M2-T046.md](../code/APP-M2-T046.md) |
| 验收 | 7 项专属自动化单测全绿；307 项前端全量单测全绿；生产构建通过（独立懒加载分块 26.91 kB）；工程治理通过 |
| 项目进度 | 前端 M2 推进，APP-M2-T046 与 APP-M2-T047 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD v1.8 §5.4、§2.3、§5.9 及原交接规范：
- **APP-M2-T046**：企业资料库通用列表页，需落实主体资质、财务审计、人员证书、业绩案例、通用模板五大法定分类导航，集成标准元数据表格与多维状态筛选（生效中、待核验、已过期、已排除），高敏个人证件字段遮蔽（`<MaskedField>`），新增与批量核验入口；
- **APP-M2-T047**：资料详情通用页与附件槽位，以抽屉展现详尽元数据、核验历史依据、关联项目引用计数，集成附件槽位列表、SHA256 防篡改指纹校验、原件安全预览与带审计提示的受控下载防线。

---

## 2. 交付成果清单

### 2.1 新增与修改源码
1. **纯业务逻辑层** (`frontend/web/src/library/library-pages-core.ts` - 新增):
   - 分类元数据 `LIBRARY_CATEGORIES` 与中文映射 `CATEGORY_LABEL_MAP`；
   - 智能生命周期推导 `deriveEvidenceStatus`；
   - 证据引用可用性深度诊断 `checkEvidenceUsability`（涵盖过期、未核验、缺合作协议等判定）；
   - 多字段模糊检索与多维筛选器 `filterEvidenceList`；
   - 八角色管理权限与高敏字段查看白名单 `canManageLibrary` / `canRevealSensitiveField`；
   - 附件槽位防篡改 SHA256 校验 `verifyAttachmentSecurity`。
2. **UI 组件层** (`frontend/web/src/library/LibraryPages.tsx` - 新增):
   - 顶部统计卡片（全部资料、生效可引用、待核验、历史参考）；
   - 响应式五大分类侧边栏导航 + SLA承诺模板切换；
   - 集成搜索栏、状态多选、可引用快速筛选、批量核验操作栏；
   - 集成 `<MaskedField>` 高敏证件脱敏；
   - 资料元数据详情抽屉（基本信息、核验说明、关联项目引用数、附件槽位、操作日志）；
   - 附件原件预览 Modal 与安全审计告知 Popconfirm。
3. **路由级按需加载** (`frontend/web/src/app/route-loaders.ts`、`lazy-routes.tsx`、`SupportPages.tsx`):
   - 抽离 `loadLibraryPages`，生成独立分块 `LibraryPages-[hash].js`；
   - `SupportPages.tsx` 保留兼容 re-export，体积压缩至 2.28 kB。
4. **自动化测试** (`tests/frontend/library-pages.test.mjs` - 新增):
   - 覆盖 7 项核心逻辑与安全防线测试。

---

## 3. 验收证据与测试输出

### 3.1 专属单测执行结果
```
node --test tests/frontend/library-pages.test.mjs
✔ LIBRARY_CATEGORIES defines standard categories and supports label lookup (1.4748ms)
✔ deriveEvidenceStatus accurately computes status with expiration checks (1.8797ms)
✔ checkEvidenceUsability diagnoses invalid reasons for project citation (0.7147ms)
✔ filterEvidenceList filters by category, status, and multi-field keywords (0.3891ms)
✔ RBAC controls library management permissions (0.6848ms)
✔ RBAC controls sensitive field reveal whitelist and masking (0.3016ms)
✔ verifyAttachmentSecurity verifies SHA256 integrity and download audit trail (0.3614ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
```

### 3.2 全量前端自动化单测回归
```
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 307
ℹ suites 0
ℹ pass 307
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3140.0092
```

### 3.3 生产构建验证
```
pnpm --dir frontend/web build
$ tsc -b && vite build
dist/assets/SupportPages-DOMhHBrJ.js           2.28 kB │ gzip:   1.23 kB
dist/assets/LibraryPages-6BAflygw.js          26.91 kB │ gzip:   9.55 kB
dist/assets/index-BZ96QUvp.js                414.52 kB │ gzip: 128.49 kB
✓ built in 1.25s
```

---

## 4. 边界与红线遵从说明

- **严格红线隔离**：未修改 `EditorPage.tsx`，与并发任务零冲突。
- **任务状态治理**：绝不私自标记任务为 `done`，当前更新为 `in-review`，关联 Issue 保持开启，等待 QA 验收签署。
