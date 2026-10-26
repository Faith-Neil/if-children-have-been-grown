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
| 状态 | in-review |
| 估算 | 4小时；沿用现有 120 秒租约，不含数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (c) |
| 完成时交付 | [BE-M0-T04](../delivery/BE-M0-T04.md) |
| 代码解释 | [BE-M0-T04](../code/BE-M0-T04.md) |

范围：把取得、续期和释放编辑权收到 `/api/v1`，沿用现有租约时长和权限判断。本卡为 in-review，不标 done。旧 `/api` 三条锁路由保留给编辑页和 `/demo`。`operationId` 留给 BE-M0-T07。不改 202/SSE，不加数据库。

- [x] v1 租约路由与现有编辑权规则一致。
- [x] 旧验证页仍能完成已有编辑流程，或交付中写明保留方式。
- [x] OpenAPI 写入三条 v1 路径，与运行中的契约一致，并有对应测试。没有重跑 `export_openapi.py`。

<a id="be-m0-t05"></a>

## BE-M0-T05 · 导出快照语义

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时；不含异步导出和数据库 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (d) |
| 完成时交付 | [BE-M0-T05](../delivery/BE-M0-T05.md) |
| 代码解释 | [BE-M0-T05](../code/BE-M0-T05.md) |

范围：按提案冻结导出当时绑定的检查、版本和输入摘要。本卡为 in-review，不标 done。不新增 `stale` 布尔字段，也不把导出改成异步任务。202/SSE 与 operationId 仍留给 T06、T07。

- [x] 导出记录能说明它绑定的检查和已提交内容。
- [x] 来源变化后旧导出不能被当成当前有效结果。
- [x] 契约与测试同步，未实现项写明。

<a id="be-m0-t06"></a>

## BE-M0-T06 · 可恢复任务（202 与 SSE）

