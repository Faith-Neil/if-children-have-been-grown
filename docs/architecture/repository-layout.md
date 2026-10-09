# 仓库目录与渐进迁移方案

日期：2026-10-09。状态：本轮目录整理方案；后续代码布局供评审。

本仓库承接前端合作开发。目前已有前端需求、架构、路线图、UX 规范和静态交互原型，尚无正式应用、依赖清单或后端实现。本轮增加维护约定、问题跟踪和原型回归验证。目录整理先让这些资产的用途和来源清楚，再随实际开发建立代码目录。

本轮保留 `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 的路径与正文，便于协作方继续评审 PR #1。`main` 上的三件套是前端实施视图，`xqr` 上的同名文件是全系统技术标方案草稿；同名不代表同一文档层级。新增的全系统 PRD v1.8、数据字典 v1.9 作为供评审的参考输入，当前未声明两套方案已经对齐或冻结。差异见 [文档基线与待评审差异](../decisions/baseline-gaps.md)。

## 本轮整理后的实际结构

以下为本轮资产归位后的结构。文件名和目录代表当前已有资产；正式应用目录在启动开发时创建。

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
