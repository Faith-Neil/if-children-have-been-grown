# 任务交付：异步任务中心与长任务流式通知前后端联调（INT-TASK-CENTER-GLUE）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-TASK-CENTER-GLUE |
| 代码解释 | [异步任务中心与长任务流式通知代码说明](../code/INT-TASK-CENTER-GLUE.md) |
| 验收 | 1. **长任务创建与 demo_job 持久化**：触发长任务操作（如章节批量生成、大纲生成），后端正确分配异步 `job_id`，写入 `demo_job` 持久化仓储（状态 `pending`，progress 0），返回 202 与标准 Location 响应头；<br>2. **SSE 流式推流与 Last-Event-ID 续传**：订阅 `/api/v1/jobs/{id}/events` 获取 `text/event-stream` 实时事件推流，支持 `Last-Event-ID` 断点恢复续传；前端胶水层 `job-progress-sse.ts` 优雅解包标准 OpenAPI `JobEvent` 事件载荷并驱动 UI；<br>3. **平滑降级 HTTP 轮询**：断线后客户端平滑降级至 `GET /api/v1/jobs/{id}`，返回标准 `JobStatus` 模型，任务到达 `completed`/`failed`/`cancelled` 终态时连接优雅关闭；<br>4. **操作动作（allowedActions）与角色权限门禁**：进行中任务 `POST /api/v1/jobs/{id}/cancel`，只读角色拦截 403 `PROJECT_WRITER_REQUIRED`，终态任务再次取消拦截 409 `VERSION_CONFLICT`；失败/已取消任务 `POST /api/v1/jobs/{id}/retry`，仅项目负责人或管理员可办理，只读与非负责人编写人拦截 403 `PROJECT_LEAD_REQUIRED`，排队中/运行中触发重试拦截 409 `VERSION_CONFLICT`，幂等重试支持 `Idempotent-Replayed`；<br>5. **多租户企业空间物理隔离**：跨公司访问长任务严格返回 404 `NOT_FOUND`（杜绝信息嗅探），任务列表 `GET /api/v1/jobs` 按当前登录用户企业空间强隔离；<br>6. **自动化回归全绿**：专属联调测试 `tests/backend/test_task_center_glue.py` 7 项全通，大回归 26 passed，前端权威单测 396 passed，OpenAPI 契约零漂移核验通过。 |
| 项目进度 | 本次交付已获 QA 独立终验签署与 PD 产品视角验收通过，并由人类 PM 正式确认标为 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 §5.12.4 及数据字典 §4.16 规范，系统支持长耗时异步任务（章节批量生成、整本导出、知识库同步等）的后台异步执行、流式推流与状态机流转。前端正落地顶栏任务抽屉与任务徽标（APP-M2-T021），本卡负责在非演示模式（`VITE_DEMO=0`）下彻底打通：
1. 异步任务创建、持久化（`demo_job` 表与状态机）；
2. SSE 实时事件流推流（`/api/v1/jobs/{id}/events`）、`Last-Event-ID` 恢复与轮询降级；
3. `allowedActions` 动作权限控制（取消与重试，8 大标准 RBAC 角色权限感知）；
4. 多租户与多企业空间物理隔离；
5. 前后端数据契约（RFC 7807 统一错误响应，OpenAPI 契约零漂移）。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/recoverable_jobs.py` | 后端核心业务域 | 长任务状态机：重试 `POST /api/v1/jobs/{id}/retry` 落地、取消 `cancel` 仓储同步、`demo_job` 仓储异步透明适配、`allowed_actions` 动态计算 |
| `backend/bid-core/icg/domain/workflow_schemas.py` | 后端契约定义 | `JobStatus` 扩展 `allowed_actions` 与 `allowedActions`，保持 `extra="forbid"` 与零契约漂移 |
| `backend/bid-core/icg/infra/memory_repository.py` | 后端基础设施 | 解决 `MemoryRepository` 嵌套事务（Nested Transaction）状态隔离覆盖，长任务与同步任务存储分流 |
| `frontend/web/src/status/job-progress-sse.ts` | 前端流式管理 | `handleMessageData` 增强，支持直接解包 OpenAPI `JobEvent` 事件体（status_changed / progress / completed / failed / cancelled），驱动长任务进度条优雅终态断开 |
| `spec/openapi/demo-v1.json` | 接口契约规范 | 同步更新导出 OpenAPI 规范，新增 `retryJob` 操作，保证代码与契约 100% 一致 |
| `tests/backend/test_task_center_glue.py` | 专属联调测试 | 覆盖长任务创建、持久化、SSE 推流、轮询降级、取消门禁、重试门禁、跨租户隔离等 7 组核心测试 |

---

## 3. 验收执行证据

### 3.1 专属前后端联调测试通过证据
```powershell
pytest tests/backend/test_task_center_glue.py -v
```
输出结果：
```
tests/backend/test_task_center_glue.py::test_long_task_creation_and_demo_job_persistence PASSED [ 14%]
tests/backend/test_task_center_glue.py::test_job_sse_events_streaming_and_resume PASSED         [ 28%]
tests/backend/test_task_center_glue.py::test_job_polling_and_terminal_completion PASSED        [ 42%]
tests/backend/test_task_center_glue.py::test_job_cancel_action_and_permissions PASSED          [ 57%]
tests/backend/test_task_center_glue.py::test_job_retry_action_and_permissions PASSED           [ 71%]
tests/backend/test_task_center_glue.py::test_tenant_and_multi_company_strong_isolation PASSED  [ 85%]
tests/backend/test_task_center_glue.py::test_persisted_demo_job_transparent_adaptation PASSED  [100%]
============================== 7 passed in 5.43s ==============================
```

### 3.2 任务模块回归与契约核验
```powershell
pytest tests/backend/test_recoverable_jobs.py tests/backend/test_outline_generation_start.py tests/backend/test_task_center_glue.py tests/backend/test_api_v1_convergence.py
```
输出结果：`26 passed in 12.14s`

### 3.3 OpenAPI 零漂移门禁核验
```powershell
python backend/bid-core/export_openapi.py --check
```
输出结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`

### 3.4 前端权威单测全量回归
```powershell
pnpm --dir frontend/web test
```
输出结果：`ℹ tests 396, pass 396, fail 0`

### 3.5 工程治理检查
```powershell
node scripts/check-project-governance.cjs
```
输出结果：`治理检查通过`
