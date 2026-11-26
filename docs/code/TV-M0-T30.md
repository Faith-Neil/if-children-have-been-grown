为什么有这个文件：说明 TV-M0-T30 偏离表兜底池按章批量语义提炼的代码改动位置与设计理由。

# TV-M0-T30 代码说明

| 项 | 内容 |
|---|---|
| 状态 | done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 交付 | [TV-M0-T30](../delivery/TV-M0-T30.md) |

## 代码结构

| 文件 | 作用 |
|---|---|
| `backend/bid-core/icg/domain/technical_deviation_llm.py` | 新增兜底池按章批量 LLM 提炼模块：分组、Prompt、JSON 解析、安全门禁、并发调用、审计与缓存 |
| `backend/bid-core/icg/domain/technical_volume.py` | 偏离表构建主流程接入“确定性优先、LLM 只处理 fallback 池”；同步增强硬件免费更换等语义锚点 |
| `backend/bid-core/icg/domain/export_service.py` | 导出技术分册时解析当前项目 `chapter_generation` 模型 provider，并传入偏离表导出链路；模型路由不可用时保持确定性导出 |
| `tests/backend/test_tv_m0_t30_deviation_llm.py` | 覆盖服务/责任两类提炼、非法与外实体回落、零串标、部分失败不写完成态缓存 |

## 关键设计

1. **确定性主干优先**：`table_rows` 先为每条招标条款执行正文匹配。只有 `_content_response_detail(...)=fallback` 的条款进入 `fallback_pool`，高置信度命中不重复消耗模型。
2. **按章批量调用**：兜底池按 `section_key` 聚合，同一章多个条款合并成一次 JSON 调用；并发度取 `_stream_concurrency()`，本轮真机审计为 2。
3. **输入压缩但不删事实**：Prompt 中本章正文只移除 Markdown 包装、内部标记、空行和表格分隔线，不按语义裁剪正文；Global Fact Sheet 做空白压缩后整体传入。
4. **闭环安全门禁**：`validate_llm_response` 检查 50～110 字、首句“我司”、句号收尾、机械套话、负偏离/历史做法、外实体；调用侧再按条款类型检查服务证据动作与责任类“完全接受并遵守”，并拒绝正文未支撑的“杜绝/完全避免/无中断/确保不发生”。
5. **缓存不冻结失败**：指纹包含正文、兜底条款、Fact Sheet 与 Prompt 版本。只有 `rejected=0` 时才写缓存；缓存命中时本次 `calls=0`，同时保留 `cached_calls` 便于审计。
6. **性能约束**：本轮新鲜调用 2 章并发，LLM 耗时 10.210 秒；缓存复导总耗时 3.898 秒，满足导出耗时增幅控制在 20 秒以内。

## 验证命令

```bash
python -m pytest tests/backend/test_tv_m0_t30_deviation_llm.py tests/backend/test_tv_m0_t29_precision_export.py tests/backend/test_tv_m0_t28_export_deviation.py -q
```

当前结果：41 passed。
