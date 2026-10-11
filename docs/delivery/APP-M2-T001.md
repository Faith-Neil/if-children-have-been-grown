为什么有这个文件：交付共同页面底座第一阶段的代码、证据及完整剩余范围。

它解决什么问题：防止一个会话接口或菜单通过就被当成整个布局、路由和权限底座完成。

# APP-M2-T001阶段交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T001 |
| 代码解释 | [会话与页面守卫](../code/APP-M2-T001.md) |
| 验收 | [262后台、72前端、16真实会话及GUI/两册内容](../testing/2026-10-11-application-session.md)；独立复核通过，整卡未验收 |
| 项目进度 | 本卡in-progress；337项14done、8in-progress、267planned、48blocked、0ready；259后续卡1进行中、258planned |
<!-- task-delivery:end -->

日期2026-10-11；ISSUE-009 / application-foundation-1；分支codex/repository-foundation；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)为草稿待合入，未发布。此文是阶段交付，不关闭任务或Issue。

## 已实现的阶段内容

真实getSession读取当前账号、公司范围、导航/动作和最小项目/章节权限；页面先核对会话再读取获准数据。三种演示角色明确兼容映射，manager未映射company_admin，也没有admin公司管理入口；旧资料/模板粗写权限仍保留，完整负责人/审核/字段范围未完成。未知或无权入口拒绝。公司资料/模板继续绑定对应读取的内容和版本；保存和导出仍经过同一后台授权。

新增后台session_navigation.py、前端session-navigation.ts及专项测试；改main.py、schemas.py、App.tsx、types.ts，导出实际OpenAPI。实际入口、调用顺序和限制见代码解释。独立审查发现的工作区撤权、迟到读取和页签竞态均已补修并复核；最终GUI还纠正了无权页提示，保留原内容与文字。

## 验收与当前进度

全后台262项通过，含33专项；前端72项、独立复核、最终类型/构建通过。真实会话16项和GUI经理/只读导航、快捷403、同后台项目与两册内部稿页面通过，4张截图登记。真实两册文件包和正文检查通过且不含个人未提交稿；Word页面版式未验收。网络/角色降级竞态仅函数回归及实际调用复核，没有在GUI注入，不由初次66项通过替代最终证据。

完整T001尚需实际ProLayout、页面地址与刷新/前后返回、全页未保存保护及完整权限采纳；OIDC按T010另验。完整资料列表/详情仍依赖元数据表格、表单及敏感展示任务，不计ready。原任务及ICG功能未缩减。

## 文档同步

| 文档 | 本阶段处理 |
|---|---|
| PRD | 原角色矩阵及完整页面目标保留，演示兼容边界明确 |
| ROADMAP | 先完整T001，再按资料库真实前置推进 |
| ARCHITECTURE / OpenAPI | 可信会话契约与实际49路径57操作 |
| Issue / TASK_BOARD | 新009和T001进行中，007完整产品继续，尚无整卡关闭 |
| PROJECT_STATUS / BRIEF | 同一产品协同、阶段结果与未完成范围分列 |
| DOCUMENT_INDEX | 登记契约、实际模块/专项和阶段交付 |
| WORKFLOW | 无治理规则变更，保持g1.1 / ISSUE-007治理块一致 |

人工Git操作前自动同步已停止；后续正常提交/推送与恢复以真实Git及工作区外运行状态核对，不重置或强推。原ICG材料保持原文，合同原件、凭据、运行输出及合成下载不提交。
