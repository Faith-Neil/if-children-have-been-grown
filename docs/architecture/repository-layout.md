为什么有这个文件：解释仓库目录怎样安排，以及何时新增实际工程目录。

它解决什么问题：避免同一种内容散落多处，或建立没有实现的空服务。

# 仓库目录与渐进迁移方案

日期：2026-10-09。状态：本轮目录整理方案；后续代码布局供评审。

本仓库承接投标系统合作工作区。当前业务资产仍是前端需求、架构、路线图、UX规范和静态交互原型，尚无正式应用、依赖清单或后端实现。目录整理先让资产用途与来源清楚，再随实际开发建立代码目录。首轮快照与本轮工作区扩展分别保留记录。

本轮保留 `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 的路径与正文，便于协作方继续评审 PR #1。`main` 上的三件套是前端实施视图，`xqr` 上的同名文件是全系统技术标方案草稿；同名不代表同一文档层级。新增的全系统 PRD v1.8、数据字典 v1.9 作为供评审的参考输入，当前未声明两套方案已经对齐或冻结。差异见 [文档基线与待评审差异](../decisions/baseline-gaps.md)。

## 首轮整理后的结构（FE-M0-T01快照）

以下为本轮资产归位后的结构。文件名和目录代表当前已有资产；正式应用目录在启动开发时创建。

后续FE-M0-T02增加任务看板、任务卡、Issue管理、治理流程、逐任务交付/代码解释、模板和检查程序。当前维护入口以 [DOCUMENT_INDEX](../DOCUMENT_INDEX.md) 为准，执行规则见 [WORKFLOW](../governance/WORKFLOW.md)，实际进度见 [TASK_BOARD](../TASK_BOARD.md)。下树保留首轮快照，避免把计划中的代码目录当作已经实现。

```text
if-children-have-been-grown/
├─ README.md
├─ AGENTS.md                         # 当前合作维护约定
├─ docs/
│  ├─ DOCUMENT_INDEX.md
│  ├─ PROJECT_STATUS.md
│  ├─ PRD.md                         # 现有前端需求
│  ├─ ARCHITECTURE.md                # 现有前端架构
│  ├─ ROADMAP.md                     # 现有前端路线图
│  ├─ design/
│  │  └─ ux.md                       # 现有 UX 规范
│  ├─ architecture/
│  │  └─ repository-layout.md        # 本文
│  ├─ decisions/
│  │  └─ baseline-gaps.md            # 分支、版本、范围和选型差异
│  ├─ reviews/
│  │  └─ pr-1-integration.md
│  ├─ testing/
│  │  └─ 2026-10-09-repository-foundation.md
│  ├─ delivery/
│  │  └─ 2026-10-09-repository-foundation.md
│  └─ reference/
│     └─ product/
│        ├─ prd-mvp-v1.8.md          # 原文参考，供评审
│        └─ kb-data-dictionary-v1.9.md
├─ prototypes/
│  └─ bidding-ux/
│     ├─ README.md
│     ├─ index.html
│     ├─ app.js
│     └─ styles.css
├─ issues/
│  ├─ index.md
│  └─ ISSUE-002.md                   # 本轮编辑锁缺陷
└─ tests/
   └─ prototype/
      └─ editor-lock.test.cjs
