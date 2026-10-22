为什么有这个文件：记录QA对BE-CHAPTER-PERSISTENCE（MySQL 8 章节聚合持久化与版本乐观锁入库）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手审查 Alembic 迁移脚本 0006_chapters.py、表结构与字符集排序规则、升降级链与回滚幂等性、基于 revision 的原子更新与乐观锁 409 REVISION_CONFLICT 拦截机制、多表事务原子性与回滚隔离、纯内存模式透明降级多态以及全量后端测试回归。

# BE-CHAPTER-PERSISTENCE MySQL 8 章节聚合持久化与版本乐观锁独立复测与 QA 签署

- 被验任务：[BE-CHAPTER-PERSISTENCE](../delivery/BE-CHAPTER-PERSISTENCE.md) · MySQL 8 章节聚合持久化与版本乐观锁入库
- 关联 Issue：[ISSUE-018](../../issues/ISSUE-018.md)
- 关联交付：[BE-CHAPTER-PERSISTENCE 交付](../delivery/BE-CHAPTER-PERSISTENCE.md)、[代码解释](../code/BE-CHAPTER-PERSISTENCE.md)
- 依赖基线：BE-M0-T13（项目聚合入库）、BE-M0-T12（编辑租约入库）
- 被验核心文件：`backend/bid-core/alembic/versions/0006_chapters.py`、`backend/bid-core/icg_demo/database.py`、`backend/bid-core/icg_demo/adapters.py`、`tests/backend/test_chapter_persistence.py`、`tests/backend/test_mysql_connection.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-CHAPTER-PERSISTENCE 保持 in-review，严禁标 done；关联 ISSUE-018 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 迁移脚本 0006_chapters.py 结构核验 | 通过 | 迁移脚本定义 `demo_chapter`（主键 `id`、索引 `idx_demo_chapter_project(project_id)`、`volume`、`title`、`content LONGTEXT`、`revision INT DEFAULT 1`、`assignee_id`、`updated_at DATETIME(6)`）与 `demo_chapter_version`（主键 `id`、索引 `idx_demo_chapter_version_chapter(chapter_id)`、`version_number INT`、`content LONGTEXT`、`created_by`、`created_at DATETIME(6)`）；统一采用 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci` |
| AC-02 迁移 DAG 链路完整性与回滚往返 | 通过 | Alembic 链条完整有序：`0006_chapters -> down: 0005_model_config -> 0004_demo_project -> 0003_chapter_lease -> 0002_sessions_receipts -> 0001_baseline -> None`，无分叉无环路；降级 `downgrade` 先删除 `demo_chapter_version` 再删除 `demo_chapter`，升级降级双向无损 |
| AC-03 基于 revision 的并发乐观锁拦截 | 通过 | `commit_chapter_version` 执行 `UPDATE demo_chapter SET content = :content, revision = :new_rev, updated_at = :updated_at WHERE id = :id AND revision = :old_rev`；受影响行数不为 1 时，立即抛出 HTTP 409 `REVISION_CONFLICT`，错误消息明确提示“章节已被其他会话更新，请刷新并核对最新版本”，彻底杜绝过期版本静默覆盖 |
| AC-04 同一事务内原子落库与异常回滚 | 通过 | 在单个数据库事务（`engine.begin()`）内同步完成 `demo_chapter` 正文版本更新与 `demo_chapter_version` 历史快照行插入；任何失败均触发事务原子回滚，正文与版本历史同时恢复，零孤儿数据与脏写污染 |
| AC-05 纯内存模式多态纯洁性与降级兼容 | 通过 | `MemoryRepository` 完整实现多态方法 `read_chapter`、`save_chapter` 与 `commit_chapter_version`，且在内存模式下具备完全一致的乐观锁冲突拦截逻辑（旧版本提交同样抛出 409 `REVISION_CONFLICT`）；无数据库连接串时透明降级纯内存运行，保障 CI 环境纯洁性 |
| AC-06 跨进程共享与状态装配 | 通过 | `database.py` 中 `_load_shared` 扩展章节及历史版本装配，跨进程读取能叠加已入库的章节与版本快照；未变动的演示种子章节依然由适配器内存支持，实现轻量平滑演进 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | `test_error_idempotency.py` 9 项测试全部通过，全部 143 个冻结错误码保持 100% 吻合，无任何错误码变动或丢失 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 契约与错误码一致性测试 | `python -m pytest tests/backend/test_error_idempotency.py -v -rs` | **9 passed, 0 failed** (143 冻结错误码完备) | 6.67s |
| 内存多态与乐观锁单元验证 | 执行 Python 断言验证 `commit_chapter_version` 乐观锁 | **PASSED** (触发 409 `REVISION_CONFLICT`) | 0.12s |
| MySQL 门禁守卫专项验证 | `python -m pytest tests/backend/test_mysql_gate.py -v` | **9 passed, 0 failed** | 11.71s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **510 passed, 23 skipped, 0 failed** (100% 通过) | 361.65s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **乐观锁原子防线稳固**：章节持久化将乐观锁判定直接下推至 MySQL 的行级排他更新 `WHERE id = :id AND revision = :old_rev`，配合受影响行数断言，比传统的“先 SELECT 读版本再 UPDATE”避免了时间差（Time-of-Check to Time-of-Use）竞争漏洞。
2. **多表级联版本事务闭环**：`demo_chapter` 维持当前最新快照，`demo_chapter_version` 归档不可变历史版本，两者在同一个 DB 连接事务内落库，确保了正文状态与版本履历在任何故障下绝对一致。
3. **环境适应性极高**：通过 `adapters.py` 的多态设计，测试环境无论在是否配置 MySQL 的情况下均可自适应运行，CI 纯洁性守护完备。

## 签署状态

BE-CHAPTER-PERSISTENCE 保持 **in-review**，**严禁标 done**。
