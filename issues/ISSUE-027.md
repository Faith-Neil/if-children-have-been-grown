为什么有这个文件：登记已批准的 Word 默认版式，并记下它要修的 W1～W4。

它解决什么问题：避免导出仍是普通段落，却没有一张卡说明版式、覆盖方式和验收。

# ISSUE-027：Word 导出默认版式

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-027 |
| 类型 | change |
| 优先级 | P2 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | style-1 |
| 关联 Task | [BE-M0-T15](../docs/tasks/BE-M0.md#be-m0-t15) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 2026-10-12 后台测试打开合成 docx。等待项目经理 QA 签收 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T15](../docs/delivery/BE-M0-T15.md) |
| 代码 / 流程解释 | [BE-M0-T15](../docs/code/BE-M0-T15.md) |
| 验证记录 | [2026-10-12 默认版式](../docs/testing/2026-10-12-be-m0-t15-word-style.md) |

## 现象与证据

QA 在 [Word 渲染记录](../docs/testing/2026-10-12-t06-smoke-word-render.md) 记下 W1～W4，位置是 `backend/bid-core/icg_demo/adapters.py` 当时的 `build_docx`。对照代码：正文没有 Heading 样式、没有 `word/numbering.xml`、没有 TOC 域、没有页眉页脚；分册把章节名和正文拼成普通段落；表头只有重复标记、单元格不加粗；`docDefaults` 的 `w:rFonts` 写了 ascii 和 eastAsia，没有 hAnsi。

## 影响与分流

- 只改后台演示导出。默认版式按项目经理批准的纸张、边距、封面、标题、正文、表格、页眉页脚、目录和页码。一个投标可以传入自己的版式对象覆盖。
- 不新增依赖。生成仍用标准库写 OOXML。
- 不改正式递交规则，不把内部稿标成可递交。不处理 Q2，也不做回执、会话、租约或业务表。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T15 | 默认版式写入 docx，并允许单个投标覆盖 | `backend/bid-core/icg_demo/docx_style.py` | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 打开合成 docx 能看到 Heading 1～3、三种字体属性、字号间距缩进、加粗表头、TOC 域、页码和页边距 | 2026-10-12 后台测试 329 passed、2 skipped。见验证记录 |
| AC-02 | 未传版式时用默认值；传入版式时左边距随之改变 | 同一测试文件中的覆盖用例 |
| AC-03 | 不新增 `requirements.txt` 依赖 | 未改依赖文件 |
| AC-04 | 卡片保持 in-review，不标 done | 看板与本文件均为 in-review |

未做发布验收。in-review 不是 closed，也不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 有影响，只改任务计数。版式不改产品规则 | `docs/PRD.md` 任务计数句 | style-1 / ISSUE-027 / 2026-10-12 | 已改 |
| ROADMAP | 有影响，只改任务计数。不改阶段或门禁 | `docs/ROADMAP.md` 任务计数句 | style-1 / ISSUE-027 / 2026-10-12 | 已改 |
| ARCHITECTURE | 无影响。演示导出的默认版式不改变架构基线 | 不改 `docs/ARCHITECTURE.md` | style-1 / ISSUE-027 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 BE-M0-T15，状态 in-review | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | style-1 / ISSUE-027 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。进度改为 363 项，并写明 W1～W4 的卡在复核 | `docs/PROJECT_STATUS.md` | style-1 / ISSUE-027 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、说明、验证和同步表 | `docs/DOCUMENT_INDEX.md` | style-1 / ISSUE-027 / 2026-10-12 | 已改 |

PROJECT_BRIEF 排期行的任务计数一并改为 363 项，记在同步表。BE-M0-T14 已由托管 MySQL 作业占用，本卡使用 BE-M0-T15。未改 `docs/reference/`。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | style-1 / in-review | 默认版式已写入导出。done 与 closed 等待项目经理在 QA 后设置 | [验证](../docs/testing/2026-10-12-be-m0-t15-word-style.md) |

## 本地验收与后续合入发布

- 本地验收：2026-10-12，见验证记录。只用合成数据。
- 未覆盖：Word 或 WPS 打开后的视觉签收，以及客户模板。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-027-sync.md)。
- PR：未新开。合入与发布均未发生。
