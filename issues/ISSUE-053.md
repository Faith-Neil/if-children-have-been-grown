为什么有这个文件：登记技术服务方案精简主路径的需求变更（三张清单、挂要点目录、双库正文、覆盖视图合一、写作助手补全）。

它解决什么问题：原 PRD 过重；用户 2026-11-20 拍板只生成技术服务方案，模块不删不藏，矩阵即覆盖视图。

# ISSUE-053：技术服务方案精简主路径

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-053 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-20 |
| 最后更新日期 | 2026-11-20 |
| revision | tech-plan-simplified-1 |
| 关联 Task | [TV-M0-T17](../docs/tasks/TV-M0.md#tv-m0-t17)、[TV-M0-T18](../docs/tasks/TV-M0.md#tv-m0-t18)、[TV-M0-T19](../docs/tasks/TV-M0.md#tv-m0-t19)、[TV-M0-T20](../docs/tasks/TV-M0.md#tv-m0-t20) |
| 关联 PR | 目标分支 `feat/iss-047-technical-volume-mvp`，不合 main |
| 本地验收 | 假模型后端单测；真实内网 Qwen / RAGFlow 未跑 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [TV-M0-T17](../docs/delivery/TV-M0-T17.md) |
| 代码 / 流程解释 | [设计](../docs/decisions/2026-11-20-technical-plan-simplified.md)；[角色审计](../docs/reviews/2026-11-20-role-feature-audit.md) |

## 目标

读标出技术需求 / 评分规则 / 废标三张清单 → 模型一次拟 1～4 级目录并挂响应要点 → 用户确认 → 双库 RAG 写正文，废标清单为硬约束 → 质量八条与废标检查 → 正文与技术偏离表导出。

## 分组

- A 后端主路径：TV-M0-T17（本次）。
- B 覆盖视图字段、单节重试、人工确认、RAG 明细：[TV-M0-T18](../docs/tasks/TV-M0.md#tv-m0-t18)。
- C 写作助手补全：[TV-M0-T19](../docs/tasks/TV-M0.md#tv-m0-t19)。
- D 三角色权限收口、演示账号改名、项目只读写拒绝核查：[TV-M0-T20](../docs/tasks/TV-M0.md#tv-m0-t20)。

## 影响核对

PRD / ROADMAP / ARCHITECTURE：本分支产品范围已由 [仅技术标决策](../docs/decisions/2026-11-08-tech-bid-only-product.md) 收窄，本次只换技术分册内部编排，不改三件套；理由记于交付。
