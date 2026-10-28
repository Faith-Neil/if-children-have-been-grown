为什么有这个文件：记录 2026-10-28 按代码实况重定任务看板的决定。

它解决什么问题：看板状态长期落后于代码（规则检查已实现仍为 planned、旧前端轨道整体 blocked、演示外壳卡仍 in-progress），用户指出看板过时，要求按实际理解调整。

# ISSUE-045：任务看板按代码实况重定

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-045 |
| 类型 | version |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) |
| 本地验收 | `node scripts/check-project-governance.cjs` 通过 |
| 合入 | 未合入 |
| 发布 | 未发布 |

## 依据

逐卡对照代码（`backend/bid-core/icg`、`frontend/web/src` 与测试）判定，状态括号内注明“2026-10-28 重定”与原因。不把任何卡直接标 done：done 仍要专属交付文档与用户验收。

## 决定

| 变化 | 卡 | 理由 |
|---|---|---|
| planned → in-review | APP-M2-T203～T210、T214～T225、T228、T229、T232～T234、T240、T242、T243、T252（R01～R20、R23～R28、R31、R32、R34、R35、R37 单卡） | `icg/domain/compliance_rules.py` 已有 `check_rXX` 与 `tests/backend/test_compliance_rules*.py` |
| planned → in-progress | T211～T213（R09）、T230～T231（R25）、T238～T239（R31） | 规则方法存在，子范围未逐项核 |
| planned → in-review | T037、T069、T076、T079、T095、T121、T149、T186 | 页面、接口与测试均已存在 |
| planned → in-progress | T011、T020、T029、T035、T036、T039、T042、T046～T048、T054～T056、T074、T075、T077、T082、T097、T101、T102、T105、T108、T110、T118、T119、T130、T134～T136、T141、T142、T145、T150～T152、T172、T173、T178、T202 | 部分实现 |
| blocked → cancelled | FE-M1～FE-M5、FE-M8 共 41 卡 | 旧前端轨道，范围已被 APP-M2 卡逐项覆盖（见 `docs/testing/icg-task-mapping.md`），保留历史 |
| in-progress/planned → cancelled | APP-M1-T01～T06、T08 | 演示外壳已按用户 2026-10-28 决定删除，真实链路由 APP-M2 与 Wave 11/12 卡承接 |

## 未动

- 仍为 planned 且代码确无的：OIDC/Keycloak（T010、T012、T013，生产走本地口令登录）、站内提醒（T030～T032）、模型配置版本/任务模型映射（T038、T040、T041）、PDF 定位（T103）、需求矩阵表（T112～T117）、确定性章节（T191～T194）、规则 R21、R22、R29、R30、R33、R36、R38～R44。
- 后端仍有旧 `/api/projects`、`/api/chapters` 路由，BE-M0-T09 保持 planned。

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 无影响 | 不改需求 |
| ROADMAP | 无影响 | 阶段不变 |
| ARCHITECTURE | 无影响 | 不改结构 |
| TASK_BOARD | 有影响 | 131 卡状态重定 |
| PROJECT_STATUS | 有影响 | 写入重定后计数 |
| DOCUMENT_INDEX | 有影响 | 登记本 Issue |
