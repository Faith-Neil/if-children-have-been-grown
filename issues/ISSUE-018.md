为什么有这个文件：登记 MySQL 8 持久化方案，供复查后决定是否实施。

它解决什么问题：把驱动、迁移、表和测试边界记在一处，避免在方案未接受时改代码或依赖。

# ISSUE-018：MySQL 8 持久化方案

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-018 |
| 类型 | decision |
| 优先级 | P1 |
| 状态 | in-progress |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | impl-4 |
| 关联 Task | [BE-M0-T08](../docs/tasks/BE-M0.md#be-m0-t08)、[BE-M0-T10](../docs/tasks/BE-M0.md#be-m0-t10)、[BE-M0-T11](../docs/tasks/BE-M0.md#be-m0-t11)、[BE-M0-T12](../docs/tasks/BE-M0.md#be-m0-t12)、[BE-M0-T13](../docs/tasks/BE-M0.md#be-m0-t13) |
| 关联 PR | 未创建。方案随既有分支提交，不新开 PR |
| 本地验收 | 方案轮次只跑治理检查。连接与空迁移的运行时验收见 BE-M0-T10，2026-10-12 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T08](../docs/delivery/BE-M0-T08.md)、[BE-M0-T11](../docs/delivery/BE-M0-T11.md)、[BE-M0-T12](../docs/delivery/BE-M0-T12.md)、[BE-M0-T13](../docs/delivery/BE-M0-T13.md) |
| 代码 / 流程解释 | 方案说明 [BE-M0-T08](../docs/code/BE-M0-T08.md)。连接实现 [BE-M0-T10](../docs/code/BE-M0-T10.md)。回执与会话 [BE-M0-T11](../docs/code/BE-M0-T11.md)。编辑租约 [BE-M0-T12](../docs/code/BE-M0-T12.md)。项目聚合 [BE-M0-T13](../docs/code/BE-M0-T13.md) |
| 验证记录 | 方案轮次为治理检查。MySQL 见 [2026-10-12 连接与迁移](../docs/testing/2026-10-12-mysql-connection.md)。回执与会话见 [2026-10-12 回执与会话](../docs/testing/2026-10-12-be-m0-t11-sessions-receipts.md)。编辑租约见 [2026-10-12 编辑租约](../docs/testing/2026-10-12-be-m0-t12-leases.md)。项目聚合见 [2026-10-12 项目聚合](../docs/testing/2026-10-12-be-m0-t13-projects.md) |

## 现象与证据

用户已决定业务库为 MySQL 8。当前仓库只有 `MemoryRepository`：`read()` 返回整份 `DemoState`，`transaction()` 在锁内深拷贝后提交。幂等回执保留 24 小时，编辑租约 120 秒。尚无驱动、迁移和表。

方案在 [MySQL 8 持久化方案](../docs/architecture/mysql-8-persistence-plan.md)。项目经理已批准方案和四项依赖。连接与空迁移由 BE-M0-T10 实施，依赖登记为 [ISSUE-023](ISSUE-023.md)。回执和登录会话由 BE-M0-T11 提交复查。编辑租约由 BE-M0-T12 提交复查。项目聚合已由 BE-M0-T13 依据 QA ae38ec3，PM 17:16 确认 done。章节和其他聚合仍在内存。

## 影响与分流

- 影响后续持久化实施的选型和测试边界。向量库和模型仍属 ISSUE-010，不在本 Issue。
- 方案轮次没有改依赖。批准后的四个包由 ISSUE-023 写入 `requirements.txt`。公网 CI 工作流仍不加 MySQL。
- 旧 `/api` 错误体另见 ISSUE-021，排在本方案之后，本轮不实施。
- 依赖：无实施依赖。解除“可以开始建表”的条件是本方案被接受，并且第 2 节的四个包逐项批准。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T08 | 写出 ORM、驱动、迁移、字符集、回执表、租约表、事务、跨进程回执与会话，以及内网测试边界 | `docs/architecture/mysql-8-persistence-plan.md` | AC-01～AC-05 | done |
| BE-M0-T10 | 连接配置与空基线迁移 | `backend/bid-core/icg_demo/database.py` | 见 ISSUE-023 | done |
| BE-M0-T11 | 幂等回执和登录会话入库，多进程共享且重启后仍在 | `backend/bid-core/icg_demo/database.py` | AC-04、AC-05 | in-review（QA REV-M0-T28 签署通过，不标 done） |
| BE-M0-T12 | 编辑租约入库，含续期和接管 | `backend/bid-core/icg_demo/database.py` | 方案第 5 节 | in-review |
| BE-M0-T13 | 先迁项目聚合。章节及其他聚合仍在内存 | `backend/bid-core/icg_demo/database.py` | 方案第 6 节 | done（QA ae38ec3，PM 17:16 确认） |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 方案覆盖选型理由、逐项依赖、聚合拆分、utf8mb4、回执表、租约表、事务和 `mysql:8.4` 测试命令 | 已写入方案。功能未实施，不能标通过 |
| AC-02 | 依赖按批准加入，密码不进仓库 | 四项已由 ISSUE-023 / BE-M0-T10 写入。方案轮次本身未改依赖。本条不把后续业务表标为通过 |
| AC-03 | 数据不出内网：方案禁止公网 CI 和托管库 | 已写入方案第 10 节。未实际连接数据库 |
| AC-04 | 幂等回执对多个进程或 worker 可见，并且进程重启后未过期回执仍在 | QA REV-M0-T28 签署通过（631d4c9）。本 Issue 不因此关闭 |
| AC-05 | 登录会话同样跨进程共享，并且重启后仍有效 | QA REV-M0-T28 签署通过（631d4c9）。本 Issue 不因此关闭 |

