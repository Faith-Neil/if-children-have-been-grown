为什么有这个文件：说明统一错误体从请求进入到响应离开的实际路径。

它解决什么问题：接手者改某个错误码时，能知道状态必须跟冻结表一致，不能在路由里另写一个。

# BE-M0-T02：代码解释

- 对应任务：[BE-M0-T02](../tasks/BE-M0.md#be-m0-t02)；Issue：[ISSUE-005](../../issues/ISSUE-005.md)；交付：[BE-M0-T02](../delivery/BE-M0-T02.md)
- 日期：2026-10-12。代码在`backend/bid-core/icg_demo/`。直接提交到`codex/repository-foundation`，未开新PR。

## 改了什么以及为什么

原先同一个code可以在不同路由返回不同HTTP状态，OpenAPI里的v1错误也还指向旧的`{error, request_id}`模型。现在`errors.py`的`ERROR_STATUS`是唯一对照表。`DomainError`如果code不在表里，或传入的状态和表不一致，会在构造时失败。

`VOLUME_OWNER_REQUIRED`收入403。角色不足本来就是403，只有确认方案时“尚未指定负责人”曾经用409，已改为403。`require_ready`提升问题时也按表取状态，因此这条同样是403。

`TWO_VOLUMES_REQUIRED`收入422。保存大纲和设置团队时它本来就是请求内容不完整；导出里那一处409已改为422。

解析任务失败后，不再把保存下来的错误一律改成422。重新抛出时使用`status_for(code)`，所以解析器不可用是502，文件展开超限是413。

## 入口和调用顺序

1. 路由或业务函数抛出`DomainError(status, code, message, details)`。
2. `DomainError`调用`status_for`，核对状态。
3. `main.py`的异常处理把v1路径写成`{code, message, details, traceId}`，并设置`X-Request-ID`。旧`/api`仍写`error`和`request_id`。
4. 请求字段不合法时，处理函数附加`details.fields`，code为`VALIDATION_ERROR`，状态422。
5. `export_openapi.py`导出后，`enrich_openapi`把表写入`components.x-error-status`，并把v1错误模型的code列成枚举。枚举只出现在接口说明里，运行时不因为未知code而在响应校验阶段变成500。

## 数据与状态

这张表是代码里的常量，不写入数据库。错误响应本身也不保存。请求编号是本次请求的`uuid4().hex`。

## 关键判断与异常

141个code的分布：401有2个，403有13个，404有1个，409有68个，413有4个，422有44个，423有2个，428有2个，500有1个，502有3个，503有1个。

只在检查结果里出现、又可能被提升成HTTP错误的码，按409登记，例如方案过期、证据过期和若干服务承诺未确认。`HTTP_ERROR`不在表中，因为它跟着原来的传输状态走。

## 验证与限制

[验证记录](../testing/2026-10-12-error-idempotency.md)保存命令和整张表。测试用语法树核对字面`DomainError`是否偏离表，并比较导出的JSON与运行中的OpenAPI。前端错误展示和复制`traceId`不在本卡。
