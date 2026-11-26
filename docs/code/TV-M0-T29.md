为什么有这个文件：说明 TV-M0-T29 偏离表精准响应、程序条款拦截、Fact Sheet 评分事实、导出净化与追溯审计精修的代码改动位置与设计理由。

# TV-M0-T29 代码说明

| 项 | 内容 |
|---|---|
| 状态 | done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 交付 | [TV-M0-T29](../delivery/TV-M0-T29.md) |

## 一、偏离表条款补全与精准响应

- `icg/domain/technical_volume.py::complete_clause_text`：条款列优先用 `source.quote` 覆盖首尾残缺碎片，保留 `7*24` 等技术符号，避免把 `acle原厂服务授权函原件` 这类断句直接填表。
- `_response_units`：把正文拆成句子与表格动作/指标单元；识别并跳过 Markdown 表头行，跳过冒号结尾的引导句；表格首列是故障场景时组合为“针对某场景，动作+恢复目标”，避免拼出“我司数据库实例崩溃”。
- `_anchors` 对表格中简写的“二级/三级”归一为“二级故障/三级故障”；`回电` 与 `电话` 视为同一通信动作，避免误杀正确候选。
- `_match_response_unit` + `_anchor_mismatch`：在字面重合、关键词、数字锚点之外增加故障等级、巡检频次、7×24 热线、硬件更换、授权函、违约金、赔偿、人为因素、咨询服务等硬锚点校验；关键锚点冲突时宁可使用条款兜底，也不能把二级违约答成一级 SLA、把人为赔偿答成非人为硬件更换、把原厂热线答成二级故障。
- `_match_response_unit` 对已明确故障等级的条款惩罚混入其他等级的总起句，避免“一级/二级/三级合并 SLA 句”压过表格里的单级精准响应。
- `_shape_response_sentence` + `_truncate_complete_sentence`：去掉列表编号和章节套话；长度截断只按完整句号/分号边界执行，严禁出现 `……一。` 这类硬切。
- `_fallback_clause_response`：匹配失败时引用较完整条款短句并补“等要求”，不再截出半个词。

## 二、偏离表去重与不可响应条款过滤

- `table_rows`：按 `complete_clause_text` 的标准化文本去重，同一招标条款重复抽取多次只保留一行。
- `_is_deviation_ineligible`：过滤招标人/招标方/甲方/业主义务、纯过渡句、付款协定、评分表表名、评分公式（如 `F2×A2`）与评分低分/区间档位碎片，这些条款不构成投标技术响应行。
- `row_is_non_tech` 词表扩充后继续拦截打印、涂改、递交、送达、开标出席、成交公示、评标办法审核、电子/纸质一致、最不利原则等程序格式条款。

## 三、Fact Sheet 与动态事实核验

- `icg/domain/workflow_schemas.py`：`GlobalFactSheetUpdate/GlobalFactSheet` 增加 `service_modules`、`asset_inventory`、`scoring_rules` 三个结构化数组字段。
- `icg/domain/technical_fact_sheet.py`：新增 list[dict] 清洗、保存、构建与 Prompt 注入；`prompt_fact_sheet_json` 自动注入 `current_year`；人工更新 Fact Sheet 后同步刷新冻结快照，防止旧快照吞掉新增结构。
- `technical_volume.py` 生成规则：评分对照只许使用招标原文评分表和 `scoring_rules` 明确给出的分值、区间与规则；禁止模型发明权重、公式、系数和早于当前年份的日程。
- `technical_digest.py`：从管道表原文回补评分项名称、分值与评分细则；只把真正 `序号 | 评审因素 | 分值 | 满分` 的行归入 S 清单，避免 `section_kind` 漂移把技术服务条款误归评分；扫描招标全文回补漏抽的“昆航DBA服务需求”评分项。
- `icg/domain/technical_verifier.py`：
  - `_sla_expectations/_sla_fact_conflicts` 从当前项目 `sla_response` 动态解析分级 SLA，检出正文与事实表不一致的到场、修复、响应时限；
  - `_team_mentions` 跨节比对团队人数口径，不预设正确人数；
  - `_team_capacity_conflicts` 用 `asset_inventory/asset_profile` 的资产总量动态校验“人数×每人负责套数”是否覆盖项目资产；
  - `_case_year_conflicts` 从评分规则动态读取案例年限并比对正文。

## 四、导出净化的项目事实中立边界

- `icg/domain/export_sanitizer.py` 现在只做通用格式/语法净化：清除 `> ` 引用前缀、内部 `T-xx/S-xx` 编号、空括号、`满足中/符合中` 缺宾语搭配、裸露 Markdown 符号和过期 `CVE-2025-XXXX` 模板；保护 `v$parameter`。
- 已移除单项目硬编码替换：不再把 `15人→7人`、`48小时→24小时`、`二级40分钟→2小时`、`三级60分钟→15分钟`、`近三年→近两年` 写死在导出层；业务一致性由生成侧 Fact Sheet 与 Verifier 负责。
- `infer_table_basis_cells` 只作用于表头含「合规条款」的正文合规表；依据名从本节上下文动态提取《...》，无依据时使用通用招标文件/保密条款表述，不写死项目、公司或协议全名；不会触碰《技术偏离表》页码列。
- `preserve_table_citation_labels` 保留表格中的可读依据来源，表头引用剥空后按列义补齐；正文孤立引用才使用“详见对应章节正文”。
- `inject_scoring_scorecard` 的加分括号格式化改为通用正则 lambda，不再写死“数据库每月巡检”文本；同时避免 `\1` 被误写成 XML 非法控制字符。
- `enforce_export_consistency` 不再做业务数字替换，只清理与项目事实无关的过期 CVE 模板。

## 五、追溯表与 RAG 审计精度

- `icg/domain/response_trace.py`：建立 requirement → outline leaf 映射，“对应章节”写叶子节号与标题；正文段落检索限制在对应 leaf 范围；知识片段来源按 task/requirement 找本分节 RAG 审计，tender 切片不作为知识来源，materials/history 命中为 0 时不强行填名称。
- `icg/domain/technical_rag.py`：`knowledge base has no synced documents` 只保留在 `routes[].error_detail`，不再提升为顶层 `skip_reason/rag.error` 干扰其他分路正常命中。

## 六、权限与验证

- `/technical-outline/rebuild-model` 只允许平台管理员或公司管理员；真机验证 `alpha-manager` 返回 403、`alpha-company-admin` 返回 200。
- 聚焦测试：`tests/backend/test_tv_m0_t29_precision_export.py` 13 passed；与 `test_tv_m0_t28_export_deviation.py` 合计 37 passed。
- 真机局部重跑第 1、4、9 节后，最终三件套位于 `.audit/final-round-v2-t29-hardfix/`；导出 revision 51。
