为什么有这个文件：登记编辑台 Gemini 风格柔和流式输出体验升级。

它解决什么问题：生成遮罩盖住正文、ProseMirror 高频重建、未闭合 Markdown 与表格裸露跳动、完成交接可能闪烁或滚动回弹。

# ISSUE-058：编辑台 Gemini 风格柔和流式输出体验升级

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-058 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-11-27 |
| 最后更新日期 | 2026-11-27 |
| revision | frontend-ux-streaming-r1 |
| 关联 Task | [FE-UX-STREAMING-RENDER](../docs/tasks/FE-UX.md#fe-ux-streaming-render)、[FE-UX-STREAMING-MARKDOWN](../docs/tasks/FE-UX.md#fe-ux-streaming-markdown)、[FE-UX-STREAMING-HANDOFF](../docs/tasks/FE-UX.md#fe-ux-streaming-handoff)、[FE-UX-STREAMING-VERIFICATION](../docs/tasks/FE-UX.md#fe-ux-streaming-verification) |
| 关联 PR | [PR #55](https://github.com/Faith-Neil/if-children-have-been-grown/pull/55) 已创建，未合入 |
| 本地验收 | 通过：tsc、生产构建、流式单测 21 passed、Playwright 模拟 SSE 2 passed；全量前端单测 647 passed / 14 failed（既有失败如实记录） |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [RENDER](../docs/delivery/FE-UX-STREAMING-RENDER.md)、[MARKDOWN](../docs/delivery/FE-UX-STREAMING-MARKDOWN.md)、[HANDOFF](../docs/delivery/FE-UX-STREAMING-HANDOFF.md)、[VERIFICATION](../docs/delivery/FE-UX-STREAMING-VERIFICATION.md) |
| 代码 / 流程解释 | [RENDER](../docs/code/FE-UX-STREAMING-RENDER.md)、[MARKDOWN](../docs/code/FE-UX-STREAMING-MARKDOWN.md)、[HANDOFF](../docs/code/FE-UX-STREAMING-HANDOFF.md)、[VERIFICATION](../docs/code/FE-UX-STREAMING-VERIFICATION.md) |
| 验证记录 | [FE-UX-STREAMING-VERIFICATION](../docs/delivery/FE-UX-STREAMING-VERIFICATION.md)；Playwright 模拟 SSE 2 passed（24.1s） |

## 现象与证据

用户基于 PR #54 后的最新 main 要求：拆掉 `.paper-wait` 不透明遮罩；等待首字阶段以阶段呼吸胶囊与 shimmer 骨架表达 `retrieve` / `deviate` / `write_section`；首字到达后切换与 TipTap 排版一致的 `StreamingPaperView`，不再每个 reveal tick 调用 `editor.commands.setContent()` 重建文档；新增文字以稳定 key 的柔和渐显 chunk 追加，末尾附着渐变微光呼吸光标；未闭合加粗、下划线、孤立井号与未成型表格安全渲染；长文滚动保留钉底和用户上翻不拉回，离开底部显示“回到底部”；`volume.done` 且 reveal settled 后服务端正式正文静默交接回可编辑 TipTap。

## 影响与分流

- 范围限定前端编辑台流式渲染、滚动交接、单元测试与 Playwright SSE 验证；不改变后端 SSE 契约和业务数据语义。
- 必须保留现有 backlog `jump`、live `push`、`createDeltaCoalescer` 合并节奏、24px 钉底与用户上翻不强行拉回逻辑。
- 真实模型与 RAGFlow 真机验收不在本 Issue 内；模拟 SSE 与单元测试不能冒充生产模型验收。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| [FE-UX-STREAMING-RENDER](../docs/tasks/FE-UX.md#fe-ux-streaming-render) | 拆遮罩、阶段胶囊、StreamingPaperView、渐显 chunk、呼吸光标 | `frontend/web/src/editor/`、`frontend/web/src/shared/styles.css` | 无遮罩盖字；稳定 key；reduced-motion 兼容 | in-review |
| [FE-UX-STREAMING-MARKDOWN](../docs/tasks/FE-UX.md#fe-ux-streaming-markdown) | 流式安全 Markdown 中间态 | `frontend/web/src/editor/streaming-markdown.ts` | 未闭合标记不裸露；未成型表格占位平滑转正 | in-review |
| [FE-UX-STREAMING-HANDOFF](../docs/tasks/FE-UX.md#fe-ux-streaming-handoff) | 智能跟随滚动、回到底部、完成/取消/失败无缝交接 | `EditorPage.tsx`、`PaperEditor.tsx` | 不强行拉回；交接无白屏/回弹/scrollTop 跳动 | in-review |
| [FE-UX-STREAMING-VERIFICATION](../docs/tasks/FE-UX.md#fe-ux-streaming-verification) | 单元测试与 Playwright SSE 模拟验收 | `frontend/web/tests/unit/`、`frontend/web/e2e/` | 覆盖加粗、下划线、表格、长文滚动与完成收口 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 等待首字显示阶段胶囊与 shimmer 骨架，不再用 `rgba(255,255,255,0.9)` 遮罩盖住正文 | 通过；`.paper-wait` 已移除，Playwright 验证胶囊可见且遮罩不存在 |
| AC-02 | 首字后切换 StreamingPaperView；流式期间不每个 tick 整棵重建 ProseMirror；交接零位移 | 通过；流式期间 TipTap 隐藏且不重建，完成时绘制前一次性写回 |
| AC-03 | live 揭示速率柔和（65～80 字/秒）；新 chunk 稳定 key 渐显，旧片段不重挂载；呼吸光标结束淡出 | 通过；速率 72 字/秒，chunk key 单测稳定，光标 220ms 淡出 |
| AC-04 | 未闭合 `**`、`<u>`、孤立 `#`、未成型表格不裸露或撑跳；表格分隔行到达后平滑展开 | 通过；streaming-markdown 单测与浏览器表格占位/正式表格证据 |
| AC-05 | 保留 24px 钉底和用户上翻不拉回；离开底部显示“回到底部”；完成后 scrollTop 不跳动、无白屏闪烁 | 通过；Playwright 验证上翻按钮、点击回底与最终交接 |
| AC-06 | 单元测试、TypeScript、生产构建、Playwright SSE 场景与治理检查按真实结果记录；PR 创建但不合并 | 通过：tsc、build、聚焦单测与 SSE 验收通过；全量单测 647 passed / 14 failed 为既有失败；PR #55 已创建且未合入 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：不改变产品范围、角色或业务规则，只提升既有章节生成编辑体验 | `docs/PRD.md` | frontend-ux-streaming-r1 / ISSUE-058 / 2026-11-27 | 已核对 |
| ROADMAP | 无影响：不改变里程碑顺序，属于当前主链路体验收口 | `docs/ROADMAP.md` | 同上 | 已核对 |
| ARCHITECTURE | 有影响：编辑台流式渲染从 TipTap 即时重建改为流式专属画布 + 完成交接 | `docs/ARCHITECTURE.md` | 同上 | 已同步 |
| TASK_BOARD | 有影响：新增四张 FE-UX-STREAMING 任务卡 | `docs/TASK_BOARD.md` | 同上 | 已同步 |
| PROJECT_STATUS | 有影响：记录 ISSUE-058 开工状态 | `docs/PROJECT_STATUS.md` | 同上 | 已同步 |
| DOCUMENT_INDEX | 有影响：新增 ISSUE-058 与后续交付/代码说明条目 | `docs/DOCUMENT_INDEX.md` | 同上 | 已同步 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-11-27 | frontend-ux-streaming-r1 / in-progress | 已基于 PR #54 合入后的 main 切出 `feat/iss-058-streaming-ux` 并登记任务；下一步实现流式渲染与验收 | 用户本轮指令 |
| 2026-11-27 | frontend-ux-streaming-r1 / in-review | 四张任务卡完成实施；模拟 SSE、单元测试、tsc 与生产构建完成；全量单测既有 14 条失败如实记录；等待 QA/PD/PM，不标 done | 本地验证记录 |

## 本地验收与后续合入发布

- 本地验收结论与日期：2026-11-27 通过聚焦验收；完整前端单测仍有 14 条既有失败，不作为本 Issue 通过证据。
- 验证方式、通过及失败项、未覆盖范围：tsc/build 通过；流式聚焦单测 21 passed；Playwright 模拟 SSE 2 passed；全量前端单测 647 passed / 14 failed（既有 app-orchestration/evidence-orchestration/company-settings/dict-config 契约失败）；未做真实模型/RAGFlow 验收。
- 六份基线同步与互链复核：已执行。
- PR 状态：[PR #55](https://github.com/Faith-Neil/if-children-have-been-grown/pull/55) 已创建，未合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
