为什么有这个文件：记录分册定稿（finalize/unlock）与工作台/导出的前后端契约胶水打通与联调交付结果。

它解决什么问题：打通前端项目工作台概览（OverviewPage）、导出中心（ExportPage）以及编辑台（EditorPage）对后端 `/api/v1/projects/{project_id}/volumes` 状态机与定稿安全门禁的感知联动，确保定稿状态 `is_finalized` 能被准确识别，在分册全部定稿后正确展示定稿徽章，并在未定稿时拦截正式递交版导出。

# INT-VOLUME-FINALIZE-GLUE：分册定稿与工作台/导出的前后端契约胶水打通交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-VOLUME-FINALIZE-GLUE |
| 代码解释 | 详见 [代码解释](../code/INT-VOLUME-FINALIZE-GLUE.md) |
| 验收 | 1. 前端权威测试套件 `pnpm --dir frontend/web test`：370 passed（含新增专属单测 `tests/unit/volume-finalize-glue.test.mjs` 5 passed）；<br>2. 后端定稿安全门禁套件 `pytest tests/backend/test_volume_finalize_gate.py`：10 passed；<br>3. 全链路冒烟套件 `pytest tests/backend/test_smoke_non_demo_pipeline.py`：3 passed；<br>4. OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check`：100% 严格一致；<br>5. 治理检查 `node scripts/check-project-governance.cjs`：校验通过（0 错误）。 |
| 项目进度 | 已经 QA 独立终验签署（D-742）与 PD 产品对照核准（D-743），人类 PM 最终确认标为 **done** |
<!-- task-delivery:end -->

## 1. 任务背景与目标

后端此前已在 `icg.api.volumes` 与 `icg.domain.volume_finalize` 中落地了分册定稿与状态机端点：
- `POST /api/v1/projects/{project_id}/volumes/{volume_id}/finalize`（`finalizeVolume`）
- `POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock`（`unlockVolume`）
- `GET /api/v1/projects/{project_id}/volumes/{volume_id}`（`getVolumeStatus`）
- `GET /api/v1/projects/{project_id}/volumes`（`listVolumesStatus`）

本任务的目标是**排查并打通前端项目工作台与导出页面对该接口的契约对齐与状态联动**：
1. 建立前端 `volume-api.ts` 客户端调用链路，打通 `GET /api/v1/projects/{project_id}/volumes` 状态读取及自动订阅刷新 Hook；
2. 验证定稿（finalize）与解锁（unlock）请求报文格式与响应字段严格匹配 OpenAPI 契约；
3. 导出中心与工作台在分册定稿后正确展示定稿徽章，在未定稿时拦截正式递交版导出；
4. 编写专属前端/后端胶水集成测试用例，保障状态机与门禁逻辑的确定性。

---

## 2. 联调排查与契约胶水打通

### 2.1 状态读取链路与 API 客户端落地（`frontend/web/src/project/volume-api.ts`）
- **契约对齐**：
  在 `shared/types.ts` 中补齐 `VolumeStatus`、`VolumeFinalizeRequest`、`VolumeUnlockRequest`、`VolumeFinalizeResponse`、`VolumeStatusResponse`、`VolumeListResponse` 标准接口，与 `spec/openapi/demo-v1.json` 保持 100% 吻合。
- **客户端与 Hook 封装**：
  在 `project/volume-api.ts` 中封装 `fetchVolumesStatus`、`fetchSingleVolumeStatus`、`finalizeVolumeApi`、`unlockVolumeApi` 以及 React Hook `useVolumesStatus(projectId, token, revision)`。
  当项目 revision 发生变动（如分册定稿、解锁、保存提交）时，Hook 自动触发 `GET /api/v1/projects/{project_id}/volumes` 并将最新定稿状态推送到调用组件。

### 2.2 导出中心定稿门禁与定稿徽章展示（`ProjectPages.tsx:ExportPage`）
- **定稿徽章**：
  在导出页顶栏 Heading 中，联动 `areAllVolumesFinalized` 与 `isVolumeFinalized`：
  - 若为两册合订范围且两册均定稿：展示 `<Tag color="success" data-testid="export-finalized-badge">分册全部定稿</Tag>`；未全定稿展示 `<Tag color="default" data-testid="export-unfinalized-badge">分册未全部定稿</Tag>`；
  - 若为单分册范围：按当前分册展示 `技术分册已定稿` / `商务分册已定稿`。
- **导出前提清单**：
  在 `premiseItems` 列表集成 `deriveFinalizePremise(volumesStatus, volume)`，明确告知用户定稿门禁状态（通过显示绿色对勾，未通过显示感叹号警示，并提供直达编辑台的跳转链接）。
- **正式递交版强门禁**：
  在 `canExportSubmission` 中集成 `isFinalized` 判定；若当前导出范围分册未定稿，禁用正式递交版生成按钮并提供明确说明：`分册尚未完成定稿锁定，禁止导出正式递交版`。

### 2.3 工作台概览与编辑台状态感知（`OverviewTab.tsx` & `EditorPage.tsx`）
- **工作台概览**（`OverviewTab.tsx`）：
  在「分册进度」卡片中，读取 `volumesStatus`，在分册名称旁展示定稿状态徽章（`已定稿` / `编制中`）。
- **编辑台文档标头**（`EditorPage.tsx`）：
  在章节正文上方展示 `分册已定稿` / `分册编制中` 标签。当分册已处于定稿锁定状态时，取得编辑权按钮被禁用，防止已定稿章节被意外编辑修改。

---

## 3. 变更文件清单

| 文件路径 | 修改性质 | 说明 |
|---|---|---|
| `frontend/web/src/shared/types.ts` | 契约对齐 | 补齐 `VolumeStatus`、`VolumeFinalizeResponse`、`VolumeListResponse` 等 TypeScript 类型，`Workspace` 补充 `volumes` |
| `frontend/web/src/project/volume-api.ts` | 新增模块 | 封装分册定稿/解锁 API 客户端、纯状态判定函数与 `useVolumesStatus` Hook |
| `frontend/web/src/project/export-checks-core.ts` | 胶水修复 | `canExportSubmission` 扩充 `isFinalized` 门禁校验 |
| `frontend/web/src/project/ProjectPages.tsx` | 胶水接入 | `ExportPage` 接入分册定稿状态读取、导出前提清单与定稿徽章展示 |
| `frontend/web/src/project/OverviewTab.tsx` | 状态感知 | `OverviewPage` 分册进度展示分册定稿徽章 |
| `frontend/web/src/editor/EditorPage.tsx` | 状态感知 | `EditorPage` 标头展示分册定稿标签，定稿状态下拦截加锁编辑 |
| `frontend/web/tests/unit/volume-finalize-glue.test.mjs` | 新增单测 | 覆盖定稿判定、全部定稿判定、徽章生成、导出前提与递交版拦截门禁 |
| `docs/code/INT-VOLUME-FINALIZE-GLUE.md` | 代码说明 | 本任务专属代码解释与接口时序说明 |
| `docs/delivery/INT-VOLUME-FINALIZE-GLUE.md` | 交付文档 | 本文件 |

---

## 4. 自动化验证结果

1. **前端单元与集成测试**：
   ```bash
   pnpm --dir frontend/web test
   ```
   **370 passed in 4.67s**，新增 5 项专属定稿胶水测试全绿。
2. **后端分册定稿安全门禁回归**：
   ```bash
   pytest tests/backend/test_volume_finalize_gate.py -v
   ```
   **10 passed in 9.62s**（覆盖项目负责人定稿、公司管理员定稿、编写人 403 拦截、跨租户 404 隔离、排他锁未释放 409 拦截、正文为空 409 拦截、存在 blocker 缺陷 409 拦截、解锁定稿全生命周期）。
3. **非演示全流程冒烟回归**：
   ```bash
   pytest tests/backend/test_smoke_non_demo_pipeline.py -v
   ```
   **3 passed in 2.77s**。
4. **OpenAPI 契约一致性校验**：
   ```bash
   python backend/bid-core/export_openapi.py --check
   ```
   输出 `[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`。
5. **工程治理合规检查**：
   ```bash
   node scripts/check-project-governance.cjs
   ```
   校验通过，0 错误。

---

## 5. 移交状态

本卡为前后端契约与状态流胶水打通，不涉及大型业务特性开发。卡片标为 **`in-review`**，移交主 Agent 及 QA 进行后续验收签署。
