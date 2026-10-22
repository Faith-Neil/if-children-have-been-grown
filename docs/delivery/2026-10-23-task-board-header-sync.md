# TASK_BOARD 板头同步 + Antigravity 指挥口令

| 项 | 内容 |
|---|---|
| 日期 | 2026-10-23 |
| 分支 | `feat/opencode-ICG` |
| 权威看板 | `docs/TASK_BOARD.md`（唯一派工源；**不另开 TASKBOARD_v2**） |
| 执行方 | Antigravity（本机）；主 agent 可读本文后派 FE/BE/AI/QA subagent |
| 约束 | 本包**优先只改文档**（板头 + 必要卡状态标注）；不改业务代码；不动 PRD/字典 |

---

## A. 板头同步（Antigravity 先做）

### A1. 在 `docs/TASK_BOARD.md` 文首插入「结构债收官指针」（半页内）

放在现有标题/统计之下、任务表之上，建议固定段落（可微调措辞，语义必须保留）：

```markdown
## 结构债收官指针（2026-10-23 · 勿忽略）

- **WP-1～WP-7 已收官**（代码结构）：前端八域、`backend/bid-core/icg/` 分包、`/api/v1`、八角色/演示关闸、OpenAPI/CI。详见 `docs/PROJECT_STATUS.md`「现行工程结构」、`docs/architecture/repository-layout.md`「现行骨架」、`docs/delivery/WP-*.md`、`AGENTS.md` 冻结规则。
- **DOC-SYNC-1 已落地**；若存在未完成的 `docs/delivery/2026-10-23-doc-sync-1.1.md`，**先做完再开业务卡**。
- **禁止把 FE-M0-T04～T10 当绿野开工**（正式工程脚手架/登录/Shell/路由等能力已被 WP + APP-M2 路径覆盖）。相关卡应标 `cancelled` 或 `done`+备注 `superseded-by-WP`，或保留 `blocked` 但备注「仅补验收文档，禁止重建工程」。
- **结构债后续**：`issues/ISSUE-038.md`（双错误体 / 巨石继续瘦身 / 空 `icg.api|app`）→ 见板内 `BE-TECH-DEBT-*` / `FE-TECH-DEBT-*`（P2，勿压过 PRD P0）。
- **完成度口径**：board `done` 张数 ≠ 产品完成度；产品以 PRD v1.8 + `docs/delivery/2026-10-22-prd-gap-summary.md` 为准。
- **下一棒默认顺序**：DOC-SYNC-1.1（若未完）→ 清 in-review / 关演示冒烟 → 按前缀啃 APP-M2 与 PRD P0。
```

### A2. 校正文首元数据

- 更新日期为当日；重新统计或注明「以表内状态为准，文首数字仅概览」
- tip 可写当前 `git rev-parse --short HEAD`（与 PROJECT_STATUS 对齐更好）

### A3. FE-M0 防误派（最小触达）

对 **FE-M0-T04～T10**（及明显「建正式前端/登录壳」的同类卡）：

- 在板表备注列或对应 `docs/tasks/FE-M0.md` 卡头加：`superseded-by-WP` / 「禁止重建；仅允许补交付/验收」
- 状态建议：`cancelled`（能力已覆盖）或保持原状态但备注强制禁止绿野  
- **不要** bulk 改 200+ 张无关 planned 卡

### A4. 挂上 ISSUE-038（三行或一行 epic）

在 `TASK_BOARD.md` 增加行（ID 可自定，建议如下），状态 `planned`，优先级 P2：

| ID | 标题要点 | 建议前缀 |
|---|---|---|
| BE-TECH-DEBT-01 | suggestions 等双错误体收敛 | BE |
| FE-TECH-DEBT-01 | EditorPage 等继续瘦身（&lt;400 精神） | FE |
| BE-TECH-DEBT-02 | 填充或删除空 `icg/api`、`icg/app` | BE |

并在 `issues/ISSUE-038.md` 顶部链回这三行（可选）。

### A5. 验收（板头同步）

- [x] 打开 `TASK_BOARD.md` 一眼能看到「WP 已收官 + 勿重做 FE-M0」
- [x] FE-M0-T04～T10 有防误派标注
- [x] ISSUE-038 三债卡可见
- [x] 未新建第二套看板文件

**提交建议：** `docs(governance): sync TASK_BOARD header after WP/DOC-SYNC`

---

## B. 主 agent 指挥口令（可整段粘贴）

### B0. 会话总约束（每次新开主 agent 会话先贴）

