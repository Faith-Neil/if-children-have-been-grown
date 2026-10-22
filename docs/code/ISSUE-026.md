为什么有这个文件：说明这次计数对齐没有改运行代码。

它解决什么问题：避免把文档里的 361 理解成请求层或后台又改了一轮。

# ISSUE-026：代码解释

- 对应任务、Issue、交付文档：无新任务卡 / [ISSUE-026](../../issues/ISSUE-026.md) / [交付](../delivery/ISSUE-026.md)
- 日期、实际代码路径、提交 / PR：2026-10-12。无应用代码路径。分支 `codex/repository-foundation`。PR #3 未合入

## 改了什么以及为什么

改的是 PRD、ROADMAP 和 PROJECT_BRIEF 里的任务计数，使它们等于任务看板。没有改 `frontend/web/src/shared/api.ts`，也没有改 `backend/`。

## 入口和调用顺序

无新入口。页面仍调用现有 `request()`。一次写入仍是一把 `Idempotency-Key`。章节版本的请求头与正文 `idempotency_key` 仍相同。网络错误、502 和 503 仍在同一次调用里再试，最多 3 次含首次。

## 数据与状态

任务状态仍只记在看板和任务卡。这次不新增卡片，所以 361 这个总数不变。演示数据仍在内存。

## 关键判断与异常

不把计数对齐当成 T001 或 T002 验收通过。409、422、423、428 的不重试规则保持原样，等项目经理另作决定后再改。

## 验证与限制

核对见 [计数记录](../testing/2026-10-12-issue-026-counts.md)。没有新的函数测试，因为没有新的函数。

## 跟进

AI-01 进入 in-review 后，三份基线改成 8 in-review、49 blocked。这次仍然没有应用代码。请求层里带 `MODEL_UNAVAILABLE` 的 502 不自动重试，那是另一次提交，本文件不改那套规则。上文「仍再试全部 502」只描述第一次对齐时没有动过的代码。

`84a3fca` 之后三份基线改成 364 项、27 done。仍然没有应用代码，不改 `api.ts` 和 `backend/`。核对见 [基线复核](../testing/2026-10-12-issue-026-baseline-count-check.md)。

`3bb311a` 之后，三份基线改为里程碑快照，不要求与之后的活看板逐项相等。检查程序仍只核对治理块、链接和完成材料，本跟进不改 `scripts/check-project-governance.cjs`。APP-M2-T001 与 APP-M2-T002 标为 done 只改任务状态和文档，不改 `frontend/web/src/shared/api.ts` 或 `backend/`。
