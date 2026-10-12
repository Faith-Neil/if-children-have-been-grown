为什么有这个文件：说明挂证据抽屉怎样判断、分组和写回。

它解决什么问题：避免把页面上的勾选当成后台已经记下了审计列。

# APP-M2-T114：代码解释

- 对应任务、Issue、交付文档：[APP-M2-T114](../tasks/APP-M2.md#app-m2-t114)，[ISSUE-007](../../issues/ISSUE-007.md)，[交付](../delivery/APP-M2-T114.md)。
- 日期、实际代码路径、提交 / PR：2026-10-12。`frontend/web/src/evidence-drawer.ts`、`EvidenceDrawer.tsx`、`ProjectPages.tsx`。PR 未创建。

## 改了什么以及为什么

矩阵原来用一个平铺列表勾选资料编号。PRD v1.8 §5.3.1 要求把结构化资料、方案片段和历史标书分开，历史标书不能挂上。冻结契约 `73fde1e` 的 `demo-v1.json` 没有单独的候选或挂接操作。条款更新仍是 `PATCH /api/v1/projects/{id}/requirements/{id}`，正文是 `{ evidence_ids }`，并带 `If-Match` 和 `Idempotency-Key`。

## 入口和调用顺序

1. 响应矩阵证据列的“挂证据”调用 `openEvidence`。没有 `permissions.response` 时按钮禁用。
2. 打开时记下项目 `revision` 和该行当时的 `evidence_ids`。
3. `groupEvidence` 把资料分成三组。方案片段按 `match_score` 从高到低，没有分数时按名称。
4. `evidenceDecision` 决定能不能勾选。历史标书、`restricted`、未确认、伙伴且 `agreement_present` 不是 true、有效期早于投标截止日、`usable_as_evidence === false` 都不能勾。
5. 已挂列表用 `attachedEvidenceLabel`。过期时写“证据失效”，并给出“刷新”。刷新调用项目 `reload`，重新读取资料库和该行 `evidence_ids`，再用 `applyRefreshedAttachment` 替换当前勾选和打开时的快照。刷新不发送 `PATCH`。
6. “保存挂接”先看打开后的项目版本或该行编号有没有变。变了就停在抽屉里。没变才 `PATCH`。后台拒绝时抽屉也不关。
7. 可引用记录为空时，“去补录”转到 `/library`。

## 数据与状态

读取的是当前公司资料库和项目工作区，都在演示内存里。写回只改该行的 `evidence_ids`。增减对照的是打开抽屉时的编号，不是字典里的 `linked_by` / `linked_at`。那些列后台没有返回。可选的 `source_tier`、`agreement_present`、`restricted`、`match_score`、`source` 只在响应里出现时才用；新建资料的请求体不能带它们。

## 关键判断与异常

只读账号的 `permissions.response` 为 false，不能打开后保存。历史标书没有勾选框，只能看原文。矩阵上证据失效用红色“证据失效”标签和行首色条表示。抽屉已挂列表对过期资料也写“证据失效”，候选卡片仍写“过期”。条款状态标签仍是待确认或已确认。打开后如果项目版本或已挂编号变了，保存按钮禁用，并提示先刷新。

## 验证与限制

单测覆盖缺协议、受限、过期、未确认、历史标书、已挂“证据失效”文案、刷新后的编号副本、增减和版本变了。浏览器覆盖未确认、历史标书、过期、抽屉内刷新、只读、保存后的版本号，以及另一个会话先摘掉证据后的版本冲突。见 [核对](../testing/2026-10-12-app-m2-t114-evidence-drawer.md)。没有改后台，没有改冻结 JSON，也没有改 `spec/openapi/README.md`。智能匹配和“过期后回到待确认”的端到端仍未做，记在交付的后续里，等 ISSUE-033 的后台字段后再测。
