# REV-M0：接手审查

日期：2026-10-09。治理修订：g1.1。此里程碑交付审查结果，不代表产品需求与技术栈已冻结。

<a id="rev-m0-t01"></a>

## REV-M0-T01 · 目录、业务与技术审查及接手brief

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 3小时，共同评审及缺件取得另计 |
| 关联Issue | [ISSUE-004](../../issues/ISSUE-004.md) |
| 依赖 | [FE-M0-T02](FE-M0.md#fe-m0-t02)；现有方案、参考文档与用户图片 |
| 来源 | [目录方案](../architecture/repository-layout.md)、[基线差异](../decisions/baseline-gaps.md)、用户接手要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T01.md) |
| 代码解释 | 无运行时代码；交付中解释审查方法和文档逻辑 |

范围：比较图片与真实文件，说明适用目录；以典型业务触发和前后端契约审查设计，不以文档/静态模拟冒充运行能力。为接手者交付可独立阅读的范围、现状、分支、风险、待定点与下一步。

步骤：并行业务/技术审查；复核证据与实现边界；更新目录方案；登记待决Issue；写brief和专属交付；同步看板/进度/索引。

- [x] 说明哪些文件/服务实际存在，图片目标与当前方案的差异可核对。
- [x] 主要场景覆盖与关键缺口有证据、后果、建议及可验证决策。
- [x] brief清楚区分已交付、未实现、待决定；不擅自关闭原有基线差异。
- [x] 无代码影响的理由、交付、Issue、进度与索引完成同步。

<a id="rev-m0-t02"></a>

