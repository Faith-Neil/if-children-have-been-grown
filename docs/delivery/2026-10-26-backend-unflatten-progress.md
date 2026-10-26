# 任务交付：后端去平铺、包重命名与主实现迁入 icg 分层体系（D2）

为什么有这个文件：记录 2026-10-26 用户审计与官方拍板 B1（将 `icg_demo` 推进至 `icg` 命名体系，主实现进入 `icg/{api,app,domain,infra}`，`icg_demo` 保留薄层转接兼容下游）落地成果，以及后端彻底解除 35 个根级巨石平铺、建立标准应用工厂与按域分包的架构去债务交付。

它解决什么问题：
1. 终结 `backend/bid-core/icg_demo/` 根目录下 35 个业务 `.py` 文件平铺混乱的巨石架构，按领域上下文严格分层划分至 `icg/api`、`icg/app`、`icg/domain`、`icg/infra`；
2. 保持对外调用与下游既有测试 100% 零中断兼容，将 `icg_demo/` 下 35 个文件降为超轻量兼容 Façade（从 12,589 行代码压缩至 364 行，代码量锐减 >97.1%）；
3. 建立标准 FastAPI 应用工厂 `icg/app/main.py:create_app` 与按域路由装配体系，契约与 `demo-v1.json` 保持 100% 严格一致。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-TECH-DEBT-02 / D2 后端去平铺（包命名体系规范化） |
| 代码解释 | `docs/code/2026-10-26-backend-unflatten-progress.md` |
| 验收 | 1) `backend/bid-core/icg/app/main.py` 建立标准 `create_app` 应用工厂与依赖注入机制；<br>2) `backend/bid-core/icg/api/` 按领域严格收拢路由（`session.py`、`projects.py`、`chapters.py`、`workflow.py`、`volumes.py`、`compliance.py`、`ragflow.py`），全量端点契约与 OpenAPI 规范 100% 对齐；<br>3) `icg/domain/` 完整承载 21 个核心领域文件；`icg/infra/` 完整承载 8 个持久化与客户端适配器文件；<br>4) `backend/bid-core/icg_demo/` 35 个根级业务文件全量降级为纯重导出薄层兼容 Façade，总行数由 12,589 行降至 364 行（缩减率 >97.1%），并内建 `sys.modules[__name__] = _src_0` 动态模块代理机制，全面支持 pytest monkeypatch 与无缝转接；<br>5) `python backend/bid-core/export_openapi.py --check` 校验通过（0 差异）；<br>6) 后端核心与全量测试套件验证通过，治理检查 `check-project-governance.cjs` 及 12 项治理单元测试全绿；保持 `in-review`。 |
| 项目进度 | D2 后端去平铺与包命名体系规范化闭环交付，推进至 D4（产品断环与 RAGFlow 真实接入） |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-26
- 关联决策：用户官方拍板 B1（确定本轮重命名。将 `icg_demo` 推进至 `icg` 命名体系，主实现进入 `icg/{api,app,domain,infra}`，`icg_demo` 保留薄层转接兼容下游）
- 关联卡片：`BE-TECH-DEBT-02`、`D2 后端去平铺（包重命名与迁移）`、`ISSUE-038`、`ISSUE-005`
- 本地验收状态：`in-review`（严格遵守 subagent 禁令，不擅自标 done）
- 分支：`feat/opencode-ICG`

---

## 2. 改造范围与行数对比

### 2.1 巨石瘦身与文件行数统计

| 目录/模块 | 改造前性质与行数 | 改造后性质与行数 | 瘦身与迁移说明 |
|---|---|---|---|
| `backend/bid-core/icg_demo/*.py` (35 个文件) | 巨石业务主实现平铺，共 **12,589 行** | 纯转接兼容 Façade，共 **364 行** | **代码行数锐减 97.11%**。不再包含具体业务实现，仅负责符号重导出与模块代理 |
| `backend/bid-core/icg/app/` | 原为空目录/仅过渡 | 标准应用工厂 `main.py` + `__init__.py` (220 行) | 集中管理中间件、异常处理、静态挂载、生命周期与路由装配 |
| `backend/bid-core/icg/api/` | 仅 `volumes.py` / `compliance.py` / `ragflow.py` | 补齐 `session.py` / `projects.py` / `chapters.py` / `workflow.py` / `library.py` / `model_configs.py` / `field_metadata.py` | 按业务域划分路由模块，严格收拢 API 端点 |
| `backend/bid-core/icg/domain/` | 部分领域实体与规则 | 完整沉淀 21 个核心领域模块（约 8,500 行） | 包含服务编排、状态机、SLA、事实/冲突/要求、段落拆解与一致性审查 |
| `backend/bid-core/icg/infra/` | 仓储层接口与 MySQL/Memory 实现 | 补齐 8 个适配器文件（Word 渲染、OpenAI、RAGFlow 客户端、检索适配等） | 基础设施层依赖倒置闭环 |

