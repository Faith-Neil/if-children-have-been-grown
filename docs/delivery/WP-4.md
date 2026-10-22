为什么有这个文件：记录质量整改路线图 WP-4（后端 database.py 与 workflow.py 模块化解耦分包）的实际完成内容、测试验收与架构设计说明。

它解决什么问题：消除 backend/bid-core/icg_demo 中 2352 行的 database.py 和 1524 行的 workflow.py 巨石代码，在 backend/bid-core/icg 下建立标准限界上下文分包（infra/repositories、domain、api、app），并由 icg_demo 保持 100% 行为与导入契约兼容。

# WP-4：后端巨石模块解耦与分包治理交付
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-4 |
| 代码解释 | 将 database.py（2352行）拆分为 mysql_gate 及 9 个细粒度仓储模块，将 workflow.py（1524行）按领域拆分为 export_service、generation_service、outline_service 与 workflow_orchestrator 编排器；保留 icg_demo 向下兼容 façade 层；详见本交付第 2、3 节。 |
| 验收 | 后端全量 pytest 606 项全绿（42 跳过，0 失败）；前端权威测试 344 项全绿（0 失败）；工程治理检查 485 份 Markdown 0 错误；所有拆解模块代码行均处于健康维护区间；严格落实 ICG_REQUIRE_MYSQL 门禁。 |
| 项目进度 | WP-4 顺利闭环；下一阶段进入 WP-5（API 接口与错误体收敛、/api/v1 统一标准化）。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 D 前半 / WP-4）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则 - 后端分包边界、持久化门禁）
- 本地验收状态：已通过（后端 606 passed, 42 skipped；前端 344 passed；治理脚本通过）
- 合入 / 发布状态：分支持续演进，与远程保持同步

---

## 完成内容与变更文件

### 1. 拆解产物概览（新建 `backend/bid-core/icg/` 分包架构）

```
backend/bid-core/icg/
├── api/                        # 路由与控制器定义
├── app/                        # 应用工厂与中间件
├── domain/                     # 纯领域服务
│   ├── export_service.py       # 检查规则、红线阻断项与 Word 导出打包（362 行）
│   ├── generation_service.py   # AI 辅助生成、原件切片检索与正文提示词组装（324 行）
│   ├── outline_service.py      # 大纲规划、章节适用性与方案持久化（204 行）
│   └── workflow_orchestrator.py# 工作流总线编排（845 行）
└── infra/                      # 基础设施与持久化
    ├── memory_repository.py    # 内存开发/测试仓储实现（367 行）
    ├── mysql_gate.py           # 数据库连接池与 ICG_REQUIRE_MYSQL 严格门禁（99 行）
    └── repositories/           # 细粒度仓储划分
        ├── chapters.py         # 章节持久化与段落分解算法（210 行）
        ├── checks_exports.py   # 检查项与双册导出记录持久化（272 行）
        ├── common.py           # 时间与 JSON 工具函数（58 行）
        ├── jobs.py             # 异步作业状态与执行记录（267 行）
        ├── library.py          # 公司资料库与凭据版本持久化（247 行）
        ├── model_config.py     # 模型配置持久化（81 行）
        ├── mysql_repository.py # MySQL 仓储主聚合与事务委托（384 行）
        ├── projects.py         # 项目元数据、团队成员与锁（158 行）
        └── sla.py              # SLA 承诺模板与矩阵事实（158 行）
```

### 2. 巨石文件瘦身与兼容 Façade

- **`backend/bid-core/icg_demo/database.py`**：
  - 从 **2352 行降至 82 行**（降幅 96.5%）；
  - 全面代理导入 `icg.infra.mysql_gate`、`icg.infra.memory_repository` 及 `icg.infra.repositories.*`。
- **`backend/bid-core/icg_demo/adapters.py`**：
  - 从 **613 行降至 36 行**（降幅 94.1%）；
  - 代理导入 `icg.infra`，保持旧测试无感平滑运行。
- **`backend/bid-core/icg_demo/workflow.py`**：
  - 从 **1524 行降至 29 行**（降幅 98.1%）；
  - 全面代理导入 `icg.domain.workflow_orchestrator`、`export_service`、`generation_service` 与 `outline_service`。

---

## 验收结果

1. **后端自动化测试**：
   - 命令：`pytest`
   - 结果：**606 passed, 42 skipped, 0 failed**（300.82s），全量通过。
2. **前端权威测试**：
   - 命令：`pnpm --dir frontend/web test`
   - 结果：**344 passed, 0 failed**（5.1s），全量通过。
3. **工程治理检查**：
   - 命令：`node scripts/check-project-governance.cjs`
   - 结果：**485 份 Markdown、399 项任务、37 项 Issue 100% 校验通过**。
4. **持久化门禁**：
   - 针对 `test_mysql_gate.py` 中的环境变量检测进行专项覆盖，当 `ICG_REQUIRE_MYSQL=1` 且未提供合规 `ICG_DATABASE_URL` 时，严格抛出异常阻断，坚决杜绝静默回退到内存仓储。
