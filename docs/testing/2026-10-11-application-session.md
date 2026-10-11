为什么有这个文件：记录共同页面底座第一阶段实际执行的后台、页面和输出检查。

它解决什么问题：避免接口测试通过被误写成整卡、整套产品或正式投标文件验收。

# 可信会话与页面导航阶段验证

日期2026-10-11；ISSUE-009 / APP-M2-T001；application-foundation-1。任务仍in-progress。范围：当前三演示身份可信会话、导航和项目读取守卫，保留原完整任务验收。

## 已执行的后台验证

- `.venv/Scripts/python.exe -m pytest tests/backend`：262 passed，113.29秒；一个既有Starlette/httpx弃用提示。新增`test_application_session.py`33项，独立复核也另跑通过。
- 真实监听8710健康：memory/mock、single_process=true、persistent=false；后台实际监听进程34948（仅当次观察，不作为后续启动依据）。
- OpenAPI从实际main.py导出：49路径、57操作，新增getSession。
- 真实`smoke_members.py`再次通过：项目`project-453da5f43da349fd94812e7531e50269`，导出`project-export-b5c6d54ae76e4479b8c02a20131562ad`；技术1940字节、商务1943字节，已检查Word包/实际正文且无个人未提交草稿；7次分工交接通过。输出在工作区外验收目录，不入库。

真实监听会话16项全部通过：三角色映射200，manager无公司/平台管理员入口；manager读取上述新项目最小权限200且无正文/草稿；viewer读取预置`alpha-project`无导出及写权限；坏/缺Bearer401；伪造角色/公司/账号参数、重复project_id、GET正文422；跨公司、同公司非成员和不存在项目404。验证器首次响应头大小写断言失败，修正外部验证器后全部通过，应用未因此修改。最终原始记录在工作区外`C:\Users\ofwangzi\AppData\Local\Temp\icg-session-live-aea5c45bfc23477da28c84cb84f04574\session-live-results-corrected.json`，不含凭据或业务正文；临时记录不作为仓库可移植链接，必要事实与截图在本文保存。

## 最终前端与实际页面

`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：72/72通过，其中会话专项14项；独立复核也实际执行72项通过，并检查辅助函数确实被App调用。最终`pnpm --dir frontend/web build`（含类型检查）通过，产物`index-BqghTeOl.js`，1334.42kB/gzip409.62kB；既有大包提示保留，性能优化未完成。

真实GUI使用最终构建：经理登录后有“管理规则（只读）”而非公司管理入口；打开同一个HTTP验收项目，条款/事实待确认0、两册已提交、有效内部稿读回一致。经理能进入真实导出页并看到两册有效下载记录；只读账号无写作/管理入口、创建禁用、项目无导出页签。只读账号通过概览快捷入口尝试导出，也显示403并保留原内容，未进入导出页。最后将通用暂停提示改为“当前页面的写入已暂停”，避免把某页无权误说成整个项目不可见；重新构建并在实际页面复验。

| 证据 | 核对内容 |
|---|---|
| [主流程项目](assets/icg-session-product-overview.jpg) | 同后台两册、响应、人工确认和有效输出 |
| [两册内部稿页面](assets/icg-session-two-volume-export.jpg) | 实际后台文件记录，内部/递交边界和已过期记录 |
| [只读导航](assets/icg-session-readonly-navigation.jpg) | 无写作/管理/导出入口 |
| [快捷入口403](assets/icg-session-readonly-denied.jpg) | 拒绝该页、保留原内容、暂停写入并准确说明 |

## 独立复核与修复项

初次66项前端函数回归虽通过，独立检查仍发现三个实际采纳路径遗漏：新会话未更新已打开工作区写权限；非项目403后旧资料GET可迟到回填；连续页签会话请求共用序号，旧响应可覆盖新导航。三项已修复并由独立复核确认：新权限与缓存权限取交集，旧条款权限先冻结，当前workspace真实读回后恢复；collection结果结束时还核对同一授权对象；session和页签使用发起序号，旧响应不采纳。新6项反例验证真实辅助函数，含同账号降权、章节交接、拒绝后迟到读取及两次导航竞争，正式正文和私人草稿对象保留。未在GUI注入角色降级/网络竞态，这部分证据是函数执行和实际App调用复核。

## 未执行与剩余

真实身份登录/续期、完整八角色授权、ProLayout三断点、浏览器深链接/前后返回和全部表单离开保护未完成，未验收。真实模型/数据库按要求预留。未做正式Word页面版式验收，包及正文检查只证明内容与私稿边界。网络故障与迟到读取采用真实函数回归时须明确，不能写成GUI故障注入。