| 字段 | 内容 |
|---|---|
| 状态 | in-review（QA REV-M0-T36 tip `0cb6c38` 已签，等 PM） |
| 估算 | 4小时；先定契约与最小行为，不加新依赖 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02)、[BE-M0-T03](BE-M0.md#be-m0-t03) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (e) |
| 完成时交付 | [BE-M0-T06](../delivery/BE-M0-T06.md) |
| 代码解释 | [BE-M0-T06](../code/BE-M0-T06.md) |

范围：长任务先返回 202，再用 SSE 报告进度，并说明断线后如何查询。本卡为 in-review（QA REV-M0-T36 已签，等 PM），不标 done。不新增 SSE 库，不把现有同步解析改成已恢复。

- [x] 选定的长任务有 202 与事件约定。
- [x] 失败和取消有明确状态，不把未实现写成已联调。
- [x] 测试覆盖约定中的最小路径。

<a id="be-m0-t07"></a>

## BE-M0-T07 · operationId 检查

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 2小时；只检查并修正操作名，不加依赖 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-M0-T02](BE-M0.md#be-m0-t02) |
| 来源 | 已批准的 ISSUE-005 契约冻结提案，卡片 (f) |
| 完成时交付 | [docs/delivery/BE-M0-T07.md](../delivery/BE-M0-T07.md) |
| 代码解释 | [docs/code/BE-M0-T07.md](../code/BE-M0-T07.md) |

范围：OpenAPI 的 `operationId` 使用 lowerCamelCase，全局唯一，已去除框架自动生成的 `_api_` 冗余前缀与下划线。本卡标为 in-review，不标 done。

- [x] 每个操作有稳定、不重复的 operationId。
- [x] 测试拒绝重复名和自动 `_api_` 名。
- [x] 重导出后的约定与代码一致。

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
| 状态 | in-review |
| 估算 | 4小时以内；统一错误体与幂等规范 |
| 关联 Issue | [ISSUE-021](../../issues/ISSUE-021.md) |
| 依赖 | [BE-M0-T08](BE-M0.md#be-m0-t08)；排在 ISSUE-018 被接受之后 |
| 来源 | 项目经理：旧路由以后并入统一错误体和同一套幂等 |
| 完成时交付 | [BE-M0-T09](../delivery/BE-M0-T09.md) |
| 代码解释 | [BE-M0-T09](../code/BE-M0-T09.md) |

范围：把仍使用 `{error, request_id}` 的旧 `/api` 改为与 `/api/v1` 相同的错误体，并统一幂等语义。另含 QA `200a105` 的 E2E-D5：页面兜底把 `/api` 前缀按大小写不敏感处理，`/API/...` 返回 JSON 404 而不是页面壳。卡片为 in-review，不标 done。

- [x] 旧 `/api` 错误体与 v1 一致。
- [x] 幂等语义与 v1 一致，并有回归测试。
- [x] `/API` 与混合大小写的 `/api` 前缀返回 JSON 404。
- [x] 未接受 ISSUE-018 之前不开工（ISSUE-018 已接受并推进）。

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
| 状态 | done（QA 5e4a627，PM 确认 REV-M0-T28；未合入/未发布） |
| 估算 | 4小时以内 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T10](BE-M0.md#be-m0-t10) |
| 来源 | 方案要求回执和会话跨进程共享，并在重启后仍在 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T11.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T11.md) |

范围：把 24 小时幂等回执和登录会话写入 MySQL，多个进程可见，重启后未过期数据仍在。未设置 `ICG_DATABASE_URL` 时仍用内存仓库。租约和业务聚合不在本卡。卡片已依据 QA 5e4a627，PM 确认 REV-M0-T28 标为 done。ISSUE-018 仍为 in-progress。

- [x] Q2：数据库连接必须移出模块导入，以及导入时对 `create_app()` 的调用。连接串已设置但不可达时，测试要在几秒内给出明确失败，不能是收集错误。连接使用较短的 `connect_timeout`。
- [x] 一个进程写入的回执能被另一个进程重放。
- [x] 重启后未过期回执和登录 token 仍有效。
- [x] 失败不保存回执。内存 2048 条上限不套到 MySQL。
- [x] QA M1（ISSUE-025，签署 `b20b844`）：真实表落地后要能 `alembic downgrade base` 再 `upgrade head`。mysql 标记测试做了这次往返。现有 `backend-mysql` 的 `pytest -m mysql` 会执行它。本卡不改工作流。DevOps 若要单独一步，可以自己加进该作业。
- [x] QA 5e4a627，PM 确认 REV-M0-T28。本卡标为 done。ISSUE-018 仍为 in-progress。REV-M0-T28 仍为 in-review。

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
| 状态 | done（QA ae38ec3，PM 17:16 确认；未合入/未发布） |
| 估算 | 4小时以内；超出则再拆卡 |
| 关联 Issue | [ISSUE-018](../../issues/ISSUE-018.md) |
| 依赖 | [BE-M0-T12](BE-M0.md#be-m0-t12) |
| 来源 | 方案中的聚合拆分。整份 `DemoState` 不再作为 MySQL 的写入单位 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T13.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T13.md) |

范围：先迁项目聚合。`demo_project` 与 `demo_project_team` 在事务内提交，失败回滚。章节、检查与导出、资料与承诺、工作流与任务、审计仍在内存。字段与字典 v1.9 的对照写在方案第 6 节。偏差已获 PM 有条件批准，待 [ISSUE-035](../../issues/ISSUE-035.md) 对齐。卡片已依据 QA ae38ec3，PM 17:16 确认 done。

- [x] 已迁移的聚合在事务内提交，失败回滚。
- [x] 未迁移的聚合仍有明确边界，不把整份状态当一条记录写入。
- [x] 单元测试默认仍不连接 MySQL。
- [x] QA ae38ec3，PM 17:16 确认。本卡标为 done。ISSUE-018 仍为 in-progress。对齐仍见 ISSUE-035。

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
| 状态 | done（用户 Word/WPS 目视 OK，PM 18:01 确认；未合入/未发布） |
| 估算 | 4小时以内；不含客户模板和视觉签收 |
| 关联 Issue | [ISSUE-027](../../issues/ISSUE-027.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) |
| 来源 | QA 记录中的 W1～W4；项目经理批准的默认版式。BE-M0-T14 已由托管 MySQL 作业占用 |
| 完成时交付 | [实际交付](../delivery/BE-M0-T15.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T15.md) |

范围：后台 `.docx` 使用已批准的默认版式。单个投标可以传入另一套版式覆盖。不新增依赖。卡片已由项目经理于 18:01 确认 done。用户已在 Word/WPS 目视确认。

- [x] 标题使用 Heading 1～3，并带多级编号、目录、页眉页脚和页码。
- [x] 分册章节名导出为一级标题，不再是普通段落。
- [x] 表头行加粗。
- [x] 每处字体同时写 eastAsia、ascii 和 hAnsi。
- [x] 项目经理于 18:01 确认。用户已在 Word/WPS 目视 OK。本卡标为 done。ISSUE-027 标为 closed。

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
- [ ] 项目经理在 QA 之后确认。QA REV-M0-T34 tip `90b2334` 已签。本卡仍为 in-review。

<a id="be-m0-t17"></a>

## BE-M0-T17 · chapter_lease 对齐字典 edit_lock

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；对齐字典 edit_lock 结构 |
| 关联 Issue | [ISSUE-032](../../issues/ISSUE-032.md) |
| 依赖 | [BE-M0-T13](BE-M0.md#be-m0-t13)；`bid_outline_node`、`sys_user`、`company` |
| 来源 | 方案第 5 节。项目经理有条件批准 `chapter_lease` 与 `edit_lock` 的偏差 |
| 完成时交付 | [BE-M0-T17](../delivery/BE-M0-T17.md) |
| 代码解释 | [BE-M0-T17](../code/BE-M0-T17.md) |

范围：把 `chapter_lease` 对齐字典 v1.9 的 `edit_lock`。包括大纲节点外键、公司隔离、A 组审计列、心跳、接管人与接管原因、释放时间与释放原因，以及 `loop_status`、`lock_release_reason` 两套枚举。`token` 与 `session_token` 删除，或写出保留理由并再次请项目经理批准。迁移必须保留历史锁行，禁止删除旧租约。本卡为 in-review，不标 done。

- [x] 三张依赖表存在后，锁表有大纲节点外键、公司隔离和 A 组审计列。
- [x] 心跳、接管、释放时间和两套枚举已入库。
- [x] `token` 与 `session_token` 已删除，或保留理由已另获项目经理批准（向下兼容多端与防跨 Tab 覆盖）。
- [x] 迁移不删除历史锁行。

<a id="be-m0-t18"></a>

## BE-M0-T18 · 挂证据拒绝过期、缺协议和受限资料

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 已提交复查。不新增错误码 |
| 关联 Issue | [ISSUE-033](../../issues/ISSUE-033.md) |
| 依赖 | [BE-M0-T13](BE-M0.md#be-m0-t13) |
| 来源 | 条款 PATCH 挂证据。沿用已有 `EVIDENCE_EXPIRED`、`EVIDENCE_NOT_USABLE`、`FORBIDDEN` |
| 完成时交付 | [实际交付](../delivery/BE-M0-T18.md) |
| 代码解释 | [实际代码解释](../code/BE-M0-T18.md) |

范围：条款 PATCH 挂证据时拒绝过期、仅供参考、缺协议和无权的受限资料。字段名是 `is_restricted`，与冻结模型 `EvidenceMountFields` 一致。协议是否存在从本项目 `project_partner.agreement_attachment_id` 推导，不写成资料列。不新增错误码。卡片为 in-review，不标 done。

- [x] 规格增量已在冻结契约。运行时已按同一套字段和已有错误码拒绝挂接。
- [x] `is_restricted` 可写入资料；旧字段名 `restricted` 被拒绝。
- [x] QA 运行时重签（REV-M0-T35 tip `90b2334`）已通过；仍由项目经理标 done。

<a id="be-m0-t19"></a>

## BE-M0-T19 · demo_project 对齐字典 bid_project

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；对齐字典 bid_project 结构 |
| 关联 Issue | [ISSUE-035](../../issues/ISSUE-035.md) |
| 依赖 | [BE-M0-T13](BE-M0.md#be-m0-t13)；正式项目表、成员表和投标主体 |
| 来源 | 方案第 6 节。项目经理有条件批准 `demo_project` 与 `bid_project` 的偏差 |
| 完成时交付 | [BE-M0-T19](../delivery/BE-M0-T19.md) |
| 代码解释 | [BE-M0-T19](../code/BE-M0-T19.md) |

范围：把 `demo_project` 对齐字典 v1.9 的 `bid_project` 结构（扩充 tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived 与 A 组系统审计字段）。Alembic 迁移（0011）严格采用 ADD COLUMN 增量变更，绝对保留历史项目数据，严禁清空旧行。接口 GET /api/v1/projects 与旧版接口向后兼容，测试全量通过。本卡为 in-review，绝不私自标 done。

- [x] 正式表存在后，项目主键、状态、主体、截止时间和正式索引与字典一致。
- [x] 成员是独立行，不是 `team_json` 一整块，并有 A 组审计列。
- [x] 迁移不删除历史项目和成员。

<a id="be-checks-export-align"></a>

## BE-CHECKS-EXPORT-ALIGN · 检查阻断红线与整本导出快照版式核对

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；检查阻断红线与导出 400 强门禁 |
| 关联 Issue | [ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-027](../../issues/ISSUE-027.md) |
| 依赖 | BE-CHECKS-EXPORTS-PERSISTENCE、[BE-M0-T15](BE-M0.md#be-m0-t15) |
| 来源 | PRD v1.8 §5.12 标书检查导出与 Word 默认版式规范 |
| 完成时交付 | [BE-CHECKS-EXPORT-ALIGN](../delivery/BE-CHECKS-EXPORT-ALIGN.md) |
| 代码解释 | [BE-CHECKS-EXPORT-ALIGN](../code/BE-CHECKS-EXPORT-ALIGN.md) |

范围：强化合规检查引擎（run_check），识别废标红线与星号条款，未有效响应或缺资质证据时赋予 blocker 严重度；整本导出（POST /api/v1/projects/{project_id}/exports）在 submission 模式下存在 blocker 时强拦截 400 CHECK_BLOCKER_EXISTS，internal_review 模式放行并标记 has_blockers=True 与合规告警；快照中注入 64 位十六进制 SHA-256 文件指纹与 Word 默认版式元数据（A4 纵向、上下 2.54cm / 左右 2.80/2.60cm 边距、仿宋 16pt 正文、28pt 行距、560 缇缩进、小标宋 22pt 居中大标题等）；保护 143 冻结错误码。本卡为 in-review，绝不私自标 done。

- [x] 废标红线与关键星号条款在未有效响应/缺资质证据时判定为 blocker 严重度。
- [x] 整本导出 submission 模式在有 blocker 时强拦截返回 HTTP 400 CHECK_BLOCKER_EXISTS。
- [x] 整本导出 internal_review 模式放行并标记 has_blockers=True 与合规告警。
- [x] 导出快照结构注入 64 位 SHA-256 版式指纹与 Word 默认版式元数据。
- [x] 专属单测 4 项通过，143 错误码基线零漂移，全量回归套件绿灯。

<a id="be-volume-finalize-gate"></a>

## BE-VOLUME-FINALIZE-GATE · 分册定稿状态机与前置检查门禁

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；分册定稿状态机与前置安全门禁 |
| 关联 Issue | [ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [BE-CHECKS-EXPORT-ALIGN](BE-M0.md#be-checks-export-align)、[BE-M0-T15](BE-M0.md#be-m0-t15) |
| 来源 | PRD v1.8 §5.8.5 分册检查与定稿闭环规范 |
| 完成时交付 | [BE-VOLUME-FINALIZE-GATE](../delivery/BE-VOLUME-FINALIZE-GATE.md) |
| 代码解释 | [BE-VOLUME-FINALIZE-GATE](../code/BE-VOLUME-FINALIZE-GATE.md) |

范围：在 `backend/bid-core/icg/` 分包架构中实现分册定稿（finalize）状态机与安全门禁；仅项目负责人（project_lead）或公司管理员（company_admin）允许触发，编写人拦截 403 FORBIDDEN，跨租户隔离返回 404 NOT_FOUND；前置门禁 1 核对分册内全部章节已具备正式正文且当前未处于排他租约锁定状态（否则拦截 409 LOCK_HELD 或 CHAPTER_CONTENT_EMPTY）；前置门禁 2 核对分册不存在未消解的 blocker 缺陷（否则拦截 409 CHECK_BLOCKER_EXISTS）；通过后流转标记 is_finalized=True 并记录定稿人与时间戳；支持定稿后先解锁后修改生命周期（POST unlock）；新端点收敛于 /api/v1。本卡为 in-review，绝不私自标 done。

- [x] 仅项目负责人与公司管理员允许定稿；编写人拦截 403，跨租户隔离 404。
- [x] 章节排他锁定拦截 409 LOCK_HELD，释放锁定后恢复放行。
- [x] 章节缺少正式正文拦截 409 CHAPTER_CONTENT_EMPTY。
- [x] 存在未消解 blocker 缺陷拦截 409 CHECK_BLOCKER_EXISTS，消减后恢复放行。
- [x] 定稿状态标记 is_finalized=True，记录定稿人与时间戳，支持解锁（unlock）全生命周期。
- [x] 专属单测 10 项通过，回归套件全绿，OpenAPI 契约一致。

<a id="be-compliance-rules-p0"></a>

## BE-COMPLIANCE-RULES-P0 · 第一批核心合规规则编号落地

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 4小时以内；合规规则体系 P0 级结构化编号落地与引擎核验 |
| 关联 Issue | [ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-027](../../issues/ISSUE-027.md) |
| 依赖 | [BE-CHECKS-EXPORT-ALIGN](BE-M0.md#be-checks-export-align)、[BE-VOLUME-FINALIZE-GATE](BE-M0.md#be-volume-finalize-gate) |
| 来源 | PRD v1.8 MVP §5.8 / §5.8.1 / §5.8.5 核心合规规则核验规范 |
| 完成时交付 | [BE-COMPLIANCE-RULES-P0](../delivery/BE-COMPLIANCE-RULES-P0.md) |
| 代码解释 | [BE-COMPLIANCE-RULES-P0](../code/BE-COMPLIANCE-RULES-P0.md) |

范围：在 `backend/bid-core/icg/domain/compliance_rules.py` 中落地 PRD 核心合规规则第一批编号体系（R15/R23/R34/R37），输出统一数据结构 `{rule_id, title, severity, passed, finding_summary, suggestion, issues, details}`；R15 证明材料齐全性（缺失/过期/未确认拦截）；R23 废标红线与关键标星条款 100% 响应与章节映射（未响应/被忽略强阻断 blocker）；R34 占位符与“待补/待完善”残留字样核验（正文与条款响应排查，拦截 blocking）；R37 偏离表一致性核验（负偏离强阻断 blocker，正偏离与无偏离一致性校验）；集成到 WorkflowService 与 run_check 导出检查门禁；在 `/api/v1` 暴露 evaluate、get 与 catalog 查询端点；保障公司租户强隔离与 RULES_INCOMPLETE 底线门禁。本卡为 in-review，绝不私自标 done。

- [x] 核心合规规则第一批编号落地（R15、R23、R34、R37），严格输出规范结构体。
- [x] R15 证明材料齐全性核验：覆盖资质、证书、财务、纳税等，拦截材料缺失、过期与未确认。
- [x] R23 废标与关键标星条款核验：100% 覆盖与非空确认，未响应/被忽略/未映射有效章节赋 blocker。
- [x] R34 占位符与“待补/待完善”残留排查：正文与响应残留排查，发现即判定 blocking/blocker。
- [x] R37 偏离表一致性核验：关键条款负偏离强阻断，正偏离与无偏离与响应矩阵校验一致。
- [x] 集成到 export_service.run_check，统一赋 rule_id 与 rules 列表；暴露 /api/v1 端点。
- [x] 专属单测 7 项全绿，回归套件 14 项全绿，OpenAPI 契约零漂移一致。




<a id="be-tech-debt-01"></a>

## BE-TECH-DEBT-01 · 收敛 suggestions 双错误体至规范体

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 4小时以内；收敛 suggestions 接口双错误体分支并完善单测 |
| 关联 Issue | [ISSUE-038](../../issues/ISSUE-038.md)、[ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [WP-5](../delivery/WP-5.md) |
| 来源 | ISSUE-038 结构债务收敛提案 |
| 完成时交付 | [BE-TECH-DEBT-01 交付](../delivery/2026-10-26-persistence-and-error-body.md) |
| 代码解释 | [BE-TECH-DEBT-01 代码说明](../code/2026-10-26-persistence-and-error-body.md) |

范围：在 `backend/bid-core/icg_demo/main.py` 的异常处理器中，彻底移除旧结构兼容分支，全站统一遵循 RFC 7807 规范错误体 `{code, message, details, traceId}`；同步更新 `tests/backend/test_openai_compatible_model.py` 等单测对标准错误体的直接解构断言；在 `/api/demo` 端点注入 RFC 8594 `Sunset: Sun, 15 Nov 2026 00:00:00 GMT` 与 `Deprecation: true` 响应头；新增错误体与废弃声明专属单测。

- [x] suggestions 接口在异常时仅返回单一标准错误体（无根级 error 与 request_id 冗余）。
- [x] /api/demo 全量端点在响应头注入 Sunset 与 Deprecation 标记。
- [x] 专属单测全绿通过，全量回归套件无断裂。

<a id="be-tech-debt-02"></a>

## BE-TECH-DEBT-02 · 后端业务主实现分层迁移至 icg 上下文分包体系（去平铺）

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 6小时；落实用户拍板决策 B1，主实现全面迁出 icg_demo/ 至 icg/{api,app,domain,infra} |
| 关联 Issue | [ISSUE-038](../../issues/ISSUE-038.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [WP-4](../delivery/WP-4.md) |
| 来源 | 用户 2026-10-26 拍板 B1 决策 |
| 完成时交付 | [BE-TECH-DEBT-02 交付](../delivery/2026-10-26-backend-unflatten-progress.md) |
| 代码解释 | [BE-TECH-DEBT-02 代码说明](../code/2026-10-26-backend-unflatten-progress.md) |

范围：将原平铺在 `backend/bid-core/icg_demo/` 根目录的 35 个业务模块分层迁移至 `backend/bid-core/icg/`：`api/`（路由）、`app/`（应用装配）、`domain/`（领域服务）与 `infra/`（持久化仓储）；`icg_demo/` 代码量由 12,589 行锐减至 364 行薄兼容 Façade（压缩率 97.11%），通过 `sys.modules` 动态模块代理保障单测零断裂；OpenAPI 契约一致性校验通过。

- [x] 主业务逻辑完全入驻 icg/{api,app,domain,infra} 分包体系。
- [x] icg_demo 保持超轻量兼容门面（< 400 行）。
- [x] 后端 41 项自动化测试全过，OpenAPI 契约零漂移。

<a id="int-volume-finalize-glue"></a>

## INT-VOLUME-FINALIZE-GLUE · 分册定稿与工作台/导出前后端契约胶水打通

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 4小时；分册定稿工作台交互、状态流转与导出前置门禁前后端联调打通 |
| 关联 Issue | [ISSUE-005](../../issues/ISSUE-005.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [BE-VOLUME-FINALIZE-GATE](BE-M0.md#be-volume-finalize-gate)、[REV-SMOKE-001](../delivery/REV-SMOKE-001.md) |
| 来源 | PRD v1.8 §5.8.5 分册定稿前后端闭环规范 |
| 完成时交付 | [INT-VOLUME-FINALIZE-GLUE 交付](../delivery/INT-VOLUME-FINALIZE-GLUE.md) |
| 代码解释 | [INT-VOLUME-FINALIZE-GLUE 代码说明](../code/INT-VOLUME-FINALIZE-GLUE.md) |

范围：排查并打通前端 `ProjectPages.tsx` / `EditorPage.tsx` 与后端 `/api/v1/projects/{project_id}/volumes/{volume_id}/finalize` 的契约胶水；验证项目负责人角色触发定稿、成功标记 `is_finalized`、章节锁定与定稿后正文禁止直接覆写的联动；验证未消解 blocker 时的 409 拦截与前端错误提示提示；打通递交版导出在分册已定稿且合规规则齐备下的顺利流转。

- [x] 前端分册定稿操作成功调用 `/api/v1` 定稿端点，状态即时刷新。
- [x] 存在 blocker 缺陷时前端正确呈现 409 拦截提示，消解后定稿成功。
- [x] 前后端联合冒烟通过，契约 100% 对齐 OpenAPI。

<a id="be-compliance-rules-p1"></a>

## BE-COMPLIANCE-RULES-P1 · 核心合规规则第二批编号落地（R03/R04/R09/R10）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时以内；PRD 核心合规规则第二批结构化落地与导出阻断联动 |
| 关联 Issue | [ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-027](../../issues/ISSUE-027.md) |
| 依赖 | [BE-COMPLIANCE-RULES-P0](BE-M0.md#be-compliance-rules-p0)、[BE-VOLUME-FINALIZE-GATE](BE-M0.md#be-volume-finalize-gate) |
| 来源 | PRD v1.8 §5.8 商务与资质合规规则核验规范 |
| 完成时交付 | [BE-COMPLIANCE-RULES-P1 交付报告](../delivery/BE-COMPLIANCE-RULES-P1.md) |
| 代码解释 | [BE-COMPLIANCE-RULES-P1 代码说明](../code/BE-COMPLIANCE-RULES-P1.md) |

范围：在 `backend/bid-core/icg/domain/compliance_rules.py` 中扩展落地 R03（资质有效期核验）、R04（联合体协议核验）、R09（服务承诺一致性与SLA响应）、R10（质保期与响应时间）规则裁决；集成至 run_check 与整本导出门禁，在 submission 模式下存在 blocker 强行拦截；编写专属单测 tests/backend/test_compliance_rules_p1.py。

<a id="int-model-config-modal"></a>

## INT-MODEL-CONFIG-MODAL · 大模型与 RAGFlow 弹窗配置前后端契约联调

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时；大模型与知识库配置弹窗前后端契约打通与连通性联调 |
| 关联 Issue | [ISSUE-010](../../issues/ISSUE-010.md)、[ISSUE-028](../../issues/ISSUE-028.md)、[ISSUE-037](../../issues/ISSUE-037.md) |
| 依赖 | [AI-RAGFLOW-KB-SYNC](AI-M0.md#ai-ragflow-kb-sync)、[APP-M2-T036](APP-M2.md#app-m2-t036) |
| 来源 | 用户 2026-10-26 拍板“模型与知识库前端定为弹窗配置页” |
| 完成时交付 | [INT-MODEL-CONFIG-MODAL 交付报告](../delivery/INT-MODEL-CONFIG-MODAL.md) |
| 代码解释 | [INT-MODEL-CONFIG-MODAL 代码说明](../code/INT-MODEL-CONFIG-MODAL.md) |

范围：打通前端设置/导航弹窗组件与后端 /api/v1/model-configs 及 /api/v1/ragflow/config 的前后端调用契约；支持模型配置列表查询、连通性实时测试、项目绑定与内网 RAGFlow 配置更新；在涉密项目绑定非本地模型时前端呈现 403 阻断；编写契约联调测试。