## REV-M0-T02 · QA独立复跑与会话真实HTTP复核入库

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 2小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | [APP-M2-T001](APP-M2.md#app-m2-t001)会话阶段已有实现 |
| 来源 | [共同底座阶段验证](../testing/2026-10-11-application-session.md) |
| 完成交付 | [专属交付](../delivery/REV-M0-T02.md) |
| 代码解释 | [代码解释](../code/REV-M0-T02.md) |

范围：独立复跑后台、前端、构建、治理/原型/同步及真实HTTP冒烟；把会话实时HTTP检查作为可重跑脚本入库；不改应用代码。

- [x] 脚本自启后台、合成数据、15项通过，不进入默认pytest收集。
- [x] 各套件命令、环境、计数与局限记录在验证文档。
- [x] Issue、看板、进度、索引同步，治理检查通过。

<a id="rev-m0-t03"></a>

## REV-M0-T03 · APP-M1-T06端到端验收计划

| 字段 | 内容 |
|---|---|
| 状态 | done（项目经理评审通过；PR待合入） |
| 估算 | 2小时 |
| 关联Issue | [ISSUE-015](../../issues/ISSUE-015.md) |
| 依赖 | [APP-M1-T06](APP-M1.md#app-m1-t06)任务卡与现有测试 |
| 来源 | [APP-M1-T06](APP-M1.md#app-m1-t06)、[ICG主流程验证](../testing/2026-10-10-icg-reference.md) |
| 完成交付 | [专属交付](../delivery/REV-M0-T03.md) |
| 代码解释 | 无；仅计划文档 |

范围：编制T06验收计划，映射现有测试并标缺口；不执行T06验收、不改代码。

- [x] 端到端、Word版式、多角色、权限反例、过期数据五部分齐全。
- [x] 每项映射现有测试或标为缺口。
- [x] 项目经理评审通过（db246b0）。

<a id="rev-m0-t05"></a>

## REV-M0-T05 · APP-M2-T008与AI-02 QA签署复核

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1.5小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | APP-M2-T008、AI-02已提交 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T05.md) |
| 代码解释 | 无；仅复核记录 |

范围：只读复跑与基线核对，不改他人代码或卡片状态。

- [x] Actions与本地复跑计数记录。
- [x] 基线差异与同步表逐项核对，缺口登记。

<a id="rev-m0-t04"></a>

## REV-M0-T04 · T06贯通冒烟与Word渲染

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 3小时 |
| 关联Issue | [ISSUE-015](../../issues/ISSUE-015.md) |
| 依赖 | [REV-M0-T03](#rev-m0-t03)计划已评审 |
| 来源 | [T06验收计划](../testing/2026-10-12-app-m1-t06-acceptance-plan.md)缺口1、3 |
| 完成交付 | [专属交付](../delivery/REV-M0-T04.md) |
| 代码解释 | [代码解释](../code/REV-M0-T04.md) |

范围：新增自启服务的T06贯通冒烟；在QA机器渲染两册及SLA函并记录发现。不改应用代码，不判定T06完成。

- [x] smoke_t06退出0，E1～E7交叉核对通过。
- [x] 渲染PNG与结构发现记录，soffice仅QA机运行已注明。
- [x] Issue、看板、进度、索引同步，治理检查通过。

<a id="rev-m0-t07"></a>

## REV-M0-T07 · BE-M0-T02与BE-M0-T03 QA签署复核

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 2小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T02、BE-M0-T03已提交（cba6282） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T07.md) |
| 代码解释 | 无产品代码；QA探针脚本见交付 |

范围：复跑、独立真实HTTP探针与基线核对，不改他人代码或卡片状态。

- [x] Actions与本地复跑计数记录。
- [x] 错误体、状态表、幂等与页面回退探针47/47。
- [x] 测试差异、依赖与基线同步表核对，缺口登记。


<a id="rev-m0-t06"></a>

## REV-M0-T06 · Playwright浏览器端到端检查

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3小时 |
| 关联Issue | [ISSUE-019](../../issues/ISSUE-019.md) |
| 依赖 | [APP-M2-T001](APP-M2.md#app-m2-t001)本切片已提交 |
| 来源 | 项目经理批准ISSUE-019 |
| 完成交付 | [专属交付](../delivery/REV-M0-T06.md) |
| 代码解释 | [代码解释](../code/REV-M0-T06.md) |

范围：仅测试依赖Playwright（Chromium）；三宽度截图、离开确认、前进后退路由用例；不改应用代码。

- [x] 一条命令、<5分钟、合成数据。
- [x] 缺陷以test.fail记录。
- [ ] 项目经理确认done。

<a id="rev-m0-t08"></a>

## REV-M0-T08 · APP-M2-T001 QA签署复核

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 1.5小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | [REV-M0-T06](#rev-m0-t06)浏览器证据 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T08.md) |
| 代码解释 | 无；仅复核记录 |

范围：只读复跑、后台兜底路由与测试改动审查、基线同步核对、浏览器证据；签署结论。

- [x] 复跑与Actions核对。
- [x] 签署结论与缺陷记录。
- [ ] 项目经理确认done。

<a id="rev-m0-t09"></a>

## REV-M0-T09 · BE-M0-T08与BE-M0-T10 QA签署复核

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 2小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T08、BE-M0-T10已提交（7d97369） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T09.md) |
| 代码解释 | 无；仅复核记录 |

范围：复跑、真实MySQL 8.4迁移与门禁核对、密码泄露检查、依赖与基线核对，不改他人代码或卡片状态。

- [x] Actions与本地复跑计数记录。
- [x] 真实MySQL迁移往返、mysql用例与字符集核对。
- [x] 门禁失败、密码不泄露、依赖锁定与基线核对，缺口登记。

<a id="rev-m0-t10"></a>

## REV-M0-T10 · BE-M0-T15 Word 默认版式 QA 签署复核

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 3小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T15已提交（7428ec7） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T10.md) |
| 代码解释 | 无产品代码；QA检查器与样张见交付 |

范围：按用户确认原文独立核对导出 docx，LibreOffice 渲染，Word/WPS 留给用户确认；不改他人代码或卡片状态。

- [x] 独立检查器覆盖原文全部条目及 V1～V3、updateFields。
- [x] 四份导出与 h1 左对齐覆盖全部通过，样张入库。
- [x] LibreOffice 渲染与字体回退说明，Word/WPS 待确认项分栏登记。

<a id="rev-m0-t11"></a>

## REV-M0-T11 · APP-M2-T001与APP-M2-T002 QA复验签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 2小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | E2E-D7 `b74cde5`、T002-F1 `47fad10`、E2E-D8 `46ef36c` 已提交 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T11.md) |
| 代码解释 | 无产品代码；QA探针与扫描脚本不入库 |

范围：在修复提交上独立复跑单测、tsc、构建、E2E、请求层探针与对比度计算；签署结论。不改他人代码或卡片状态。

- [x] 复跑92/35、tsc、构建、E2E 13/13、治理与Actions核对。
- [x] 探针27/27（含F1逐场景请求计数）、对比度独立计算与页面扫描。
- [x] T001、T002签署通过；开发卡保持in-review待项目经理设置done。

<a id="rev-m0-t12"></a>

## REV-M0-T12 · BE-M0-T14 托管 MySQL CI QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1.5小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T14 `ac6ea02` 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T12.md) |
| 代码解释 | 无产品代码 |

范围：核对工作流与真实Actions日志，在本地MySQL 8.4独立复跑迁移往返与mysql测试，抽出守卫脚本做负例；签署结论。不改他人代码或卡片状态。

- [x] AC-01～04逐条核对，Actions成功与失败样例均查日志。
- [x] 本地upgrade/downgrade往返、mysql 2 passed、全套337 passed、守卫负例。
- [x] 签署通过；BE-M0-T14保持in-review待项目经理设置done。

<a id="rev-m0-t13"></a>

## REV-M0-T13 · ISSUE-026 基线快照规则 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-026 `c9a3cd5` 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T13.md) |
| 代码解释 | 无产品代码 |

范围：核对三份基线快照、规则落点、检查程序与模拟签收、CI。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] AC通过；看板独立重数366项（32/6/7/268/49/4）与快照一致；规则在ISSUE-026、同步表、WORKFLOW第4节；检查程序不比对快照；模拟签收AI-03仍通过；CI 38212117391全绿。
- [x] ISSUE-026保持in-review，待项目经理设置done

<a id="rev-m0-t14"></a>

## REV-M0-T14 · ISSUE-014 ProLayout依赖与体积 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-014 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T14.md) |
| 代码解释 | 无产品代码 |

范围：核对直接依赖、引入前后体积复现。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] AC-01、AC-02通过；直接依赖仅新增pro-layout 7.22.7；引入前后1334.42→1564.53 kB逐字复现。
- [x] ISSUE-014保持in-review，待项目经理设置done

