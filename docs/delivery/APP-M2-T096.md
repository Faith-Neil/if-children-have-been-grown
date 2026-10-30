为什么有这个文件：记录 APP-M2-T096 新建项目与 R19 关联投标冲突提示的实际交付和测试证据。

它解决什么问题：说明同标段冲突在什么时候被拦下、提示里给什么、说明怎样留痕与通知，以及原“R19”规则的更正。

# APP-M2-T096：新建项目与 R19 提示

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T096 |
| 代码解释 | [APP-M2-T096](../code/APP-M2-T096.md) |
| 验收 | 2026-10-31：新建项目或在项目设置保存招标编号、项目名称时，后台按“招标编号 + 标段”（写法差异如全角、空格、短横线不影响）在平台内其他公司的在投项目中查找，没有编号时按“招标人 + 项目名称”近似判断；找到时返回 409 RELATED_BID_CONFLICT，页面弹出 PRD 原文提示（引用《招标投标法实施条例》第三十四条与《政府采购法实施条例》第十八条），只列对方公司名称，不透露对方项目任何内容；项目负责人只能“确认无上述关系并继续”（须填写至少 5 个字的说明）或“取消”，不写说明不能继续，后台同样拒绝（PRD 验收②③）。确认记入项目、通知集团管理员；之后出现新的冲突公司须重新确认。解析后才发现的冲突在项目设置显示提示条，负责人填写说明确认；导出前全文检查报 R19 警告，确认后旧检查过期、重新检查不再报。验证见 [验证记录](../testing/2026-10-31-t096-related-bid.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T096](../tasks/APP-M2.md#app-m2-t096)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；新登记 [ISSUE-046](../../issues/ISSUE-046.md)（规则编号与 PRD 不符）
- 依据：PRD v1.8 §5.1.2 业务规则 2 与异常与边界、§8.3、§5.8.1 R19（立项；导出前；警告，须填写说明并通知集团管理员）、Q03（强提示 + 填写说明，不硬拦截）

## 发现并更正
- 代码里的 `check_r19` 检查的是“环保、节能与绿色采购强制产品认证”，PRD 的 R19 是“关联投标冲突”，系统此前没有任何关联投标检查。原检查保留为扩展规则 `EXT-GREEN`（不占用 PRD 编号），R19 改为本卡的关联投标冲突。逐条对照后另有约 19 条规则编号与 PRD 不符，登记为 [ISSUE-046](../../issues/ISSUE-046.md)，本卡不改。
- 项目设置页一直显示“当前使用合成演示账号验证多人编标……正式公司账号、登录安全及完整角色管理仍未交付”，已与现状不符，删除。

## 实际文件
- 后端：`backend/bid-core/icg/domain/related_bids.py`（新）；`workflow_orchestrator.py`（`patch_project` 改招标编号或项目名称时核对）；`workflow_schemas.py`（`ProjectPatch.related_bid_reason`、`RelatedBidAck`、`RelatedBidStatus`）；`icg/api/workflow.py`（`GET /api/v1/projects/{p}/related-bids`、`POST …/related-bids/ack`）；`compliance_rules.py`（R19 改为关联投标冲突，原检查改为 `EXT-GREEN`）；`input_snapshot.py`（确认说明进入输入指纹）；`errors.py`、`frozen_error_codes.py`（RELATED_BID_CONFLICT，409）
- 前端：`frontend/web/src/project/related-bid-core.ts`、`RelatedBidPrompt.tsx`（均新）；`app/App.tsx`（新建项目保存招标编号时接确认）；`project/ProjectSettingsPage.tsx`（保存基本信息时接确认、提示条）
- 测试辅助：`tests/backend/test_reference_flow.py` 的 `ProjectFlow.reviewed` 带上说明（不同公司的用例共用同一合成招标编号）
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_related_bids.py`（4 项）：写法不同的同一编号被拦、只给对方公司名称、整次修改不保存、说明太短仍拦、写明后保存并通知集团管理员且通知不含对方项目名称；无冲突时确认返回 409、编写人不能确认、他公司读不到；全文检查报 R19 警告且不含对方项目名称，确认后旧检查过期、重新检查不再报；规范化与匹配规则、目录中 R19 为“关联投标冲突”且保留 EXT-GREEN
- 改动的旧用例：`test_compliance_rules_p5.py`（绿色采购检查按 EXT-GREEN 取结果）、`test_compliance_rules.py`（目录编号允许 `EXT-` 扩展规则）
- `frontend/web/tests/unit/related-bid.test.mjs`（3 项）
- `frontend/web/e2e/related-bid.spec.ts`：乙公司先立项 → 甲公司新建同编号项目 → 弹出提示且不含乙公司项目名称 → 不写说明点确认仍停留 → 写明后进入招标文件页 → 后台已保存编号与说明 → 项目设置显示已确认

## 未实现项与限制
- “集团内”按整个平台的公司处理：系统还没有集团与公司的归属和控股关系数据（PRD 写“在公司管理中维护”），本平台按集团私有化部署时两者一致；多集团共用一个平台时须补集团归属。
- 标段号从事实表的“标段/标段编号/包号/采购包”读取，项目上没有单独的标段字段；没有标段时同编号按“可能是同一项目”提示。
- 新建项目只填项目名称、不填招标编号时不核对（PRD 的近似匹配需要招标人，新建时还没有）；解析后在项目设置与导出前检查补上。
- 导出时只在全文检查报警告，不在导出接口另行拦截（PRD 为警告级）。
- 任务卡里的“投标截止时间倒计时 ≤3 天标红、页签按权限、完整值类别只有项目负责人可勾选”属于项目列表与递交版导出的其他卡，本卡未做。
