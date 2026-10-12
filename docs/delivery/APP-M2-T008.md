为什么有这个文件：记录离线检查进入 GitHub Actions 的实际结果。

它解决什么问题：把工作流、验证计数和尚未实现的主题接口分开，避免把本地门禁写成已上线。

# APP-M2-T008：离线检查纳入 CI

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T008 |
| 代码解释 | [离线 CI 工作流](../code/APP-M2-T008.md) |
| 验收 | [cf2c2a1 三作业通过](../testing/2026-10-12-offline-ci.md)：pytest 262、会话 15、smoke_t06 12、前端 72、cjs 35、治理检查通过。QA 已签署。`buildTheme` 未执行。项目经理于 10-12 12:10 在 QA 签署后确认，卡片为 done |
| 项目进度 | 本卡 done。343 项中 done 20、in-review 1、in-progress 7、planned 266、blocked 49、ready 0。APP-M2 为 T001 in-review、T008 done、其余 257 张 planned。未合入，未发布 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；APP-M2；[ISSUE-012](../../issues/ISSUE-012.md)；[任务卡](../tasks/APP-M2.md#app-m2-t008)。
- 分支、提交、PR：`codex/repository-foundation`；工作流提交 `cf2c2a1`；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 为既有草稿，本轮不新建 PR。
- 本地验收状态：done。项目经理于 10-12 12:10 在 QA 签署后确认。Actions 运行 [38200746746](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38200746746) 三个作业均为 success。QA 签署见 [57ef015](../testing/2026-10-12-qa-signoff.md)。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

新增 `.github/workflows/offline-check.yml`。推送和拉取请求在 `codex/repository-foundation` 上并行运行三个作业：

- backend：安装 `backend/bid-core/requirements.txt`，运行 `python -m pytest tests/backend`，再单独运行 `python tests/backend/session_live_http.py`，然后在 `backend/bid-core` 运行 `python smoke_t06.py`。该步骤不调用 soffice，也不另做 Word 渲染。
- frontend：用 pnpm 11.25.0 按锁文件安装，运行 `pnpm build`，再运行 `tests/frontend/*.test.mjs` 与 `frontend/web/tests/*.test.mjs`。
- governance：运行治理、原型、工作区同步和旧页 `.cjs` 测试，以及 `node scripts/check-project-governance.cjs`。

Python 固定 3.13.5，Node 固定 24.9.0。pip 与 pnpm 使用 Actions 缓存。工作流不读取密钥，不调用外网模型，存储仍是内存仓库。

偏差：原卡还要求 `buildTheme` 换主色后锁定令牌不变。仓库没有该函数，本轮按项目经理指定的离线门禁实施，不把这项写成通过。品牌运行时仍是 APP-M2-T033。

## 代码解释

入口、作业顺序和限制见 [代码解释](../code/APP-M2-T008.md)。

## 验收结果

命令与计数记在 [离线 CI 验证](../testing/2026-10-12-offline-ci.md)。运行 [38200746746](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38200746746) 在 `cf2c2a1` 上成功。

## 项目进度

S4 当时把本卡放回 in-review，当时快照是 343 项中 done 19、in-review 1。该句保留为当时事实。

本卡现为 done。项目经理于 10-12 12:10 在 QA 签署后确认。当前看板 343 项：done 20、in-review 1（APP-M2-T001）、in-progress 7、planned 266、blocked 49、ready 0。AI-02 已在另一次确认中标为 done，本卡不改 ISSUE-011。APP-M2 的 259 张卡中 T001 为 in-review，T008 为 done，其余 257 张 planned。PR #3 待合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。页面、规则和验收口径未改，治理块保持 g1.1 / 2026-10-11 / ISSUE-007 |
| ROADMAP | 本轮未改。阶段、依赖和发布顺序未改。计数字句仍写 T008 为 in-review，按本轮范围不改正文 |
| ARCHITECTURE | 无影响。模块、数据、接口和部署结构未改；CI 只重复现有离线检查。本轮未改 |
| Issue 看板/详情 | ISSUE-012 为 closed，APP-M2-T008 为 done。合入状态仍是 PR #3 待合入。未改 ISSUE-010、ISSUE-011 |
| TASK_BOARD / PROJECT_STATUS | T008 为 done。343 项：20 done、1 in-review、7 in-progress、266 planned、49 blocked、0 ready |
| PROJECT_BRIEF | 排期从 19 done、2 in-review 改为 20 done、1 in-review。T008 改为 done。原因：项目经理于 10-12 12:10 在 QA 签署后确认。AI-02 的 done 保留，不改 ISSUE-011。详见同步表 |
| DOCUMENT_INDEX | 本轮未改。索引里仍有 T008 / ISSUE-012 为 in-review 的条目 |

同步表见 [ISSUE-012-sync](../governance/ISSUE-012-sync.md)。

## 风险与后续

`cf2c2a1` 的三个作业均成功，没有需要记成既有失败的套件。`buildTheme` 与构建产物的主题令牌扫描未做。合入和发布另记。运行器现固定 `ubuntu-24.04`。动作主版本为 checkout v7、setup-python v7、setup-node v7、pnpm/action-setup v6，它们的 `action.yml` 使用 `node24`。依赖缓存仍由 setup-python 与 setup-node 完成；独立的 actions/cache 最新主版本是 v6，同样是 `node24`，工作流没有另加一步。
