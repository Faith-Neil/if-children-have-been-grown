为什么有这个文件：记录第一步后端开发的具体范围、依赖和验收标准。

它解决什么问题：让后台工作有真实交付单位，避免用前端文档任务代替后端实现进度。

# BE-M0：后端最小可运行链路

日期：2026-10-10。BE表示后端任务，独立于现有前端计划。

<a id="be-m0-t01"></a>

## BE-M0-T01 · 开发准备和本地demo

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收，未合入/未发布） |
| 估算 | 4小时；生产接入与完整一期另行拆分 |
| 关联 Issue | [ISSUE-006](../../issues/ISSUE-006.md) |
| 依赖 | [FE-M0-T02](FE-M0.md#fe-m0-t02)；用户已确认技术/商务两册及接口演示边界 |
| 来源 | [一期建议](../decisions/phase-one-scope.md)、[技术审查](../reviews/2026-10-09-technical-readiness.md) |
| 完成时交付 | [实际交付](../delivery/BE-M0-T01.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T01.md) |

范围：建立可运行后台、统一请求与错误、公司权限、章节锁与版本写入，模型/数据库接口及演示实现；提供简单页面和实际Word输出。同步补齐安装、启动、开发约定和验证入口。

- [x] 一套安装/启动方法可复现，页面与后台真实交互。
- [x] 公司隔离、角色权限、失去编辑权/版本过期/重复请求有必要验证。
- [x] 模型和数据库可在独立接口处替换，没有真实服务调用。
- [x] Word文件实际生成；旧检查不能用于修改后的章节导出。
- [x] 文档说明实际能力和限制，交付、代码解释及看板同步完成。

<a id="be-m0-t02"></a>

## BE-M0-T02 · v1统一错误体与HTTP状态码表

| 字段 | 内容 |
|---|---|
| 状态 | done（项目经理于 10-12 12:28 在 QA 签署后确认；未合入/未发布） |
| 估算 | 4小时；不含前端请求层和数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (a) |
| 完成时交付 | [实际交付](../delivery/BE-M0-T02.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T02.md) |

范围：`/api/v1` 错误体为 `{code, message, details, traceId}`，`traceId` 与服务端 `X-Request-ID` 相同。每个业务 code 只对应一个 HTTP 状态。`VOLUME_OWNER_REQUIRED` 固定 403，`TWO_VOLUMES_REQUIRED` 固定 422。字段校验的 `details.fields` 列出路径。旧 `/api` 仍用 `{error:{code, message}, request_id}`。不含锁迁移、导出快照、202/SSE 或 operationId 改名。

- [x] v1 路由声明统一错误体和 `X-Request-ID`。
- [x] 状态码表与代码、OpenAPI 一致；未知 code 或错误状态不能构造 `DomainError`。
- [x] 原先一个 code 两个状态的两处已各收成一个状态，并有测试。
- [x] 旧 `/api` 错误形状保持。

<a id="be-m0-t03"></a>

## BE-M0-T03 · v1幂等键与24小时回执

| 字段 | 内容 |
|---|---|
| 状态 | done（项目经理于 10-12 12:28 在 QA 签署后确认；未合入/未发布） |
| 估算 | 4小时；内存回执，不含数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (b)；回执保留 24 小时已批准 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T03.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T03.md) |

范围：写操作使用请求头 `Idempotency-Key`。范围是 scope、账号和键。同一请求重放首次成功结果；同一键不同内容返回 409 `IDEMPOTENCY_CONFLICT`；缺少或格式不符返回 428。失败不保存回执。回执 24 小时过期，内存最多 2048 条。客户端只对网络错误、502、503 用同一键重试。旧章节提交仍接受正文字段，并与新回执共用存储规则。

- [x] 同键同内容重放，响应头 `Idempotent-Replayed: true`。
- [x] 同键不同内容 409，且不产生第二次写入。
- [x] 缺键或过短键 428；失败后同一键仍可重试。
- [x] 超过 24 小时的回执不再重放；超过上限时丢掉最旧回执。

<a id="be-m0-t04"></a>

## BE-M0-T04 · 编辑租约迁到 /api/v1

| 字段 | 内容 |
|---|---|
| 状态 | ready |
| 估算 | 4小时；沿用现有 120 秒租约，不含数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (c) |
| 完成时交付 | `docs/delivery/BE-M0-T04.md` |
| 代码解释 | `docs/code/BE-M0-T04.md` |

范围：把取得、续期和释放编辑权收到 `/api/v1`，沿用现有租约时长和权限判断。本卡尚未开工。不改 202/SSE，不加数据库。

- [ ] v1 租约路由与现有编辑权规则一致。
- [ ] 旧验证页仍能完成已有编辑流程，或交付中写明保留方式。
- [ ] OpenAPI 从代码导出，并有对应测试。

