为什么有这个文件：记录 P0-EXPORT-STATE-HOTFIX 检查过期误判、编辑台保存提交死锁恢复与进度写入一致性止血的实际完成内容、验收证据与遗留风险。

# P0-EXPORT-STATE-HOTFIX 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review；建议 PM 复核后标 done |
| Issue | [ISSUE-059](../../issues/ISSUE-059.md) |
| 任务卡 | [P0-HOTFIX](../tasks/P0-HOTFIX.md#p0-export-state-hotfix) |
| 代码说明 | [P0-EXPORT-STATE-HOTFIX](../code/P0-EXPORT-STATE-HOTFIX.md) |
| 验证登记 | [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | P0-EXPORT-STATE-HOTFIX |
| 代码解释 | [代码说明](../code/P0-EXPORT-STATE-HOTFIX.md) |
| 验收 | 前端 `frontend/web/tests/unit/fingerprint-recovery.test.mjs` 14 例全绿；后端 `tests/backend/test_iss059_backend_hotfix.py` 含真实 MySQL 标记用例（全量态 vs 热路径指纹一致 2 passed）、generation_session 组合 17 passed 2 skipped；`RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 门禁语义未削弱。 |
| 项目进度 | in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡全部实施完成进入 in-review，等待 QA 签署 + PD 产品验收 + 人类 PM 确认；未创建 PR，未合入，未发布。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-11-27；P0 止血（无里程碑变更）；[ISSUE-059](../../issues/ISSUE-059.md)；[P0-HOTFIX 任务卡](../tasks/P0-HOTFIX.md#p0-export-state-hotfix)。
- 分支、提交、PR：分支 `feat/iss-059-p0-security-export-deploy-hotfix`；PR 未创建。
- 本地验收状态：聚焦单测与真实 MySQL 标记用例通过（见验收结果）；真实浏览器联调未执行。
- 合入 / 发布状态：未合入、未发布。

## 完成内容与变更文件

对应用户止血清单组 2（d/e/f），无范围偏差：

1. **(d) 热路径误判过期根治**：`backend/bid-core/icg/infra/repositories/hot_reads.py` 两个根因——① `body LIKE '%"company_id":"..."%'` 依赖紧凑 JSON 文本形状，历史行/转义差异/通配符漏配导致资料与 SLA 模板条目加载不全；② 全量内存态字典插入序与热路径主键序不同，指纹列表序不一致。修复：新增 `apply_entries_by_json_field()`，用 `JSON_EXTRACT` + `COLLATE utf8mb4_bin` 在 SQL 层精确匹配过滤（不退回全量加载）；`backend/bid-core/icg/domain/input_snapshot.py` 指纹输入按 id 规范化排序、章节缺失 `chapter_order` 时以 id 稳定兜底。**如实记录**：修复前已生成的受影响指纹会安全地显示一次 stale（过期）后稳定，不会错误放行也不会持续死锁。
2. **(e) 编辑台指纹死锁恢复**（追踪号 `056a411dff69418f92eafbed9649791b`，`.audit` 未找到现场，按复现场景修复）：`frontend/web/src/editor/EditorPage.tsx` + 新增 `frontend/web/src/editor/fingerprint-recovery.ts`。自动同步：章节切换后、流式生成完成、目录刷新、提交成功后均用最新 workspace `input_fingerprint` 刷新（原先流式完成时使用生成前闭包旧指纹，等于必败指纹）。冲突恢复：409 `INPUT_FINGERPRINT_STALE` / `INPUT_FINGERPRINT_REQUIRED` 时展示「刷新最新来源并保留当前草稿重试」按钮，拉取最新指纹后保留草稿原样重试（拉取失败零写入），恢复成功后自动保存解除暂停；revision 冲突仍走既有合并流程。
3. **(f) 进度写入失败不静默**：`backend/bid-core/icg/domain/technical_volume_sessions.py`：`save_job` 失败 → 不启动生成线程、任务落 failed、返回 RFC 7807 500；`update_job_progress` 返回 False 或异常 → 取消信号停止后续正文写入、`volume.failed`、任务落 failed；`finally` 中二次异常不覆盖第一现场。内存与 MySQL 两种仓储语义一致。

## 代码解释

详见 [代码说明](../code/P0-EXPORT-STATE-HOTFIX.md)：热路径 SQL 精确匹配、指纹规范化排序、前端指纹自动刷新与恢复按钮状态机、进度写入失败传播链。

## 验收结果

| 验收条目 | 执行方式 | 结果与证据 |
|---|---|---|
| 有效合规检查不再被误判过期，递交导出门禁按真实输入指纹判定 | `tests/backend/test_iss059_backend_hotfix.py` 真实 MySQL 标记用例 | 2 passed：全量态 vs 热路径指纹一致；`test_iss059_backend_hotfix` + `test_kb_admin` 合计 23 passed 2 skipped |
| 追踪号场景：指纹自动刷新；恢复按钮保留当前草稿重试成功 | `frontend/web/tests/unit/fingerprint-recovery.test.mjs` | 14 例全绿：自动刷新时机、409 恢复按钮、拉取失败零写入、恢复后自动保存、revision 冲突走合并 |
| 进度写入失败注入：不静默提交正文，状态不分裂 | generation_session 组合测试 | 17 passed 2 skipped；内存与 MySQL 语义一致 |
| `RULES_INCOMPLETE` / `CHECK_BLOCKER_EXISTS` 门禁语义不被削弱 | T28/T29/T30 导出回归 | 41 passed；导出门禁行为无变化 |

未验证范围：真实浏览器端到端保存/提交联调未执行（前端测试为 jsdom 单元级）；`.audit` 中未找到追踪号 `056a411dff69418f92eafbed9649791b` 原始现场，修复按复现场景与指纹生命周期分析验证。

## 项目进度

in-review；建议 PM 复核后标 done。ISSUE-059 四张止血卡全部实施完成并进入 in-review；下一步为 QA 独立签署、PD 产品验收与人类 PM 确认。本卡不标 done。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响：止血修复不改变产品范围与业务规则，恢复的是 PRD 既定「来源变化后检查过期」语义的正确执行 |
| ROADMAP | 无影响：不改变里程碑顺序，属当前主链路阻断止血 |
| ARCHITECTURE | 无新增架构变更：热路径仍为 MySQL 作用域读取（ISSUE-055 既定方向），指纹机制与导出门禁结构未变；架构正文对齐由后续统一处理 |
| Issue 看板/详情 | 已同步：ISSUE-059 验收条目 AC-04～AC-06 更新为实证，处理记录追加一行 |
| TASK_BOARD / PROJECT_STATUS | 已同步：看板本卡 in-review 并链接本交付；PROJECT_STATUS P0 段落同步四卡 in-review |
| DOCUMENT_INDEX | 已登记：本交付与代码说明条目（D-1099 / D-1103） |

## 风险与后续

- **遗留（如实记录）**：输入指纹仍含全项目章节 content/revision（结构根源），任何章节编辑都会使整项目指纹变化；建议后端契约演进（按章/按输入分量指纹），当前实现为前端可达最优，不改后端契约语义。
- 修复前已生成的受影响指纹会安全地显示一次 stale 后稳定——用户遇到时在编辑台用恢复按钮刷新一次即可，不会丢草稿。
- 恢复按钮拉取最新指纹失败时零写入，用户草稿保持原样；该路径有单测覆盖但未做真实浏览器联调。
- `update_job_progress` 失败即取消后续正文写入，意味着长任务在进度写入抖动时会整体失败而非部分成功——这是止血语义（宁可如实失败，禁止状态分裂），后续如需断点续写属新需求。
