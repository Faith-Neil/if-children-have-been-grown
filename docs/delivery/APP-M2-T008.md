为什么有这个文件：记录离线检查进入 GitHub Actions 的实际结果。

它解决什么问题：把工作流、验证计数和尚未实现的主题接口分开，避免把本地门禁写成已上线。

# APP-M2-T008：离线检查纳入 CI

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T008 |
| 代码解释 | [离线 CI 工作流](../code/APP-M2-T008.md) |
| 验收 | 三个并行作业已写入；Actions 运行与测试计数见[验证](../testing/2026-10-12-offline-ci.md)。`buildTheme` 未执行 |
| 项目进度 | 本卡 in-review。340 项中 done 17、in-progress 8、in-review 1、planned 266、blocked 48、ready 0。APP-M2 为 T001 in-progress、T008 in-review、其余 257 张 planned |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12；APP-M2；[ISSUE-012](../../issues/ISSUE-012.md)；[任务卡](../tasks/APP-M2.md#app-m2-t008)。
- 分支、提交、PR：`codex/repository-foundation`；提交在推送时回填；[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 为既有草稿，本轮不新建 PR。
- 本地验收状态：in-review。工作流已提交，Actions 绿色结果尚未回填，因此不标 done。
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

命令与计数记在 [离线 CI 验证](../testing/2026-10-12-offline-ci.md)。Actions 网址在该文件回填之前，本卡保持 in-review。

## 项目进度

ISSUE-015 之后为 340 项：done 17、in-progress 8、planned 267、blocked 48。本卡从 planned 改为 in-review 后，planned 为 266，并增加 1 项 in-review。APP-M2 的 259 张卡中 T001 仍 in-progress，T008 为 in-review，其余 257 张 planned。下一张产品卡仍按依赖推进，不因本门禁把 T001 或完整产品标完成。PR #3 待合入，未发布。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。页面、规则和验收口径未改，治理块保持 g1.1 / 2026-10-11 / ISSUE-007 |
| ROADMAP | 无影响。阶段、依赖和发布顺序未改 |
| ARCHITECTURE | 无影响。模块、数据、接口和部署结构未改；CI 只重复现有离线检查 |
| Issue 看板/详情 | 新增 ISSUE-012，状态 in-review；ISSUE-013 与 ISSUE-015 保留。下一编号改为 ISSUE-016，ISSUE-014 留给并行的 ProComponents 变更 |
| TASK_BOARD / PROJECT_STATUS | T008 改为 in-review 并链接本交付；进度口径同步 |
| DOCUMENT_INDEX | 登记工作流、Issue、交付、代码解释、验证和同步表 |

同步表见 [ISSUE-012-sync](../governance/ISSUE-012-sync.md)。

## 风险与后续

Actions 尚未在本提交上跑完。若某套件失败且与推送前的既有失败一致，写入验证记录，不用 skip 掩盖。`buildTheme` 与构建产物的主题令牌扫描未做。合入和发布另记。
