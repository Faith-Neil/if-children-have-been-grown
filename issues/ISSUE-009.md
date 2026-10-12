为什么有这个文件：登记完整资料库实施前必须补齐的会话、导航和共同页面底座。

它解决什么问题：避免在缺少可信权限、页面地址和元数据组件时，把通用文字弹窗当作完整示例。

# ISSUE-009：ICG共同页面底座与资料库前置

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-009 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-review |
| 登记 / 更新日期 | 2026-10-11 / 2026-10-12 |
| revision | application-foundation-1；本轮 layout-review-1 |
| 关联 Task | APP-M2-T001；APP-M2-T002；后续T003、T005、T006、T014～018、T046～050 |
| 关联 PR | [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3)，待合入 |
| 本地验收 | QA 于 200a105 签署不通过。D1–D4 与 D6 修复后重新提交 in-review。T002 请求层前端 90 项通过，同样等待项目经理签收。阶段一262后台、72前端、16真实HTTP及GUI仍为历史证据 |
| 合入 / 发布 | 未合入 / 未发布 |

## 当前缺口与完整范围

开工前页面缺少`getSession`可信会话入口；会话与页面守卫已经接入。ProLayout、浏览器地址和编辑台未保存离开已提交复核，仍缺元数据表格/表单、完整敏感查看和资料治理。APP-M2-T046/047依赖T005、T006、T017，这些前置尚未验收，不能标ready。根前置T001依赖BE-M0-T01已本地验收。本 Issue 保持 in-review，不标 closed。

T001完整范围保留原交接M1-P08-01：实际ProLayout并保留ICG布局、浏览器地址及返回导航、可信会话与菜单/页面守卫、公司与项目资源权限、统一请求失败和未保存离开保护。先实现会话契约及服务端导航，再接路由和布局；任何阶段结果不能把整个T001或OIDC、细粒度权限、完整资料库提前标done。

原8角色及角色叠加按PRD2.2/2.3细矩阵；当前三种演示角色不是完整生产权限。身份仍为合成演示，会话接口明确返回模式和实际角色映射，不把公司经理默认提升为公司管理员。平台默认无公司正文权限；集团只读且无生成/检索/导出；公司和项目范围由后台身份决定。写作档案设计规范的“其他只读”与PRD具体矩阵不一致，执行具体矩阵并单列差异。

## 阶段一实际结果

getSession已真实实现并由页面消费；实际OpenAPI49路径57操作。后台当前身份重读、参数拒绝及最小资源响应通过；页面按后台导航/动作读取公司集合，项目session先于workspace。独立复核发现的缓存项目权限、拒绝后迟到资料读取及连续页签竞态已修复并实际复核。最终GUI经理/只读导航、快捷403与两册内部稿记录通过，末次只调整准确提示并重新构建/页面复验。

后台262项、会话33专项、前端72项（会话14专项）、真实会话HTTP16项通过；4张截图及真实两册文件内容证据见[验证](../docs/testing/2026-10-11-application-session.md)，调用关系见[代码解释](../docs/code/APP-M2-T001.md)，[阶段交付](../docs/delivery/APP-M2-T001.md)保留完整剩余。网络/角色降级竞态仅函数与实际App调用验证；正式Word版式及完整八角色业务仍未完成。URL、ProLayout 和编辑台离开保护已提交复核，Issue 与 T001 为 in-review，不能标 done 或 closed。

## 验收要求

- 会话仅从Bearer身份获取，不信任客户端角色、账号或公司；坏/过期会话401，未知角色拒绝。
- 原角色菜单映射、无权地址不读取业务正文；跨公司及同公司未入项目拒绝且不暴露数据。
- 实际使用ProLayout，三断点保留原侧栏、顶栏、摘要和页签；页面深链接刷新/前后导航/登录后回原目标。
- 未保存取消离开时地址、页面和文字保留；401/403/409明确显示，T16版本核对与迟到公司读取保护继续有效。
- 类型/构建、必要实际函数/HTTP/GUI和原主流程回归；真实身份供应商与T010单独验收。

## 基线同步

