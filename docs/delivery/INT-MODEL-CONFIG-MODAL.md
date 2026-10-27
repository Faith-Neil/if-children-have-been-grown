# 任务交付：模型配置弹窗前后端联调与涉密本地隔离守卫（INT-MODEL-CONFIG-MODAL）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | INT-MODEL-CONFIG-MODAL |
| 代码解释 | [模型配置弹窗前后端联调代码说明](../code/INT-MODEL-CONFIG-MODAL.md) |
| 验收 | 1. 前端弹窗全功能：`frontend/web/src/admin/ModelConfigModal.tsx` 支持本地 Qwen 与云端模型新增、修改、API Key 掩码保护与连通性即时探测；<br>2. 业务页面集成：在 `App.tsx` 导航中心与 `ProjectSettingsPage.tsx` 项目设置页深度集成模型配置与绑定；<br>3. 物理隔离与涉密门禁：敏感项目尝试绑定云端模型时，后端严格拦截返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，返回统一错误体；<br>4. 内部网络防代理劫持：调用内网模型与 RAGFlow 的 HTTP 客户端显式设置 `trust_env=False`，防止操作系统 VPN/透明代理劫持；<br>5. 单元测试与端到端联调测试全绿：前端单测与 `tests/backend/test_model_config_glue.py` 3 项测试全部通过。 |
| 项目进度 | 本次交付已获 QA 独立终验签署与 PD 产品视角验收通过，并由人类 PM 正式确认标为 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 PRD MVP v1.8 规范及敏感情报物理隔离要求：
1. 客户招标文件、投标正文、Prompt 组装内容与事实片段，严禁发往公网外部大模型；
2. 涉密项目必须强制绑定本地模型（如本地 Qwen），禁止选用云端模型；
3. 为管理员和项目经理提供直观友好的模型配置管理弹窗 `ModelConfigModal.tsx`，支持本地模型与云端模型配置维护；
4. 确保前后端数据流契约严格对齐（RFC 7807 统一错误响应，ETag 乐观并发锁）。

---

## 2. 交付清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `frontend/web/src/admin/ModelConfigModal.tsx` | 前端组件 | 模型配置抽屉/弹窗：支持 provider 切换、base_url、API Key 掩码、is_local 标识及测试连通性 |
| `frontend/web/src/app/App.tsx` | 前端集成 | 顶栏与全局系统设置中唤起模型配置弹窗 |
| `frontend/web/src/project/ProjectSettingsPage.tsx` | 前端集成 | 项目设置页面模型绑定与敏感项目本地模型规则提示 |
| `backend/bid-core/icg/api/model_configs.py` | 后端路由 | 提供模型配置 CRUD、连通性探测、以及项目模型绑定（含 403 涉密本地拦截） |
| `backend/bid-core/icg/api/ragflow.py` | 后端服务 | RAGFlow 与模型调用 HTTP 客户端配置 `trust_env=False`，防止透明代理干扰 |
| `frontend/web/tests/unit/model-config-modal.test.mjs` | 前端单测 | 验证弹窗渲染、字段绑定、表单校验与操作交互 |
| `tests/backend/test_model_config_glue.py` | 后端单测 | 验证连通性测试、项目模型绑定、涉密项目 403 强阻断及统一错误体契约 |

---

## 3. 验收执行证据

1. 后端联调测试：
```powershell
pytest tests/backend/test_model_config_glue.py -v
```
输出：`3 passed in 7.92s`

2. 前端单测：
```powershell
node --test frontend/web/tests/unit/model-config-modal.test.mjs
```
全部测试通过。