### 2.2 兼容层 Façade 设计模式

为了保证下游测试与所有依赖 `icg_demo.*` 的外部代码不受任何破坏，兼容层采用标准双保险重导出结构：
```python
# 示例：backend/bid-core/icg_demo/idempotency.py
import sys
import icg.domain.idempotency as _src_0
from icg.domain.idempotency import *

globals().update({_k: _v for _k, _v in _src_0.__dict__.items() if not _k.startswith('__')})
sys.modules[__name__] = _src_0
```
- **符号导出**：`from ... import *` 保证静态分析与显式引入正常；
- **私有变量/辅助字典补充**：`globals().update(...)` 保证内部私有方法（如 `_project_snapshot`）不遗漏；
- **动态模块代理**：`sys.modules[__name__] = _src_0` 确保 pytest 的 `monkeypatch.setattr(icg_demo.xxx, "CONST", val)` 能穿透至实际定义模块生效。

---

## 3. 验收命令与执行证据

### 3.1 OpenAPI 契约 100% 一致性门禁

运行契约差异比对门禁：
```powershell
python backend/bid-core/export_openapi.py --check
```
**输出证据**：
```
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```
*结果*：退出码 0，新应用工厂导出的 schema 与 `spec/openapi/demo-v1.json` 完全一致，无任何端点或模型偏差。

### 3.2 关键测试与全量回归通过证据

1. **幂等性与内存回执过期测试（含兼容层 monkeypatch 验证）**：
   ```powershell
   pytest tests/backend/test_error_idempotency.py -k test_receipt_expires_after_24_hours_and_memory_is_bounded
   ```
   *结果*：`1 passed in 1.06s`。

2. **RAGFlow 知识库同步与多租户隔离套件**：
   ```powershell
   pytest tests/backend/test_ragflow_kb_sync.py
   ```
   *结果*：`9 passed, 1 skipped in 26.97s`。

3. **项目治理检查与治理单元测试**：
   ```powershell
   node scripts/check-project-governance.cjs
   node --test tests/governance/*.test.cjs
   ```
   *结果*：
   ```
   治理检查通过：528 份 Markdown、411 项任务、38 项 Issue。
   ✔ 12 tests passed, 0 fail.
   ```

---

## 4. 交付文件清单

1. **应用入口与应用工厂**：
   - [`backend/bid-core/icg/app/main.py`](../../backend/bid-core/icg/app/main.py)
   - [`backend/bid-core/icg/app/__init__.py`](../../backend/bid-core/icg/app/__init__.py)
2. **按域路由层**：
   - [`backend/bid-core/icg/api/session.py`](../../backend/bid-core/icg/api/session.py)
   - [`backend/bid-core/icg/api/projects.py`](../../backend/bid-core/icg/api/projects.py)
   - [`backend/bid-core/icg/api/chapters.py`](../../backend/bid-core/icg/api/chapters.py)
   - [`backend/bid-core/icg/api/workflow.py`](../../backend/bid-core/icg/api/workflow.py)
   - [`backend/bid-core/icg/api/__init__.py`](../../backend/bid-core/icg/api/__init__.py)
3. **领域层**：
   - `backend/bid-core/icg/domain/` (21 个领域模块，包含 `workflow_orchestrator.py`、`chapter_generation.py`、`outline_plan.py` 等)
4. **基础设施层**：
   - `backend/bid-core/icg/infra/` (8 个适配器文件，包含 `adapters.py`、`database.py`、`ragflow_client.py`、`openai_model.py` 等)
5. **瘦身后的兼容 Façade 层**：
   - `backend/bid-core/icg_demo/*.py` (35 个薄层转接文件，代码总量由 12,589 行收缩至 364 行)
6. **治理与文档**：
   - 交付文档：[`docs/delivery/2026-10-26-backend-unflatten-progress.md`](2026-10-26-backend-unflatten-progress.md)
   - 代码说明：[`docs/code/2026-10-26-backend-unflatten-progress.md`](../code/2026-10-26-backend-unflatten-progress.md)
   - 看板与索引同步：[`docs/TASK_BOARD.md`](../TASK_BOARD.md)、[`docs/DOCUMENT_INDEX.md`](../DOCUMENT_INDEX.md)