<a id="rev-m0-t15"></a>

## REV-M0-T15 · ISSUE-020 路由分包 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-020 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T15.md) |
| 代码解释 | 无产品代码 |

范围：在当前HEAD重建，核对入口与全部产物体积、前端测试与E2E。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] AC-01～03通过；入口317.71 kB/gzip 101.64 kB，预加载合计1081.97 kB低于1334.42 kB；node --test 92/92、tsc、E2E 13 passed。
- [x] ISSUE-020保持in-review，待项目经理设置done

<a id="rev-m0-t16"></a>

## REV-M0-T16 · ISSUE-016 检索层内存骨架 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-016 / AI-03 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T16.md) |
| 代码解释 | 无产品代码 |

范围：核对检索协议、无依赖无连库、三路径回退与公司隔离，补失败探针，复跑后台全套。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] AC-01～05通过；契约7项、补充探针（越界记录、嵌入超时）均回退到A；后台349 passed/6 skipped(mysql)。
- [x] ISSUE-016与AI-03保持in-review，待项目经理设置done

<a id="rev-m0-t17"></a>

## REV-M0-T17 · ISSUE-028 配置驱动对话模型设计 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-028 已提交 in-review |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T17.md) |
| 代码解释 | 无产品代码 |

范围：只看Provider侧设计：验收条目、与现有适配器及冻结错误码一致性、密钥来源、依赖与契约未改。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] AC-01～03通过；与openai_model.py、errors.py冻结表、ISSUE-024错误码表一致；未改OpenAPI与依赖；D-1（P2）流式/JSON字段名在028与024间互相推诿。
- [x] ISSUE-028保持in-review，待项目经理设置done

