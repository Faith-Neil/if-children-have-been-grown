# 合作项目维护约定

## 开工前

1. 阅读 `docs/DOCUMENT_INDEX.md`、`docs/PROJECT_STATUS.md` 与 `issues/index.md`。
2. 核对工作分支和工作区；保留他人的修改，不重置或强推合作分支。
3. 按现有实现工作。当前只有静态原型，不假设 API、数据库、模型调用或正式应用已经存在。

## 文档与目录

- `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 是当前前端实施视图，暂时保留路径。
- `docs/reference/product/` 是原文保存的供评审参考输入；不得把版本较新等同于已全面对齐。
- `prototypes/bidding-ux/` 保持无构建、可离线打开。移动原型时将同目录资源一起移动。
- 未来代码目录以 `docs/architecture/repository-layout.md` 为依据；技术方案未核对前，不建立无实现的应用或微服务。
- `xqr` 的系统文档与 `main` 的前端文档属于不同层级，按 `docs/reviews/pr-1-integration.md` 整合；不直接覆盖。
- 不把真实客户原件、内部历史稿、凭据、环境密钥或运行输出提交到仓库。测试数据使用合成数据。

## 修改与交付

- 内部目录维护可直接处理；需要跟踪或验收的 Bug 与功能先在 `issues/` 登记。
- 源文件使用 UTF-8；提交信息用英文。只改任务相关文件。
- 行为变更运行针对实际脚本的必要验证。静态原型至少检查资源引用、JavaScript 语法和受影响交互。
- 编辑锁与写入确认要同时校验；不能只依赖按钮禁用或 `contenteditable`。
- 在 `docs/testing/` 记录验证方式与局限，在 `docs/delivery/` 记录交付，并同步文档索引。
- 生成的 API SDK 后续从 `spec/openapi/` 契约生成，避免手改生成文件。
