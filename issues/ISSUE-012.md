为什么有这个文件：登记把现有离线检查放进 GitHub Actions 的流程变更。

它解决什么问题：避免后台测试、页面构建和治理检查只在某台开发机上通过，而合作分支没有统一门禁。

# ISSUE-012：离线检查纳入 GitHub Actions

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-012 |
| 类型 | workflow |
| 优先级 | P1 |
| 状态 | closed（本地验收） |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | offline-ci-1 |
| 关联 Task | [APP-M2-T008](../docs/tasks/APP-M2.md#app-m2-t008)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入；本轮不新建 PR |
| 本地验收 | 通过；2026-10-12。运行 [38200746746](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38200746746) 三个作业 success |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [APP-M2-T008交付](../docs/delivery/APP-M2-T008.md) |
| 代码 / 流程解释 | [APP-M2-T008代码解释](../docs/code/APP-M2-T008.md) |
| 验证记录 | [离线 CI 验证](../docs/testing/2026-10-12-offline-ci.md) |

## 现象与证据

合作分支 `codex/repository-foundation` 此前没有 GitHub Actions。后台 pytest、前端 `pnpm build` 与函数测试、治理检查和 `.cjs` 套件只在开发机执行。APP-M2-T008 的离线检查门禁要求这些检查在推送和拉取请求上重复执行，并且不使用密钥、外网模型或内网服务。

QA 于 2026-10-12 在 Python 3.13.5、Node v24.9.0、pnpm 11.25.0 上复跑通过，见 [QA复跑](../docs/testing/2026-10-12-qa-rerun.md)。前端 `frontend/web/tests/*.test.mjs` 直接导入 `.ts`，Node 20 会以 `ERR_UNKNOWN_FILE_EXTENSION` 失败，因此 CI 固定 Node 24.9.0。Python 固定 3.13.5。会话脚本 `tests/backend/session_live_http.py` 不以 `test_` 开头，pytest 不会收集它。

## 影响与分流

- 影响：新增 `.github/workflows/offline-check.yml`，以及本 Issue、交付、代码解释和验证记录。检查使用已有内存仓库和模型替身，安装依赖之后的测试不再访问外网模型。
- 不涉及：不实现 `buildTheme`，不改页面主题、接口或产品范围。品牌运行时仍由 APP-M2-T033 承接。不合并 PR #3，不发布。
- 依赖：BE-M0-T01 与 APP-M2-T001 已有可运行的本地后台和页面。ISSUE-013 的会话脚本已在 `adc2600`。ISSUE-015 的 `smoke_t06.py` 已在 `f310a9f`，backend 作业在安装依赖后单独运行它，不增加 soffice。ISSUE-014 的锁文件变更由并行任务处理，推送前变基保留双方条目。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T008 | 三个并行离线作业覆盖 pytest、会话 HTTP、smoke_t06、前端构建与测试、`.cjs` 套件和治理检查 | `.github/workflows/offline-check.yml` | AC-01～AC-04 | done |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 推送和拉取请求触发本分支工作流；backend、frontend、governance 并行；依赖有缓存；无密钥 | 通过。`cf2c2a1` 的 push 运行三个作业均为 success |
| AC-02 | backend 安装 `backend/bid-core/requirements.txt` 后运行 `python -m pytest tests/backend`，再单独运行 `python tests/backend/session_live_http.py` 和 `cd backend/bid-core && python smoke_t06.py`；不增加 soffice 或 Word 渲染 | 通过。262 passed、TOTAL 15 PASS 15、smoke_t06 12 项且 `passed: true` |
| AC-03 | frontend 用 pnpm 11.25.0 按锁文件安装，执行 `pnpm build`（`tsc -b && vite build`）和 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`；Node 为 24.9.0 | 通过。构建成功，72 pass |
| AC-04 | governance 运行治理、原型、工作区同步、旧页 `.cjs` 套件和 `node scripts/check-project-governance.cjs` | 通过。35 pass；治理检查 129 份 Markdown、340 项任务、12 项 Issue |
| AC-05 | `buildTheme` 换主色后锁定令牌不变 | 未执行。仓库没有 `buildTheme`；本轮范围是离线 CI 门禁，不把它写成通过 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响：未改页面、业务规则或验收口径 | 不改 `docs/PRD.md` | g1.1 / ISSUE-012 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响：未改阶段、依赖或发布顺序；任务状态在任务看板 | 不改 `docs/ROADMAP.md` | g1.1 / ISSUE-012 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响：未改模块、数据、接口或部署结构；CI 只重复现有离线检查 | 不改 `docs/ARCHITECTURE.md` | g1.1 / ISSUE-012 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响：APP-M2-T008 改为 done 并关联本 Issue | `docs/TASK_BOARD.md` | 0.6 / ISSUE-012 / 2026-10-12 | 已同步 |
| PROJECT_STATUS | 有影响：记录离线 CI 本地验收，完成数随任务状态更新 | `docs/PROJECT_STATUS.md` | g1.1 / ISSUE-012 / 2026-10-12 | 已同步 |
| DOCUMENT_INDEX | 有影响：登记工作流、Issue、交付、代码解释、验证和同步表 | `docs/DOCUMENT_INDEX.md` | g1.1 / ISSUE-012 / 2026-10-12 | 已同步 |

治理块保持 WORKFLOW 的 g1.1 / 2026-10-11 / ISSUE-007。本 Issue 不改该块。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | offline-ci-1 / in-progress | 预分配 ISSUE-012，按 QA 命令编写三个并行作业，并纳入 ISSUE-013 会话脚本 | 项目经理指定范围 |
| 2026-10-12 | offline-ci-1 / in-review | 工作流写入 `cf2c2a1` 并推送 | 待运行结果 |
| 2026-10-12 | offline-ci-1 / closed | 运行 38200746746 三作业 success；pytest 262、会话 15、smoke_t06 12、前端 72、cjs 35、治理检查通过 | [验证](../docs/testing/2026-10-12-offline-ci.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：通过，2026-10-12。closed 只表示本地验收，PR #3 未合入，软件未发布。
- 验证方式：见验证记录。Node 20 的 `.ts` 导入失败是环境问题，CI 固定 Node 24，不跳过该套件。没有既有失败需要隐藏。
- 六份基线同步与互链复核：上表已填；PRD、ROADMAP、ARCHITECTURE 无正文改动。
- PR 状态：沿用 PR #3，未新建，未合入。
- 发布版本与日期：未发布。
