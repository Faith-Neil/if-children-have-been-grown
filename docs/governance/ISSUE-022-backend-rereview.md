为什么有这个文件：留下大纲契约的后台复审原文，以及项目经理随后拍板的两条决定。

它解决什么问题：让 ISSUE-022 能指向同一次复审，而不是把决定散落在对话里。

# ISSUE-022 契约修订复审（046f8e5、fe9582c，只读）

对照：上次评审 `/workspace/issue022-review.md`（基于 16e0b9e）和后台冻结契约。行号按 fe9582c 上的 `spec/openapi/demo-v1.json` 和 `docs/governance/ISSUE-022-t078-plan.md`。fe9582c 只改文档（记录 rebase 后的检查结果），契约改动都在 046f8e5。本地没复跑测试。

## 结论
**基本可以冻结，但先补 3 处（B1–B3），不需要再整轮评审。** 上次 14 项必改里，12 项已解决，2 项部分解决。剩下的阻断都和 startGeneration 有关：模型配置的错误码和快照，以及锁（423）。T078 方案可以按现稿实施，只差一句 ETag。

## 评审一（spec）逐项
| # | 上次问题 | 结论 | 证据 |
|---|---|---|---|
| 1 | JobStatus 继承 Job | **已解决** | `demo-v1.json:18263` JobStatus 单独定义，不继承 Job，status 为 queued/running/completed/failed/cancelled；已实现的 Job 没动（`:13815` recoverable 仍是 const false）。小问题：JobStatus 没有 `recoverable` 字段，见 N4 |
| 2 | 事件没有序号，不能续传 | **已解决** | `:18186` JobEvent 必填 seq、id（`<job_id>:<seq>`）、occurred_at，type 是枚举；`:11972` streamJobEvents 是 text/event-stream（`:12022`），`:11992` 有 Last-Event-ID |
| 3 | 缺取消接口 | **部分解决** | `:12112` cancelJob 已加，带 Idempotency-Key。但任务已经结束时，返回 200 和当前状态，不是我上次建议的 409。这个做法也行（幂等），但要在 BE-M0-T06 里定死，前端按 200 加 status 判断。我接受，不阻断 |
| 4 | getJob 路径和权限 | **已解决** | `:11842` 路径参数是 `{job_id}`；描述写明不属于本公司或本项目的任务一律 404，不区分不存在和无权 |
| 5 | 错误响应按操作列 | **已解决** | getOutlinePlan 去掉了 413/423/428/502；getJob 去掉了 409；502 只留在 startGeneration；confirmOutlinePlan 去掉了 502 |
| 6 | 确认接口有两个版本号 | **已解决** | `:11354` 描述：If-Match 对应整份计划的 revision，不符返回 409 VERSION_CONFLICT；expected_revision 对应章，不符返回 409 PLAN_STALE；`:11252` GET 200 必带 ETag；没有 fingerprint 字段 |
| 7 | startGeneration 的 If-Match 和幂等 | **已解决** | `:11589` 描述写了 If-Match 比对的对象、409 和 428；同键重放返回同一个 job id、同一个 Location 和 202；202 带 Idempotent-Replayed 和 Location（`:11686`） |
| 8 | 和旧路由重叠 | **已解决** | 旧的 plan/confirm（`:3519`）、plan（`:6676`）、generate（`:6955`）都标了 `deprecated: true`，描述写明新旧并存，前端切换后由后续 Issue 删除。注意：运行时还没标 deprecated，比对时由探针去掉这个标记（046f8e5 改了 `test_error_idempotency.py` 和 `qa_error_idempotency_live_http.py`，各加 11 行），QA 要知道这一点 |