```

静态原型的运行方式和演示范围见 [原型说明](../../prototypes/bidding-ux/README.md)。原型当前使用模拟数据，用于确认信息架构、编辑器布局与交互；正式开发需要补真实接口、权限、任务状态及模型接入。本轮回归测试针对编辑锁期间的写入保护，范围及局限见 [验证记录](../testing/2026-10-09-repository-foundation.md)。全仓文档入口见 [文档索引](../DOCUMENT_INDEX.md)，分支整合依据见 [PR #1 评审](../reviews/pr-1-integration.md)。

## 后续目标结构

以下目录随对应功能开始实现再建立；本轮仅记录布局约定。前端框架、编辑器、业务数据库、任务队列和工作流组件仍需结合 PR #1、技术验证及参考需求共同确认。

```text
if-children-have-been-grown/
├─ README.md
├─ AGENTS.md
├─ docs/
│  ├─ DOCUMENT_INDEX.md
│  ├─ PROJECT_STATUS.md
│  ├─ PRD.md                         # 保持入口；评审后明确适用范围
│  ├─ ARCHITECTURE.md
│  ├─ ROADMAP.md
│  ├─ design/
│  ├─ architecture/
│  ├─ decisions/                    # 评审结论与技术决策
│  ├─ reviews/                      # 合作变更评审
│  ├─ testing/                      # 验证方式、结果与局限
│  ├─ delivery/                     # 每轮交付说明
│  ├─ reference/product/            # 按原版本保留参考输入
│  ├─ operations/                   # 部署、升级、备份恢复
│  └─ archive/                      # 后续经脱敏、可入库的历史材料
├─ prototypes/bidding-ux/
├─ issues/                          # 可追踪的功能、缺陷与技术决策
├─ frontend/
│  └─ web/                          # 正式前端应用
│     └─ src/
│        ├─ app/                    # 启动、路由、全局与项目 Shell
│        ├─ features/               # 按业务域组织页面、状态与交互
│        └─ shared/                 # 应用内部共用能力
├─ packages/
│  ├─ ui/                           # 有实际复用需求的基础组件
│  ├─ editor/                       # 段落结构、来源、锁定、选区、Diff
│  └─ api-sdk/                      # 从 spec/openapi 生成的客户端
├─ backend/                         # 模块化业务层及运行入口
│  ├─ api/                          # 接口、认证入口与请求转换
│  ├─ jobs/                         # 后台任务入口
│  ├─ modules/                      # 业务规则与用例
│  ├─ adapters/                     # 模型、解析、检索、存储接入
│  ├─ platform/                     # 公司权限、审计、配置等共用能力
│  └─ migrations/                   # 版本化数据库迁移
├─ spec/
│  └─ openapi/                      # 前后端评审的 API 契约
├─ config/
│  └─ defaults/                     # 默认字典、规则、提示词与任务卡
├─ templates/
│  └─ word/                         # 平台默认 Word 模板
├─ deploy/                          # 部署配置和运行环境示例
├─ tests/                           # 契约、集成、主链路与版式验证
└─ evals/                           # 模型任务评测与可复现记录
```

`backend/` 内部的包名、代码后缀和入口文件由最终语言与框架决定。后端 API 与后台任务共用业务规则；模型调用和外部服务转换由适配器承担。是否需要多个独立进程由任务运行方式决定，业务模块先在同一代码边界内组织。

`packages/api-sdk` 只保存契约生成的代码；手写的请求编排和业务 hooks 放在前端应用，字段变更先调整 `spec/openapi` 契约再重新生成 SDK。

前端 `features/` 可沿用现有架构文档的业务域：工作台、项目、招标文件、响应矩阵、项目事实、章节、编辑台、助手、检查、资料库、写作档案、导出及管理。`packages/` 只提取有稳定边界或实际复用价值的能力；应用专属页面仍归 `frontend/web`。

后端模块建议对应项目与分册、招标解析、响应矩阵与证据、企业资料、写作档案、章节生成、合规检查、编辑与对话助手、Word 导出、平台运维。公司隔离、权限和审计统一约束所有模块。模型、MinerU/RAGFlow 等解析与检索组件的自身源码仍由其上游维护，本仓库管理接入与部署配置。

默认配置进入版本管理，用于初始化、验证及交付。公司运行时修改后的资料、配置和 Word 模板由业务系统管理；数据库迁移、逻辑数据字典与默认种子分别维护。真实上传件、生成文件、索引、数据库文件、模型权重、密钥及环境凭据由部署环境保存，测试使用合成或脱敏样本。

## 迁移映射

| 当前或来源路径 | 本轮目标路径 | 操作与约束 |
|---|---|---|
| `README.md` | `README.md` | 更新导航和仓库阶段说明 |
| `docs/PRD.md` | 原路径 | 保留前端实施视图，后续逐条收敛需求 |
| `docs/ARCHITECTURE.md` | 原路径 | 保留前端架构，后续关联系统级决策 |
| `docs/ROADMAP.md` | 原路径 | 保留前端排期；与系统里程碑单独映射 |
| `ui/ux.md` | `docs/design/ux.md` | 移动；更新 README 与原型引用 |
| `bidding-ux-prototype/` | `prototypes/bidding-ux/` | 移动；保留静态演示行为和四个原型文件 |
| 本地 `ICG/product doc/prd-mvp-v1.8.md` | `docs/reference/product/prd-mvp-v1.8.md` | 原文复制；标明供评审参考 |
| 本地 `ICG/product doc/kb-data-dictionary-v1.9.md` | `docs/reference/product/kb-data-dictionary-v1.9.md` | 原文复制；与 PRD v1.8 配套 |
| `xqr` 同名三件套及技术决策 | PR #1 评审后决定 | 按文档层级整合，保留差异与来源 |
| 后续正式前端、后端及契约 | 目标树的对应目录 | 确认技术与首个任务后创建 |

本地 `ICG` 目录名与合作仓库名 `if-children-have-been-grown` 不同。本轮将前者作为参考资料来源，使用后者作为仓库标识；产品显示名和协作边界在 README 及评审记录中明确。

## 分阶段实施

### 阶段一：资产归位与导航

1. 保留现有前端三件套，移动 UX 和静态原型。
2. 原文复制最新已脱敏 PRD 与配套字典，登记其供评审状态。
3. 建立文档索引、目录说明和基线差异记录。
4. 检查全部本地链接、原型入口及引用路径；确认参考文件复制前后内容一致。

本阶段交付的是可阅读、可追踪的仓库骨架，现有原型继续可运行。

### 阶段二：共同评审与接口约定

1. 评审 PR #1，明确 `main` 前端视图和 `xqr` 系统草稿分别保留在哪里。
2. 根据差异表确认一期范围、公司隔离、生成方式、解析接入、云端策略及数据库等决策。
3. 补齐被引用但尚未取得的技术方案和设计版本，登记其来源及有效性。
4. 先约定核心 API、任务事件、段落元数据和答案卡，再开始 SDK 与应用接入。
5. 将阶段结论写入决策文档，更新前端三件套中的适用范围及验收项。

### 阶段三：建立可运行的最小应用

1. 按确认选型建立 `frontend/web` 与后端入口及依赖清单。
2. 优先实现一条可演示的业务链路，前端采用服务端业务状态。
3. 按真实调用建立适配器、默认配置、迁移和部署样例。
4. 随编辑器接入逐步提取 `packages/editor`；公共组件与 API SDK 按复用需求提取。
5. 增加必要的公司隔离、权限、编辑锁、任务状态、接口和导出版式验证。

### 阶段四：完整主链路与交付

1. 根据已评审范围扩展解析、矩阵、证据、生成、编辑、检查和导出。
2. 将模型质量评测放入 `evals`，常规确定性验证放入 `tests`。
3. 补齐部署、升级、备份恢复及内网离线资源说明。
4. 每次目录或基线变更同步更新索引和迁移映射。

## 布局依据

- 现有 [前端架构](../ARCHITECTURE.md) 第 2、5、6、19 节：业务域划分、服务端状态、编辑器元数据、前端目录建议。
- 现有 [前端路线图](../ROADMAP.md) 第 11、13 节：一期范围和安全、追溯、主链路门禁。
- 参考 [PRD v1.8](../reference/product/prd-mvp-v1.8.md) 第 4.1、6.1、7.1、7.4、7.6 节：自研业务层、统一适配器、私有化交付、后台任务、维护性。
- 参考 [数据字典 v1.9](../reference/product/kb-data-dictionary-v1.9.md) 第 1.1、1.7、3.7.6、4 章：资料与检索分层、公司隔离、版本任务卡、代码表来源。

这些材料为目录划分提供依据。具体范围及技术冲突仍按 [基线差异记录](../decisions/baseline-gaps.md) 评审。

## 用户图片已检查：适用骨架与调整

2026-10-09，关联ISSUE-004 / REV-M0-T01。图片是候选目标树，不能据此认定已有正式前端、业务核心、AI/doc服务或集群部署。详细逐路径对照见 [技术审查](../reviews/2026-10-09-technical-readiness.md) §3。

| 图片分组 | 结论与方案 |
|---|---|
| frontend/web + backend/bid-core | 前后端职责分组合理。正式代码先实现一个模块化业务核心与worker；上述目标树的api/jobs/modules/adapters/platform/migrations可承载它。实际命名在选型后统一，不并行维护两套后端骨架 |
| ai/ai-service + doc-service | 作为潜在进程边界保留，先用适配器隔离模型、检索、解析和Word处理。若资源/依赖/发布需要拆进程，先确认任务、产物、超时、重试、取消和授权合同；不先拆编辑锁、版本与导出许可的事实源 |
| deploy/dev/helm/k3s-installer/offline-bundle | 先随最小链路产生可复现开发环境；集群安装待目标机房/运维条件明确。离线包是经过安装验证的发布产物，源库保存构建清单和脚本，模型/客户数据/密钥不直接入库 |
| docs/adr、runbooks、source、specs/cards | 决策沿用docs/decisions，运行说明沿用docs/operations；docs/source管理来源清单。工程任务沿用docs/tasks，模型业务task_card/defaults单独管理，不建第二套M0排期 |
| spec/data-dictionary/openapi/schemas | 逻辑字典、物理迁移、网络DTO职责不同。HTTP DTO优先OpenAPI components；独立schema仅在复用时抽取并引用，避免一字段多处手改 |
| eval、tests/hooks/repo、tools | 评测统一evals；保留prototype/governance测试，随真实实现增加契约、并发、集成与Word样本。hook只做调用入口。当前tools/workspace-sync已实际建立；其他CI/format目录有实际工具再创建 |
| 图片缺少的协作入口 | 保留issues、TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX、逐任务delivery/code与静态prototypes，不用目标目录替代完成证据 |

## 整个本地工作区纳入同一历史

Git根从原 `X:\ICG CO\if-children-have-been-grown` 提升到 `X:\ICG CO`，原有根文件与docs/prototypes等相对路径不变；Git提交历史与分支不变。`ICG/`的34份来源材料保持原目录及内容，登记 [来源清单](../source/WORKSPACE_MATERIALS.md)。两个合同原件根由用户明确排除，原件资料留本地；令牌和运行状态在工作区外。

本轮实际增加tools/workspace-sync、业务/技术审查、brief、OPS/REV任务与运行说明。后续目标树仍是方案，不创建空应用/服务目录。持续同步与人工任务验收关系见 [工作流](../governance/WORKFLOW.md) §7。

## 2026-10-10实际后端骨架

以下目录已包含可运行代码；上面的目标方案和10月9日快照继续保留为当时记录。

```text
backend/bid-core/
  Start-Demo.ps1             Windows安装与启动
  requirements.txt           已验证的依赖版本
  export_openapi.py          从实际接口生成约定
  smoke_demo.py              真实HTTP流程验收
  icg_demo/
    main.py                 请求、权限入口和统一错误
    schemas.py              请求及响应的数据字段
    domain.py               编辑权、草稿、版本、检查和输出规则
    ports.py                数据库和模型的替换接口
    adapters.py             内存仓库、演示模型及Word生成
    static/                 连接实际后台的简单操作页面
spec/openapi/               已生成的前后端接口约定
tests/backend/              后台成功及失败场景验证
```

先使用一个模块化业务核心。模型接口负责返回建议；数据库接口负责读取和一次性完成整组写入，后续接真实服务时保留业务规则。简单页面与后台由同一个本地服务提供，减少demo的安装步骤。

当前仅限单进程演示：编辑权和数据在内存中，重启清空；接生产数据库、多实例、真实模型和解析器前继续核对接口与部署要求。具体结论见[后端准备核对](backend-demo-readiness.md)，交付见[BE-M0-T01](../delivery/BE-M0-T01.md)。
