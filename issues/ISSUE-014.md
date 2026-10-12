为什么有这个文件：登记项目经理批准的前端布局依赖，并留下引入前后的打包体积。

它解决什么问题：避免在未记录体积时加入 ProLayout，或顺便带上未批准的包。

# ISSUE-014：引入 ProLayout 并记录打包体积

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-014 |
| 类型 | version |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | pro-layout-7.22.7 |
| 关联 Task | APP-M2-T001；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入。本轮不新建 PR |
| 本地验收 | 已提交 in-review。体积和命令见 [复核记录](../docs/testing/2026-10-12-prolayout-routes.md)。项目经理尚未标 done |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [APP-M2-T001 交付](../docs/delivery/APP-M2-T001.md) |
| 代码 / 流程解释 | [APP-M2-T001 代码解释](../docs/code/APP-M2-T001.md) |
| 验证记录 | [2026-10-12 布局复核](../docs/testing/2026-10-12-prolayout-routes.md) |

## 现象与证据

设计规范要求使用 `@ant-design/pro-components` 的 ProLayout。项目经理批准二选一：`@ant-design/pro-components` 或 `@ant-design/pro-layout`，除此之外不得新增任何直接依赖。引入前基线约为 1334 kB。

引入前，Node v24.21.0、pnpm 11.25.0，在 `frontend/web` 执行 `pnpm install --frozen-lockfile && pnpm build`：

- `dist/assets/index-BqghTeOl.js` 1,334.42 kB，gzip 409.62 kB
- `dist/assets/index-CniIfmqA.css` 20.77 kB，gzip 5.00 kB

这个 JS 文件名和体积与 [QA 复跑](../docs/testing/2026-10-12-qa-rerun.md) 记录一致。

引入 `@ant-design/pro-layout@7.22.7` 之后，同一命令的结果是：

- `dist/assets/index-BmV8EgUZ.js` 1,564.53 kB，gzip 486.19 kB
- `dist/assets/index-D3NkcTW6.css` 21.02 kB，gzip 5.04 kB

原始脚本增加约 230.11 kB，gzip 增加约 76.57 kB。

选用 pro-layout 而不是 pro-components 2.8.10，是因为后者依赖同一版 pro-layout，还会带上 ProTable、ProForm 等本卡不用的包。没有加入 react-router。传递依赖随锁文件进入，不另写直接依赖。

## 影响与分流

- 影响 `frontend/web/package.json`、`pnpm-lock.yaml` 和产品外壳。ISSUE-009 / APP-M2-T001 使用这个包。
- 不改请求层、元数据表、OIDC、通用表单离开或断点记忆。
- 没有其他新依赖。状态保持 in-review，done 由项目经理在 QA 签收后标记。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T001 | 用批准的 ProLayout 做外壳，并记录体积 | `frontend/web` | 引入前后 `pnpm build` 体积 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 直接依赖只增加批准的包之一 | 已提交复核。`package.json` 仅新增 `@ant-design/pro-layout` 7.22.7 |
| AC-02 | 记录引入前后 `pnpm build` 体积 | 已提交复核。1334.42 kB → 1564.53 kB，见验证记录 |
| AC-03 | 项目经理 QA 签收后才能 done | 未执行。本 Issue 保持 in-review |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无正文修改。第19行仍写 T001 已开工、其余 258 卡 planned。第21行仍写整个 T001 未完成；本卡未 done，第21行成立 | `docs/PRD.md` 第19行、第21行 | layout-review-1 / ISSUE-014 / 2026-10-12 | 已核对，未改 |
| ROADMAP | 无正文修改。第17行仍是 343 项、18 done、8 in-progress、2 in-review。第19行仍写接下来补 ProLayout。活计数在任务看板：343 项，18 done、3 in-review、7 in-progress | `docs/ROADMAP.md` 第17行、第19行 | 同上 | 已核对，未改 |
| ARCHITECTURE | 无正文修改。第21行仍写布局和路由继续本卡。地址补充写在会话契约 | `docs/ARCHITECTURE.md` 第21行；`docs/architecture/application-session-contract.md` | 同上 | 已核对 |
| TASK_BOARD | 有影响。T001 改为 in-review。T008 与 AI-02 保持 in-review。完成数为 343 项：18 done、3 in-review、7 in-progress、266 planned、49 blocked、0 ready | `docs/TASK_BOARD.md` | 同上 | 已提交复核 |
| PROJECT_STATUS | 有影响。共同底座改为 in-review。保留 MySQL 8 决定 | `docs/PROJECT_STATUS.md` | 同上 | 已提交复核 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、验证和同步表 | `docs/DOCUMENT_INDEX.md` | 同上 | 已提交复核 |
| PROJECT_BRIEF | 无正文修改。第30行排期仍是 18 done、2 in-review、8 in-progress，并写 T001 底座开工。第68行仍写接下来补布局组件。未签收前不改 brief | `docs/PROJECT_BRIEF.md` 第30行、第68行 | 同上 | 已核对，未改 |

治理块保持 g1.1 / 2026-10-11 / ISSUE-007。参考原文不改。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | pro-layout-7.22.7 / in-review | 已加入依赖并记录体积。等待项目经理 QA 签收，不标 done | [验证](../docs/testing/2026-10-12-prolayout-routes.md) |

## 本地验收与后续合入发布

- 本地复核材料已提交，日期 2026-10-12。这不是项目经理签收。
- 构建体积和前端 77 项、后台 293 项见验证记录。三断点浏览器截图未做。
- 六份基线已按上表核对。PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF 未改正文。
- PR 状态：不新建 PR。PR #3 仍待合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