未做浏览器、服务或发布验收。方案 in-review 不是实施完成。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。未改页面、角色或业务规则 | 不改 `docs/PRD.md` | plan-1 / ISSUE-018 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。持久化仍是未实施项，本轮不改路线图计数 | 不改 `docs/ROADMAP.md` | plan-1 / ISSUE-018 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。持久化步骤留在方案。ISSUE-005 另补的一句不在本 Issue 修改 | 不改架构正文 | plan-1 / ISSUE-018 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。T08 仍 in-review。T10 in-review，T11～T13 planned | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | impl-1 / ISSUE-018 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。进度改为 360 项，并写明连接已提交、业务表未建 | `docs/PROJECT_STATUS.md` | impl-1 / ISSUE-018 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记方案、交付、说明和同步表 | `docs/DOCUMENT_INDEX.md` | plan-1 / ISSUE-018 / 2026-10-12 | 已改 |

PROJECT_BRIEF 排期行随任务数改为 352 项，记在下方同步表。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | plan-1 / in-review | 方案已提交复查。当时未安装依赖，未建表 | 方案与治理检查 |
| 2026-10-12 | impl-1 / in-progress | 项目经理批准方案和四项依赖。只实施连接与空迁移。T11～T13 仍 planned。不关闭 | [BE-M0-T10](../docs/delivery/BE-M0-T10.md) |
| 2026-10-12 | impl-1 / in-progress | 项目经理在 QA 签署 98c5129 后确认 BE-M0-T08 与 BE-M0-T10 为 done。本 Issue 仍 in-progress。ISSUE-023 仍 in-review，等待 QA 复核 Q1 | [QA签署](../docs/testing/2026-10-12-be-m0-t10-mysql-signoff.md) |
| 2026-10-12 | impl-1 / in-progress | 托管 MySQL 作业登记为 [ISSUE-025](ISSUE-025.md)，不改变本 Issue 状态。回执、会话、租约和聚合表仍未做 | [BE-M0-T14](../docs/delivery/BE-M0-T14.md) |
| 2026-10-12 | impl-1 / in-progress | 项目经理在 QA 签署 16cf971 后确认 ISSUE-023 为 closed。本 Issue 仍 in-progress，T11～T13 未做 | [QA签署](../docs/testing/2026-10-12-be-m0-t10-mysql-signoff.md) |
| 2026-10-12 | impl-1 / in-progress | BE-M0-T11 增加验收：真实业务表进入仓库后，CI 必须做 downgrade base 再 upgrade head。本 Issue 仍 in-progress，这一步尚未加进作业 | [QA签署](../docs/testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) |
| 2026-10-12 | impl-2 / in-progress | BE-M0-T11 提交回执和登录会话。downgrade base 再 upgrade head 由 mysql 标记测试执行，现有 `-m mysql` 会跑到。未改工作流。T12、T13 仍 planned。不标 closed | [BE-M0-T11](../docs/delivery/BE-M0-T11.md) |
| 2026-10-12 | impl-3 / in-progress | BE-M0-T12 提交编辑租约。续期后占用者不变，过期后其他会话可以接管。字典 v1.9 对照写在方案第 5 节，偏差需要项目经理批准。T13 仍 planned。不标 closed | [BE-M0-T12](../docs/delivery/BE-M0-T12.md) |
| 2026-10-12 | impl-4 / in-progress | BE-M0-T13 提交项目聚合。另一个进程能看见已提交项目，看不见其新章节。字典 v1.9 对照写在方案第 6 节，偏差需要项目经理批准。章节及其他聚合仍在内存。不标 closed | [BE-M0-T13](../docs/delivery/BE-M0-T13.md) |
| 2026-10-12 | impl-4 / in-progress | 项目经理有条件批准方案第 5 节偏差。对齐登记为 [ISSUE-032](ISSUE-032.md) / BE-M0-T17，状态 new / planned。本 Issue 仍 in-progress。T12 与 T13 仍 in-review | [ISSUE-032](ISSUE-032.md) |
| 2026-10-12 | impl-4 / in-progress | QA ae6fd10，PM 15:32 确认。BE-M0-T12 标为 done。本 Issue 仍 in-progress。T13 仍 in-review。释放后库内行删除，已补 mysql 测试 | [BE-M0-T12](../docs/delivery/BE-M0-T12.md) |
| 2026-10-12 | impl-4 / in-progress | 项目经理有条件批准方案第 6 节偏差。对齐登记为 [ISSUE-035](ISSUE-035.md) / BE-M0-T19，状态 new / planned。本 Issue 仍 in-progress。T13 仍 in-review。不改表 | [ISSUE-035](ISSUE-035.md) |
| 2026-10-12 | impl-4 / in-progress | 项目经理确认 BE-M0-T13 为 done，依据是 QA ae38ec3，PM 17:16 确认。本 Issue 仍 in-progress。ISSUE-035 仍为 new。章节及其他聚合仍在内存 | [BE-M0-T13](../docs/delivery/BE-M0-T13.md) |

## 本地验收与后续合入发布

- 本地验收：未做运行时验收。2026-10-12 治理检查见交付。
- 未覆盖：MySQL 容器、迁移命令、并发和真实内网部署。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-018-sync.md)。
- PR：未新开。合入与发布均未发生。
