为什么有这个文件：解释 TV-M0-T26 五段隔离 Prompt、章间串行摘要与后置核验器的代码。

# TV-M0-T26 代码说明

| 文件 | 说明 |
|---|---|
| [technical_volume.py](../../backend/bid-core/icg/domain/technical_volume.py) | `_section_user` 五段隔离 Prompt（写作定位→全局项目事实 JSON→项目级约束→本章任务→招标原文→知识库→生成规则），删除全量 `rejection_lines` 灌入只留 `graded.project`/`graded.section`；`_top_key`/`_breadcrumb`/`_neighbors`/`_chapter_running_summary` 支撑章调度；`write_volume` 一级章间串行 + 章内 `ThreadPoolExecutor` 并发，章摘要存 `workflow["chapter_summaries"]`；落盘后跑 `verify_sections` 写 `task["verify_warnings"]` 与 `workflow["technical_verify"]` |
| [technical_verifier.py](../../backend/bid-core/icg/domain/technical_verifier.py) | `verify_sections`：外项目实体残留（白名单放行本标业主/项目名）、事实表数字口径冲突（服务期/质保/SLA/驻场）、评分点实质响应与空泛口号、跨节同一指标数字口径互查；产出按节警示与汇总 |
| [technical_response_plan.py](../../backend/bid-core/icg/domain/technical_response_plan.py) | `confirm_reasons` 增加「后置核验待复核」 |
| [technical_query_plan.py](../../backend/bid-core/icg/domain/technical_query_plan.py) | 供 `_draft_one` 经 `retrieve_for_section(breadcrumb/points/model)` 启用意图拆解（T25） |
| [test_tv_m0_t26_verifier_schedule.py](../../tests/backend/test_tv_m0_t26_verifier_schedule.py) | 五段结构与标签顺序、非技术废标不注入、章间 running_summary 传递、核验器四类警示与 confirm_reasons 联动 |
