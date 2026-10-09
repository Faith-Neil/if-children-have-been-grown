# ISSUE-002：原型编辑锁未阻止 AI Diff 确认写入

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-002 |
| 类型 | bug |
| 优先级 | P1 |
| 登记日期 | 2026-10-09 |
| 状态 | closed |
| revision | bug-r1；本轮跟踪格式 g1.0 |
| 最后更新日期 | 2026-10-09 |
| 本地验收 | 通过；2026-10-09，6 项回归 |
| PR / 合入 / 发布 | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 待合入 / 未合入 / 未发布 |
| 关联任务 | FE-M0-T01；[任务看板](../docs/TASK_BOARD.md) |
| 交付说明 | [FE-M0-T01](../docs/delivery/FE-M0-T01.md)；保留 [首轮原交付](../docs/delivery/2026-10-09-repository-foundation.md) |
| 代码解释 | [FE-M0-T01](../docs/code/FE-M0-T01.md) |
| 影响路径 | prototypes/bidding-ux/app.js、index.html |
| 复现依据 | 原脚本的 confirm-diff 处理器直接改写段落；锁定只设置 contentEditable=false |

## 现象与影响

先打开 AI Diff，再开启演示编辑锁，确认 Diff 仍能改写段落。即使页面正文不能手输，确认按钮的脚本写入仍绕过只读状态。该缺陷破坏原型所演示的编辑锁约束。

## 本轮方案

只读时禁用相关写入交互，并在 Diff 确认处理器再次检查当前编辑状态。接管必须有理由，恢复编辑后才允许写入。本轮仅修原型，不宣称实现服务端编辑锁。

## 验收

- 锁定期间点击生成/写入操作不能改正文。
- 锁前打开的 Diff，锁定后确认仍不能写入。
- 空理由不能接管；有效理由接管后可恢复确认写入。
- 原型整体移动后资源仍存在，JavaScript 语法正常。
- 回归验证执行实际 app.js 事件处理器，不以实现镜像替代。

## 基线同步

本次修复不改变产品范围、技术选型、API、数据模型或产品路线图；现有前端三件套无语义变化。项目状态、目录方案、文档索引、测试和交付记录已按首轮维护同步。首轮验收时 TASK_BOARD 尚不存在；治理 ISSUE-003 后续建立任务看板并以 FE-M0-T01 登记历史修复，不追溯宣称旧看板已存在。

| 基线 | 本次 bug impact 与更新路径 | revision / Issue ID / 日期 | 同步结论 |
|---|---|---|---|
| PRD | 无影响：修复原型已有只读约束，`docs/PRD.md` 产品范围不变 | bug-r1 / ISSUE-002 / 2026-10-09 | 无语义更新 |
| ROADMAP | 无影响：不增删阶段、范围或交付承诺，`docs/ROADMAP.md` 原计划不变 | 同上 | 无语义更新 |
| ARCHITECTURE | 无影响：实现已有锁定约束，不改变 `docs/ARCHITECTURE.md` 模块、接口或服务设计 | 同上 | 无语义更新 |
| TASK_BOARD | 有影响：首轮缺少看板；治理建立后以 FE-M0-T01 登记历史修复事实 | 本次治理由 ISSUE-003 / g1.0 / 2026-10-09 承接 | 待新看板入口核对 |
| PROJECT_STATUS | 有影响：`docs/PROJECT_STATUS.md` 首轮维护记录锁缺陷修复与静态原型限制 | bug-r1 / ISSUE-002 / 2026-10-09 | 已同步首轮事实 |
| DOCUMENT_INDEX | 有影响：`docs/DOCUMENT_INDEX.md` 登记首轮 Issue、验证与交付 | 同上 | 已同步首轮入口 |

## 代码解释与互链

实际修改位于 [app.js](../prototypes/bidding-ux/app.js)：只读切换同时禁用写入控件，Diff 确认前重新检查编辑状态，撤销/重做也遵循编辑锁。新增禁用样式位于 [styles.css](../prototypes/bidding-ux/styles.css)。这只修复本地演示，不实现服务端锁或持久化；独立解释见 [FE-M0-T01](../docs/code/FE-M0-T01.md)。

关联 [回归验证](../tests/prototype/editor-lock.test.cjs)、[测试记录](../docs/testing/2026-10-09-repository-foundation.md)、[FE-M0-T01 交付](../docs/delivery/FE-M0-T01.md)、[首轮原交付](../docs/delivery/2026-10-09-repository-foundation.md) 与 [任务看板](../docs/TASK_BOARD.md)。后续浏览器验收、PR 合入与发布记录由根维护者追加，当前不据 closed 宣称这些步骤已完成。

## 验收记录

2026-10-09：6 项实际 app.js 事件回归全部通过，覆盖锁前打开 Diff / 锁后确认、只读期间生成与编辑命令、空理由拒绝接管、有效理由恢复以及原型资源。JavaScript 语法检查通过，详见 [测试记录](../docs/testing/2026-10-09-repository-foundation.md)。本次关闭表示本地验收完成，合入与浏览器验证状态分别记录，不等同于服务端锁已实现。
