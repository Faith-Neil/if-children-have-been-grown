为什么有这个文件：记录额度暂停期前后端六点专项审查结论、用户决策（①~④顺序、弹窗配置页形态、真 RAGFlow 服务接入、写码由用户本人通过 Antigravity 完成/ICG bot只读）以及任务看板（TASK_BOARD.md）板头与任务备注变更依据。

它解决什么问题：明确工单任务完成率（done≈13%）与真实产品完备度（约28%～35%）的差距，固化模型配置与知识库/RAGFlow 前端弹窗形态的用户拍板，避免因口径不一或跳序执行导致项目偏离主路径。

# 任务看板变更交付：模型与 RAGFlow 专项审查及用户拍板

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | TASK-BOARD-FE-BE-REVIEW |
| 代码解释 | 无代码变更；看板板头与任务卡备注治理同步 |
| 验收 | 看板文首 tip 更新至 `4c7e4b3`；移除过时的「PR #3待合入」；下一棒默认顺序收敛为 ①~④；板头追加「额度暂停期审查纪要」；APP-M2 模型卡与 AI-01/04/05/06 补充弹窗配置与真 RAGFlow 接入备注；治理检查通过 |
| 项目进度 | 看板基线校准，明确下一棒由 ① 修复 Actions 离线 CI 开始有序推进 |
<!-- task-delivery:end -->

## 1. 变更背景与审查前因

### 1.1 总判断
- 看板任务完成率（done≈52/404，约 13%）仅代表拆分工单的局部状态；
- 产品功能完备度经深度审查粗估仅约 28%～35%（依据 `docs/delivery/2026-10-22-prd-gap-summary.md`）；
- 主链路（建项→解析→矩阵→生成→编辑→检查→导出）多处于部分交付或演示兼容壳状态；递交版导出仍因全量规则未齐被 `RULES_INCOMPLETE` 门禁强行拦截。

### 1.2 六点专项审查结论（模型配置与知识库 / RAGFlow）
| 专项项 | 审查结论 | 现状说明 |
|---|---|---|
| **模型配置前端页** | **无** | 无独立路由与交互入口；APP-M2-T036～T041 多处于 planned，前端未做连接表单 |
| **模型后端运行时** | **部分** | 后端已有 `/api/v1/model-configs` CRUD、测试连接及项目绑定能力；ISSUE-028/AI-01 为 in-review；仅假服务跑通 |
| **模型前后端联调（含 UI）** | **无** | 前端完全未调用 `/api/v1/model-configs`，无联调界面 |
| **RAGFlow 前端配置页** | **无** | 无任何针对 RAGFlow 端点、密钥、知识库数据集绑定的前端管理界面 |
| **RAGFlow 后端检索** | **部分** | 客户端具备 env 门控；AI-04/05/06 为 in-review；章节 AI 闭环仅在假 RAG 服务下跑通 |
| **RAGFlow 配置联调（含 UI）** | **无** | 缺乏前后端真实配置联动，配置当前仅依赖环境变量，未对齐真实数据集 |

### 1.3 ICG 各角色意见摘要（只读审查）
- **后端**：主流量与多数聚合调用仍在 `icg_demo/`；Memory 旁路与 MySQL 双路径存在质量风险；demo 命名与 `/api/demo` + `/api/v1` 双前缀未收口；前端未调用 model-configs。
- **前端**：无独立模型与 RAGFlow 配置入口；公司设置页中的只读展示字段不等于联调完成。
- **AI**：当前仅在假服务假数据下全绿；真 RAGFlow 服务从未实际验收；缺少 dataset 绑定与 kb_sync 导致知识摄入闭环缺失；配置目前仅靠环境变量硬编码。
- **QA**：单测绿不等于产品可验收；看板上积压多张 in-review；关演示真实环境（`VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1`）必须具备独立端到端人工冒烟证据。
- **DevOps**：`.github/workflows/offline-check.yml` 的 `on.push` / `pull_request` 分支仅配置了已删除的 `codex/repository-foundation`，导致向 `feat/opencode-ICG` 与 `main` 推送代码时根本不会触发 CI；远程 tip 处于 checks=0 状态；分支保护未开启；看板上仍残留「PR #3待合入」的陈旧叙述。

---

## 2. 用户决策落实

依据用户明确拍板（必须按此执行）：
1. **严格按序执行四项任务**：① → ② → ③ → ④（不要跳序）：
   - **① 修 CI 工作流**：修复 `.github/workflows/offline-check.yml`，分支覆盖 `main` 与 `feat/opencode-ICG`，推送后确认 Actions 五大作业全绿并编写交付报告；
   - **② 对齐 tip 与真实冒烟**：回写看板与 PROJECT_STATUS 真实 tip；梳理「已签等 PM」清单交由用户/PM确认；在 `VITE_DEMO=0` + `ICG_REQUIRE_MYSQL=1` 下完成主路径人工冒烟留证；
   - **③ 前端弹窗配置与真 RAGFlow 接入**：模型配置与 RAGFlow 配置前端形态明确采用**弹窗配置页**；对接 `/api/v1/model-configs`；接入真实 RAGFlow 服务（参考 https://github.com/infiniflow/ragflow）；假服务仅保留供 CI 离线回归；真实端点/Key 向用户索取，严禁编造；
   - **④ 规则最小可递交集 + 分册定稿闸门**：推进合规规则编号集与定稿锁定闭环。
2. **配置交互形态**：模型配置与知识库/RAGFlow 配置前端形态定为**弹窗配置页**（不是只靠环境变量或整页大重构）。
3. **真实服务底线**：RAGFlow 必须接入真实运行服务；假服务仅保留给 CI 离线检查使用。
4. **代码编写权**：写码由用户本人通过 Antigravity 完成；ICG bot 仅执行只读审查。

---

## 3. 看板修改点核对

1. **文首 tip 校准**：`tip：7b3c196` 更新为 `tip：4c7e4b3`；
2. **清理过期描述**：移除「PR #3待合入」，澄清 PR #3 已合入且 foundation 分支已删除；
3. **更新下一棒顺序**：将「下一棒默认顺序」替换为用户决策的 ①~④ 四步流程；
4. **新增纪要小节**：在板头完整记录「额度暂停期审查纪要（2026-10-23）」；
5. **模型与 RAGFlow 任务卡备注更新**：
   - APP-M2-T036～T041：标注“用户要求弹窗配置；后端 API 已有、前端未接”；
   - AI-01：标注“后端已有 /api/v1/model-configs，用户要求弹窗配置，前端未接；保持 in-review”；
   - AI-04～06：标注“保持 in-review；真 RAGFlow 列入 ③，假服务仅限 CI，勿标生产已接好”。

---

## 4. 验证与同步记录

- `node scripts/check-project-governance.cjs` 检查通过；
- 登记入 `docs/DOCUMENT_INDEX.md`；
- PRD、ROADMAP、ARCHITECTURE 保持对齐，无冲突。
