为什么有这个文件：记录QA对APP-M2-T008（ISSUE-012）与AI-02（ISSUE-011）的独立复核签署。

它解决什么问题：卡片转done前须有QA独立复跑与基线核对证据；记录发现的同步缺口，供项目经理决定。

# QA签署复核（2026-10-12）

ISSUE-013 / REV-M0-T05；执行人成长测试QA；复核HEAD `0c60842`。环境：Linux、Python 3.13.5、Node v24.9.0、pnpm 11.25.0。只读复核，未改两张卡的代码或状态。

## A. APP-M2-T008 / ISSUE-012 离线CI（cf2c2a1、af2f81c）——签署：通过（附2项文档缺口）

工作流`.github/workflows/offline-check.yml`：push/PR到`codex/repository-foundation`；`permissions: contents: read`；无secrets、无内网地址；Python 3.13.5、Node 24.9.0、pnpm 11.25.0；backend作业跑`pytest tests/backend`、`session_live_http.py`、`smoke_t06.py`；frontend作业`pnpm install --frozen-lockfile`、`pnpm build`（tsc -b && vite build）、`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`；governance作业跑governance/prototype/workspace-sync/demo-page四组.cjs及治理检查。覆盖要求齐全。

| Actions运行 | 提交 | 结论 | 实际计数 |
|---|---|---|---|
| [38200746746](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38200746746) | cf2c2a1 | 成功 | pytest 262；会话15/15；smoke_t06 passed；前端72/72；.cjs 35/35；治理通过 |
| [38201144235](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38201144235) | af2f81c | 成功 | 同上 |
| [38201502827](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38201502827) | 0c60842 | 成功 | pytest **292**（含新30项模型测试）；会话15/15；smoke_t06 passed；前端72/72；.cjs 35/35；治理通过 |

日志确认各步骤实际执行并输出计数，无失败步骤。注释仅有警告：checkout/setup-*等v4动作基于Node 20已弃用；`ubuntu-latest`将于2026-10-19迁至Ubuntu 26。

## B. AI-02 / ISSUE-011 OpenAI兼容适配器（0c60842）——签署：通过（附1项文档缺口）

| 核对项 | 证据 | 结论 |
|---|---|---|
| 默认关闭 | `create_app(use_configured_model=False)`默认；仅`ICG_MODEL_PROVIDER=openai-compatible`时构造；否则返回None保留替身 | 符合 |
| 失败502 | 适配器抛ModelUnavailable；`workflow.py:714`、`domain.py:454`映射502 `MODEL_UNAVAILABLE`，两文件自4e1cd6b起未改 | 符合 |
| 敏感项目仅本地 | `domain.py:211`判断`is_local`未改；`test_reference_boundaries.py`在全量中通过 | 符合 |
| 无新依赖 | `git diff 4e1cd6b HEAD -- backend/bid-core/requirements.txt`为空；只用已有httpx | 符合 |
| 测试无网络 | 测试注入`httpx.MockTransport` | 符合 |

## 本地复跑（HEAD 0c60842）

| 命令 | 结果 |
|---|---|
| `python -m pytest tests/backend/test_openai_compatible_model.py -q` | 30 passed |
| `python -m pytest tests/backend -q` | 292 passed，1条既有弃用提示 |
| `python tests/backend/session_live_http.py` | TOTAL 15 PASS 15 |
| `cd backend/bid-core && python smoke_t06.py` | passed，退出0 |
| `pnpm --dir frontend/web install --frozen-lockfile && pnpm --dir frontend/web build` | 通过 |
| `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | 72/72 |
| `node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs` | 35/35 |
| `node scripts/check-project-governance.cjs` | 通过：138份Markdown、342项任务、14项Issue |

## 基线差异核对

| 提交 | 文件 | 实际改动 | 同步表是否登记 |
|---|---|---|---|
| cf2c2a1/af2f81c | PROJECT_BRIEF | 维护日期改10-12、加ISSUE-012关联、排期计数改为340/18done | **未登记**（ISSUE-012-sync无BRIEF行） |
| cf2c2a1 | WORKFLOW | 验收节补CI命令入口，治理块未变 | 已登记 |
| 0c60842 | ROADMAP | 计数改342/19done/49blocked，新增AI-01/AI-02说明 | 已登记（ISSUE-010、011） |
| 0c60842 | ARCHITECTURE | 新增10-12段：可选适配器、默认替身、502、库未选 | 已登记（ISSUE-010、011） |
| 0c60842 | PROJECT_BRIEF | 排期计数改342/19done，加AI-01/AI-02 | **未登记**（ISSUE-010/011同步表无BRIEF行） |

治理块：PRD、ROADMAP、ARCHITECTURE、issues/index、WORKFLOW均为g1.1 / 2026-10-11 / ISSUE-007，彼此一致，与WORKFLOW相同。

## 缺陷与建议

| 编号 | 现象 | 严重度 | 建议负责人 |
|---|---|---|---|
| S1 | ISSUE-012同步表未列PROJECT_BRIEF改动 | P3 | DevOps |
| S2 | ISSUE-010/011同步表未列PROJECT_BRIEF改动 | P3 | AI |
| S3 | BRIEF排期格重复写“T008离线CI已本地验收” | P3 | DevOps |
| S4 | 两卡在QA签署前已自标done/closed | 流程 | 项目经理 |
| S5 | Actions使用基于Node 20的v4动作；`ubuntu-latest`将迁Ubuntu 26，建议固定`ubuntu-24.04`并升级动作 | P3 | DevOps |

签署：两卡功能与验收证据通过，建议项目经理在S1～S3补齐后确认done；QA未自行修改其卡片状态。
