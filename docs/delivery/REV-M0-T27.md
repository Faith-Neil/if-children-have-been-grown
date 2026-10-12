为什么有这个文件：交付用户要求的最新分支复核和限定修复。

它解决什么问题：让修改通过单独PR审查，保留协作分支和原验收历史。

# REV-M0-T27交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | REV-M0-T27 |
| 代码解释 | [限定修复](../code/REV-M0-T27.md) |
| 验收 | [复核与实际回归](../reviews/2026-10-12-foundation-review.md)；[实际验证命令和结果](../testing/2026-10-12-foundation-review.md) |
| 项目进度 | 新复核卡in-review；并入 foundation 9e3fcdd 后看板 384项49done、10in-review、7in-progress、265planned、48blocked、5ready；本轮不推进新功能 |
<!-- task-delivery:end -->

日期2026-10-12；ISSUE-034 / foundation-review-fix-1。初次审查云端73fde1e，复核快照9c178782，随后并入 foundation 9e3fcdd。保留新增项目、租约、证据抽屉、T114 冲突刷新、ISSUE-036 对比修正和 QA 交付。修复分支 codex/review-foundation-fixes，目标 PR 为 codex/repository-foundation。尚未合入或发布。用户要求仅复核，需修改则提 PR。

本卡原先误用 ISSUE-033 / REV-M0-T22。那两个编号已分别属于挂证据规则和 APP-M2-T114 QA。本交付改为 ISSUE-034 / REV-M0-T27，不覆盖同伴记录，也不自行 done/closed。

## 完成内容

本PR修复八项：旧会话迟到错误、失败切页后未保存提醒、同进程片段并发、数据库有效回执读取、旧快照误删新回执、旧租约覆盖新锁、证据抽屉旧权限及绕过统一导航。密钥503重试由上游0a5b655修复，本轮保留并验证。实际实现和反例见专属代码与复核记录；片段与回执提交失败同步恢复，租约失配回滚。

本轮限定修复，其他项目实施停止。合成身份、局部MySQL、内存片段和模型/检索边界不扩大；大纲/任务冻结契约和 T124 的 ready 状态不改。原已签署任务状态与里程碑快照保留。APP-M2-T114 与 REV-M0-T22 保持 done。新复核卡提交 in-review 待审，不由开发者 done/closed。

## 文档与Issue同步

| 对象 | 处理 / 无影响依据 |
|---|---|
| PRD | 无新业务需求；恢复既有账号隔离、文字保留和失败保护，原里程碑快照不重写 |
| ROADMAP | 不新增功能或改变排期；只登记本次复核卡 |
| ARCHITECTURE | 已有会话/幂等约束的实现纠错，补当前修复说明；不新建服务或接口 |
| OpenAPI | 现有接口、冻结错误码及未来x-implemented:false未改变，无重新生成影响 |
| Issue / TASK_BOARD | ISSUE-034与REV-M0-T27、实际验证、PR和发布分列。ISSUE-033 与 REV-M0-T22 保持原义 |
| PROJECT_STATUS / DOCUMENT_INDEX | 复核结论及当前计数，新增交付/代码/回归入口 |
| WORKFLOW | 治理规则及共同治理块不变；本轮以PR待审交付 |

当前环境未连接真实MySQL；SQLite执行生产SQL不是MySQL实机验收。R4、R6、R7 仍需真实 MySQL。正文等仍在内存，完整数据库业务写入和锁核验未原子化，多副本仍未开放；原任务的局部签署不改写。代码与测试用合成数据，临时输出/凭据留仓库外；原工作区、合作分支和运行中的他人环境不改。验收命令与实际结果见[验证记录](../testing/2026-10-12-foundation-review.md)。

PR：[#4](https://github.com/Faith-Neil/if-children-have-been-grown/pull/4)，等待审核，未合入/发布。