<a id="rev-m0-t18"></a>

## REV-M0-T18 · ISSUE-031错误码名单冻结 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-031 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T18.md) |
| 代码解释 | 无产品代码 |

范围：复核ISSUE-031（2439616）。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] 三项变异：换码与只改名单都被拦住，同步新增只被总数检查拦住；351个通过，8个跳过。
- [x] 被验卡和Issue的状态不变，等项目经理设置

<a id="rev-m0-t19"></a>

## REV-M0-T19 · BE-M0-T12编辑租约入库 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T12、ISSUE-018 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T19.md) |
| 代码解释 | 无产品代码 |

范围：复核BE-M0-T12（09ada43，ISSUE-018）。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] 真实MySQL跨进程续期、过期接管、释放都通过；pytest -m mysql 8个通过；CI backend-mysql 8个通过，跳过0。
- [x] 被验卡和Issue的状态不变，等项目经理设置

<a id="rev-m0-t20"></a>

## REV-M0-T20 · ISSUE-022契约冻结 QA复签

| 字段 | 内容 |
|---|---|
| 状态 | done（本地验收；PR待合入） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-022 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T20.md) |
| 代码解释 | 无产品代码 |

范围：复签ISSUE-022契约冻结（73fde1e + ae91024）。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] README补上N7两码例外，P3句子已加入x-idempotency.retry；契约测试15个、后端351个通过，live HTTP 49/49；CI五个job全绿。
- [x] 被验卡和Issue的状态不变，等项目经理设置

<a id="rev-m0-t21"></a>

## REV-M0-T21 · 0a5b655请求层重试修复 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（QA 3e91aee，PM 恢复确认；未合入/未发布） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-030 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T21.md) |
| 代码解释 | 无产品代码 |

范围：签署前端请求层重试修复（0a5b655）。不改他人代码或卡片状态。

- [x] 验收条目逐条核对并独立复跑。
- [x] 探针34/34；502 MODEL_UNAVAILABLE与503 SECRET_KEY_UNAVAILABLE各1次请求；普通503与无错误体502照常重试，无Idempotency-Key写入不重试；Node 24.9.0前端单测97/97。
- [x] 被验卡和Issue的状态不变，等项目经理设置
- [x] 项目经理恢复后确认本卡 done，依据是 QA 3e91aee，PM 恢复确认。ISSUE-030 仍为 in-review。APP-M2-T002 仍为 done。

<a id="rev-m0-t23"></a>

## REV-M0-T23 · BE-M0-T13项目聚合入库 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（QA ae38ec3，PM 17:16 确认；未合入/未发布） |
| 估算 | 1.5小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T13、ISSUE-018 |
| 来源 | 项目经理签署要求（行为验收；演示表待 ISSUE-035） |
| 完成交付 | [专属交付](../delivery/REV-M0-T23.md) |
| 代码解释 | 无产品代码 |

范围：按行为验收 BE-M0-T13（9c17878）。装载叠种子、变更保存、revision 409；不按字典逐字段卡。不改他人代码；不把被验卡标为 done。T22 已用于 T114 复签。

- [x] 验收条目逐条核对并独立复跑。
- [x] 行为三项与 mysql/无库套件、CI 38219738690 通过；方案第 6 节有对照表；批准句待 ISSUE-035。
- [x] 被验卡和Issue的状态不变，等项目经理设置
- [x] 项目经理确认本卡与 BE-M0-T13 为 done，依据是 QA ae38ec3，PM 17:16 确认。ISSUE-018 仍为 in-progress。ISSUE-035 仍为 new。


<a id="rev-m0-t22"></a>

## REV-M0-T22 · APP-M2-T114 e691405 冲突刷新 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（QA f521950，PM 17:13 确认；未合入/未发布） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | APP-M2-T114（e691405） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T22.md) |
| 代码解释 | 无产品代码 |

