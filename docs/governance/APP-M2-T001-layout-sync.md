为什么有这个文件：记录 QA 退回后的布局修复核对了哪些基线。

它解决什么问题：避免修复顶栏和历史时，悄悄改掉仍写着“尚未完成”的基线句子。

# APP-M2-T001 布局修复同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。APP-M2-T001、ISSUE-009 与 ISSUE-014 保持 in-review。QA 在 `200a105` 的签署结论仍是不通过；本轮修复后重新提交复核，不标 done 或 closed。任务仍是 356 项：23 done、6 in-review、7 in-progress、266 planned、50 blocked、4 ready。不新增任务卡。AI-02 与 APP-M2-T008 保持项目经理已确认的 done。BE-M0-T02 与 BE-M0-T03 已由项目经理标为 done。ISSUE-011 与 ISSUE-012 保持 closed。ISSUE-018、ISSUE-021、ISSUE-022 保持原状态。

| 对象 | 实际处理 |
|---|---|
| PRD | 无正文修改。第19行仍写「其中T001共同底座已开工，其余258卡planned」。第21行仍写「整个T001、OIDC和完整资料库仍未完成」 |
| ROADMAP | 无正文修改。第17行仍写「当前共354项任务，21done、7in-review、7in-progress、265planned、50blocked、4ready」。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 无正文修改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」 |
| PROJECT_BRIEF | 无正文修改。第30行仍写「当前共356项：23done、6in-review、7in-progress、266planned、50blocked、4ready」。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | ISSUE-009 保持 in-review，补上 QA 不通过和本轮修复。ISSUE-014 仍是 pro-layout 依赖，不升版本。ISSUE-019 的失败记录保留 |
| TASK_BOARD | T001 保持 in-review。356 项计数不变 |
| PROJECT_STATUS | 写明签署不通过后的修复已重新提交复核，未写 done |
| DOCUMENT_INDEX | 登记本同步表、验证记录和修复后截图 |
| WORKFLOW | 无规则变化，治理块不升版 |
| 参考原文 | 不改 `docs/reference/` |
| 后台 | 不改 `backend/` 与 `tests/backend/`。D5 未处理 |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。
