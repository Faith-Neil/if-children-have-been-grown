为什么有这个文件：记录 TV-M0-T32 强制模型两阶段目录规划、失败上浮、前端重跑入口与全量均衡挂载的交付证据。

# TV-M0-T32 交付说明

| 项 | 内容 |
|---|---|
| 状态 | in-review；建议 PM 复核后决定是否标 done |
| Issue | [ISSUE-060](../../issues/ISSUE-060.md) |
| 任务卡 | [TV-M0-T32](../tasks/TV-M0.md#tv-m0-t32) |
| 代码说明 | [TV-M0-T32](../code/TV-M0-T32.md) |
| 验证登记 | [iss-060-cq-real-validation](../testing/2026-11-28-iss060-cq-real-validation.md) |

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | TV-M0-T32 |
| 代码解释 | [代码说明](../code/TV-M0-T32.md) |
| 验收 | Review 修复轮后端大纲聚焦回归通过；OpenAPI 100% 一致；前端 tsc 与 production build 通过；真实 `qwen3:30b-a3b-instruct-2507-q4_K_M` 生成 33 个标题、23 个非空叶子，`outline_source=model`，空叶子 0，最大叶子 11 条（9.65%），无「其他服务承诺」。 |
| 项目进度 | in-review。实现与真实模型验证完成；QA/PD 独立签署未执行，建议 PM 标 done 前复核 PR 与实证样本。 |
<!-- task-delivery:end -->

## 完成内容

1. 目录规划改为两阶段：先生成章节骨架，再把全部有效 T/S 编号挂载到叶子节点；高分评分项在 prompt 中按分值权重约束归位。
2. 移除每章 9 条硬上限；漏挂编号只进入 `validation.unmounted_digest_refs` 与未挂载池，不倒进兜底章。
3. 每阶段最多 3 次尝试（首次 + 2 次重试），带 JSON 围栏/注释/尾逗号修复；挂载反馈包含未挂编号、非叶子节点、重复挂载与过度集中。
4. 模型不可用或输出非法时明确写 `tree_model_failed`、可读 `outline_reason` 与内部结构化错误；不再偷偷生成通用规则树冒充模型目录。
5. 前端编辑台新增错误级驻留告警和管理员「重新生成目录」按钮，成功后刷新工作台与目录，dirty 状态下不覆盖未保存编辑。

## 验收结果

| 验收条目 | 结果 |
|---|---|
| 模型失败不静默降级 | 通过；`qwen3.6:35b` 挂载输出非法时 501.18 秒后返回 `tree_model_failed=true`、`outline_source=rule_fallback`、空 plan，无伪模型目录 |
| 真实模型成功生成 | 通过；`qwen3:30b-a3b-instruct-2507-q4_K_M` 108～170 秒级生成模型目录，来源为 `model` |
| 无 9 条硬上限 | 通过；实证单叶最多 19 条，最大占比 16.67%，不是 9 条截断 |
| 无兜底倾倒 | 通过；目录无「其他服务承诺/其他/综合」标题 |
| 前端重跑入口 | 通过；聚焦测试覆盖权限、HTTP 200 但 `ok:false/tree_model_failed:true`、刷新失败与 dirty 守卫 |

## 限制

- 真机首轮实证仍有少量漏挂编号进入未挂载池，系统如实暴露 `validation` 而不倾倒兜底章；挂载语义完美度仍需产品人工复核。
- `qwen3.6:35b` 在相同输入上出现挂载 JSON 不稳定；`qwen3:30b-a3b-instruct-2507-q4_K_M` 可成功。失败路径已按设计要求显式上浮。
