为什么有这个文件：记录 BE-M0-T17 chapter_lease 对齐字典 edit_lock 的交付事实、数据库迁移规范与测试证据。

它解决什么问题：作为质量门禁依据，证明租约数据结构已对齐字典规范、Alembic 迁移保留历史数据不删除、向后兼容 token 字段理由明确，状态流转为 in-review。

# BE-M0-T17：chapter_lease 对齐字典 edit_lock 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T17 |
| 代码解释 | [BE-M0-T17](../code/BE-M0-T17.md) |
| 验收 | 2026-10-22：chapter_lease 字段完全对齐 edit_lock 字典定义（含取得时间、心跳时间、持锁原因、接管历史、释放原因、A 组审计列与租户隔离）；Alembic 增量迁移脚本 0010 已就绪，禁止删除历史锁行；保留 token 鉴权机制以保障前端兼容性；全套自动化测试通过 |
| 项目进度 | 任务看板是准绳。本卡从 planned 改为 in-review。看板状态保持 0 错误，严禁私自标 done，等待项目经理复审 |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-032](../../issues/ISSUE-032.md)、[ISSUE-018](../../issues/ISSUE-018.md)
- **关联任务**：[BE-M0-T17](../tasks/BE-M0.md#be-m0-t17)
- **状态流转**：从 `planned` 流转为 `in-review`。遵循规范，严禁私自将任务标为 `done` 或私自关闭 Issue，等待主 Agent / 项目经理进行复审验收。

## 完成内容与变更清单
1. **租约数据结构与字典 v1.9 对齐**：
   - 领域实体 `Lease` 扩充：支持 `acquired_at`, `heartbeat_at`, `lock_reason`, `taken_over_from_user_id`, `takeover_reason`, `released_at`, `release_reason`, `company_id`, `record_version`。
   - 提供 `owner_id` 与 `user_id` 双向兼容访问。
   - `_lease_response` 输出结构增强，向前端透出 `acquired_at` 与 `heartbeat_at` 时间戳。
2. **数据库持久化与数据快照对齐**：
   - `backend/bid-core/icg_demo/database.py` 中 `_load_state`、`_save_leases` 及 `_lease_snapshot` 全面更新，落库与加载新列，并自动填充 A 组系统审计字段。
3. **Alembic 增量迁移安全实施**：
   - 创建 `backend/bid-core/alembic/versions/0010_edit_lock_alignment.py`。
   - 严格采用增量 `ADD COLUMN` 语法，绝对保留数据库历史锁行，杜绝数据截断或删除风险；支持完备的 `downgrade()` 逆向回滚。
4. **保留 token 与 session_token 的兼容理由**：
   - Web 多端及同用户多 Tab 并发时，必须依赖强随机客户端持锁 Token 防跨标签页覆盖与非持锁端写冲突；同时保障既有前端与自动化测试平滑运行。

## 变更文件清单
- `backend/bid-core/icg_demo/domain.py`: 扩充 `Lease` 模型字段与别名属性、响应时间戳。
- `backend/bid-core/icg_demo/database.py`: 数据库加载、存储与快照对齐。
- `backend/bid-core/alembic/versions/0010_edit_lock_alignment.py`: 增量迁移脚本。
- `tests/backend/test_error_idempotency.py`: 增加租约模型与快照字段持久化验证测试。
- `docs/code/BE-M0-T17.md`: 代码说明文档。
- `docs/delivery/BE-M0-T17.md`: 本交付文档。

## 验收结果
- `pytest tests/backend/test_error_idempotency.py`: 12 个测试全部通过。
- `pytest tests/backend/test_v1_lease.py tests/backend/test_lease_review.py`: 12 个测试全部通过。
- `node scripts/check-project-governance.cjs`: 检查通过（0 错误）。

## 限制与未完成事项
- 遵循工作规范，本卡状态置为 `in-review`，绝不私自标记 `done`。
- ISSUE-032 保持跟进状态，待项目经理确认后关闭。
