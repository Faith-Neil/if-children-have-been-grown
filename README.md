为什么有这个文件：说明项目入口、已有成果和本地运行方式。

它解决什么问题：帮助接手者快速找到实际代码、文档与验证方法。

# if-children-have-been-grown

投标文档智能撰写项目的合作工作区。当前目标是先按 `ICG/` 给出的布局和操作流程实现完整产品，再逐项修改不合理的设计。浏览器页面与后端是同一产品的两个部分：页面让人操作，后端负责保存业务状态、核对权限和编辑权、执行检查并生成文件。

目前已经接通“项目 → 上传招标文件 → 解析并人工确认 → 响应矩阵与证据 → 技术/商务章节编辑 → 流程检查 → 两册 Word 内部稿”。这条流程已完成一轮真实页面操作，仍有大量示例功能待补齐，不能视为完整一期已交付。数据库和模型保留替换接口，当前使用内存存储和模型替身。Git根为本地 `X:\ICG CO`，GitHub私有仓库保存协作分支的云端版本。

从 [文档索引](docs/DOCUMENT_INDEX.md)、[任务看板](docs/TASK_BOARD.md) 和 [项目状态](docs/PROJECT_STATUS.md) 开始阅读。[协作流程](docs/governance/WORKFLOW.md)规定 Issue、任务验收、逐任务交付、代码解释和文档同步。[工程目录方案](docs/architecture/repository-layout.md)说明现行 8 域分层与分包工程骨架、八角色单源收口与演进映射。

中途接手先读 [PROJECT_BRIEF](docs/PROJECT_BRIEF.md)。本轮审查见 [业务报告](docs/reviews/2026-10-09-business-readiness.md) 和 [技术报告](docs/reviews/2026-10-09-technical-readiness.md)，待决事项见 [ISSUE-005](issues/ISSUE-005.md)。

## 当前目录

| 路径 | 用途 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 当前实施入口；ICG完整目标与旧需求视图保留来源 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 当前页面与后台边界、共用状态及旧架构视图 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 先贯通主流程，再逐页补齐ICG目标的执行入口 |
| [docs/design/ux.md](docs/design/ux.md) | UX 规范；原路径为 `ui/ux.md` |
| [docs/reference/product/](docs/reference/product/) | 已脱敏 PRD v1.8、字典 v1.9，供评审与差异核对 |
| [docs/decisions/baseline-gaps.md](docs/decisions/baseline-gaps.md) | 版本差异、缺件与技术决策状态 |
| [docs/reviews/pr-1-integration.md](docs/reviews/pr-1-integration.md) | `main` 与 `xqr` 的文档整合评审 |
| [prototypes/bidding-ux/](prototypes/bidding-ux/) | 工作台、项目概览、响应矩阵、章节编辑静态原型 |
| [frontend/web/](frontend/web/README.md) | 按 8 大业务域物理分层的 React 前端应用；单源收口八角色与状态字典，支持正式凭据登录与演示关闸 |
| [backend/bid-core/](backend/bid-core/README.md) | 同一产品的 Python 业务后台；`icg/` 领域与仓储分包 + `icg_demo/` 兼容门面，提供 `/api/v1` 接口与 Word 输出 |
| [spec/openapi/](spec/openapi/README.md) | 从实际代码生成的前后端接口约定 |
| [docs/testing/icg-coverage.md](docs/testing/icg-coverage.md) | 完整示例的页面、能力和规则覆盖情况，保留未完成项 |
| [issues/index.md](issues/index.md) | 本地问题跟踪 |

产品参考文档、前端实施文档、原型和系统选型提案属于不同层级。实施目标以ICG产品资料和设计交接为依据，具体版本与缺件见 [差异记录](docs/decisions/icg-reference-deviations.md)。现有ICG入口引用的一部分HTML、资源和设计版本尚缺，不能把目录页当成完整前端源码包。`ICG/`的34份历史项目资料原样纳入并登记到 [来源清单](docs/source/WORKSPACE_MATERIALS.md)；用户明确排除的两个银行合同目录仅留本地，不进入Git版本管理。

