为什么有这个文件：说明 INT-VOLUME-FINALIZE-GLUE 分册定稿与工作台/导出的前后端契约胶水打通涉及的代码实现、调用流与状态流。

它解决什么问题：阐述前端与后端 `/api/v1/projects/{project_id}/volumes` 状态机端点的对齐、定稿门禁校验与工作台/导出中心徽章展示逻辑。

# INT-VOLUME-FINALIZE-GLUE：分册定稿与前后端契约胶水代码说明

- 对应任务：[INT-VOLUME-FINALIZE-GLUE](../delivery/INT-VOLUME-FINALIZE-GLUE.md)
- 关联问题：[ISSUE-005](../../issues/ISSUE-005.md)、[ISSUE-007](../../issues/ISSUE-007.md)
- 核心源文件：
  - [volume-api.ts](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/project/volume-api.ts)
  - [export-checks-core.ts](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/project/export-checks-core.ts)
  - [ProjectPages.tsx](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/project/ProjectPages.tsx)
  - [OverviewTab.tsx](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/project/OverviewTab.tsx)
  - [EditorPage.tsx](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/editor/EditorPage.tsx)
  - [types.ts](file:///c:/Users/徐佳馨/if-children-have-been-grown/frontend/web/src/shared/types.ts)

---

## 1. 架构与调用时序

前端通过 `volume-api.ts` 与后端分册状态机进行交互：

```
[OverviewPage / ExportPage / EditorPage]
      │
      ├── useVolumesStatus(projectId, token, revision)
      │     └─► GET /api/v1/projects/{project_id}/volumes
      │           └─► 返回 { revision, project_id, volumes: [VolumeStatus] }
      │
      ├── [用户触发分册定稿]
      │     └─► POST /api/v1/projects/{project_id}/volumes/{volume_id}/finalize
      │           ├─► Headers: If-Match, Idempotency-Key
      │           └─► 触发章节排他锁清空、正文非空与 blocker 清零核查
      │
      └── [用户解锁定稿分册]
            └─► POST /api/v1/projects/{project_id}/volumes/{volume_id}/unlock
                  ├─► Body: { reason: "..." }
                  └─► 流转为未定稿并递增 revision
```

---

## 2. 核心模块与实现细节

### 2.1 API 客户端与 Hook 封装（`volume-api.ts`）

1. **`fetchVolumesStatus(projectId, token)`**：
   通过 `shared/api.ts` 的 `request<VolumeListResponse>` 统一发起 GET 请求，对齐 OpenAPI operationId `listVolumesStatus`。
2. **`useVolumesStatus(projectId, token, revision)`**：
   React Hook，依赖 `projectId`、`token` 以及 `workspace.revision`；在项目发生保存、定稿、解锁或其他任何 revision 递增操作时，自动重新读取最新分册状态。
3. **`isVolumeFinalized` 与 `areAllVolumesFinalized`**：
   提供纯函数判定单个分册是否定稿或技术/商务两册是否全部定稿。
4. **`deriveFinalizePremise(volumes, volume)`**：
   为导出页面提供结构化的定稿前提检查对象：
   ```typescript
   {
     label: isAll ? '分册定稿门禁：技术与商务两册均已定稿锁定' : `分册定稿门禁：${volLabel}已定稿锁定`,
     ready: boolean,
     tab: 'editor',
   }
   ```

### 2.2 导出页面联动（`ProjectPages.tsx:ExportPage`）

1. **导出顶栏徽章联动**：
   在 `ExportPage` 的 `<h2>` 标题旁，渲染定稿徽章：
   - 全两册范围且两册均定稿：绿色 Tag 展示 `分册全部定稿`；
   - 未全部定稿：默认灰色 Tag 展示 `分册未全部定稿`；
   - 单分册范围：展示 `${volumeName(volume)}已定稿` 或 `未定稿`。
2. **导出前提清单**：
   在 `premiseItems` 中追加定稿门禁前提项，未通过时展示警告图标与前往查看按钮。
3. **正式递交版导出强拦截**：
   在 `canExportSubmission` 中集成 `isFinalized` 参数：若用户切换到 `kind === 'submission'`（正式递交版）且分册尚未定稿，按钮强行置灰禁用，Tooltip 提示 `分册尚未完成定稿锁定，禁止导出正式递交版`。

### 2.3 工作台与编辑台感知（`OverviewTab.tsx` 与 `EditorPage.tsx`）

1. **工作台分册进度**：
   在 `OverviewPage` 的「分册进度」卡片中，展示每个分册的名称与定稿徽章（`已定稿` / `编制中`）。
2. **编辑台章节标头**：
   在章节正文上方展示 `分册已定稿` 徽章。若该分册已处于定稿状态，禁用取得编辑权按钮并给出提示，杜绝已定稿章节被随意编辑篡改。

---

## 3. OpenAPI 契约与错误体保障

- 严格使用 `/api/v1` 路由，完全符合 `demo-v1.json` 契约；
- 解锁请求报文必填 `reason`（1~500 字符），缺失由 FastAPIs Pydantic 校验返回 422；
- 定稿遇到未释放的排他锁返回 409 `LOCK_HELD`；遇到 blocker 缺陷返回 409 `CHECK_BLOCKER_EXISTS`；遇到正文为空返回 409 `CHAPTER_CONTENT_EMPTY`；
- 所有异常均统一包裹在 `V1Error` 响应格式中。
