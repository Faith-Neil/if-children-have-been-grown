为什么有这个文件：登记投标技术方案主路径的收口。

它解决什么问题：编写人不再穿过十个页签，也不再自己写响应正文。

# ISSUE-048：简化投标技术方案流程

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-048 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-progress |
| 登记日期 | 2026-11-04 |
| 最后更新日期 | 2026-11-05 |
| revision | flow-3role-1 |
| 关联 Task | [FLOW-3ROLE](../docs/tasks/FLOW.md#flow-3role)，in-review。不标 done |
| 关联 PR | 未创建 |
| 本地验收 | 2026-11-04：前端 `pnpm --dir frontend/web test` 598 项通过。后端角色、会话、技术分册与社保覆盖用例在内存仓储通过。未在浏览器点选。未在 `ICG_REQUIRE_MYSQL=1` 的真实库重跑。未声称生产 RAGFlow 已接通 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [FLOW-3ROLE](../docs/delivery/FLOW-3ROLE.md) |
| 代码 / 流程解释 | [FLOW-3ROLE](../docs/code/FLOW-3ROLE.md) |
| 验证记录 | 见交付说明。参考原文 [PRD v1.8](../docs/reference/product/prd-mvp-v1.8.md) 不改 |

## 现象与证据

编写人要穿过十个项目页签，并在响应矩阵里手写「我方响应要点」。没有检索命中时，系统会写成「无偏离。按本次招标文件响应……」。项目事实表单独占一页。管理入口写着只读，已保存的项目规则覆盖没有进入检查。登录角色仍是八个，种子账号 `admin` 可以打开投标正文。

## 影响与分流

- 影响登录角色、项目页签、矩阵正文、事实展示和项目规则覆盖。参考原文 PRD v1.8 不改。
- 废标红线目录仍然全部不可关闭。不新增公司级总开关。
- 不把本 Issue 标 closed，不把任务标 done。
- 2026-11-04 补充：普通用户可以查看本公司知识库，不能上传、停用、删除或修改连接。没有任务指定时使用管理员添加的模型，不再自动使用「默认内网模型」。
- 2026-11-05 补充：`.doc` / `.docx` 先转成 PDF 再交给 RAGFlow DeepDOC。直接上传 Word 时没有版面位置，条款会挤在第 1 页。这种结果可以再抽取，不再被「已经抽取过」拦住。
- 2026-11-05 补充：分析页整页可以往下滚动。解析区仍占一屏，矩阵统计卡和事实表不再被裁在视口外。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| FLOW-3ROLE | 三个登录角色、四段项目路径、检索生成响应、事实嵌入分析、检查读取项目覆盖 | `frontend/web/src`、`backend/bid-core/icg` | 见交付说明 | in-review |

## 与参考原文的差异

参考原文仍写八个登录角色和单独的响应矩阵、项目事实表。活动说明改在 `docs/PRD.md`、`docs/ARCHITECTURE.md`、`docs/ROADMAP.md` 和 `docs/architecture/application-session-contract.md`。
