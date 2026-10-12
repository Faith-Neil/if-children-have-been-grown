为什么有这个文件：给APP-M1-T06核心流程端到端验收制定可执行计划。

它解决什么问题：明确端到端步骤、Word版式、多角色、权限反例和过期数据如何验收，哪些已有测试覆盖、哪些仍是缺口；本文只是计划，不代表T06已验收。

# APP-M1-T06 端到端验收计划

日期2026-10-12；ISSUE-015 / REV-M0-T03（计划）；被验收任务[APP-M1-T06](../tasks/APP-M1.md#app-m1-t06)保持in-progress。基于提交`adc2600`的实际代码。

## 0. 运行方式与环境

- 后台：`python -m uvicorn icg_demo.main:app --app-dir backend/bid-core --host 127.0.0.1 --port 8710 --workers 1`（内存数据，重启清空；模型为替身）。
- 页面：`pnpm --dir frontend/web build`后由同源后台提供；Node 24。
- 数据：仅用种子合成账号（alpha-manager/editor/viewer/tech/business/outsider-manager、beta-manager/editor）和`backend/bid-core/smoke_*.py`生成的合成招标包；不用客户原件。
- 证据目录在仓库外；截图/录像按需入`docs/testing/assets/`。

## 1. 端到端主流程（真实HTTP + GUI）

| 步骤 | 角色 | 操作 | 预期 | 现有覆盖 | 缺口 |
|---|---|---|---|---|---|
| E1 | alpha-manager | 登录、建项目、设团队/分册负责人 | 201；团队版本+1 | `smoke_members.py`、`test_project_assignments.py` | — |
| E2 | alpha-manager | 上传合成招标文件、文字提取 | 解析结果可见，坏文件被移除 | `smoke_reference.py`、`test_reference_boundaries.py` | GUI截图需补 |
| E3 | alpha-manager | 人工确认条款/事实、冲突处理 | 待确认归0；未确认阻止生成 | `test_reference_flow.py::test_review_gate_and_conflicts_require_explicit_resolution` | — |
| E4 | 负责人 | 响应矩阵、SLA取值 | 矩阵映射完整；SLA派生事实 | `smoke_sla.py`、`test_sla.py` | — |
| E5 | 章节编写人 | 本节方案确认→生成候选→采纳→提交 | 只本节可生成；正文版本+1 | `smoke_writing.py`、`test_generation_context.py`、`test_candidate_write_guard.py` | 替身模型；真实模型不在T06 |
| E6 | 分册负责人/项目负责人 | 全文检查→两册导出→下载 | 两册.docx仅含已提交正文 | `smoke_members.py`、`test_demo.py::test_uncommitted_draft_never_enters_exported_docx` | 四个核心基准页截图与ICG示例比对缺 |
| E7 | 任意 | 同一后台状态贯通（页面、HTTP、文件一致） | 页面所见=API读回=Word正文 | 各冒烟脚本分别验证 | **缺单一贯通脚本**：一次跑完E1～E6并交叉比对 |

## 2. Word导出版式验收

当前实现`backend/bid-core/icg_demo/adapters.py::build_docx`手写最小OOXML：A4（11906×16838）、四边1440缇页边距、默认字体Calibri/微软雅黑11pt、styles.xml仅默认样式、表格带边框与表头重复；**无numbering.xml、无目录域、无页眉页脚、无标题样式层级**，内含“本地演示内部稿，不可正式递交”标记。

| 检查项 | 方法 | 预期（内部稿阶段） | 现状 |
|---|---|---|---|
| 包完整 | `zipfile`/python-docx打开，`[Content_Types].xml`与关系齐全 | 可打开 | 已覆盖：`test_demo.py::test_export_is_real_docx_and_cannot_cross_company_or_skip_authentication` |
| 正文内容 | python-docx读段落/表格，比对API正文 | 只含已提交正文、无私稿 | 已覆盖（冒烟+测试） |
| 页面设置 | 读`sectPr`：A4、边距 | 与实现一致 | 无断言 → 缺口 |
| 字体 | 读`docDefaults rFonts`、东亚字体 | 中文为雅黑或客户模板字体 | 无断言；客户字体规范未定 → 缺口 |
| 标题/样式 | 段落`pStyle`是否为Heading 1～n | 章节标题有层级 | **未实现** |
| 编号 | numbering.xml、多级编号 | 章节编号连续 | **未实现** |
| 目录 | TOC域 | 可更新目录 | **未实现** |
| 表格 | 边框、表头重复、宽度不越界 | 不裁切 | 部分实现，无视觉证据 |
| 视觉渲染 | `soffice --headless --convert-to pdf`后`pdftoppm -png`逐页查看 | 无缺字/重叠/裁切 | **10-10记录渲染失败**（当时Windows无soffice，Word16转换失败）。QA的box有`/usr/bin/soffice`，可重试；仍需在Word/WPS实际打开复核 |

结论：版式目前只能验“内部稿可打开、内容正确、页面设置符合实现”；标题/编号/目录/客户模板属于正式Word任务，T06不得以内部稿冒充版式通过。

## 3. 多角色回归

后台`session_navigation.py`定义8角色（platform_admin、group_admin、company_admin、data_admin、project_lead、bid_writer、reviewer、readonly），但种子只有manager/editor/viewer三类，映射为project_lead/bid_writer/readonly；其余5角色返回403 `SESSION_ROLE_UNSUPPORTED`。

| 角色 | 验收内容 | 现有覆盖 | 缺口 |
|---|---|---|---|
| project_lead | 全流程、导出 | 冒烟、`test_application_session.py` | — |
| bid_writer | 仅本节写作/确认 | `test_project_assignments.py` | — |
| readonly | 无写/导出入口，写请求403 | `test_demo.py::test_viewer_cannot_save_drafts_or_versions`、GUI截图(10-11) | — |
| 其余5角色 | 会话被拒 | `test_unadapted_roles_are_denied_...` | **业务权限未实现**，T06只验“拒绝”，完整矩阵归T010等 |

## 4. 权限反例

| 用例 | 预期 | 现有覆盖 |
|---|---|---|
| 未登录/坏令牌 | 401 | `test_application_session.py`、`tests/backend/session_live_http.py` |
| 跨公司读写/下载 | 404，不泄露 | `test_export_is_real_docx_and_cannot_cross_company...`、`test_library_basis.py` |
| 同公司非成员 | 404 | `test_nonmembers_cannot_see_any_existing_resource_or_jobs` |
| 编写人改他人/他册章节 | 403 | `test_volume_owner_cannot_change_other_volume_chapter` |
| 非负责人检查/导出 | 403 | `test_only_lead_or_volume_owner_can_check_and_export_matching_scope` |
| 伪造角色/公司参数 | 422 | `test_client_cannot_override_session_identity_or_company` |
| GUI中隐藏入口+直接URL访问 | 拒绝且不读业务数据 | 函数级14项；**浏览器直接URL未验**（无路由，依赖T001） |

## 5. 过期数据

| 用例 | 预期 | 现有覆盖 |
|---|---|---|
| 新版本提交后旧导出下载 | 拒绝/标过期 | `test_new_committed_version_invalidates_previous_check_and_export_download` |
| 输入（条款/事实/SLA）变更 | 检查与导出失效 | `test_input_change_invalidates_check_and_export_download`、`test_legacy_check_export_download_cannot_bypass_sla` |
| 候选来源变更 | 旧候选不可采用 | `test_candidate_input_changes_mark_history_stale` |
| 章节换人 | 旧权限/缓存回执失效、私稿保留 | `test_cached_generation_cannot_be_replayed_after_reassignment`、`test_old_formal_commit_receipt_cannot_be_used_after_losing_chapter_assignment` |
| 版本冲突 | 409且原子 | `test_stale_revision_rejects_both_draft_and_version_atomically`、`test_version_and_repeated_request_protection` |
| 旧表单借新版本覆盖 | 拒绝 | `test_library_basis.py`、`test_sla_template_basis.py` |
| GUI中过期导出提示 | 页面显示过期并禁下载 | 10-11截图有过期记录；**无自动化** |

## 6. 缺口汇总（建议拆卡/负责人）

1. 单一贯通脚本E1～E7交叉比对页面/API/Word（QA，可新建`smoke_t06.py`）。
2. Word页面设置/字体断言（QA+后端）；标题样式、编号、目录、页眉页脚未实现（后端，正式Word任务）。
3. LibreOffice渲染PNG视觉检查重试并留证（QA）；Word/WPS人工打开复核。
4. 四个核心基准页与ICG示例截图比对（前端+QA）。
5. 浏览器直接URL/前进后退权限验证依赖T001路由（前端）。
6. 其余5角色业务权限未实现（后端，T010及权限卡）。
7. GUI过期导出/冲突提示自动化（前端，可选Playwright，需批准依赖）。

## 7. 通过标准

第1～5节全部“预期”项有当次证据（命令输出、文件、截图），缺口项要么完成、要么在T06交付中明示并关联后续卡；任一失败即T06保持in-progress。
