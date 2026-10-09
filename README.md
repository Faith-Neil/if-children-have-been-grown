# if-children-have-been-grown

投标技术标智能撰写系统的前端合作仓库。当前交付包含前端实施文档和可交互静态原型；正式应用、后端接口、真实 AI、文档解析与知识库尚未实现。

从 [文档索引](docs/DOCUMENT_INDEX.md) 和 [项目状态](docs/PROJECT_STATUS.md) 开始阅读。[目录重构方案](docs/architecture/repository-layout.md) 说明当前骨架、目标骨架与迁移顺序。

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
| [issues/index.md](issues/index.md) | 本地问题跟踪 |

产品参考文档、前端实施文档、原型和系统选型提案属于不同层级。当前实施文档尚未与新参考版本完整对齐，详见差异清单。真实合同、招标原件与客户资料继续存放在本仓库之外。

## 打开原型

直接打开 [prototypes/bidding-ux/index.html](prototypes/bidding-ux/index.html)，无需安装依赖或构建。也可以在仓库根目录运行：

```bash
python -m http.server 8080 --directory prototypes/bidding-ux
```

然后打开 `http://localhost:8080`。原型使用模拟数据，保存、版本、审计、AI 与编辑锁均为演示交互。

## 协作与验证

修改前阅读 [AGENTS.md](AGENTS.md)，按实际实现更新文档索引、问题和交付记录。当前三个 `docs/*.md` 入口暂时保留，以降低与合作分支的整合冲突。正式前端与后端目录在技术基线核对后按需创建。

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
