为什么有这个文件：记录五段多源隔离 Prompt、废标分级注入、章间串行摘要调度与后置核验器交付。

# TV-M0-T26 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码 | [TV-M0-T26](../code/TV-M0-T26.md) |

## 实际变更

- `_section_user` 重构为五段多源隔离 Prompt：写作定位（章节面包屑 + 相邻章节防重 + 前文承诺摘要）→ 全局项目事实 JSON（冻结快照，全书统一口径）→ 项目级约束 → 本章任务（挂载要点/评分细则/本章硬约束）→ 招标原文 → 知识库 → 生成规则。
- 废标注入改为分级：只注入 `build_constraint_context` 产出的 L0 全局技术硬约束（项目级约束）与本节关联 L1（本章硬约束），删除全量 `rejection_lines` 灌入；资格/商务/包装类废标不再进入每节 Prompt。
- 生成规则强化：评分点显性化举措、故障案例升维为应急预案、`[待人工补充：说明]` 事实缺口占位、历史标书严禁照抄旧实体。
- `write_volume` 调度改为一级章间串行 + 章内并发（沿用 `SECTION_STREAM_CONCURRENCY` 上限）：每完成一个一级章提炼 ≤150 字 `running_summary` 注入后续章节 Prompt，快照存 `workflow["chapter_summaries"]`；单节重试复用已存摘要。
- 新增 `technical_verifier.py` 后置核验：外项目实体残留扫描（白名单仅放行本标业主/项目名）、全局事实表数字口径冲突（服务期/质保/SLA/驻场）、评分点实质响应核验、空泛口号检测、跨节同一指标数字口径互查；警示写入 `task["verify_warnings"]` 并经 `confirm_reasons` 汇入覆盖视图「后置核验待复核」，`workflow["technical_verify"]` 记录汇总；核验失败不静默标合规。
- `retrieve_for_section` 在生成链路接收面包屑/挂载点/模型，接入意图拆解检索。

## 验收证据

- `tests/backend/test_tv_m0_t26_verifier_schedule.py`：3 passed（五段结构/面包屑/事实表 JSON/非技术废标不注入/章间摘要传递/核验器四类警示/confirm_reasons 联动）。
- `test_technical_rag.py`、`test_technical_digest.py`、`test_section_stream.py`、`test_draft_one_section_stages.py` 适配新契约后全绿。
- `export_openapi.py` 重新导出契约，`--check` 一致。

## 局限

- 跨节数字冲突按「指标词 ±24 字符窗口内数字+单位」字面比对，非同义词改写可能漏检。
- 平铺一级章目录（每章仅一节）会退化为全串行，属设计取舍。
- 只用模型替身验证；真实 Qwen 长文一致性待内网复验。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-054](../../issues/ISSUE-054.md) 的 Wave 5 设计执行。
