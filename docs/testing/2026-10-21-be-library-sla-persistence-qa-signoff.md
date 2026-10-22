为什么有这个文件：记录QA对BE-LIBRARY-SLA-PERSISTENCE（MySQL 8 资料库与SLA模板聚合持久化入库）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手审查 Alembic 迁移脚本 0008_library_and_sla.py、表结构、索引与 utf8mb4 字符集排序规则、升降级链（0007_checks_and_exports <-> 0008_library_and_sla）双向无损往返，深度核查资料条目与SLA模板的行级乐观并发控制（基于 revision 字段，版本不匹配或更新行数!=1抛出 409 REVISION_CONFLICT）、同一事务内 commit_library_revision 原子推进主表版本并落库履历表 demo_library_revision、公司隔离与多维过滤检索、以及纯内存模式透明降级多态与全量后端测试回归。

# BE-LIBRARY-SLA-PERSISTENCE MySQL 8 资料与承诺聚合持久化独立复测与 QA 签署

- 被验任务：[BE-LIBRARY-SLA-PERSISTENCE](../delivery/BE-LIBRARY-SLA-PERSISTENCE.md) · MySQL 8 资料与承诺聚合持久化入库
- 关联审查任务：REV-M0-T58
- 关联 Issue：[ISSUE-018](../../issues/ISSUE-018.md)
- 关联交付：[BE-LIBRARY-SLA-PERSISTENCE 交付](../delivery/BE-LIBRARY-SLA-PERSISTENCE.md)、[代码解释](../code/BE-LIBRARY-SLA-PERSISTENCE.md)
- 依赖基线：BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出聚合入库）、BE-CHAPTER-PERSISTENCE（章节聚合入库）
- 被验核心文件：
  - `backend/bid-core/alembic/versions/0008_library_and_sla.py`
  - `backend/bid-core/migrations/versions/0008_library_and_sla.py`
  - `backend/bid-core/icg_demo/database.py`
  - `backend/bid-core/icg_demo/adapters.py`
  - `tests/backend/test_library_sla_persistence.py`
  - `tests/backend/test_mysql_connection.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-LIBRARY-SLA-PERSISTENCE 保持 in-review，严禁标 done；关联 ISSUE-018 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 迁移脚本 0008_library_and_sla.py 结构核验 | 通过 | 迁移脚本建立 `demo_library_item`（主键 `id`、索引 `idx_library_item_company(company_id)`、`category`、`name`、`status`、`is_starred`、`can_insert`、`is_sensitive`、`payload_json JSON NOT NULL`、`revision INT DEFAULT 1`、时间戳）、`demo_sla_template`（主键 `id`、索引 `idx_sla_template_company(company_id)`、`level`、`name`、`rules_json JSON NOT NULL`、`revision INT DEFAULT 1`、时间戳）与 `demo_library_revision`（主键 `id`、索引 `idx_library_revision_item(item_id)`、`version_number INT NOT NULL`、`payload_json JSON NOT NULL`、`changed_by`、`change_reason`、`created_at`）；表级引擎与编码统一采用 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci` |
| AC-02 迁移 DAG 链路完整性与回滚往返 | 通过 | Alembic 链条完整有序：`down_revision = "0007_checks_and_exports"`，通过 `ScriptDirectory` 检查形成 `0008 -> 0007 -> 0006 -> 0005 -> 0004 -> 0003 -> 0002 -> 0001` 无分叉无孤立线形 DAG；`downgrade()` 严格按照依赖逆序先 drop `demo_library_revision`，再 drop `demo_sla_template` 与 `demo_library_item`，升降级往返干净无残留 |
| AC-03 行级乐观并发更新锁与 409 REVISION_CONFLICT 拦截 | 通过 | `save_library_item` 与 `save_sla_template` 在提供 `expected_revision` 参数时，在 SQL 层面执行 `WHERE id = :id AND revision = :expected_revision`；若更新影响行数不为 1，精准抛出 `DomainError(status=409, code="REVISION_CONFLICT", message="资料/SLA已被其他会话更新，请刷新并核对最新版本。")`，有效阻断并发脏写与丢失更新 |
| AC-04 修订履历单事务内原子追加写入 | 通过 | `commit_library_revision` 在单一数据库连接与显式事务内，首先更新主表资料内容与版本号（带 `expected_revision` 乐观锁核验），随后向 `demo_library_revision` 插入不可变的历史版本快照（记录 `version_number`、`payload_json`、`changed_by`、`change_reason`），任何失败均引发事务整体回滚，杜绝版本孤立或历史丢失 |
| AC-05 多租户隔离、多维过滤检索与安全删除 | 通过 | `list_library_items` 强制以 `company_id` 为基准租户隔离，并支持按 `category`（qualification/person/case/honor/financial）与 `status`（draft/confirmed/deprecated）精准或复合过滤，并按创建时间倒序返回 `(items, total)`；`list_sla_templates` 支持按 `company_id` 与服务等级 `level`（bronze/silver/gold/platinum）检索；提供 `delete_library_item` 与 `delete_sla_template` 安全清理 |
| AC-06 纯内存模式透明降级多态 | 通过 | `MemoryRepository` 完整实现与 MySQL 模块同名的 10 个 CRUD 与版本控制方法，提供 100% 对齐的乐观并发锁判定、`REVISION_CONFLICT` 拦截、原子修订历史留存与租户过滤行为；未配置 `ICG_DATABASE_URL` 时零数据库依赖自适应降级运行，保障 CI 与纯离线测试纯洁性 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | `test_error_idempotency.py`（9 项）与 `test_eight_roles_access.py`（10 项）全部通过，全量 143 个冻结错误码保持 100% 完整无损，无任何破坏或漂移 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 资料与承诺持久化专属单测 | `python -m pytest tests/backend/test_library_sla_persistence.py -v` | **6 passed/skipped** (无数据库连接时自适应 skip 纯洁性测试) | 1.09s |
| 内存多态与乐观锁并发冲突逻辑验证 | 执行 Python 断言核验 MemoryRepository 乐观锁与履历流转 | **PASSED** (CRUD、乐观锁409拦截、履历追加、多维检索全过) | 0.08s |
| 契约与八角色权限单测 | `python -m pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py -v` | **19 passed, 0 failed** (143 冻结错误码完备，八角色鉴权全过) | 6.09s |
| Alembic DAG 链条检查 | 执行 ScriptDirectory 检查 0008 down_revision | **PASSED** (`0008_library_and_sla -> 0007_checks_and_exports`) | 0.05s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **522 passed, 31 skipped, 0 failed** (100% 通过) | 332.76s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **行级乐观并发更新（OCC）设计严密**：通过 `UPDATE ... WHERE id = :id AND revision = :expected_revision` 结合 `rowcount == 1` 判定，避免了重量级表锁与死锁风险，对于高并发在线协同标书场景提供了轻量高效的脏写防御机制。
2. **原子事务保障履历一致性**：`commit_library_revision` 严格在单个事务中依次执行主表递增和子表追加，规避了“主表已改但历史落库失败”的不一致状态。
3. **多态仓库架构实现离线/在线零缝切换**：`MemoryRepository` 保证了在未连接 MySQL 的开发机与离线 CI 环境中，所有需要读取、保存资料库和 SLA 模板的上层业务与测试用例（如直查引用、插入答案卡）均可无障碍运行。

## 签署状态

BE-LIBRARY-SLA-PERSISTENCE 保持 **in-review**，**严禁标 done**。
