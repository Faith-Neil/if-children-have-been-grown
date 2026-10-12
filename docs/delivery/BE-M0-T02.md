为什么有这个文件：记录统一错误体和每个错误码唯一状态的实际交付。

它解决什么问题：让前端按同一份错误体和状态码表处理失败，不再猜同一个码会返回哪个HTTP状态。

# BE-M0-T02：v1统一错误体与HTTP状态码表交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T02 |
| 代码解释 | [实际代码解释](../code/BE-M0-T02.md)，包含错误体、状态表和两处收口 |
| 验收 | `PYTHONPATH=backend/bid-core python3 -m pytest tests/backend -q --tb=line` 通过，含 `MODEL_UNAVAILABLE` 的 v1 统一错误体。治理检查见[验证记录](../testing/2026-10-12-error-idempotency.md) |
| 项目进度 | 350项中20done、4in-review、7in-progress、266planned、49blocked、4ready。本卡为in-review，done只由项目经理在QA签收后标记。未合入、未发布 |
<!-- task-delivery:end -->

日期：2026-10-12。关联：[ISSUE-005](../../issues/ISSUE-005.md)、[任务卡](../tasks/BE-M0.md#be-m0-t02)。分支`codex/repository-foundation`直接提交。状态为in-review；未合入、未发布。done只由项目经理在QA签收后标记。

## 实际成果

`/api/v1`失败响应为`{code, message, details, traceId}`。`traceId`与响应头`X-Request-ID`相同，由服务端生成，不接受客户端传入。每个业务code只对应一个HTTP状态，共141个码。字段校验失败时`details.fields`列出路径，例如`body.name`。

`VOLUME_OWNER_REQUIRED`固定403。它和“缺少所需角色”是同一类；原先有一处“尚未指定负责人”返回409，现已改成403。`TWO_VOLUMES_REQUIRED`固定422。大纲和团队设置本来就是422，导出原先是409，现已改成422。

解析失败重新抛出时使用该code自己的状态。`PARSER_UNAVAILABLE`因此是502，不再被写成422。旧`/api`仍返回`{error:{code, message}, request_id}`。

OpenAPI从代码导出，仍是49路径、57操作。v1不再引用旧错误模型。完整表见[验证记录](../testing/2026-10-12-error-idempotency.md)。

## 验收与限制

专项测试覆盖v1与旧错误形状、字段路径、状态表和导出文件一致。`/api/v1` 的 `MODEL_UNAVAILABLE` 使用统一错误体；旧 `/api` 章节建议保持 `error` 体。全量后台测试通过，次数见验证记录。前端未改，未跑前端测试。

非404的普通HTTP异常仍按传输状态返回，不进入这张一对一表。202排队、SSE、锁迁移、导出快照和operationId改名不在本卡。

## 文档同步与下一步

| 对象 | 本次结果 |
|---|---|
| PRD | 未改。没有改变页面、业务范围或验收口径 |
| ROADMAP | 未改。六张卡记在任务看板和 BE-M0 |
| ARCHITECTURE | 未改。项目经理要求本轮不改该基线；错误码表仍在接口约定。见[同步表](../governance/ISSUE-005-sync.md) |
| PROJECT_BRIEF | 已改。排期改为349项且本卡为in-review；后台写明 MySQL 8 未接入。AI-02 与 T008 保持项目经理已确认的 done |
| Issue | ISSUE-005改为in-review，不标closed。DG-01～04、DG-06和后四张卡未关闭 |
| 任务/进度 | BE-M0-T02为in-review；BE-M0-T04～T07为ready；APP-M2-T002仍planned |
| 文档索引 | 登记本交付、代码解释、验证和同步表 |

同一Issue下的幂等卡BE-M0-T03也已提交为in-review。前端请求层仍由APP-M2-T002实现。