```text
你是主 coding agent。唯一派工源：docs/TASK_BOARD.md + docs/tasks/<前缀>.md。
遵守 AGENTS.md：八域目录、icg 分包、只新增 /api/v1、Layout First、前端测试在 frontend/web/tests/、不重置/强推合作分支。
结构以 repository-layout「现行骨架」+ PROJECT_STATUS 结构节为准；禁止把 FE-M0-T04～T10 当新建工程。
开发者最高把卡标到 in-review；done 必须等 QA 签署 + 人类 PM 确认。
每卡交付：docs/delivery/<卡ID>.md；有代码则 docs/code/<卡ID>.md。
一次给每个 subagent 最多 1～2 张卡；改完回写同一 TASK_BOARD 状态。不要另开 TASKBOARD_v2。
```

### B1. 若 DOC-SYNC-1.1 未完成（串行，先于业务）

```text
先只做文档包：读 docs/delivery/2026-10-23-doc-sync-1.1.md，按 A→E 执行。
必须先列出 backend/bid-core/icg 实树再改模块表，禁止抄假模块名。
不改业务代码、不动 PRD。提交并填写完成记录后再向我要下一张业务卡。
```

### B2. 派 QA：清 in-review（不新开功能）

```text
QA subagent：只处理 TASK_BOARD 上状态为 in-review 的卡（优先 BE-M0 / AI-M0 / APP-M2 已提测项）。
复跑或核对交付证据；通过则准备签署说明，不通过开/补 REV 卡。
禁止新开功能开发；禁止自行标 done（done 留给 PM）。
```

### B3. 冒烟（你或 QA，关演示）

```text
关 VITE_DEMO / 按生产门禁：正式登录 → 上传或进项目 → 矩阵 → 生成 → 导出。
结果写入 docs/delivery/（可挂 APP-M1-T06 或新建 REV-SMOKE-001）。演示路径通过不算正式通过。
```

### B4. 并行业务（DOC-1.1 + 冒烟后；按前缀）

**前端 FE**

```text
FE subagent：从 TASK_BOARD 取 APP-M2 中依赖已满足的 planned 或需补的 in-review（组件壳、<Can>、进度等），或 PRD gap P0 最小页（知识库/写作档案入口）。
代码只放 frontend/web/src 八域内；禁止 src 根平铺。测：pnpm --dir frontend/web test。
```

**后端 BE**

```text
BE subagent：优先 PRD P0 相关（规则最小可递交、门禁）或 board 上依赖已清的 BE-M0 / ISSUE 剩余项。
新逻辑进 backend/bid-core/icg/；icg_demo 仅 façade。API 只加 /api/v1。测：pytest 相关路径。
```

**AI / RAG**

```text
AI subagent：只做 board 上 AI-M0 已具备接口的验收或最小对接；禁止声称生产模型已完成。
无内网端点时写清 blocked 原因与复现，不要假绿。
```

**QA（每个切片后）**

```text
本切片合并前：开/更新 REV 签署卡，对照 delivery+code；不通过不得建议 PM 标 done。
```

### B5. P2 插空（勿压 P0）

```text
仅当 P0/in-review 清账空隙：做 BE-TECH-DEBT-01/02 或 FE-TECH-DEBT-01（见 ISSUE-038）。
仍只改任务相关文件；先交付文档再标 in-review。
```

---

## C. 给人类 PM 的检查清单

1. Antigravity 是否已提交板头同步？  
2. DOC-SYNC-1.1 是否 tip 回写且模块表无假路径？  
3. 主会话是否贴了 B0？有没有人在派 FE-M0 绿野卡？  
4. 并行是否「每角色 1～2 卡」而非四线巨型需求？  
5. 对外汇报用 PRD gap，不用 board done/总数比。

## D. 完成记录（执行板头同步后填写）

| 项 | 填写 |
|---|---|
| 完成 tip | 待落地提交 HEAD（见本卡交付提交） |
| 改动文件 | `docs/TASK_BOARD.md`<br>`docs/tasks/FE-M0.md`<br>`issues/ISSUE-038.md`<br>`docs/delivery/2026-10-23-task-board-header-sync.md` |
| FE-M0 标注方式 | 在板表任务名及 tasks/FE-M0.md 卡头显式标注 `superseded-by-WP` / 「禁止重建；仅允许补交付/验收」，状态标为 `cancelled` |
| ISSUE-038 行 ID | `BE-TECH-DEBT-01`、`FE-TECH-DEBT-01`、`BE-TECH-DEBT-02`（均关联 ISSUE-038，状态 planned，优先级 P2） |
