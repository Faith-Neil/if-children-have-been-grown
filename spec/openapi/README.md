为什么有这个文件：解释后台接口约定文件的用途和更新方法。

它解决什么问题：让前端与测试读取同一份字段约定，避免人工复制后逐渐偏离代码。

# ICG产品接口约定

`demo-v1.json`是从实际FastAPI应用导出的OpenAPI，即“前端向后台发送什么、后台返回什么”的机器可读约定。文件名沿用首个后台demo，当前内容已扩展到ICG产品主流程，应用版本为`reference-1`。JSON不能放普通文字注释，因此用途在这里说明；该文件不手工修改。

更新入口：在仓库根运行以下命令，后端运行时也可读取`/openapi.json`：

```powershell
& .\.venv\Scripts\python.exe backend\bid-core\export_openapi.py
```

## 当前两组接口

| 接口组 | 用途 | 关键约定 |
|---|---|---|
| `/api` | 演示登录、项目新建/列表、章节编辑权、草稿、提交版本及旧验证页 | 章节写入校验本次登录的编辑凭据、正文基础版本与重复请求标记；保留旧错误格式 |
| `/api/v1` | 产品工作区、招标文件、解析确认、响应矩阵、项目事实、大纲候选、项目检查、两册输出、基础公司资料与任务记录 | 写入需要`If-Match`和`Idempotency-Key`；按项目或资料库版本核对；使用产品错误格式 |

两组由同一个后端提供并共用一份仓库和公司权限，`frontend/web`同时调用它们。根页面`/`为ICG产品入口；`/demo`是旧开发验证页，不登记为产品接口。

`If-Match`表示“保存时数据仍须是我读到的版本”，缺少它返回428，旧版本返回409。`Idempotency-Key`是同一次操作的重复请求标记；同操作、同内容、同原版本和同标记重试返回原结果，不重复创建内容。项目工作区和资料库读取响应返回`ETag`，即对应的数据版本标签。

`/api/v1`错误为`{code, message, details, traceId}`，`/api`保留`{error: {code, message}, request_id}`；响应头均提供`X-Request-ID`。业务接口及文件下载持续校验登录和所属公司。上传目前通过JSON中的Base64字段传原件字节，文件及Word下载返回二进制内容。

## 修改与验收

接口变更先关联Issue与任务，修改实际服务及请求/响应模型，再重新导出本文件，并核对页面和测试。重新运行 `export_openapi.py` 之前，必须保住已保存 spec 里的草案操作和 `deprecated` 标注。当前脚本会整文件重写，这两类内容会被删掉。脚本修正以后再做，本轮不改导出脚本。新增或删除一个错误码时，必须在同一提交里更新 `backend/bid-core/icg_demo/frozen_error_codes.py` 的 `FROZEN_NAMES`。只改 `errors.py` 再运行 `export_openapi.py`，导出的枚举会跟着新表走，总数也可以仍是 143；冻结名单仍是旧名字，`set(ERROR_STATUS) == FROZEN_NAMES` 和 spec 枚举对照会失败。主流程字段与人工确认规则详见 [示例接口约定](../../docs/architecture/icg-reference-contract.md)。目前页面客户端`frontend/web/src/api.ts`是手写请求层，尚未从OpenAPI生成SDK；后续生成代码需要独立目录与更新流程，不能把手写文件当成自动生成成果。

当前约定只代表已经运行的本地实现。异步202任务、持续事件通知、恢复/取消、完整结构化编辑、分册定稿和正式递交能力尚未实现。演示账号、内存存储、模型替身及已接通的内部稿输出不代表生产身份、数据库或完整合规服务。ICG完整目标由 [ISSUE-007](../../issues/ISSUE-007.md)推进，生产边界继续按 [ISSUE-005](../../issues/ISSUE-005.md)完善。

reference-sla-1阶段从代码新增结构化服务承诺模板、项目值、负责人核对、承诺函及派生只读事实。当前约定共43路径49操作；应用名版本仍沿用reference-1。详细单位、变量与门禁见示例接口约定；本次没有生成或手改SDK。