工作区同步工具见 [运行说明](docs/operations/workspace-sync.md)：启用时，稳定10秒后的本地项目变化自动保存到协作分支，远端更新在可快进时获取，分叉或人工暂存时暂停。人工提交和整合前先停止同步，实际运行状态以工作区外的状态记录为准。自动WIP提交不表示任务验收、PR合入或产品发布。

## 启动当前产品

在仓库根目录使用PowerShell运行：

```powershell
& .\backend\bid-core\Start-Demo.ps1 -Install
```

首次安装需要Python、Node.js和pnpm。启动器安装后台依赖、构建 `frontend/web` 页面，再启动本机服务。安装后再次启动可省略`-Install`。打开 [本机产品页面](http://127.0.0.1:8710/)，支持选择合成演示账号或输入 Access Token 凭据登录（可通过 `VITE_DEMO=0` 关闭演示），新建项目并按页面流程操作。

后台提供根页面 `/` 和构建资源 `/assets`，产品页面调用同一个服务的接口。`/api/v1` 作为主接口处理会话、项目、上传、解析确认、矩阵、事实、检查和两册输出；旧 `/api/demo` 端点仅供兼容并标记 Deprecated。旧的简单后台验证页保留在 `/demo`，原静态原型仍可离线打开。

当前可读取UTF-8文本、DOCX和含文字的PDF，扫描PDF需要后续接入文字识别。提取结果必须由人核对，DOCX位置按明确分页符记录，并非最终印刷页码。数据只保存在当前进程，重启清空。

技术、商务两个Word内部稿已经通过真实页面下载并核对文件包及各册正文。Word页面渲染尚未成功，排版、目录、附件和正式定稿尚未验收；完整规则尚未实现，正式递交版会被后台拒绝。其余页面、结构化编辑、完整业务检查和生产登录均未完成。实际边界见 [运行说明](backend/bid-core/README.md)、[ISSUE-007](issues/ISSUE-007.md) 与 [覆盖清单](docs/testing/icg-coverage.md)。

## 打开静态原型

直接打开 [prototypes/bidding-ux/index.html](prototypes/bidding-ux/index.html)，无需安装依赖或构建。也可以在仓库根目录运行：

```bash
python -m http.server 8080 --directory prototypes/bidding-ux
```

然后打开 `http://localhost:8080`。原型使用模拟数据，保存、版本、审计、AI 与编辑锁均为演示交互。

## 协作与验证

需求变更、版本更新、Bug 修复先登记 Issue，再关联任务推进。每个任务完成后提交 `docs/delivery/<TASK_ID>.md`，写验收、代码解释和进度；有代码修改时维护 `docs/code/<TASK_ID>.md`。PRD、ROADMAP、ARCHITECTURE、Issue看板、项目进度及DOCUMENT_INDEX同步检查，规则见 [工作流](docs/governance/WORKFLOW.md)。

修改前阅读 [AGENTS.md](AGENTS.md)，按实际实现更新文档索引、问题和交付记录。当前三个 `docs/*.md` 入口暂时保留，以降低与合作分支的整合冲突。前端和业务后台已经建立，后续继续在同一产品内实现示例，不先建立没有实现的独立服务。

协作记录一致性检查：

```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```

自动化验证套件（先安装依赖）：

```powershell
# 后端测试全量回归（652 项用例，610 passed / 42 skipped）
python -m pytest tests/backend -q

# 前端权威测试（348 项测试全绿）与类型检查
pnpm --dir frontend/web test
pnpm --dir frontend/web run lint
pnpm --dir frontend/web build

# OpenAPI 契约与 FastAPI 运行时一致性检查
python backend/bid-core/export_openapi.py --check
```

编辑锁回归检查使用 Node.js，无第三方依赖：

```bash
node --test tests/prototype/*.test.cjs
node --check prototypes/bidding-ux/app.js
```

## 文档沿革

以下是历史文档版本，不代表当前产品需求版本或已运行的技术栈：

- v0.1：三件套初稿（草稿）。
- v0.2：记录 RAGFlow、openGauss DataVec 与解析器多选方案。
- v0.2.1：确定性工作流编排，非自主 Agent。
- v0.3：记录 AI 编辑器、图片资产库与知识库读写隔离方案。
- `xqr` v0.4 / PR #1：提出 RAGFlow 自带文档/向量引擎与 MySQL；仍待整合评审，不能以该分支覆盖当前前端文档。
