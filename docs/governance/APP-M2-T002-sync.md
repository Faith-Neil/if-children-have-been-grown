为什么有这个文件：记录请求层提交复核时核对了哪些基线，以及哪些句子故意留着。

它解决什么问题：避免为了对齐计数去改仍写着「尚未完成」的产品基线。

# APP-M2-T002 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。APP-M2-T002 与 ISSUE-009 为 in-review。T001 与 ISSUE-014 仍为 in-review。不标 done 或 closed。

活的计数是 360 项：23 done、8 in-review、7 in-progress、268 planned、50 blocked、4 ready。APP-M2 其余 255 张 planned。AI-02 与 APP-M2-T008 保持 done。BE-M0-T02 与 BE-M0-T03 保持 done。ISSUE-005 保持 in-progress。ISSUE-011 与 ISSUE-012 保持 closed。ISSUE-018、ISSUE-021、ISSUE-022、ISSUE-023 保持原状态。

| 对象 | 实际处理 |
|---|---|
| PRD | 无正文修改。第19行仍写「其中T001共同底座已开工，其余258卡planned」。第21行仍写「整个T001、OIDC和完整资料库仍未完成」 |
| ROADMAP | 无正文修改。第17行仍写「当前共356项任务，23done、6in-review、7in-progress、266planned、50blocked、4ready」。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 无正文修改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」 |
| PROJECT_BRIEF | 无正文修改。第30行仍写「当前共360项：23done、7in-review、7in-progress、269planned、50blocked、4ready」。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | ISSUE-009 补 T002，仍 in-review。ISSUE-005 去掉「T002 仍 planned」，Issue 状态不改。ISSUE-007 活计数改为其余 255 张 |
| TASK_BOARD | T002 改为 in-review，关联 ISSUE-009。360 项改为 8 in-review、268 planned |
| PROJECT_STATUS | 同一计数，并写明章节版本的头和正文使用同一把键 |
| DOCUMENT_INDEX | D-277 交付、D-278 代码解释、D-279 验证、D-280 本同步表 |
| WORKFLOW | 无规则变化，治理块不升版 |
| 参考原文 | 不改 `docs/reference/` |
| 后台 | 不改 `backend/` 与 `tests/backend/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。
