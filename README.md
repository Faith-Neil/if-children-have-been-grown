为什么有这个文件：说明项目入口、已有成果和本地运行方式。

它解决什么问题：帮助接手者快速找到实际代码、文档与验证方法。

# if-children-have-been-grown

投标文档智能撰写项目的合作工作区。已有前端实施文档、可交互静态原型，以及能保存草稿、提交版本、检查和下载Word的本地后端demo。模型与数据库预留替换接口，当前使用演示实现；真实模型、持久数据库、招标文档解析与完整一期交付仍待实施。Git根为本地 `X:\ICG CO`，GitHub私有仓库保存协作分支的云端版本。

从 [文档索引](docs/DOCUMENT_INDEX.md)、[任务看板](docs/TASK_BOARD.md) 和 [项目状态](docs/PROJECT_STATUS.md) 开始阅读。[协作流程](docs/governance/WORKFLOW.md)规定 Issue、任务验收、逐任务交付、代码解释和文档同步。[目录重构方案](docs/architecture/repository-layout.md)说明当前骨架、目标骨架与迁移顺序。

中途接手先读 [PROJECT_BRIEF](docs/PROJECT_BRIEF.md)。本轮审查见 [业务报告](docs/reviews/2026-10-09-business-readiness.md) 和 [技术报告](docs/reviews/2026-10-09-technical-readiness.md)，待决事项见 [ISSUE-005](issues/ISSUE-005.md)。

## 当前目录

| 路径 | 用途 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 现有前端产品需求，依据旧产品版本，保留为实施视图 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 现有前端模块、状态、编辑器与权限设计 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 前端分阶段路线图；不等同于全系统排期 |
| [docs/design/ux.md](docs/design/ux.md) | UX 规范；原路径为 `ui/ux.md` |
| [docs/reference/product/](docs/reference/product/) | 已脱敏 PRD v1.8、字典 v1.9，供评审与差异核对 |
| [docs/decisions/baseline-gaps.md](docs/decisions/baseline-gaps.md) | 版本差异、缺件与技术决策状态 |
| [docs/reviews/pr-1-integration.md](docs/reviews/pr-1-integration.md) | `main` 与 `xqr` 的文档整合评审 |
| [prototypes/bidding-ux/](prototypes/bidding-ux/) | 工作台、项目概览、响应矩阵、章节编辑静态原型 |
| [backend/bid-core/](backend/bid-core/README.md) | 可运行业务后台与简单页面；合成账号、内存数据、模型演示实现 |
| [spec/openapi/](spec/openapi/README.md) | 从实际代码生成的前后端接口约定 |
| [issues/index.md](issues/index.md) | 本地问题跟踪 |

产品参考文档、前端实施文档、原型和系统选型提案属于不同层级。当前实施文档尚未与新参考版本完整对齐，详见差异清单。`ICG/`的34份历史项目资料原样纳入并登记到 [来源清单](docs/source/WORKSPACE_MATERIALS.md)；用户明确排除的两个银行合同目录仅留本地，不进入Git版本管理。

工作区同步工具见 [运行说明](docs/operations/workspace-sync.md)：稳定10秒后的本地变化自动保存到协作分支，远端更新在可快进时获取，分叉或人工暂存时暂停。自动WIP提交不表示任务验收、PR合入或产品发布。

## 启动后端demo

在仓库根目录使用PowerShell运行：

```powershell
& .\backend\bid-core\Start-Demo.ps1 -Install
```

安装后再次启动可省略`-Install`。打开`http://127.0.0.1:8710`，选择演示账号登录，进入技术或商务章节，取得编辑权后编辑、保存草稿、提交版本，再检查并下载Word。

演示的后台处理真实请求；数据只保存在当前进程，重启清空，Word为单章内部演示稿。完整能力、接口和替换方法见 [运行说明](backend/bid-core/README.md)，实际交付见 [BE-M0-T01](docs/delivery/BE-M0-T01.md)。

## 打开静态原型

直接打开 [prototypes/bidding-ux/index.html](prototypes/bidding-ux/index.html)，无需安装依赖或构建。也可以在仓库根目录运行：

```bash
python -m http.server 8080 --directory prototypes/bidding-ux
```

然后打开 `http://localhost:8080`。原型使用模拟数据，保存、版本、审计、AI 与编辑锁均为演示交互。

## 协作与验证

需求变更、版本更新、Bug 修复先登记 Issue，再关联任务推进。每个任务完成后提交 `docs/delivery/<TASK_ID>.md`，写验收、代码解释和进度；有代码修改时维护 `docs/code/<TASK_ID>.md`。PRD、ROADMAP、ARCHITECTURE、Issue看板、项目进度及DOCUMENT_INDEX同步检查，规则见 [工作流](docs/governance/WORKFLOW.md)。

修改前阅读 [AGENTS.md](AGENTS.md)，按实际实现更新文档索引、问题和交付记录。当前三个 `docs/*.md` 入口暂时保留，以降低与合作分支的整合冲突。后端已从一个业务核心开始；正式前端与其他服务按实际需要建立。

协作记录一致性检查：

```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```

后台验证（先安装demo依赖）：

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/backend -q
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
