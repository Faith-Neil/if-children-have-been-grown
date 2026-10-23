# 任务交付：大模型服务与 RAGFlow 知识库弹窗配置及连通性闭环

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-BE-MODEL-RAGFLOW-CONFIG / APP-M2-T036 / APP-M2-T037 / AI-01 |
| 代码解释 | `docs/code/2026-10-23-model-ragflow-config-modals.md` |
| 验收 | 前端弹窗组件单元测试全绿（378 passed）、后端 API 与加密单测全绿（28 passed, 1 skipped live）、OpenAPI `--check` 100% 一致、多租户隔离与 If-Match 乐观锁通过 |
| 项目进度 | 完成用户拍板决策 Step ③ 前端弹窗与后端 API 闭环；为 Step ④ 最小可递交规则与定稿导出打通配置底座 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-23
- 里程碑：APP-M2 / PRD P0
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-028](../../issues/ISSUE-028.md)、[ISSUE-010](../../issues/ISSUE-010.md)
- 关联卡片：`APP-M2-T036`、`APP-M2-T037`、`AI-01`、`AI-04`、`AI-05`、`AI-06`
- 本地验收状态：`in-review`（严格遵守不自行标 done 约定）
- 分支：`feat/opencode-ICG`

## 背景与用户拍板决策

依据 2026-10-23 专项审查结论与用户直接拍板决策：
1. **产品形态严格定为弹窗配置页**：拒绝单独开孤立页面路由或仅依赖底层环境变量，大模型配置与知识库配置均以优雅的模态弹窗（Modal）交互落地；
2. **践行 Layout First 界面设计克制原则**：杜绝将界面写成说明书，避免堆砌冗余次级标签与大段说教文本，依靠视觉层级、布局与交互流自然表达意图；
3. **对接已有 `/api/v1/model-configs`**：支持列表切换、创建、编辑、密钥掩码与在线测连；
4. **扩展租户级 RAGFlow 检索配置**：在 `/api/v1` 暴露标准化 `GET/PUT/test` 端点，支持多数据集绑定、超时控制与 `/api/v1/system/healthz` 健康检测；
5. **真假服务隔离**：假 RAGFlow 服务严格限制在 CI 离线回归；真实 RAGFlow 服务端点向用户索取并保持动态配置，绝不臆造假端点。

## 完成内容与变更文件

### 1. 后端领域模型与 API
- `backend/bid-core/icg/domain/ragflow_config.py`：实现 `RagflowCompanyConfig` 领域实体与 `RagflowConfigService`，提供 Fernet 对称加密、密钥掩码输出、多租户强隔离与 If-Match 乐观锁并发保护；
- `backend/bid-core/icg/api/ragflow.py`：注册 `/api/v1/ragflow-config`（GET / PUT）与 `/api/v1/ragflow-config/test`（POST），采用规范 lowerCamelCase `operationId`（`getRagflowConfig`、`updateRagflowConfig`、`testRagflowConfig`）；
- `backend/bid-core/icg/api/__init__.py`：汇聚导出 RAGFlow API 路由与 Schema；
- `backend/bid-core/icg_demo/main.py`：注册 `include_ragflow_routes`；
- `tests/backend/test_ragflow_config_api.py`：新增 3 项自动化测试（默认隔离、乐观锁与密钥防泄露、健康测连）。

### 2. 前端弹窗与交互设计
- `frontend/web/src/admin/model-config-core.ts`：纯逻辑模块，提供大模型参数校验、涉密项目本地模型双门禁判定（`is_local && allow_sensitive`）与密钥更新载荷构造；
- `frontend/web/src/admin/ragflow-config-core.ts`：纯逻辑模块，提供 Base URL 格式校验、Dataset IDs 解析与 RAGFlow 更新载荷构造；
- `frontend/web/src/admin/ModelConfigModal.tsx`：大模型服务配置弹窗，对接 `/api/v1/model-configs`，支持列表切换、新建配置、保存修改与连通性测试耗时反馈；
- `frontend/web/src/admin/RagflowConfigModal.tsx`：知识库检索配置弹窗，对接 `/api/v1/ragflow-config`，支持 Base URL、API Key、Dataset IDs 与一键连通性测试；
- `frontend/web/src/admin/CompanyManagePage.tsx`：在本地模型约束模块直接挂接「配置大模型服务」与「配置 RAGFlow 知识库检索」交互按钮并挂载弹窗；
- `frontend/web/src/app/App.tsx`：在顶栏快捷操作区新增「模型配置」与「知识库配置」快捷入口，方便管理员与项目成员快速唤起；
- `frontend/web/tests/unit/model-config-modal.test.mjs`：新增 4 项前端纯逻辑单测；
- `frontend/web/tests/unit/ragflow-config-modal.test.mjs`：新增 4 项前端纯逻辑单测。

## 验收结果与证据

1. **前端 TypeScript 静态编译**：
   - 命令：`pnpm --dir frontend/web lint`
   - 结果：`$ tsc -b --noEmit`，0 错误通过。

2. **前端全量单测套件**：
   - 命令：`pnpm --dir frontend/web test`
   - 结果：`tests 378, pass 378, fail 0` 全部通过（包含 8 项新核心测试）。

3. **后端单测与契约验证**：
   - 命令：`pytest tests/backend/test_ragflow_config_api.py tests/backend/test_ragflow_client.py`
   - 结果：`28 passed, 1 skipped`（跳过项为需真实外部端点的 live 测试）。
   - 命令：`pytest tests/backend/test_model_config_storage.py tests/backend/test_model_config_provider.py`
   - 结果：`23 passed, 1 skipped` 全部通过。
   - 命令：`python backend/bid-core/export_openapi.py --check`
   - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`

4. **真实 RAGFlow 服务接入与测连实测记录**：
   - 用户提供生产内网参数：Base URL `http://192.168.100.212:9380`，API Key `ragflow-MyNmQZTQwY2ViZjExZjFiNTEzTYYyZW`，Dataset ID `03bb2312cec211f1b511e62eeb823f56`；
   - 写入租户配置测试：`PUT /api/v1/ragflow-config` 返回 200，API Key 经 Fernet 加密后成功持久化，掩码返回 `rag***YyZW`，版本递增至 `2`；
   - 读回校验：`GET /api/v1/ragflow-config` 返回 200，明文不回显，严格按租户隔离保护；
   - 连通性测试：`POST /api/v1/ragflow-config/test` 针对该内网服务发起健康检查，正如用户预先说明（内网服务器在 VPN 隔离环境下），请求在超时限制内返回优雅的业务失败反馈 `ok: false, message: "连接失败: health request timed out"`，耗时 4116 ms，未产生未捕获异常或 500 崩溃，充分证明连通性检测与错误容灾链路健壮。

5. **工程治理检查**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：`治理检查通过：518 份 Markdown、409 项任务、38 项 Issue。`

## 文档与 Issue 同步

| 对象 | 更新说明 |
|---|---|
| PRD | 对齐 §6.2、§6.4、§6.6.1，模型与知识库配置采用弹窗落地，符合敏感项目强门禁与租户隔离 |
| ROADMAP | 推进 Step ③ 目标，大模型配置与 RAGFlow 知识库配置前端形态与契约正式闭环 |
| ARCHITECTURE | 前端八域结构（`admin/` 与 `app/`）与后端分包（`icg/domain/`、`icg/api/`）严格保持，无平铺代码 |
| TASK_BOARD / PROJECT_STATUS | 登记 Step ③ 交付，推至 `in-review` |
| DOCUMENT_INDEX | 登记 D-724 |
