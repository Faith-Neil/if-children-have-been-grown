# 合作项目维护约定

## 开工前

1. 阅读 `docs/DOCUMENT_INDEX.md`、`docs/governance/WORKFLOW.md`、`docs/TASK_BOARD.md`、`docs/PROJECT_STATUS.md` 与 `issues/index.md`。
2. 核对工作分支和工作区；保留他人的修改，不重置或强推合作分支。
3. 按现有实现工作。当前只有静态原型，不假设 API、数据库、模型调用或正式应用已经存在。

## 文档与目录

- `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 是当前前端实施视图，暂时保留路径。
- `docs/reference/product/` 是原文保存的供评审参考输入；不得把版本较新等同于已全面对齐。
- `prototypes/bidding-ux/` 保持无构建、可离线打开。移动原型时将同目录资源一起移动。
- 未来代码目录以 `docs/architecture/repository-layout.md` 为依据；技术方案未核对前，不建立无实现的应用或微服务。
- `xqr` 的系统文档与 `main` 的前端文档属于不同层级，按 `docs/reviews/pr-1-integration.md` 整合；不直接覆盖。
- 不把真实客户原件、内部历史稿、凭据、环境密钥或运行输出提交到仓库。测试数据使用合成数据。
- 用户本轮明确授权纳入整个 `X:\ICG CO` 中的项目资料，并明确排除两类银行合同根。`ICG/`历史材料保持来源与原版本，通过 `docs/source/WORKSPACE_MATERIALS.md`登记；它们不自动替代活动基线。合同目录、凭据及运行输出仍不得入库。
- Git根已提升到工作区根，不在旧子目录重建第二套Git。自动同步配置和加密令牌保存在工作区外，操作说明见 `docs/operations/workspace-sync.md`。

## 修改与交付

- 每次需求变更、版本更新和 Bug 修复必须先登记或更新 Issue，关联任务再开工；工程治理、选型和接口变更也登记。细则见 `issues/README.md`。
- 以 `docs/TASK_BOARD.md` 的单个任务推进；每个任务核对任务卡、依赖和验收，再标 `in-progress`。缺基线、接口或其他必要输入时不得标 `ready`。
- 每任务完成必须保存 `docs/delivery/<TASK_ID>.md`，写实际完成内容、验收、项目进度、代码解释及同步记录；有代码变更同时维护 `docs/code/<TASK_ID>.md`。模板在 `docs/templates/`。
- 只有验收通过、交付和代码说明齐全、看板/进度/索引同步后，任务才可 `done`；Issue关闭与PR合入、发布分别记录，不能把本地通过写成已上线。
- 每个变更必须检查 PRD、ROADMAP、ARCHITECTURE、Issue看板/详情的影响并对齐，连同 TASK_BOARD、PROJECT_STATUS、DOCUMENT_INDEX 一起更新。无影响在 Issue和交付同步表说明原因，禁止默默跳过。
- 三件套与Issue看板的治理块和 `docs/governance/WORKFLOW.md` 保持同一版本、日期与Issue；业务版本按实际变化独立维护，参考原文不改。
- 自动WIP快照只保存进行中的文件，不标任务done/Issue closed；人工Git暂存、分支切换或整合前先停止同步。双方分叉保留现场，不强推或重置覆盖。
- 源文件使用 UTF-8；提交信息用英文。只改任务相关文件。
- 行为变更运行针对实际脚本的必要验证。静态原型至少检查资源引用、JavaScript 语法和受影响交互。
- 编辑锁与写入确认要同时校验；不能只依赖按钮禁用或 `contenteditable`。
- 在 `docs/testing/` 记录验证方式与局限，在 `docs/delivery/` 记录交付，并同步文档索引。
- 收尾运行 `node scripts/check-project-governance.cjs`；检查程序只能验证记录一致性，实际功能仍按任务验收。检查程序修改时运行 `node --test tests/governance/*.test.cjs`。
- 生成的 API SDK 后续从 `spec/openapi/` 契约生成，避免手改生成文件。
