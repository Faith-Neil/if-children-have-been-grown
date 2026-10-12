为什么有这个文件：交付用户要求的最新分支复核和限定修复。

它解决什么问题：让修改通过单独PR审查，保留协作分支和原验收历史。

# REV-M0-T20交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T20 |
| 代码解释 | [六项修复](../code/REV-M0-T20.md) |
| 验收 | [复核与实际回归](../reviews/2026-10-12-foundation-review.md)；最终整体验证正在执行 |
| 项目进度 | 新复核卡进行中；372项37done、8in-review、8in-progress、266planned、49blocked、4ready；本轮不推进新功能 |
<!-- task-delivery:end -->

日期2026-10-12；ISSUE-032 / foundation-review-fix-1。审查云端73fde1e，修复分支codex/review-foundation-fixes，目标PR为codex/repository-foundation；尚未合入或发布。用户要求仅复核，需修改则提PR。

## 完成内容

修复旧会话迟到错误、失败切页后未保存提醒、不可重试密钥错误、同进程片段并发、数据库回执2048条边界及旧快照误删除新回执。实际实现和证据见专属代码与复核记录。片段写入与回执提交失败同步恢复，新增回归先证明旧问题再验证修复。

本轮限定修复，其他项目实施停止。合成身份、局部MySQL、内存片段和模型/检索边界不扩大；大纲/任务冻结契约和T124未满足依赖不改。原已签署任务状态与里程碑快照保留，新复核卡提交in-review待审，不由开发者done/closed。

## 文档与Issue同步

| 对象 | 处理 / 无影响依据 |
|---|---|
| PRD | 无新业务需求；恢复既有账号隔离、文字保留和失败保护，原里程碑快照不重写 |
| ROADMAP | 不新增功能或改变排期；只登记本次复核卡 |
| ARCHITECTURE | 已有会话/幂等约束的实现纠错，补当前修复说明；不新建服务或接口 |
| OpenAPI | 现有接口、冻结错误码及未来x-implemented:false未改变，无重新生成影响 |
| Issue / TASK_BOARD | 030与REV-M0-T20、实际验证、PR和发布分列 |
| PROJECT_STATUS / DOCUMENT_INDEX | 复核结论及当前计数，新增交付/代码/回归入口 |
| WORKFLOW | 治理规则及共同治理块不变；本轮以PR待审交付 |

当前环境未连接真实MySQL；SQLite执行生产SQL不是MySQL实机验收。代码与测试用合成数据，临时输出/凭据留仓库外；原工作区、合作分支和运行中的他人环境不改。