范围：复签挂证据抽屉冲突刷新（e691405）。不改他人代码；不把被验卡标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] 冲突提示旁抽屉内「刷新」；e2e 他人先保存→刷新→再保存；已挂过期仍「证据失效」；五条 PRD v1.8 挂接规则单测仍成立；Node 24.9.0 单测98、Playwright 14、build 通过；CI run 38227446697。
- [x] 签署注明缺协议、受限依赖 ISSUE-033；智能匹配与规则2端到端挂 ISSUE-033。
- [x] 被验卡和本卡均不标 done，等项目经理设置
- [x] 项目经理确认本卡与 APP-M2-T114 为 done，依据是 QA f521950，PM 17:13 确认。ISSUE-033 仍开放：缺协议、受限、智能匹配和规则 2 端到端不在本卡关闭

<a id="rev-m0-t24"></a>

## REV-M0-T24 · APP-M2-T078 内存片段发布 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | done（QA 19c4862，PM 17:20 确认；未合入/未发布） |
| 估算 | 1.5小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | APP-M2-T078（e6215d4）、ISSUE-022 |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T24.md) |
| 代码解释 | 无产品代码 |

范围：签署 APP-M2-T078 内存片段发布（e6215d4）。核对拦截原因、kb_sync_status、ETag/If-Match、幂等与公司隔离。不改他人代码。签署当时页面未做，等项目经理设置。项目经理随后确认本卡与被验卡为 done（QA 19c4862，PM 17:20 确认），页面不挡住 done。T23 已用于 T13 签署。

- [x] 验收条目逐条核对并独立复跑。
- [x] 聚焦 18 passed；全量 352 passed / 12 skipped；CI 38212117391 全绿；HEAD 含 e6215d4。
- [x] 页面未做，APP-M2-T078 与本卡均不标 done，等项目经理设置
- [x] 项目经理确认本卡与 APP-M2-T078 为 done，依据是 QA 19c4862，PM 17:20 确认。范围只含内存片段发布层。页面未做，不挡住 done。本轮不实现 APP-M2-T124，只把它改为 ready

<a id="rev-m0-t25"></a>

## REV-M0-T25 · ISSUE-036 橙色标签对比 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-036（7f5f74d） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T25.md) |
| 代码解释 | 无产品代码 |

范围：签署 ISSUE-036 橙色/金色/warning 标签对比（7f5f74d）。不改他人代码；不把 ISSUE-036 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] 对比计算过线；前端单测 98；build 通过；Playwright「meet 4.5:1」1 passed；CI 38229790793 全绿。
- [x] ISSUE-036 与本卡均不标 done，等项目经理设置

<a id="rev-m0-t26"></a>

## REV-M0-T26 · ISSUE-033 规格增量契约复签

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-033（32b184c） |
| 来源 | 项目经理签署要求 |
| 完成交付 | [专属交付](../delivery/REV-M0-T26.md) |
| 代码解释 | 无产品代码 |

范围：复签 ISSUE-033 规格增量（32b184c）。核对 `is_restricted`、派生 `agreement_present`、对照 `bid_deadline_at`、复用三错误码。不改他人代码；不把 ISSUE-033 / BE-M0-T18 标为 done。运行时仍待后端。

- [x] 验收条目逐条核对并独立复跑。
- [x] 契约测试 10 passed；CI 38228282444 全绿；运行时未接通已写明。
- [x] ISSUE-033 / BE-M0-T18 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t27"></a>

## REV-M0-T27 · 最新合作分支复核与限定缺陷修复

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 按实际复核记录，不作新功能交期 |
| 关联Issue | [ISSUE-034](../../issues/ISSUE-034.md) |
| 依赖 | 初次73fde1e，复核快照9c178782；本卡并入 foundation 9e3fcdd。ISSUE-033 与 REV-M0-T22 已由同伴占用。`ee5aaa6` 占用 REV-M0-T25（ISSUE-036）与 REV-M0-T26（ISSUE-033 规格复签），本卡保持 T27 |
| 来源 | 用户要求复核最新分支，修改仅提PR，暂停功能推进 |
| 完成交付 | [专属交付](../delivery/REV-M0-T27.md) |
| 代码解释 | [修复解释](../code/REV-M0-T27.md) |

