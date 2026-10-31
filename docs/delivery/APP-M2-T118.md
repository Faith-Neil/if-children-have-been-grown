为什么有这个文件：记录 APP-M2-T118 挂证据候选三路显示的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或未接真实知识库的结果当作已验收。

# APP-M2-T118：挂证据候选的三路显示

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T118 |
| 代码解释 | [APP-M2-T118](../code/APP-M2-T118.md) |
| 验收 | 2026-11-01：新增 `GET /api/v1/projects/{project_id}/requirements/{requirement_id}/evidence-candidates`（`listEvidenceCandidates`），按资料库规则匹配、知识库片段、历史标书三路返回候选，每条带版本、来源、推荐理由、不可挂接原因与是否可挂接；片段永远不可直接挂接，历史标书只可查看（带内容预览）。响应带知识库状态（available/unavailable/disabled）和当前调用人能否挂接（只读成员为 false）。知识库不可用时仍返回资料库规则匹配结果。抽屉按三组显示，历史与片段不可勾选；用历史标书走条款 PATCH 仍返回 409 EVIDENCE_NOT_USABLE。 验证见 [验证记录](../testing/2026-11-01-wp5-batch1-loop-evidence.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T118](../tasks/APP-M2.md#app-m2-t118)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.3.1 规则 2、11

## 实际文件
- `matrix.py`：`_requirement_candidates`（单条条款三路候选，批量匹配与新接口共用）、`list_evidence_candidates`；`match_evidence`（`POST …/matrix/match`）行为不变
- `api/evidence_candidates.py`：`EvidenceCandidate`、`EvidenceCandidatesResponse`、`include_evidence_candidate_routes`，在 `api/__init__.py`、`app/main.py` 注册
- 前端：`matrix-core.ts`（`fetchEvidenceCandidates`、`groupCandidates`、`candidateSelectable`、`kbStatusText`、`candidateMeta`）、`MatrixMatchDrawer.tsx`

## 测试证据
- `tests/backend/test_matrix.py`：`test_evidence_candidates_split_into_routes_and_history_is_never_attachable`、`test_history_candidate_cannot_be_attached_through_patch`、`test_evidence_candidates_isolated_by_project_and_requirement`、`test_evidence_candidates_still_return_structured_when_kb_unavailable`、`test_readonly_member_reads_candidates_but_cannot_attach`
- `frontend/web/tests/unit/matrix-core.test.mjs`：分组、可选规则、版本与知识库状态文案
- `frontend/web/e2e/matrix.spec.ts`：抽屉里三组标题都存在

## 未实现项与限制
- 没有对“已并入主条目”的条款（merged_into）写后端用例，接口返回 409 REQUIREMENT_MERGED 的逻辑与 `patch_requirement` 一致，但未验证。
- 知识库片段与历史标书的内容预览只截取前 200 字；片段如何经资料库确认后再挂接，沿用现有流程，本卡没有新增“一键转资料库”。
- 本地没有真实 RAGFlow，测试里的知识库是内置实现，片段路由是否有命中取决于测试数据；e2e 只断言三组标题存在，不断言片段命中。
- 候选排序和匹配分仍是名称与内容的字面重合，不是语义检索。
- 打开抽屉时每条选中条款各发一次请求（最多取选中行数），没有做批量合并。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端与 e2e 用例只在 CI 执行；结果以 CI 为准。`spec/openapi/demo-v1.json` 未手改，新增 `listEvidenceCandidates` 由 CI 产物 `openapi-regenerated` 更新。