<a id="be-m0-t05"></a>

## BE-M0-T05 · 导出快照语义

| 字段 | 内容 |
|---|---|
| 状态 | ready |
| 估算 | 4小时；不含异步导出和数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (d) |
| 完成时交付 | `docs/delivery/BE-M0-T05.md` |
| 代码解释 | `docs/code/BE-M0-T05.md` |

范围：按提案冻结导出当时绑定的检查、版本和输入摘要。本卡尚未开工。不新增 `stale` 布尔字段，也不把导出改成异步任务。

- [ ] 导出记录能说明它绑定的检查和已提交内容。
- [ ] 来源变化后旧导出不能被当成当前有效结果。
- [ ] 契约与测试同步，未实现项写明。

<a id="be-m0-t06"></a>

## BE-M0-T06 · 可恢复任务（202 与 SSE）

| 字段 | 内容 |
|---|---|
| 状态 | ready |
| 估算 | 4小时；先定契约与最小行为，不加新依赖 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (e) |
| 完成时交付 | `docs/delivery/BE-M0-T06.md` |
| 代码解释 | `docs/code/BE-M0-T06.md` |

范围：长任务先返回 202，再用 SSE 报告进度，并说明断线后如何查询。本卡尚未开工。不新增 SSE 库，不把现有同步解析改成已恢复。

- [ ] 选定的长任务有 202 与事件约定。
- [ ] 失败和取消有明确状态，不把未实现写成已联调。
- [ ] 测试覆盖约定中的最小路径。

<a id="be-m0-t07"></a>

## BE-M0-T07 · operationId 检查

| 字段 | 内容 |
|---|---|
| 状态 | ready |
| 估算 | 2小时；只检查并修正操作名，不加依赖 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (f) |
| 完成时交付 | `docs/delivery/BE-M0-T07.md` |
| 代码解释 | `docs/code/BE-M0-T07.md` |

范围：OpenAPI 的 `operationId` 使用 lowerCamelCase，不能重复，也不能保留框架自动生成的 `_api_` 名字。本卡尚未开工。当前导出文件除 `getSession` 外仍是框架原名。

- [ ] 每个操作有稳定、不重复的 operationId。
- [ ] 测试拒绝重复名和自动 `_api_` 名。
- [ ] 重导出后的约定与代码一致。

<a id="be-m0-t08"></a>

## BE-M0-T08 · MySQL 8 持久化方案

| 字段 | 内容 |
|---|---|
| 状态 | done（项目经理在 QA 签署 98c5129 后确认；未合入/未发布） |
| 估算 | 方案已提交；实施另计，且须先逐项批准依赖 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) |
| 来源 | 用户决定业务库为 MySQL 8；本卡只写方案 |
| 完成时交付 | [docs/delivery/BE-M0-T08.md](../delivery/BE-M0-T08.md) |
| 代码解释 | [docs/code/BE-M0-T08.md](../code/BE-M0-T08.md) |

范围：见 [方案](../architecture/mysql-8-persistence-plan.md)。本卡只交付方案。项目经理批准后的依赖和连接由 BE-M0-T10 实施。

- [x] 方案写明选型、逐项依赖、聚合拆分、utf8mb4、回执表、租约表、事务和内网 `mysql:8.4` 命令。
- [x] 方案要求回执和登录会话跨进程共享，并在重启后仍在。本轮不实施。
- [x] 本卡只交付方案。驱动和空迁移不在本卡，见 BE-M0-T10。
- [x] 项目经理在 QA 签署 [98c5129](../testing/2026-10-12-be-m0-t10-mysql-signoff.md) 后确认。

<a id="be-m0-t09"></a>

## BE-M0-T09 · 旧 /api 统一错误体与幂等

| 字段 | 内容 |
|---|---|
| 状态 | planned |
| 估算 | 未开工 |
| 关联 Issue | [ISSUE-021](../../issues/ISSUE-021.md) |
| 依赖 | [BE-M0-T08](BE-M0.md#be-m0-t08)；排在 ISSUE-018 被接受之后 |
| 来源 | 项目经理：旧路由以后并入统一错误体和同一套幂等，本轮不实施 |
| 完成时交付 | `docs/delivery/BE-M0-T09.md` |
| 代码解释 | `docs/code/BE-M0-T09.md` |

范围：把仍使用 `{error, request_id}` 的旧 `/api` 改为与 `/api/v1` 相同的错误体，并统一幂等语义。另含 QA `200a105` 的 E2E-D5：页面兜底把 `/api` 前缀按大小写不敏感处理，`/API/...` 返回 JSON 404 而不是页面壳。本卡尚未开工。

- [ ] 旧 `/api` 错误体与 v1 一致。
- [ ] 幂等语义与 v1 一致，并有回归测试。
- [ ] `/API` 与混合大小写的 `/api` 前缀返回 JSON 404。
- [ ] 未接受 ISSUE-018 之前不开工。

<a id="be-m0-t10"></a>

## BE-M0-T10 · 连接配置与迁移骨架

| 字段 | 内容 |
|---|---|
| 状态 | done（项目经理在 QA 签署 98c5129 后确认；未合入/未发布） |
| 估算 | 4小时以内；不含回执、会话、租约和聚合表 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md)、[ISSUE-023](../../issues/ISSUE-023.md) |
| 依赖 | [BE-M0-T08](BE-M0.md#be-m0-t08)；项目经理已批准方案和四项依赖 |
| 来源 | ISSUE-018 方案第 1 卡 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T10.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T10.md) |