范围：九项确认问题中密钥重试由上游已修复；本PR修其余八项身份、导航、片段、回执、租约和证据抽屉缺陷，并纠正部署事实。保留 foundation 上 T114 冲突刷新、ISSUE-036 橙色标签对比，以及 T078/T114 的状态记录。不新增页面、接口或模型/数据库功能。不改写已完成的 APP-M2-T114 / REV-M0-T22。独立修复分支的 PR 以 codex/repository-foundation 为目标。

- [x] 回归先证明原缺陷，再证明修复结果。
- [x] 运行相关实际函数/HTTP、构建及治理；真实MySQL未连接须明确。
- [x] 保存复核、代码、交付和基线影响；提交PR等待审核，不自行done/closed。
- [x] QA 正式签署（2026-10-12，tip `5eced4f`）：R1～R9 通过，含真实 MySQL R4/R6/R7；见[签署记录](../testing/2026-10-12-issue-034-qa-signoff.md)。**状态仍 in-review，不标 done。**

修复PR：[#4](https://github.com/Faith-Neil/if-children-have-been-grown/pull/4)，等待审核。


<a id="rev-m0-t28"></a>

## REV-M0-T28 · BE-M0-T11 回执与会话入库 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T11（631d4c9） |
| 来源 | 项目经理签署要求。REV-M0-T27 已用于 ISSUE-034，状态 in-review，不标 done |
| 完成交付 | [专属交付](../delivery/REV-M0-T28.md) |
| 代码解释 | 无产品代码 |

范围：正式签署 BE-M0-T11 幂等回执与登录会话入库。真实 MySQL 上复跑 downgrade/upgrade、Q2 快速失败、双 worker 与重启存活。不改他人代码；不把 BE-M0-T11 / ISSUE-018 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] 无库 355 passed / 13 skipped；`-m mysql` 12 passed；Q2 ~1s failed；双 worker + 重启通过；CI 38212536927 全绿。
- [x] BE-M0-T11 / ISSUE-018 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t29"></a>

## REV-M0-T29 · ISSUE-028 AC-02 假端点夹具 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-028（9e3fcdd） |
| 来源 | 项目经理签署要求。REV-M0-T27 已用于 ISSUE-034。T28 已用于 BE-M0-T11 |
| 完成交付 | [专属交付](../delivery/REV-M0-T29.md) |
| 代码解释 | 无产品代码 |

范围：签署 ISSUE-028 AC-02 假 OpenAI 兼容端点夹具（9e3fcdd）。核对 fixture、默认 skip、CI 不设旗、无生产改动。路径规范化 hold，不要求改适配器。不改他人代码；不把 ISSUE-028 / AI-01 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] 聚焦 34 passed / 1 skipped；全后台 355 passed / 13 skipped；治理通过；CI 38231417634 绿。
- [x] ISSUE-028 / AI-01 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t30"></a>

## REV-M0-T30 · ISSUE-028 AC-03 OpenAPI/依赖/演示替身 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | ISSUE-028（9e3fcdd；证据 be3ce98） |
| 来源 | 项目经理签署要求。REV-M0-T27 已用于 ISSUE-034，状态 in-review，不标 done。T28/T29 已用 |
| 完成交付 | [专属交付](../delivery/REV-M0-T30.md) |
| 代码解释 | 无产品代码 |

范围：签署 ISSUE-028 AC-03。独立复跑 AI 证据：夹具提交不改 OpenAPI/依赖；create_app 默认演示替身。不改他人代码；不把 ISSUE-028 / AI-01 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] OpenAPI/requirements/openai_model 夹具 diff 为空；34 passed / 1 skipped；治理通过。
- [x] ISSUE-028 / AI-01 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t31"></a>