## 评审二（T078 方案）逐项
| # | 上次问题 | 结论 | 证据 |
|---|---|---|---|
| 1 | 路由被抢先匹配 | **已解决** | `t078-plan.md:43-45` 改用 `/api/v1/snippet-publications`，不依赖注册顺序 |
| 2 | 独立 Protocol | **已解决** | `:19`、`:29-39`，每个方法都显式带 company_id；内存实现在 snippet_publication.py（`:25`） |
| 3 | 幂等作用域 | **已解决** | `:63` scope 是 `library:{company_id}`，同键不同指纹返回 409，缺失返回 428 |
| 4 | If-Match 语义 | **部分解决** | `:65-74` PUT 和 publish 比对 draft_revision，sync 比对 published_revision，428 和 409 都写了。**还缺：GET 详情要返回 ETag**，否则客户端拿不到 If-Match 的值。补一句就行，不阻断 |
| 5 | 被拦截时的写入 | **已解决** | `:71`、`:80`、`:90` 被拦截时返回 200，原因只在响应里，records 和 audits 都不变。我建议补一句：被拦截的 200 算成功，会登记幂等回执，同键重放还返回这次的结果 |
| 6 | 接口不全 | **已解决** | `:67` 加了 POST 创建，服务端分配 id；`:69` 删掉了 `GET .../sync` |

## 新问题
- **B1（P1，阻断冻结）startGeneration 没有模型配置相关的错误和快照**：`:11589` 只写了 502 MODEL_UNAVAILABLE。按 ISSUE-024，启动任务时会出现 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（敏感项目配了非本地模型）和 503 `SECRET_KEY_UNAVAILABLE`（没有主密钥，无法解密 key），而且“任务启动时快照模型配置”也要写进描述，并说明 JobEvent 里的 provider/model/is_local 取自这份快照。这两个码还没进冻结码表，正在和 AI bot 对齐。做法：ISSUE-024 先登记这两个码，这里只引用、不定义；或者冻结时先写明“由 ISSUE-024 补充”，并在 startGeneration 的响应里预留 403 和 503。ISSUE-028 只管提供方一侧，这里也不要重复定义模型配置字段。
- **B2（P2，阻断冻结）锁（423）去掉了**：码表里 423 是 LOCK_HELD 和 LOCK_LOST（`:18501`），旧的 generate 和 plan/confirm 都有 423。confirmOutlinePlan 和 startGeneration 现在没有 423。要定下来：章被别人锁住时，确认和生成是 423 还是忽略锁。我建议保留 423 LOCK_HELD。
- **B3（P2，阻断冻结）SSE 事件类型只有 `job.model_call`**（`:18186`）：只靠这一类事件，前端看不到状态和进度变化，也收不到结束事件，最后还得回去轮询。建议枚举里加 `job.status`（带 status、progress）和 `job.completed`/`job.failed`/`job.cancelled`（或者一个带最终状态的 `job.finished`）。如果字段没定，就先在描述里写“BE-M0-T06 扩充”，只要枚举能扩展就行。
- **N4（P3）** JobStatus 没有 `recoverable` 字段。可恢复任务设计里有这个字段，建议加上 boolean，或者写明交给 T06。
- **N5（P3）** cancelJob 的 200 响应要求 Location（`:12183`），没必要，建议去掉或改成非必填。
- **N6（P3）** getJob 和 streamJobEvents 保留了 403，但描述说无权一律 404。要写明 403 只在角色不够时出现（例如没有读任务的权限），否则就删掉。

## 冻结检查清单（都已满足）
错误体 `{code,message,details,traceId}`；Idempotency-Key 的描述和冻结版一致；If-Match/ETag 都对应 revision；202 + Location + 轮询/SSE + Last-Event-ID；草案状态值没改（`x-contract-drafts` 在 `:18556`），探针照样会去掉草案路径。冻结时，把状态值的修改和实现放进同一个提交，这一条仍然有效。

## 判定
B1–B3 补完就可以冻结。可以在同一个小提交里补，我复核差异就行。T078 方案现在可以动工，实施时补上 GET 的 ETag。

---

## 第三轮：复核 c6948c0（只看这个提交的 diff，只读）

行号是 c6948c0 上的 `spec/openapi/demo-v1.json`，按 diff 的 hunk 起点推算，可能差几行。这个提交还改了 `tests/backend/test_outline_contract_draft.py`（+37/−3），给下面每一项都加了断言。本地没复跑测试。