范围：`ICG_DATABASE_URL` 为空时继续使用内存仓库。有值时进程连上 MySQL 8，字符集 `utf8mb4`。Alembic 空基线只建立版本表。标记 `mysql` 的测试在 `ICG_REQUIRE_MYSQL=1` 且缺库时失败。不改公网 CI。

- [x] 未设置连接串时现有测试仍用内存仓库。
- [x] 只设置 `ICG_DATABASE_URL` 时 uvicorn 能连上 `mysql:8.4`。
- [x] `alembic -c backend/bid-core/alembic.ini upgrade head` 不创建业务表。
- [x] `ICG_REQUIRE_MYSQL=1` 时缺连接串或连不上为失败，不是跳过。
- [x] 项目经理在 QA 签署 [98c5129](../testing/2026-10-12-be-m0-t10-mysql-signoff.md) 后确认。

<a id="be-m0-t11"></a>

## BE-M0-T11 · 幂等回执与登录会话入库

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T10](BE-M0.md#be-m0-t10) |
| 来源 | 方案要求回执和会话跨进程共享，并在重启后仍在 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T11.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T11.md) |

范围：把 24 小时幂等回执和登录会话写入 MySQL，多个进程可见，重启后未过期数据仍在。未设置 `ICG_DATABASE_URL` 时仍用内存仓库。租约和业务聚合不在本卡。卡片为 in-review，不标 done。

- [x] Q2：数据库连接必须移出模块导入，以及导入时对 `create_app()` 的调用。连接串已设置但不可达时，测试要在几秒内给出明确失败，不能是收集错误。连接使用较短的 `connect_timeout`。
- [x] 一个进程写入的回执能被另一个进程重放。
- [x] 重启后未过期回执和登录 token 仍有效。
- [x] 失败不保存回执。内存 2048 条上限不套到 MySQL。
- [x] QA M1（ISSUE-025，签署 `b20b844`）：真实表落地后要能 `alembic downgrade base` 再 `upgrade head`。mysql 标记测试做了这次往返。现有 `backend-mysql` 的 `pytest -m mysql` 会执行它。本卡不改工作流。DevOps 若要单独一步，可以自己加进该作业。

<a id="be-m0-t12"></a>

## BE-M0-T12 · 编辑租约入库

| 字段 | 内容 |
|---|---|
| 状态 | done（QA ae6fd10，PM 15:32 确认；未合入/未发布） |
| 估算 | 4小时以内 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T11](BE-M0.md#be-m0-t11) |
| 来源 | 方案中的 120 秒租约、续期和接管 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T12.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T12.md) |

范围：编辑租约写入 MySQL，支持续期和接管。未设置 `ICG_DATABASE_URL` 时单元测试仍用内存仓库。卡片为 in-review，不标 done。字段与字典 v1.9 的对照写在方案第 5 节。偏差已获 PM 有条件批准，待 [ISSUE-032](../../issues/ISSUE-032.md) 对齐。

- [x] 租约 120 秒，续期后占用者不变。
- [x] 过期后其他会话可以接管。
- [x] 释放后库内该行删除，另一个会话可以再取得。
- [x] 单元测试仍可在内存仓库上跑。
- [x] QA ae6fd10，PM 15:32 确认。本卡标为 done。

<a id="be-m0-t13"></a>

## BE-M0-T13 · 按聚合迁移仓库

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；超出则再拆卡 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T12](BE-M0.md#be-m0-t12) |
| 来源 | 方案中的聚合拆分。整份 `DemoState` 不再作为 MySQL 的写入单位 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T13.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T13.md) |

范围：先迁项目聚合。`demo_project` 与 `demo_project_team` 在事务内提交，失败回滚。章节、检查与导出、资料与承诺、工作流与任务、审计仍在内存。字段与字典 v1.9 的对照写在方案第 6 节，偏差需要项目经理批准。卡片为 in-review，不标 done。

