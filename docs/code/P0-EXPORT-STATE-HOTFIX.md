为什么有这个文件：说明 P0-EXPORT-STATE-HOTFIX 热路径指纹误判、编辑台指纹恢复与进度写入一致性代码的修改原因、运行过程与限制。

# P0-EXPORT-STATE-HOTFIX：代码解释

- 对应任务、Issue、交付文档：[P0-EXPORT-STATE-HOTFIX](../tasks/P0-HOTFIX.md#p0-export-state-hotfix)、[ISSUE-059](../../issues/ISSUE-059.md)、[交付说明](../delivery/P0-EXPORT-STATE-HOTFIX.md)
- 日期、实际代码路径、提交 / PR：2026-11-27；`backend/bid-core/icg/infra/repositories/hot_reads.py`、`backend/bid-core/icg/domain/input_snapshot.py`、`backend/bid-core/icg/domain/technical_volume_sessions.py`、`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/editor/fingerprint-recovery.ts`；分支 `feat/iss-059-p0-security-export-deploy-hotfix`，PR 未创建。

## 改了什么以及为什么

原行为有三处 P0 缺陷：

1. 热路径作用域读取用 `body LIKE '%"company_id":"..."%'` 匹配 `demo_state_entry` 条目——该写法依赖紧凑 JSON 文本形状：历史行字段顺序不同、转义差异、通配符 `_`/`%` 未转义都会漏配，输入指纹所需的资料与 SLA 模板条目加载不全，仍有效的合规检查被误判「已过期」，阻断递交导出。同时全量内存态按字典插入序、热路径按主键序加载，同一逻辑指纹输入列表序不同，指纹值不一致。
2. 重庆中烟项目保存/提交死锁（追踪号 `056a411dff69418f92eafbed9649791b`）：流式生成完成时前端用生成前闭包里的旧指纹刷新，等于必败指纹；来源变化后指纹不自动刷新，保存/提交互相 409 拒绝形成死锁，用户只能丢弃草稿。
3. `technical_volume_sessions.py` 进度写入失败时静默继续提交正文，任务进度与正文/状态分裂。

目标行为与实现：

- `hot_reads.py` 新增 `apply_entries_by_json_field()`：用 `JSON_EXTRACT` + `COLLATE utf8mb4_bin` 在 SQL 层精确匹配 JSON 字段值过滤条目，不再依赖文本形状；仍在 SQL 层过滤，不退回全量加载。
- `input_snapshot.py`：指纹输入按 id 规范化排序；章节缺失 `chapter_order` 时以 id 稳定兜底，内存态与热路径指纹输入顺序一致。
- `fingerprint-recovery.ts`（新增）+ `EditorPage.tsx`：四个时机自动用最新 workspace `input_fingerprint` 刷新——章节切换后、流式生成完成、目录刷新、提交成功后；409 `INPUT_FINGERPRINT_STALE` / `INPUT_FINGERPRINT_REQUIRED` 时展示「刷新最新来源并保留当前草稿重试」按钮：拉取最新指纹（失败则零写入）→ 保留草稿原样重试 → 恢复成功后自动保存解除暂停；revision 冲突仍走既有合并流程，不与指纹恢复混用。
- `technical_volume_sessions.py`：`save_job` 失败 → 不启动生成线程、任务落 failed、RFC 7807 500；`update_job_progress` 返回 False/异常 → 置取消信号停止后续正文写入、`volume.failed`、任务落 failed；`finally` 中二次异常不覆盖第一现场。

## 入口和调用顺序

- 指纹一致性链路：`read_auth_state`/`read_project` 等热路径 → `apply_entries_by_json_field` SQL 精确过滤 → 条目加载 → `input_snapshot` 规范化排序 → 指纹计算 → 与全量内存态同输入同序同值。
- 编辑台保存链路：用户保存/提交 → 409 指纹类错误 → `fingerprint-recovery` 判定可恢复 → 拉取最新 workspace 指纹 → 成功则携带新指纹原样重试草稿 → 自动保存解除暂停；拉取失败零写入、草稿不动。
- 进度写入链路：生成线程每节写完 → `update_job_progress` → 失败/异常 → 取消信号 → 后续正文写入停止 → `volume.failed` + 任务 failed 落盘 → RFC 7807 错误透出。

## 数据与状态

- 热路径全部走 MySQL `demo_state_entry` 作用域读取；内存仓储保留多态 fallback，两种仓储下进度写入失败语义一致（都有失败注入测试）。
- 前端指纹状态随 workspace 刷新而更新；恢复流程不修改用户草稿内容一个字节。

## 关键判断与异常

- 指纹 stale 是一次性安全过渡：修复前已生成的受影响指纹会显示一次 stale，用户用恢复按钮刷新后稳定——不会错误放行，也不会持续死锁。
- 409 中 revision 冲突与指纹冲突严格分流：revision 走既有合并流程，指纹走恢复按钮。
- `finally` 块内二次异常只记录不覆盖第一异常现场。

## 验证与限制

- `frontend/web/tests/unit/fingerprint-recovery.test.mjs` 14 例全绿；`tests/backend/test_iss059_backend_hotfix.py` 真实 MySQL 标记用例 2 passed（全量态 vs 热路径指纹一致）；generation_session 组合 17 passed 2 skipped；T28/T29/T30 导出回归 41 passed（门禁语义未削弱）。
- 验证登记见 [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md)。
- 限制（如实记录）：输入指纹仍含全项目章节 content/revision（结构根源），任何章节编辑都会使整项目指纹变化，建议后端契约演进为按章/按输入分量指纹；当前为前端可达最优。前端测试为 jsdom 单元级，未做真实浏览器联调。解释只对应当前实现。