## REV-M0-T31 · 2026-10-13最新增量复核

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 本轮限新增内容与必要专项 |
| 关联Issue | [ISSUE-034](../../issues/ISSUE-034.md) |
| 依赖 | 固定foundation b7b3191；PR #4 tip 9986747及原QA签署 |
| 来源 | 用户要求再次复核，极速、省略重复全套验证、做好标记 |
| 完成交付 | [专属交付](../delivery/REV-M0-T31.md) |
| 代码解释 | 无产品代码；只更新审查及交付记录 |

- [x] 检查新增挂证据、v1租约和导出输入绑定，未确认新的阻断。
- [x] 必要后端专项11项通过；全套构建、浏览器、真实数据库/模型未在本轮重复执行。
- [x] 沿用原QA签署和ISSUE-034，不覆盖他人编号；[PR #4](https://github.com/Faith-Neil/if-children-have-been-grown/pull/4)待审、未合入/发布。

<a id="rev-m0-t32"></a>

## REV-M0-T32 · BE-M0-T04 编辑租约 v1 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T04（tip 90b2334） |
| 来源 | 项目经理恢复派活。T31 已用于增量复核 |
| 完成交付 | [专属交付](../delivery/REV-M0-T32.md) |
| 代码解释 | 无产品代码 |

范围：正式签署 BE-M0-T04 编辑租约迁到 `/api/v1`。不改他人代码；不把 BE-M0-T04 / ISSUE-005 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] `test_v1_lease.py` 通过；无库 381 passed / 13 skipped；OpenAPI 含三条 v1 路径。
- [x] BE-M0-T04 / ISSUE-005 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t33"></a>

## REV-M0-T33 · BE-M0-T05 导出快照 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T05（tip 90b2334） |
| 来源 | 项目经理恢复派活 |
| 完成交付 | [专属交付](../delivery/REV-M0-T33.md) |
| 代码解释 | 无产品代码 |

范围：正式签署 BE-M0-T05 导出快照语义。不改他人代码；不把 BE-M0-T05 / ISSUE-005 标为 done。

- [x] 验收条目逐条核对并独立复跑。
- [x] 绑定字段齐全；CHECK_STALE / EXPORT_STALE；无库 381/13。
- [x] BE-M0-T05 / ISSUE-005 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t34"></a>

## REV-M0-T34 · BE-M0-T16 错误码名字冻结 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T16（tip 90b2334）；ISSUE-031 已 closed |
| 来源 | 项目经理恢复派活。REV-M0-T18 为 ISSUE-031 名单签署 |
| 完成交付 | [专属交付](../delivery/REV-M0-T34.md) |
| 代码解释 | 无产品代码 |

范围：正式签署 BE-M0-T16。核对 `set(ERROR_STATUS)==FROZEN_NAMES` 与 spec 枚举。不改他人代码；不把 BE-M0-T16 标为 done；不重开 ISSUE-031。

- [x] 验收条目逐条核对并独立复跑。
- [x] 143 名集合相等；无库 381/13。
- [x] BE-M0-T16 / 本卡均不标 done，等项目经理设置

<a id="rev-m0-t35"></a>

## REV-M0-T35 · BE-M0-T18 / ISSUE-033 挂证据运行时 QA签署

| 字段 | 内容 |
|---|---|
| 状态 | in-review（本地验收；等项目经理设置 done） |
| 估算 | 1小时 |
| 关联Issue | [ISSUE-013](../../issues/ISSUE-013.md) |
| 依赖 | BE-M0-T18 / ISSUE-033（tip 90b2334） |
| 来源 | 项目经理恢复派活。REV-M0-T26 为规格复签 |
| 完成交付 | [专属交付](../delivery/REV-M0-T35.md) |
| 代码解释 | 无产品代码 |

范围：正式签署挂证据**运行时**规则。核对 is_restricted、agreement_present 派生、有效期对照截止日、三错误码复用。不改他人代码；不把 BE-M0-T18 / ISSUE-033 标为 done / closed。

- [x] 验收条目逐条核对并独立复跑。
- [x] `test_evidence_mount.py` 通过；名单仍 143；无库 381/13。
- [x] BE-M0-T18 / ISSUE-033 / 本卡均不标 done，等项目经理设置