reference-writing-1阶段新增本章方案事实/要点/字数、实际输入快照、当前输入只读预览与事实变量字段；目前44路径50操作。从实际请求/响应模型重导出，应用版本仍reference-1，不手改生成文件。

写作阶段草稿/版本请求与Draft响应包含input_fingerprint；来源项目强制在后台写入事务核对，缺失或过期返回409。JSON已从实际代码重导出，仍为44路径50操作。

reference-members-1成员阶段（2026-10-11）从实际代码重导出48路径56操作，应用版本仍reference-1。新增项目team读取/完整保存、章节assignment、单章plan保存/确认及本人草稿明确删除；工作区返回项目/章节权限、团队分工和逐章确认依据。旧接口、原件、任务、历史和下载同时核对当前项目成员，公司manager不等于项目负责人。请求回放也必须核对当前资格；生成各次模型调用前后及保存前重新核对。实际代码和页面验证见[成员验收](../../docs/testing/2026-10-10-project-assignments.md)，未生成SDK。

2026-10-12契约阶段从实际代码重导出，仍是49路径、57操作、其中v1为37个操作，没有新增路由。`/api/v1`错误改为`V1Error`：`{code, message, details, traceId}`，并带`X-Request-ID`。每个code只对应一个HTTP状态，写在`components.x-error-status`；`VOLUME_OWNER_REQUIRED`为403，`TWO_VOLUMES_REQUIRED`为422。`components.x-idempotency`记录键的格式、范围、指纹、冲突、缺失、失败不保存、86400秒过期和最多2048条回执。同键同内容重放时响应可带`Idempotent-Replayed`。说明里写明客户端只对网络错误、502和503用同一键重试。502 MODEL_UNAVAILABLE 与 503 SECRET_KEY_UNAVAILABLE 不是瞬时故障，客户端不要自动重试，后端不发送 Retry-After。JSON仍由导出脚本生成，不手改。挂证据字段写在冻结模型 `EvidenceMountFields`：`source_tier`、`is_restricted`（不是 `restricted`）、派生只读的 `agreement_present`，以及对照项目 `bid_deadline_at` 的 `valid_to` / `is_long_term`。资料列表和条款 PATCH 的 `x-issue-033` 写明挂接拒绝，复用 409 `EVIDENCE_EXPIRED`、409 `EVIDENCE_NOT_USABLE` 和 403 `FORBIDDEN`，不新增错误码。运行时资料列表返回已入库字段，条款 PATCH 按这些规则拒绝。`agreement_present` 按项目派生，不写进资料行。验收见[错误体与幂等验证](../../docs/testing/2026-10-12-error-idempotency.md)与[挂证据核对](../../docs/testing/2026-10-12-be-m0-t18-evidence-mount.md)。

BE-M0-T04 增加三条运行中的租约路径：`POST /api/v1/chapters/{chapter_id}/lock`、`/lock/renew`、`/lock/release`。旧 `/api` 三条锁路由仍在。这三条从当时运行中的 OpenAPI 写入本文件，没有重跑 `export_openapi.py`，因此冻结草案和 `deprecated` 标注仍在。`operationId` 仍是框架原名。

BE-M0-T05 在单章 `ExportResponse` 上写明当时绑定的 `check_id`、`revision`、`content_hash` 和 `input_fingerprint`。没有新增 `stale` 布尔字段，也没有把导出改成异步任务。这一段同样从运行中的模型写入，没有重跑 `export_openapi.py`。

BE-M0-T06 把 `startGeneration`、`getJob`、`streamJobEvents`、`cancelJob` 和 `JobStatus` 从冻结草案改成运行中的模型。`getOutlinePlan` 与 `confirmOutlinePlan` 仍是冻结草案。没有重跑 `export_openapi.py`，因此其余冻结草案和 `deprecated` 标注仍在。没有新增错误码，也没有新增 SSE 库。