| 项 | 结论 | 证据 |
|---|---|---|
| B1 两个码只引用 ISSUE-024 | **通过** | startGeneration 描述在约 `:11615`；403 描述在约 `:11732`，并列出 VOLUME_OWNER_REQUIRED 和 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；新增 503 响应在约 `:11875`。两处都写明“只引用 ISSUE-024，不在本文件的 V1Error 枚举或 x-error-status 中定义”，测试也断言两个码不在 enum 和 x-error-status 里。这里没有重复定义模型配置字段 |
| B1 快照 | **通过** | 约 `:11615` 写了“任务开始时对模型配置做快照，job.model_call 的 provider、model 取自快照”；JobEvent 描述在约 `:18206`，说法相同 |
| B1 503 不自动重试 | **通过（本条）**，但引出了 N7，见下 | 约 `:11875`：“不是瞬时故障，客户端不要自动重试，与 MODEL_UNAVAILABLE 相同” |
| B2 423 | **通过** | confirmOutlinePlan 描述在约 `:11362`，新增 423 响应在约 `:11586`；startGeneration 新增 423 在约 `:11857`；LOCK_HELD 和 LOCK_LOST 都列了，和旧路由一致 |
| B3 SSE 事件类型 | **通过** | 约 `:18226` 的枚举加了 job.status_changed、job.progress、job.completed、job.failed、job.cancelled；约 `:18269` 新增 payload，并写明每种类型带哪些字段；描述注明由 BE-M0-T06 实现 |
| P3 JobStatus.recoverable | **通过** | 约 `:18359` 是 boolean，约 `:18377` 列入 required，不继承 Job 的 const false |
| P3 cancel 不强制 Location | **通过** | 约 `:12206` 删掉了 required 的 Location，描述在约 `:12144` |
| P3 getJob 和 SSE 不列 403 | **通过** | getJob 的 403 删了（描述在约 `:11904`），SSE 的 403 也删了（约 `:12019`） |

### 这次带进来的新问题
- **N7（P2）全局重试规则和“503 不重试”冲突**：`info.description`（`:5`）和每个 Idempotency-Key 参数的描述（例如 `:1255`）仍然写着“客户端只对网络错误、502、503 复用本标记重试”，没有排除 MODEL_UNAVAILABLE（502）和 SECRET_KEY_UNAVAILABLE（503）。按全局规则，前端会自动重试，和 startGeneration 这里的说法正好相反。修法：全局规则加一句“例外：MODEL_UNAVAILABLE、SECRET_KEY_UNAVAILABLE 不自动重试”，或者改成“按 code 判断”。只改文字，可以和冻结状态值的修改放在同一个提交里。
- **N8（P3）job.model_call 的 6 个字段不再强制**：`required` 缩成 seq/id/occurred_at/type（约 `:18279`），model_call 事件缺 provider、model 等字段也能通过校验。建议用 `oneOf` 加 `discriminator: type`，或者 `if type == job.model_call then required[...]`，按类型分别要求字段。T06 实现前补上就行。
- **N9（P3）**：新增的 423 和 503 响应带了 `Idempotent-Replayed` 头。失败不登记回执，这个头不会出现。这是照抄已有写法，不影响行为，可删可不删。
- **提示**：403 和 503 的响应体引用 V1Error，但 V1Error.code 的枚举里没有这两个码。ISSUE-024 登记码表之前，严格按 schema 校验会失败。这是按引用定义的预期代价，条件是 ISSUE-024 必须在 startGeneration 实现前把这两个码写进码表和 x-error-status。

### 判定
**可以冻结。** B1–B3 和三项 P3 都通过了。N7 只改文字，要在冻结提交里一起修掉（否则前端 T114 会照全局规则去重试）。N8 和 N9 不阻断，T06 实现时处理。冻结时，状态值的修改仍然要和实现放进同一个提交，以免探针变红。

## 项目经理决定

- B2: keep 423 LOCK_HELD for locked chapter and LOCK_LOST for lost lock, same as legacy routes.
- B3: status-change, progress and terminal SSE event types are added to the contract now, implementation in BE-M0-T06.