- [x] 已迁移的聚合在事务内提交，失败回滚。
- [x] 未迁移的聚合仍有明确边界，不把整份状态当一条记录写入。
- [x] 单元测试默认仍不连接 MySQL。

<a id="be-m0-t14"></a>

## BE-M0-T14 · 托管 MySQL CI 作业

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 对照已有 mysql 标记测试加一条作业；不含业务表 |
| 关联 Issue | [ISSUE-025](../../issues/ISSUE-025.md) |
| 依赖 | [BE-M0-T10](BE-M0.md#be-m0-t10) 的连接与空迁移 |
| 来源 | ISSUE-018 的连接实现 `7d97369`。ISSUE-024 留给后台，本卡不占用该号 |
| 完成时交付 | [专属交付](../delivery/BE-M0-T14.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T14.md) |

范围：在 `.github/workflows/offline-check.yml` 增加 `backend-mysql`。运行时生成密码，启动 `mysql:8.4`，执行空迁移和 `pytest -m mysql`。不改原 `backend` 作业，不建业务表。

当前条件：项目经理依据 QA 签署 `b20b844` 把本卡标为 done。未合入，未发布。

- [x] 作业不把固定密码写入仓库。junit 缺失、0 条、任一跳过，或有失败/错误时作业失败。
- [x] 项目经理依据 QA 签署 [b20b844](../testing/2026-10-12-be-m0-t14-mysql-ci-signoff.md) 把本卡标为 done。
- [x] 两个进程共享回执仍属于 BE-M0-T11，不由本作业代替。

<a id="be-m0-t15"></a>

## BE-M0-T15 · Word 导出默认版式

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；不含客户模板和视觉签收 |
| 关联 Issue | [ISSUE-027](../../issues/ISSUE-027.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) |
| 来源 | QA 记录中的 W1～W4；项目经理批准的默认版式。BE-M0-T14 已由托管 MySQL 作业占用 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T15.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T15.md) |

范围：后台 `.docx` 使用已批准的默认版式。单个投标可以传入另一套版式覆盖。不新增依赖。不把本卡标为 done。

- [x] 标题使用 Heading 1～3，并带多级编号、目录、页眉页脚和页码。
- [x] 分册章节名导出为一级标题，不再是普通段落。
- [x] 表头行加粗。
- [x] 每处字体同时写 eastAsia、ascii 和 hAnsi。
- [ ] 项目经理在 QA 之后确认。本卡仍为 in-review。

<a id="be-m0-t16"></a>

## BE-M0-T16 · 冻结错误码名字

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；不含新增业务错误码 |
| 关联 Issue | [ISSUE-031](../../issues/ISSUE-031.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02) 的状态表 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T16.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T16.md) |

范围：把当前 143 个错误码名字写入冻结名单。`set(ERROR_STATUS)` 和 spec 的 `V1Error.code` 枚举都必须等于这份名单。新增或删除错误码时，同一提交必须更新名单。卡片为 in-review，不标 done。不新增、不删除现有错误码。

- [x] `FROZEN_NAMES` 与运行时表、已保存 spec 的名字一致。
- [x] 只改代码并重新导出时，名字对照失败。
- [x] 接口约定写明同一提交必须更新名单。
- [ ] 项目经理在 QA 之后确认。本卡仍为 in-review。

<a id="be-m0-t17"></a>

## BE-M0-T17 · chapter_lease 对齐字典 edit_lock

| 字段 | 内容 |
|---|---|
| 状态 | planned |
| 估算 | 未开工。等 BE-M0-T13 之后，且 `bid_outline_node`、`sys_user`、`company` 已存在 |
| 关联 Issue | [ISSUE-032](../../issues/ISSUE-032.md) |
| 依赖 | [BE-M0-T13](BE-M0.md#be-m0-t13)；`bid_outline_node`、`sys_user`、`company` |
| 来源 | 方案第 5 节。项目经理有条件批准 `chapter_lease` 与 `edit_lock` 的偏差 |
| 完成时交付 | `docs/delivery/BE-M0-T17.md` |
| 代码解释 | `docs/code/BE-M0-T17.md` |

范围：把 `chapter_lease` 对齐字典 v1.9 的 `edit_lock`。包括大纲节点外键、公司隔离、A 组审计列、心跳、接管人与接管原因、释放时间与释放原因，以及 `loop_status`、`lock_release_reason` 两套枚举。`token` 与 `session_token` 删除，或写出保留理由并再次请项目经理批准。迁移必须保留历史锁行，禁止删除旧租约。本卡尚未开工，不标 done。

- [ ] 三张依赖表存在后，锁表有大纲节点外键、公司隔离和 A 组审计列。
- [ ] 心跳、接管、释放时间和两套枚举已入库。
- [ ] `token` 与 `session_token` 已删除，或保留理由已另获项目经理批准。
- [ ] 迁移不删除历史锁行。