| 基线 | 影响 / 处理 | 状态 |
|---|---|---|
| PRD | 原ICG功能不缩减；可信角色阶段与完整共同底座分列 | 阶段同步 |
| ROADMAP | 资料库前完整T001，按真实依赖继续 | 阶段同步 |
| ARCHITECTURE | 新可信会话/导航契约及49路径57操作；布局、路由及元数据后续接入 | 阶段同步 |
| Issue / TASK_BOARD | 009与T001改为 in-review；ISSUE-014 登记依赖。完整C01等仍planned。done/closed 留给项目经理 | 已提交复核 |
| PROJECT_STATUS / BRIEF | PROJECT_STATUS 改为 in-review。PROJECT_BRIEF 未改正文，见下方同步表 | 已核对 |
| DOCUMENT_INDEX | 本Issue、契约、实际模块/专项、交付和4截图登记 | 阶段同步 |
| WORKFLOW | 无规则变化，保持g1.1 / ISSUE-007治理块 | 已核对 |

逐阶段交付保存`docs/delivery/APP-M2-T001.md`，实际代码解释保存`docs/code/APP-M2-T001.md`；未执行或未完成明确记录。完整产品ISSUE-007保持进行中。

## 本轮提交复核（不标 done）

页面使用已批准的 `@ant-design/pro-layout@7.22.7`，没有引入 `react-router`，也没有改用整包 `@ant-design/pro-components`。设计规范写的是 pro-components；本轮改用它所依赖的同一版 ProLayout，避免带上 ProTable 和 ProForm。体积见 [ISSUE-014](ISSUE-014.md)。地址用 History API：全局路径与 `/projects/:projectId/:tab` 可深链接，登录后回到原地址，未知地址显示 404 且不读取工作区。编辑台未保存时，站内切换、前进后退和刷新/关闭都会拦截；取消后地址、页面和文字保留。401 退出不弹离开确认。

未纳入本轮、也不能标 done 的范围：OIDC（T010）、原八角色业务迁移、请求层细化（T002）、元数据表格/表单（T005/T006）、通用表单离开条（T007）、断点记忆（T009）、三断点实机截图、Word 视觉。PR #3 仍未合入，产品未发布。

## 未改基线的同步

本轮没有修改 `docs/PRD.md`、`docs/ROADMAP.md`、`docs/ARCHITECTURE.md`、`docs/PROJECT_BRIEF.md` 的正文，也没有改治理块。它们仍写整卡未完成，与 in-review、尚未由项目经理标 done 一致；其中“接下来补 ProLayout”已过时，以本 Issue 和任务看板为准。

| 文件 | 仍在的句子 | 不改的原因 |
|---|---|---|
| `docs/PRD.md` 第19行 | T001共同底座已开工，其余258卡planned | 本卡未 done。活状态在任务看板：T001 为 in-review，其余 257 张 APP-M2 卡 planned |
| `docs/PRD.md` 第21行 | 整个T001、OIDC和完整资料库仍未完成 | 本卡未 done，这句话仍然成立 |
| `docs/ROADMAP.md` 第17行 | 当前共343项任务，18done、8in-progress、2in-review；AI-02 与 T008 为 in-review | 路线图正文不改。活的计数在任务看板：343 项，18 done、3 in-review（T001、T008、AI-02）、7 in-progress |
| `docs/ROADMAP.md` 第19行 | 整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护 | 协作要求非必须不改路线图。实现已提交复核，但项目经理尚未签收，所以不把路线图改成完成 |
| `docs/ARCHITECTURE.md` 第21行 | 布局、浏览器路由和全页离开保护继续本卡 | 架构正文不改。会话契约 `docs/architecture/application-session-contract.md` 已补上实际地址 |
| `docs/PROJECT_BRIEF.md` 第30行 | 排期仍写 18done、2in-review、8in-progress，并写 T001底座开工 | brief 排期行是 ISSUE-010 刚登记的 MySQL 8 快照。本轮不改 brief |
| `docs/PROJECT_BRIEF.md` 第68行 | 整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护 | brief 不改。接手说明仍把本卡当作未签收是对的 |

`docs/PROJECT_STATUS.md`、任务看板、文档索引和本 Issue 已改为 in-review。同步细节见 [ISSUE-014 同步](../docs/governance/ISSUE-014-sync.md)。

## QA 退回后的修复（仍不标 done）

签署记录 [2026-10-12-e2e-t001-signoff.md](../docs/testing/2026-10-12-e2e-t001-signoff.md) 的结论保持不通过。本轮把内容区改回浅色，把公司、用户和退出放回白顶栏，并按历史序号恢复前进/后退，不再用 `pushState` 截断前进记录。演示会话只在内存：刷新后需重新登录，登录后回到原地址；确认刷新会丢失未保存文字。D5 不在本轮。证据见 [布局与历史修复](../docs/testing/2026-10-12-t001-layout-history.md)。Playwright 11 项通过。Issue 与 T001 仍为 in-review。

| 文件 | 仍在的句子 | 不改的原因 |
|---|---|---|
| `docs/PRD.md` 第19行 | T001共同底座已开工，其余258卡planned | 本卡未 done。活状态在任务看板 |
| `docs/PRD.md` 第21行 | 整个T001、OIDC和完整资料库仍未完成 | 本卡未 done，这句话仍然成立 |
| `docs/ROADMAP.md` 第17行 | 当前共354项任务，21done、7in-review、7in-progress、265planned、50blocked、4ready | 路线图正文不改。活的计数在任务看板：356 项，23 done、6 in-review |
| `docs/ROADMAP.md` 第19行 | 整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护 | 实现已再次提交复核，项目经理尚未签收 |
| `docs/ARCHITECTURE.md` 第21行 | 布局、浏览器路由和全页离开保护继续本卡 | 架构正文不改 |
| `docs/PROJECT_BRIEF.md` 第30行 | 当前共356项：23done、6in-review、7in-progress、266planned、50blocked、4ready | brief 排期行不改 |
| `docs/PROJECT_BRIEF.md` 第68行 | 整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护 | brief 不改。接手说明仍把本卡当作未签收 |

同步表见 [布局修复同步](../docs/governance/APP-M2-T001-layout-sync.md)。

## 请求层（仍不标 done）

APP-M2-T002 按 `cba6282` 冻结的错误体和幂等约定提交 in-review。`/api/v1` 读取 `{code, message, details, traceId}`，旧 `/api` 读取 `{error, request_id}`，响应头 `X-Request-ID` 优先。同一次写入只使用一把 `Idempotency-Key`。自动重试只覆盖网络错误、没有统一错误体的 502（网关）和 503，并复用该键，最多 3 次（含首次）。带 `code: MODEL_UNAVAILABLE` 的 502 不重试，页面立刻显示追踪号。409、422、423、428、401 和 500 也不自动重试。`POST /api/chapters/{id}/versions` 的请求头与正文 `idempotency_key` 相同，避免服务端因两处不一致返回 409。证据见 [请求层验证](../docs/testing/2026-10-12-request-layer.md) 与 [交付](../docs/delivery/APP-M2-T002.md)。上文「未纳入本轮」里的请求层细化指布局那一轮；本段起 T002 单独提交复核。Issue 与 T001、T002 仍为 in-review。更早几节引用的 258 卡和 356 项是当时留下的旧句；任务计数现由 ISSUE-026 写成看板的 361 项。

| 文件 | 句子 | 处理 |
|---|---|---|
| `docs/PRD.md` 第19行 | 项目共361项：26done、6in-review、7in-progress、268planned、50blocked、4ready。其余255卡planned | 计数已由 ISSUE-026 改成看板数字。T001 与 T002 仍未 done |
| `docs/PRD.md` 第21行 | 整个T001、OIDC和完整资料库仍未完成 | T001 未 done，这句话仍然成立 |
| `docs/ROADMAP.md` 第17行 | 当前共361项任务，26done、6in-review、7in-progress、268planned、50blocked、4ready | 计数已由 ISSUE-026 改成看板数字 |
| `docs/ROADMAP.md` 第19行 | 整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护 | 这句不是任务总数。布局已提交复核，项目经理尚未签收，所以保留 |
| `docs/ARCHITECTURE.md` 第21行 | 布局、浏览器路由和全页离开保护继续本卡 | 架构正文不改 |
| `docs/PROJECT_BRIEF.md` 第30行 | 当前共361项：26done、6in-review、7in-progress、268planned、50blocked、4ready | 计数已由 ISSUE-026 改成看板数字 |
| `docs/PROJECT_BRIEF.md` 第68行 | 整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护 | 这句不是任务总数。接手说明仍把底座当作未签收 |

同步表见 [请求层同步](../docs/governance/APP-M2-T002-sync.md)。
