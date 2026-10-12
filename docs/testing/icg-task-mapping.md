为什么有这个文件：把原ICG47个页面组和44条规则映射到实际可实施任务。

它解决什么问题：便于登记看板、排查漏项/重复计完成，并保持原一期与二期边界。

# ICG页面、规则与任务映射

日期：2026-10-11。版本：icg-task-map-1。关联[ISSUE-007](../../issues/ISSUE-007.md) / [APP-M1-T07](../tasks/APP-M1.md#app-m1-t07)。卡片见[APP-M2](../tasks/APP-M2.md)；来源清单见[icg-coverage](icg-coverage.md)，原依据为[交接v1](<../../ICG/frontend doc/frontend-handoff-v1.md>) §4～6及[PRD v1.8](../reference/product/prd-mvp-v1.8.md) §5.8.1。

本次仅完成范围拆分，未实现这些功能。259张新卡全部planned；190原M1～M6原子细卡各有入口，13独立章节/Word/Excel/年度划型产物和56规则子单位共同推进同一功能，不重复计功能完成。47组仍未完整实现，44规则仍未完整交付；原规则数36一期完整、3一期简化、5二期未变。旧59FE卡保留；T14/T15拆分时in-progress，只引用不增加新任务，之后状态看原卡和看板。APP-M2是批次编号，非PRD二期；模型/数据库仅留接口不豁免业务。

T07上段为范围拆分阶段记录；当前ISSUE-009 / APP-M2-T001为 in-review，T008离线CI为 in-review，其余257张后续卡planned。功能映射与原完整期次不变。T001 尚未由项目经理标 done，不把布局提交或会话接口等同整套页面底座。

## 页面/能力47组逐项映射

原WBS是原文拆小项的编号；一个页面可依赖多个任务，基础任务可复用多个页面。映射数量不表示完成率。

| 来源组 | 页面/能力 | PRD | 原WBS | 实际新任务/既有任务 | 状态 |
|---|---|---|---|---|---|
| PG01 | G-01 登录（Keycloak 主题） | 5.12.1 | P02a（2）、P02（2） | [APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)、[APP-M2-T002](../tasks/APP-M2.md#app-m2-t002)、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)、[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)、[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005)、[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006)、[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007)、[APP-M2-T008](../tasks/APP-M2.md#app-m2-t008)、[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009)、[APP-M2-T010](../tasks/APP-M2.md#app-m2-t010)、[APP-M2-T011](../tasks/APP-M2.md#app-m2-t011)、[APP-M2-T012](../tasks/APP-M2.md#app-m2-t012)、[APP-M2-T013](../tasks/APP-M2.md#app-m2-t013)、[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015)、[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016) | 未完整实现 |
| PG02 | G-02 站内提醒列表 + 顶栏下拉 | 5.12.2 | P11（2）、P11a（2） | [APP-M2-T029](../tasks/APP-M2.md#app-m2-t029)、[APP-M2-T030](../tasks/APP-M2.md#app-m2-t030)、[APP-M2-T031](../tasks/APP-M2.md#app-m2-t031)、[APP-M2-T032](../tasks/APP-M2.md#app-m2-t032) | 未完整实现 |
| PG03 | 全局搜索（顶栏 + 结果页） | 5.12.3 | P16（1） | [APP-M2-T035](../tasks/APP-M2.md#app-m2-t035) | 未完整实现 |
| PG04 | G-03 后台任务中心 + 顶栏抽屉 | 5.12.4 | P05（3）、P05a（1） | [APP-M2-T019](../tasks/APP-M2.md#app-m2-t019)、[APP-M2-T020](../tasks/APP-M2.md#app-m2-t020)、[APP-M2-T021](../tasks/APP-M2.md#app-m2-t021)、[APP-M2-T022](../tasks/APP-M2.md#app-m2-t022) | 未完整实现 |
| PG05 | P-01 项目列表（工作台） | 5.1.1 | E01 | [APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)、[APP-M2-T002](../tasks/APP-M2.md#app-m2-t002)、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)、[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)、[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005)、[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006)、[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007)、[APP-M2-T008](../tasks/APP-M2.md#app-m2-t008)、[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009)、[APP-M2-T094](../tasks/APP-M2.md#app-m2-t094)、[APP-M2-T095](../tasks/APP-M2.md#app-m2-t095)、[APP-M2-T096](../tasks/APP-M2.md#app-m2-t096)、[APP-M2-T097](../tasks/APP-M2.md#app-m2-t097)、[APP-M2-T098](../tasks/APP-M2.md#app-m2-t098)、[APP-M2-T099](../tasks/APP-M2.md#app-m2-t099)、[APP-M2-T100](../tasks/APP-M2.md#app-m2-t100)、[APP-M2-T153](../tasks/APP-M2.md#app-m2-t153)、[APP-M2-T154](../tasks/APP-M2.md#app-m2-t154) | 未完整实现 |
| PG06 | P-02 新建项目（含 R19） | 5.1.2 | E01 | [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094)、[APP-M2-T095](../tasks/APP-M2.md#app-m2-t095)、[APP-M2-T096](../tasks/APP-M2.md#app-m2-t096)、[APP-M2-T097](../tasks/APP-M2.md#app-m2-t097)、[APP-M2-T098](../tasks/APP-M2.md#app-m2-t098)、[APP-M2-T099](../tasks/APP-M2.md#app-m2-t099)、[APP-M2-T100](../tasks/APP-M2.md#app-m2-t100) | 未完整实现 |
| PG07 | P-03 项目概览（含 P-17 折叠区） | 5.1.3、5.7.13 | E01、E01b（2） | [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094)、[APP-M2-T095](../tasks/APP-M2.md#app-m2-t095)、[APP-M2-T096](../tasks/APP-M2.md#app-m2-t096)、[APP-M2-T097](../tasks/APP-M2.md#app-m2-t097)、[APP-M2-T098](../tasks/APP-M2.md#app-m2-t098)、[APP-M2-T099](../tasks/APP-M2.md#app-m2-t099)、[APP-M2-T100](../tasks/APP-M2.md#app-m2-t100)、[APP-M2-T153](../tasks/APP-M2.md#app-m2-t153)、[APP-M2-T154](../tasks/APP-M2.md#app-m2-t154) | 未完整实现 |
| PG08 | P-04 招标文件上传与解析进度 | 5.2.1 | E02（2） | [APP-M2-T101](../tasks/APP-M2.md#app-m2-t101)、[APP-M2-T102](../tasks/APP-M2.md#app-m2-t102) | 未完整实现 |
| PG09 | P-05 解析结果 + 抽取后处理 | 5.2.2、5.2.4 | E04（6）、E04a（3） | [APP-M2-T103](../tasks/APP-M2.md#app-m2-t103)、[APP-M2-T104](../tasks/APP-M2.md#app-m2-t104)、[APP-M2-T105](../tasks/APP-M2.md#app-m2-t105)、[APP-M2-T106](../tasks/APP-M2.md#app-m2-t106)、[APP-M2-T107](../tasks/APP-M2.md#app-m2-t107)、[APP-M2-T108](../tasks/APP-M2.md#app-m2-t108)、[APP-M2-T109](../tasks/APP-M2.md#app-m2-t109)、[APP-M2-T110](../tasks/APP-M2.md#app-m2-t110)、[APP-M2-T111](../tasks/APP-M2.md#app-m2-t111) | 未完整实现 |
| PG10 | P-06 响应矩阵 + 挂证据抽屉 | 5.3.1 | E05（6）、E05a（1） | [APP-M2-T112](../tasks/APP-M2.md#app-m2-t112)、[APP-M2-T113](../tasks/APP-M2.md#app-m2-t113)、[APP-M2-T114](../tasks/APP-M2.md#app-m2-t114)、[APP-M2-T115](../tasks/APP-M2.md#app-m2-t115)、[APP-M2-T116](../tasks/APP-M2.md#app-m2-t116)、[APP-M2-T117](../tasks/APP-M2.md#app-m2-t117)、[APP-M2-T118](../tasks/APP-M2.md#app-m2-t118) | 未完整实现 |
| PG11 | P-07 SLA 矩阵 | 5.3.2 | E06 | [APP-M2-T119](../tasks/APP-M2.md#app-m2-t119)、[APP-M2-T120](../tasks/APP-M2.md#app-m2-t120)、[APP-M2-T121](../tasks/APP-M2.md#app-m2-t121)、[APP-M2-T122](../tasks/APP-M2.md#app-m2-t122) | 未完整实现 |
| PG12 | P-09 项目事实表 | 5.7.8 | E06（与 P-07 共 4） | [APP-M2-T119](../tasks/APP-M2.md#app-m2-t119)、[APP-M2-T120](../tasks/APP-M2.md#app-m2-t120)、[APP-M2-T121](../tasks/APP-M2.md#app-m2-t121)、[APP-M2-T122](../tasks/APP-M2.md#app-m2-t122) | 未完整实现 |
| PG13 | P-18 分册分流确认 | 5.3.1 规则 8 | E05 | [APP-M2-T112](../tasks/APP-M2.md#app-m2-t112)、[APP-M2-T113](../tasks/APP-M2.md#app-m2-t113)、[APP-M2-T114](../tasks/APP-M2.md#app-m2-t114)、[APP-M2-T115](../tasks/APP-M2.md#app-m2-t115)、[APP-M2-T116](../tasks/APP-M2.md#app-m2-t116)、[APP-M2-T117](../tasks/APP-M2.md#app-m2-t117)、[APP-M1-T14](../tasks/APP-M1.md#app-m1-t14) | 未完整实现 |
| PG14 | P-16 项目设置 | 5.1.4 | E01 | [APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015)、[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016)、[APP-M2-T094](../tasks/APP-M2.md#app-m2-t094)、[APP-M2-T095](../tasks/APP-M2.md#app-m2-t095)、[APP-M2-T096](../tasks/APP-M2.md#app-m2-t096)、[APP-M2-T097](../tasks/APP-M2.md#app-m2-t097)、[APP-M2-T098](../tasks/APP-M2.md#app-m2-t098)、[APP-M2-T099](../tasks/APP-M2.md#app-m2-t099)、[APP-M2-T100](../tasks/APP-M2.md#app-m2-t100)、[APP-M1-T14](../tasks/APP-M1.md#app-m1-t14) | 未完整实现 |
| PG15 | P-10 写作方案与大纲确认 | 5.7.2 | F01（4） | [APP-M2-T123](../tasks/APP-M2.md#app-m2-t123)、[APP-M2-T124](../tasks/APP-M2.md#app-m2-t124)、[APP-M2-T125](../tasks/APP-M2.md#app-m2-t125)、[APP-M2-T126](../tasks/APP-M2.md#app-m2-t126)、[APP-M1-T15](../tasks/APP-M1.md#app-m1-t15) | 未完整实现 |
| PG16 | P-12 章节循环进度 | 5.7.6 | F10 | [APP-M2-T019](../tasks/APP-M2.md#app-m2-t019)、[APP-M2-T020](../tasks/APP-M2.md#app-m2-t020)、[APP-M2-T021](../tasks/APP-M2.md#app-m2-t021)、[APP-M2-T129](../tasks/APP-M2.md#app-m2-t129)、[APP-M2-T130](../tasks/APP-M2.md#app-m2-t130)、[APP-M2-T131](../tasks/APP-M2.md#app-m2-t131)、[APP-M2-T132](../tasks/APP-M2.md#app-m2-t132)、[APP-M2-T133](../tasks/APP-M2.md#app-m2-t133)、[APP-M2-T134](../tasks/APP-M2.md#app-m2-t134)、[APP-M2-T135](../tasks/APP-M2.md#app-m2-t135)、[APP-M2-T136](../tasks/APP-M2.md#app-m2-t136) | 未完整实现 |
| PG17 | P-13 人工处理队列 | 5.7.7 | F10 | [APP-M2-T129](../tasks/APP-M2.md#app-m2-t129)、[APP-M2-T130](../tasks/APP-M2.md#app-m2-t130)、[APP-M2-T131](../tasks/APP-M2.md#app-m2-t131)、[APP-M2-T132](../tasks/APP-M2.md#app-m2-t132)、[APP-M2-T133](../tasks/APP-M2.md#app-m2-t133)、[APP-M2-T134](../tasks/APP-M2.md#app-m2-t134)、[APP-M2-T135](../tasks/APP-M2.md#app-m2-t135)、[APP-M2-T136](../tasks/APP-M2.md#app-m2-t136) | 未完整实现 |
| PG18 | 系统生成章节预览（五类） | 5.7.2 规则 1、5.11.8 | F09（2） | [APP-M2-T127](../tasks/APP-M2.md#app-m2-t127)、[APP-M2-T128](../tasks/APP-M2.md#app-m2-t128)、[APP-M2-T191](../tasks/APP-M2.md#app-m2-t191)、[APP-M2-T192](../tasks/APP-M2.md#app-m2-t192)、[APP-M2-T193](../tasks/APP-M2.md#app-m2-t193)、[APP-M2-T194](../tasks/APP-M2.md#app-m2-t194)、[APP-M2-T195](../tasks/APP-M2.md#app-m2-t195) | 未完整实现 |
| PG19 | P-17 / W-03 写作观察统计 | 5.7.13 | F11（3） | [APP-M2-T137](../tasks/APP-M2.md#app-m2-t137)、[APP-M2-T138](../tasks/APP-M2.md#app-m2-t138)、[APP-M2-T139](../tasks/APP-M2.md#app-m2-t139)、[APP-M2-T189](../tasks/APP-M2.md#app-m2-t189)、[APP-M2-T190](../tasks/APP-M2.md#app-m2-t190) | 未完整实现 |
| PG20 | P-14 合规检查 | 5.8.2、5.8.3、5.8.5 | G04（6） | [APP-M2-T140](../tasks/APP-M2.md#app-m2-t140)、[APP-M2-T141](../tasks/APP-M2.md#app-m2-t141)、[APP-M2-T142](../tasks/APP-M2.md#app-m2-t142)、[APP-M2-T143](../tasks/APP-M2.md#app-m2-t143)、[APP-M2-T144](../tasks/APP-M2.md#app-m2-t144)、[APP-M2-T145](../tasks/APP-M2.md#app-m2-t145)、[APP-M2-T203](../tasks/APP-M2.md#app-m2-t203)、[APP-M2-T204](../tasks/APP-M2.md#app-m2-t204)、[APP-M2-T205](../tasks/APP-M2.md#app-m2-t205)、[APP-M2-T206](../tasks/APP-M2.md#app-m2-t206)、[APP-M2-T207](../tasks/APP-M2.md#app-m2-t207)、[APP-M2-T208](../tasks/APP-M2.md#app-m2-t208)、[APP-M2-T209](../tasks/APP-M2.md#app-m2-t209)、[APP-M2-T210](../tasks/APP-M2.md#app-m2-t210)、[APP-M2-T211](../tasks/APP-M2.md#app-m2-t211)、[APP-M2-T212](../tasks/APP-M2.md#app-m2-t212)、[APP-M2-T213](../tasks/APP-M2.md#app-m2-t213)、[APP-M2-T214](../tasks/APP-M2.md#app-m2-t214)、[APP-M2-T215](../tasks/APP-M2.md#app-m2-t215)、[APP-M2-T216](../tasks/APP-M2.md#app-m2-t216)、[APP-M2-T217](../tasks/APP-M2.md#app-m2-t217)、[APP-M2-T218](../tasks/APP-M2.md#app-m2-t218)、[APP-M2-T219](../tasks/APP-M2.md#app-m2-t219)、[APP-M2-T220](../tasks/APP-M2.md#app-m2-t220)、[APP-M2-T221](../tasks/APP-M2.md#app-m2-t221)、[APP-M2-T222](../tasks/APP-M2.md#app-m2-t222)、[APP-M2-T223](../tasks/APP-M2.md#app-m2-t223)、[APP-M2-T224](../tasks/APP-M2.md#app-m2-t224)、[APP-M2-T225](../tasks/APP-M2.md#app-m2-t225)、[APP-M2-T226](../tasks/APP-M2.md#app-m2-t226)、[APP-M2-T227](../tasks/APP-M2.md#app-m2-t227)、[APP-M2-T228](../tasks/APP-M2.md#app-m2-t228)、[APP-M2-T229](../tasks/APP-M2.md#app-m2-t229)、[APP-M2-T230](../tasks/APP-M2.md#app-m2-t230)、[APP-M2-T231](../tasks/APP-M2.md#app-m2-t231)、[APP-M2-T232](../tasks/APP-M2.md#app-m2-t232)、[APP-M2-T233](../tasks/APP-M2.md#app-m2-t233)、[APP-M2-T234](../tasks/APP-M2.md#app-m2-t234)、[APP-M2-T235](../tasks/APP-M2.md#app-m2-t235)、[APP-M2-T236](../tasks/APP-M2.md#app-m2-t236)、[APP-M2-T237](../tasks/APP-M2.md#app-m2-t237)、[APP-M2-T238](../tasks/APP-M2.md#app-m2-t238)、[APP-M2-T239](../tasks/APP-M2.md#app-m2-t239)、[APP-M2-T240](../tasks/APP-M2.md#app-m2-t240)、[APP-M2-T241](../tasks/APP-M2.md#app-m2-t241)、[APP-M2-T242](../tasks/APP-M2.md#app-m2-t242)、[APP-M2-T243](../tasks/APP-M2.md#app-m2-t243)、[APP-M2-T244](../tasks/APP-M2.md#app-m2-t244)、[APP-M2-T245](../tasks/APP-M2.md#app-m2-t245)、[APP-M2-T246](../tasks/APP-M2.md#app-m2-t246)、[APP-M2-T247](../tasks/APP-M2.md#app-m2-t247)、[APP-M2-T248](../tasks/APP-M2.md#app-m2-t248)、[APP-M2-T249](../tasks/APP-M2.md#app-m2-t249)、[APP-M2-T250](../tasks/APP-M2.md#app-m2-t250)、[APP-M2-T251](../tasks/APP-M2.md#app-m2-t251)、[APP-M2-T252](../tasks/APP-M2.md#app-m2-t252)、[APP-M2-T253](../tasks/APP-M2.md#app-m2-t253)、[APP-M2-T254](../tasks/APP-M2.md#app-m2-t254)、[APP-M2-T255](../tasks/APP-M2.md#app-m2-t255)、[APP-M2-T256](../tasks/APP-M2.md#app-m2-t256)、[APP-M2-T257](../tasks/APP-M2.md#app-m2-t257)、[APP-M2-T258](../tasks/APP-M2.md#app-m2-t258) | 未完整实现 |
| PG21 | P-15 导出 | 5.9.1、5.9.2 | H03（3）、H04（1） | [APP-M2-T149](../tasks/APP-M2.md#app-m2-t149)、[APP-M2-T150](../tasks/APP-M2.md#app-m2-t150)、[APP-M2-T151](../tasks/APP-M2.md#app-m2-t151)、[APP-M2-T152](../tasks/APP-M2.md#app-m2-t152)、[APP-M2-T196](../tasks/APP-M2.md#app-m2-t196)、[APP-M2-T197](../tasks/APP-M2.md#app-m2-t197)、[APP-M2-T198](../tasks/APP-M2.md#app-m2-t198)、[APP-M2-T199](../tasks/APP-M2.md#app-m2-t199)、[APP-M2-T200](../tasks/APP-M2.md#app-m2-t200)、[APP-M2-T201](../tasks/APP-M2.md#app-m2-t201)、[APP-M2-T202](../tasks/APP-M2.md#app-m2-t202) | 未完整实现 |
| PG22 | P-11 编辑台 | 5.11.2～5.11.10 | I01（12）、I02（4） | [APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)、[APP-M2-T002](../tasks/APP-M2.md#app-m2-t002)、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)、[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)、[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005)、[APP-M2-T006](../tasks/APP-M2.md#app-m2-t006)、[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007)、[APP-M2-T008](../tasks/APP-M2.md#app-m2-t008)、[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009)、[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015)、[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016)、[APP-M2-T160](../tasks/APP-M2.md#app-m2-t160)、[APP-M2-T161](../tasks/APP-M2.md#app-m2-t161)、[APP-M2-T162](../tasks/APP-M2.md#app-m2-t162)、[APP-M2-T163](../tasks/APP-M2.md#app-m2-t163)、[APP-M2-T164](../tasks/APP-M2.md#app-m2-t164)、[APP-M2-T165](../tasks/APP-M2.md#app-m2-t165)、[APP-M2-T166](../tasks/APP-M2.md#app-m2-t166)、[APP-M2-T167](../tasks/APP-M2.md#app-m2-t167)、[APP-M2-T168](../tasks/APP-M2.md#app-m2-t168)、[APP-M2-T169](../tasks/APP-M2.md#app-m2-t169)、[APP-M2-T170](../tasks/APP-M2.md#app-m2-t170)、[APP-M2-T171](../tasks/APP-M2.md#app-m2-t171)、[APP-M2-T172](../tasks/APP-M2.md#app-m2-t172)、[APP-M2-T173](../tasks/APP-M2.md#app-m2-t173)、[APP-M2-T174](../tasks/APP-M2.md#app-m2-t174)、[APP-M2-T175](../tasks/APP-M2.md#app-m2-t175)、[APP-M1-T15](../tasks/APP-M1.md#app-m1-t15) | 未完整实现 |
| PG23 | P-11 对话助手 + 答案卡 | 5.11.3～5.11.6、5.11.15 | I04（5）、I04a（2）、I04b（1）、I05（4）、I06（2）、E08（1，可选） | [APP-M2-T176](../tasks/APP-M2.md#app-m2-t176)、[APP-M2-T177](../tasks/APP-M2.md#app-m2-t177)、[APP-M2-T178](../tasks/APP-M2.md#app-m2-t178)、[APP-M2-T179](../tasks/APP-M2.md#app-m2-t179)、[APP-M2-T180](../tasks/APP-M2.md#app-m2-t180)、[APP-M2-T181](../tasks/APP-M2.md#app-m2-t181)、[APP-M2-T182](../tasks/APP-M2.md#app-m2-t182)、[APP-M2-T183](../tasks/APP-M2.md#app-m2-t183)、[APP-M2-T184](../tasks/APP-M2.md#app-m2-t184)、[APP-M2-T185](../tasks/APP-M2.md#app-m2-t185)、[APP-M2-T186](../tasks/APP-M2.md#app-m2-t186)、[APP-M2-T187](../tasks/APP-M2.md#app-m2-t187)、[APP-M2-T188](../tasks/APP-M2.md#app-m2-t188)、[APP-M2-T189](../tasks/APP-M2.md#app-m2-t189)、[APP-M2-T190](../tasks/APP-M2.md#app-m2-t190) | 未完整实现 |
| PG24 | K-01 资料库首页 | 5.4.2 | C07（3） | [APP-M2-T071](../tasks/APP-M2.md#app-m2-t071)、[APP-M2-T072](../tasks/APP-M2.md#app-m2-t072)、[APP-M2-T073](../tasks/APP-M2.md#app-m2-t073) | 未完整实现 |
| PG25 | K-02 / K-03 资料列表与详情（通用框架） | 5.4.1、5.4.3、5.4.4 | C01（5） | [APP-M2-T046](../tasks/APP-M2.md#app-m2-t046)、[APP-M2-T047](../tasks/APP-M2.md#app-m2-t047)、[APP-M2-T048](../tasks/APP-M2.md#app-m2-t048)、[APP-M2-T049](../tasks/APP-M2.md#app-m2-t049)、[APP-M2-T050](../tasks/APP-M2.md#app-m2-t050) | 未完整实现 |
| PG26 | K-04 人员与人员证书 | 5.4.5 | C04（4） | [APP-M2-T017](../tasks/APP-M2.md#app-m2-t017)、[APP-M2-T018](../tasks/APP-M2.md#app-m2-t018)、[APP-M2-T060](../tasks/APP-M2.md#app-m2-t060)、[APP-M2-T061](../tasks/APP-M2.md#app-m2-t061)、[APP-M2-T062](../tasks/APP-M2.md#app-m2-t062)、[APP-M2-T063](../tasks/APP-M2.md#app-m2-t063) | 未完整实现 |
| PG27 | K-05 原厂授权与授权链 | 5.4.6 | C05（3） | [APP-M2-T064](../tasks/APP-M2.md#app-m2-t064)、[APP-M2-T065](../tasks/APP-M2.md#app-m2-t065)、[APP-M2-T066](../tasks/APP-M2.md#app-m2-t066) | 未完整实现 |
| PG28 | K-06～K-08、K-11～K-13 公司主体、证明材料、资质、划型、附件、合规事件、工具设备 | 5.4.7 | C03（6） | [APP-M2-T054](../tasks/APP-M2.md#app-m2-t054)、[APP-M2-T055](../tasks/APP-M2.md#app-m2-t055)、[APP-M2-T056](../tasks/APP-M2.md#app-m2-t056)、[APP-M2-T057](../tasks/APP-M2.md#app-m2-t057)、[APP-M2-T058](../tasks/APP-M2.md#app-m2-t058)、[APP-M2-T059](../tasks/APP-M2.md#app-m2-t059)、[APP-M2-T259](../tasks/APP-M2.md#app-m2-t259) | 未完整实现 |
| PG29 | K-09、K-10、K-14 SLA 模板、全局变量、业绩 | 5.4.7 | C06（4） | [APP-M2-T067](../tasks/APP-M2.md#app-m2-t067)、[APP-M2-T068](../tasks/APP-M2.md#app-m2-t068)、[APP-M2-T069](../tasks/APP-M2.md#app-m2-t069)、[APP-M2-T070](../tasks/APP-M2.md#app-m2-t070) | 未完整实现 |
| PG30 | 平台主数据（厂商产品、证书类别、附件槽位、划型标准） | 5.10.3 | C02（3） | [APP-M2-T051](../tasks/APP-M2.md#app-m2-t051)、[APP-M2-T052](../tasks/APP-M2.md#app-m2-t052)、[APP-M2-T053](../tasks/APP-M2.md#app-m2-t053) | 未完整实现 |
| PG31 | 附件智能识别填表 | 5.4.4 | C08（2） | [APP-M2-T074](../tasks/APP-M2.md#app-m2-t074)、[APP-M2-T075](../tasks/APP-M2.md#app-m2-t075) | 未完整实现 |
| PG32 | K-15 方案片段库 | 5.5.2 | D01（4） | [APP-M2-T076](../tasks/APP-M2.md#app-m2-t076)、[APP-M2-T077](../tasks/APP-M2.md#app-m2-t077)、[APP-M2-T078](../tasks/APP-M2.md#app-m2-t078)、[APP-M2-T079](../tasks/APP-M2.md#app-m2-t079) | 未完整实现 |
| PG33 | K-16 历史标书导入 | 5.5.3 | D02（2） | [APP-M2-T080](../tasks/APP-M2.md#app-m2-t080)、[APP-M2-T081](../tasks/APP-M2.md#app-m2-t081) | 未完整实现 |
| PG34 | W-01 写作档案 | 5.6.2 | D03（6） | [APP-M2-T082](../tasks/APP-M2.md#app-m2-t082)、[APP-M2-T083](../tasks/APP-M2.md#app-m2-t083)、[APP-M2-T084](../tasks/APP-M2.md#app-m2-t084)、[APP-M2-T085](../tasks/APP-M2.md#app-m2-t085)、[APP-M2-T086](../tasks/APP-M2.md#app-m2-t086)、[APP-M2-T087](../tasks/APP-M2.md#app-m2-t087) | 未完整实现 |
| PG35 | 任务卡与提示词模板 | 5.7.9、5.6.4 | D04（3） | [APP-M2-T088](../tasks/APP-M2.md#app-m2-t088)、[APP-M2-T089](../tasks/APP-M2.md#app-m2-t089)、[APP-M2-T090](../tasks/APP-M2.md#app-m2-t090) | 未完整实现 |
| PG36 | W-02 风格样例 + 审查清单 | 5.6.5、5.6.4（默认审查清单） | D05（3） | [APP-M2-T091](../tasks/APP-M2.md#app-m2-t091)、[APP-M2-T092](../tasks/APP-M2.md#app-m2-t092)、[APP-M2-T093](../tasks/APP-M2.md#app-m2-t093) | 未完整实现 |
| PG37 | A-01 公司管理、A-02 用户与角色 | 5.10.1、5.10.2 | P10（3） | [APP-M2-T026](../tasks/APP-M2.md#app-m2-t026)、[APP-M2-T027](../tasks/APP-M2.md#app-m2-t027)、[APP-M2-T028](../tasks/APP-M2.md#app-m2-t028) | 未完整实现 |
| PG38 | A-03 字典配置 | 5.10.3 | P09（3，含状态注册表） | [APP-M2-T023](../tasks/APP-M2.md#app-m2-t023)、[APP-M2-T024](../tasks/APP-M2.md#app-m2-t024)、[APP-M2-T025](../tasks/APP-M2.md#app-m2-t025) | 未完整实现 |
| PG39 | A-08 模型登记、A-09 文档解析服务 | 6.6.1、6.6.2 | B01（4） | [APP-M2-T036](../tasks/APP-M2.md#app-m2-t036)、[APP-M2-T037](../tasks/APP-M2.md#app-m2-t037)、[APP-M2-T038](../tasks/APP-M2.md#app-m2-t038)、[APP-M2-T039](../tasks/APP-M2.md#app-m2-t039) | 未完整实现 |
| PG40 | A-10 任务与模型对应表、A-05 模型开放 | 6.6.3、5.10.5 | B02（2） | [APP-M2-T040](../tasks/APP-M2.md#app-m2-t040)、[APP-M2-T041](../tasks/APP-M2.md#app-m2-t041) | 未完整实现 |
| PG41 | A-05 生成闭环与编辑台配置（联动校验） | 6.9、5.10.5 | B06（3） | [APP-M2-T043](../tasks/APP-M2.md#app-m2-t043)、[APP-M2-T044](../tasks/APP-M2.md#app-m2-t044)、[APP-M2-T045](../tasks/APP-M2.md#app-m2-t045) | 未完整实现 |
| PG42 | A-04 资料库设置 | 5.10.4 | C07 或 C01（随资料库） | [APP-M2-T071](../tasks/APP-M2.md#app-m2-t071)、[APP-M2-T072](../tasks/APP-M2.md#app-m2-t072)、[APP-M2-T073](../tasks/APP-M2.md#app-m2-t073) | 未完整实现 |
| PG43 | A-06 审计日志、服务健康基础 | 5.10.6、6.7 | J01（3）、P04（2，含 MaskedField 查看留痕） | [APP-M2-T017](../tasks/APP-M2.md#app-m2-t017)、[APP-M2-T018](../tasks/APP-M2.md#app-m2-t018)、[APP-M2-T157](../tasks/APP-M2.md#app-m2-t157)、[APP-M2-T158](../tasks/APP-M2.md#app-m2-t158)、[APP-M2-T159](../tasks/APP-M2.md#app-m2-t159) | 未完整实现 |
| PG44 | A-11 部署与服务状态 | 5.12.6 | J01a（1） | [APP-M2-T042](../tasks/APP-M2.md#app-m2-t042) | 未完整实现 |
| PG45 | A-12 界面品牌 | 5.12.7 | P15（2） | [APP-M2-T033](../tasks/APP-M2.md#app-m2-t033)、[APP-M2-T034](../tasks/APP-M2.md#app-m2-t034) | 未完整实现 |
| PG46 | A-07 规则配置（合规规则 + 兜底扫描词表） | 5.12.5 | G06（3） | [APP-M2-T146](../tasks/APP-M2.md#app-m2-t146)、[APP-M2-T147](../tasks/APP-M2.md#app-m2-t147)、[APP-M2-T148](../tasks/APP-M2.md#app-m2-t148) | 未完整实现 |
| PG47 | 集团管理员只读视图 | 5.10、2.3 | J02（2） | [APP-M2-T155](../tasks/APP-M2.md#app-m2-t155)、[APP-M2-T156](../tasks/APP-M2.md#app-m2-t156) | 未完整实现 |

## 44条规则逐项映射

卡中保留原目标、时机、循环范围、级别和原备注。拆多卡的规则必须全部子机制和原触发点直接验收后才能判整条完成。

| 规则 | 原PRD范围 | 实施/验收任务 | 直接证据计划 | 状态 |
|---|---|---|---|---|
| R01 | 一期完整 | [APP-M2-T203](../tasks/APP-M2.md#app-m2-t203) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R02 | 一期完整 | [APP-M2-T204](../tasks/APP-M2.md#app-m2-t204) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R03 | 一期完整 | [APP-M2-T205](../tasks/APP-M2.md#app-m2-t205) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R04 | 一期完整 | [APP-M2-T206](../tasks/APP-M2.md#app-m2-t206) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R05 | 二期 | [APP-M2-T207](../tasks/APP-M2.md#app-m2-t207) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R06 | 二期 | [APP-M2-T208](../tasks/APP-M2.md#app-m2-t208) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R07 | 一期完整 | [APP-M2-T209](../tasks/APP-M2.md#app-m2-t209) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R08 | 一期完整 | [APP-M2-T210](../tasks/APP-M2.md#app-m2-t210) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R09 | 一期完整 | [APP-M2-T211](../tasks/APP-M2.md#app-m2-t211)、[APP-M2-T212](../tasks/APP-M2.md#app-m2-t212)、[APP-M2-T213](../tasks/APP-M2.md#app-m2-t213) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R10 | 一期完整 | [APP-M2-T214](../tasks/APP-M2.md#app-m2-t214)、[APP-M2-T215](../tasks/APP-M2.md#app-m2-t215) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R11 | 一期完整 | [APP-M2-T216](../tasks/APP-M2.md#app-m2-t216) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R12 | 一期完整 | [APP-M2-T217](../tasks/APP-M2.md#app-m2-t217) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R13 | 一期简化 | [APP-M2-T218](../tasks/APP-M2.md#app-m2-t218) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R14 | 一期完整 | [APP-M2-T219](../tasks/APP-M2.md#app-m2-t219) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R15 | 一期完整 | [APP-M2-T220](../tasks/APP-M2.md#app-m2-t220) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R16 | 一期简化 | [APP-M2-T221](../tasks/APP-M2.md#app-m2-t221) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R17 | 一期完整 | [APP-M2-T222](../tasks/APP-M2.md#app-m2-t222) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R18 | 一期完整 | [APP-M2-T223](../tasks/APP-M2.md#app-m2-t223) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R19 | 一期完整 | [APP-M2-T224](../tasks/APP-M2.md#app-m2-t224) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R20 | 二期 | [APP-M2-T225](../tasks/APP-M2.md#app-m2-t225) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R21 | 二期 | [APP-M2-T226](../tasks/APP-M2.md#app-m2-t226) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R22 | 二期 | [APP-M2-T227](../tasks/APP-M2.md#app-m2-t227) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R23 | 一期完整 | [APP-M2-T228](../tasks/APP-M2.md#app-m2-t228) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R24 | 一期简化 | [APP-M2-T229](../tasks/APP-M2.md#app-m2-t229) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R25 | 一期完整 | [APP-M2-T230](../tasks/APP-M2.md#app-m2-t230)、[APP-M2-T231](../tasks/APP-M2.md#app-m2-t231) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R26 | 一期完整 | [APP-M2-T232](../tasks/APP-M2.md#app-m2-t232) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R27 | 一期完整 | [APP-M2-T233](../tasks/APP-M2.md#app-m2-t233) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R28 | 一期完整 | [APP-M2-T234](../tasks/APP-M2.md#app-m2-t234) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R29 | 一期完整 | [APP-M2-T235](../tasks/APP-M2.md#app-m2-t235) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R30 | 一期完整 | [APP-M2-T236](../tasks/APP-M2.md#app-m2-t236)、[APP-M2-T237](../tasks/APP-M2.md#app-m2-t237) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R31 | 一期完整 | [APP-M2-T238](../tasks/APP-M2.md#app-m2-t238)、[APP-M2-T239](../tasks/APP-M2.md#app-m2-t239) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R32 | 一期完整 | [APP-M2-T240](../tasks/APP-M2.md#app-m2-t240) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R33 | 一期完整 | [APP-M2-T241](../tasks/APP-M2.md#app-m2-t241) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R34 | 一期完整 | [APP-M2-T242](../tasks/APP-M2.md#app-m2-t242) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R35 | 一期完整 | [APP-M2-T243](../tasks/APP-M2.md#app-m2-t243) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R43 | 一期完整 | [APP-M2-T244](../tasks/APP-M2.md#app-m2-t244)、[APP-M2-T245](../tasks/APP-M2.md#app-m2-t245)、[APP-M2-T246](../tasks/APP-M2.md#app-m2-t246) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R44 | 一期完整 | [APP-M2-T247](../tasks/APP-M2.md#app-m2-t247)、[APP-M2-T248](../tasks/APP-M2.md#app-m2-t248)、[APP-M2-T249](../tasks/APP-M2.md#app-m2-t249) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R36 | 一期完整 | [APP-M2-T250](../tasks/APP-M2.md#app-m2-t250)、[APP-M2-T251](../tasks/APP-M2.md#app-m2-t251) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R37 | 一期完整 | [APP-M2-T252](../tasks/APP-M2.md#app-m2-t252) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R38 | 一期完整 | [APP-M2-T253](../tasks/APP-M2.md#app-m2-t253) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R39 | 一期完整 | [APP-M2-T254](../tasks/APP-M2.md#app-m2-t254) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R40 | 一期完整 | [APP-M2-T255](../tasks/APP-M2.md#app-m2-t255) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R41 | 一期完整 | [APP-M2-T256](../tasks/APP-M2.md#app-m2-t256) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |
| R42 | 一期完整 | [APP-M2-T257](../tasks/APP-M2.md#app-m2-t257)、[APP-M2-T258](../tasks/APP-M2.md#app-m2-t258) | 每列举条件正反例、公司/资源权限、全部触发点、定位/依据、缺输入与旧源失效、原级别/放行/转人工/递交；实际章节或Word/Excel按卡核对 | 未完整交付 |

## 看板完整录入表

每行一个新交付单位。统一Issue ISSUE-007，交付docs/delivery/ID.md；不要生成空交付就标done。

| ID | 标题 | 状态 | 依赖 | 原细卡/规则 |
|---|---|---|---|---|
| [APP-M2-T001](../tasks/APP-M2.md#app-m2-t001) | ProLayout 布局、路由、权限守卫、请求层 | in-review | BE-M0-T01 | M1-P08-01 |
| [APP-M2-T002](../tasks/APP-M2.md#app-m2-t002) | 请求层细化：错误体、traceId 复制、Idempotency-Key 注入、重试策略 | in-review | BE-M0-T01、APP-M2-T001 | M1-P08-F2 |
| [APP-M2-T003](../tasks/APP-M2.md#app-m2-t003) | 通用状态组件（骨架、空态、错误、无权限、已过期、只读） | planned | BE-M0-T01、APP-M2-T001 | M1-P08-F3 |
| [APP-M2-T004](../tasks/APP-M2.md#app-m2-t004) | 业务小组件：LevelTag、AiTag、DirectTag、Cite、SourceBar | planned | BE-M0-T01、APP-M2-T003 | M1-P08-F4 |
| [APP-M2-T005](../tasks/APP-M2.md#app-m2-t005) | 元数据驱动表格（ProTable 封装、列合并、无横滚优先） | planned | BE-M0-T01、APP-M2-T003 | M1-P08-F5 |
| [APP-M2-T006](../tasks/APP-M2.md#app-m2-t006) | 元数据驱动表单（★ 字段、系统键两行标签、不支持字段置灰） | planned | BE-M0-T01、APP-M2-T003 | M1-P08-F6 |
| [APP-M2-T007](../tasks/APP-M2.md#app-m2-t007) | 表单通用：底部保存条、离开未保存提示、就近报错 | planned | BE-M0-T01、APP-M2-T006 | M1-P08-F7 |
| [APP-M2-T008](../tasks/APP-M2.md#app-m2-t008) | 主题运行时接口位与离线检查纳入 CI（应用级） | in-review | BE-M0-T01、APP-M2-T001 | M1-P08-F8 |
| [APP-M2-T009](../tasks/APP-M2.md#app-m2-t009) | 断点与侧栏记忆（1280 / 1440 / 1680）、面包屑 | planned | BE-M0-T01、APP-M2-T001 | M1-P08-F9 |
| [APP-M2-T010](../tasks/APP-M2.md#app-m2-t010) | OIDC 登录跳转、会话续期、401 回登录并返回原页 | planned | APP-M2-T001 | M1-P02-F1 |
| [APP-M2-T011](../tasks/APP-M2.md#app-m2-t011) | 会话超时处理、用户菜单与退出登录 | planned | APP-M2-T001、APP-M2-T010 | M1-P02-F2 |
| [APP-M2-T012](../tasks/APP-M2.md#app-m2-t012) | Keycloak 自定义登录主题（离线；错误、锁定、超时，已有示例卡） | planned | APP-M2-T010 | M1-P02a-02 |
| [APP-M2-T013](../tasks/APP-M2.md#app-m2-t013) | 登录主题：首次登录强制改密、公司停用提示、读取品牌设置 | planned | APP-M2-T010 | M1-P02a-F3 |
| [APP-M2-T014](../tasks/APP-M2.md#app-m2-t014) | 路由守卫与 403 页 | planned | APP-M2-T010 | M1-P03-F1 |
| [APP-M2-T015](../tasks/APP-M2.md#app-m2-t015) | 权限指令 `<Can>` 与按钮隐藏 | planned | APP-M2-T010 | M1-P03-F2 |
| [APP-M2-T016](../tasks/APP-M2.md#app-m2-t016) | 数据权限的前端表现：只读态切换（项目 / 分册 / 章节） | planned | APP-M2-T010 | M1-P03-F3 |
| [APP-M2-T017](../tasks/APP-M2.md#app-m2-t017) | MaskedField 与“查看完整值”弹窗（原因必填） | planned | APP-M2-T014 | M1-P04-F1 |
| [APP-M2-T018](../tasks/APP-M2.md#app-m2-t018) | 掩码规则读取与查看留痕提示 | planned | APP-M2-T014、APP-M2-T017 | M1-P04-F2 |
| [APP-M2-T019](../tasks/APP-M2.md#app-m2-t019) | JobProgress：步骤、子进度、AI 紫进度条 | planned | APP-M2-T014 | M1-P05-F1 |
| [APP-M2-T020](../tasks/APP-M2.md#app-m2-t020) | JobProgress：SSE 订阅、断线提示与轮询回退 | planned | APP-M2-T014、APP-M2-T019 | M1-P05-F2 |
| [APP-M2-T021](../tasks/APP-M2.md#app-m2-t021) | 任务中心页基础 + 顶栏任务角标与抽屉 | planned | APP-M2-T014、APP-M2-T019、APP-M2-T020 | M1-P05-F3 |
| [APP-M2-T022](../tasks/APP-M2.md#app-m2-t022) | 平台管理员脱敏视图；从失败步骤重试、取消权限 | planned | APP-M2-T021 | M1-P05a-F1 |
| [APP-M2-T023](../tasks/APP-M2.md#app-m2-t023) | StatusTag 状态注册表（9.3 全部代码表） | planned | APP-M2-T005 | M1-P09-F1 |
| [APP-M2-T024](../tasks/APP-M2.md#app-m2-t024) | A-03 字典配置页 | planned | APP-M2-T005 | M1-P09-F2 |
| [APP-M2-T025](../tasks/APP-M2.md#app-m2-t025) | 扩展字段与公司设置键表单框架 | planned | APP-M2-T005、APP-M2-T024 | M1-P09-F3 |
| [APP-M2-T026](../tasks/APP-M2.md#app-m2-t026) | A-01 公司管理 | planned | APP-M2-T014 | M1-P10-F1 |
| [APP-M2-T027](../tasks/APP-M2.md#app-m2-t027) | A-02 用户列表、新增、停用前转交；“账号安全设置”面板（公司密码策略，只能调严） | planned | APP-M2-T014、APP-M2-T026 | M1-P10-F2 |
| [APP-M2-T028](../tasks/APP-M2.md#app-m2-t028) | A-02 角色分配、解锁、重置密码 | planned | APP-M2-T014、APP-M2-T027 | M1-P10-F3 |
| [APP-M2-T029](../tasks/APP-M2.md#app-m2-t029) | 顶栏铃铛与未读数 | planned | APP-M2-T010 | M1-P11-F1 |
| [APP-M2-T030](../tasks/APP-M2.md#app-m2-t030) | 提醒下拉：最近 7 条、标已读、全部已读 | planned | APP-M2-T010、APP-M2-T029 | M1-P11-F2 |
| [APP-M2-T031](../tasks/APP-M2.md#app-m2-t031) | G-02 站内提醒列表页（筛选、已读 / 未读、合并显示） | planned | APP-M2-T029 | M1-P11a-F1 |
| [APP-M2-T032](../tasks/APP-M2.md#app-m2-t032) | 17 类提醒的跳转目标映射与“对象已不存在”提示 | planned | APP-M2-T029、APP-M2-T031 | M1-P11a-F2 |
| [APP-M2-T033](../tasks/APP-M2.md#app-m2-t033) | BrandProvider 运行时主题 + 品牌校验函数（对比度、ΔE） | planned | APP-M2-T008 | M1-P15-F1 |
| [APP-M2-T034](../tasks/APP-M2.md#app-m2-t034) | A-12 界面品牌页（表单 + 预览 + 恢复默认） | planned | APP-M2-T008、APP-M2-T033 | M1-P15-F2 |
| [APP-M2-T035](../tasks/APP-M2.md#app-m2-t035) | 全局搜索：顶栏下拉与结果页 | planned | APP-M2-T014 | M1-P16-F1 |
| [APP-M2-T036](../tasks/APP-M2.md#app-m2-t036) | A-08 模型列表与 `service_status` | planned | APP-M2-T014 | M1-B01-F1 |
| [APP-M2-T037](../tasks/APP-M2.md#app-m2-t037) | 模型登记表单（不支持字段置灰）与测试连接 | planned | APP-M2-T014、APP-M2-T036 | M1-B01-F2 |
| [APP-M2-T038](../tasks/APP-M2.md#app-m2-t038) | 模型配置版本与回滚 | planned | APP-M2-T014、APP-M2-T037 | M1-B01-F3 |
| [APP-M2-T039](../tasks/APP-M2.md#app-m2-t039) | A-09 文档解析服务（云端 / 本地两组页签） | planned | APP-M2-T014、APP-M2-T021 | M1-B01-F4 |
| [APP-M2-T040](../tasks/APP-M2.md#app-m2-t040) | A-10 任务与模型对应表（首选本地 → 备用只列本地） | planned | APP-M2-T036 | M1-B02-F1 |
| [APP-M2-T041](../tasks/APP-M2.md#app-m2-t041) | A-05 公司模型开放 | planned | APP-M2-T036 | M1-B02-F2 |
| [APP-M2-T042](../tasks/APP-M2.md#app-m2-t042) | A-11 部署与服务状态页 | planned | APP-M2-T036 | M1-J01a-F1 |
| [APP-M2-T043](../tasks/APP-M2.md#app-m2-t043) | CrossFieldHint 组件与 9.11 规则函数 | planned | APP-M2-T025 | M2-B06-F1 |
| [APP-M2-T044](../tasks/APP-M2.md#app-m2-t044) | A-05 生成闭环参数 | planned | APP-M2-T025、APP-M2-T043 | M2-B06-F2 |
| [APP-M2-T045](../tasks/APP-M2.md#app-m2-t045) | 编辑台与对话助手参数（自动保存、心跳 15～120、锁超时） | planned | APP-M2-T025、APP-M2-T043 | M2-B06-F3 |
| [APP-M2-T046](../tasks/APP-M2.md#app-m2-t046) | 资料列表通用页 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | M2-C01-F1 |
| [APP-M2-T047](../tasks/APP-M2.md#app-m2-t047) | 资料详情通用页（附件槽位、来源） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017 | M2-C01-F2 |
| [APP-M2-T048](../tasks/APP-M2.md#app-m2-t048) | 确认 / 审核状态机界面（★ 字段重确认） | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047、APP-M2-T203 | M2-C01-F3 |
| [APP-M2-T049](../tasks/APP-M2.md#app-m2-t049) | 受限资料与转交 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | M2-C01-F4 |
| [APP-M2-T050](../tasks/APP-M2.md#app-m2-t050) | 变更历史与被引用情况 | planned | APP-M2-T005、APP-M2-T006、APP-M2-T017、APP-M2-T047 | M2-C01-F5 |
| [APP-M2-T051](../tasks/APP-M2.md#app-m2-t051) | 厂商产品树 | planned | APP-M2-T024 | M2-C02-F1 |
| [APP-M2-T052](../tasks/APP-M2.md#app-m2-t052) | 证书类别与附件槽位 | planned | APP-M2-T024、APP-M2-T051 | M2-C02-F2 |
| [APP-M2-T053](../tasks/APP-M2.md#app-m2-t053) | 中小企业划型标准 | planned | APP-M2-T024、APP-M2-T051 | M2-C02-F3 |
| [APP-M2-T054](../tasks/APP-M2.md#app-m2-t054) | 公司主体（含关联关系） | planned | APP-M2-T047 | M2-C03-F1 |
| [APP-M2-T055](../tasks/APP-M2.md#app-m2-t055) | 证明材料 | planned | APP-M2-T047 | M2-C03-F2 |
| [APP-M2-T056](../tasks/APP-M2.md#app-m2-t056) | 资质证书 | planned | APP-M2-T047 | M2-C03-F3 |
| [APP-M2-T057](../tasks/APP-M2.md#app-m2-t057) | 安全与合规事件 | planned | APP-M2-T047 | M2-C03-F4 |
| [APP-M2-T058](../tasks/APP-M2.md#app-m2-t058) | 工具与设备 | planned | APP-M2-T047、APP-M2-T051 | M2-C03-F5 |
| [APP-M2-T059](../tasks/APP-M2.md#app-m2-t059) | 附件库 | planned | APP-M2-T047 | M2-C03-F6 |
| [APP-M2-T060](../tasks/APP-M2.md#app-m2-t060) | 人员列表 | planned | APP-M2-T047、APP-M2-T059 | M2-C04-F1 |
| [APP-M2-T061](../tasks/APP-M2.md#app-m2-t061) | 人员详情（MaskedField） | planned | APP-M2-T047、APP-M2-T059、APP-M2-T017 | M2-C04-F2 |
| [APP-M2-T062](../tasks/APP-M2.md#app-m2-t062) | 人员证书 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T061、APP-M2-T052 | M2-C04-F3 |
| [APP-M2-T063](../tasks/APP-M2.md#app-m2-t063) | 占用（R12）与离职提示 | planned | APP-M2-T047、APP-M2-T059、APP-M2-T060 | M2-C04-F4 |
| [APP-M2-T064](../tasks/APP-M2.md#app-m2-t064) | 授权列表 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | M2-C05-F1 |
| [APP-M2-T065](../tasks/APP-M2.md#app-m2-t065) | 授权详情 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054 | M2-C05-F2 |
| [APP-M2-T066](../tasks/APP-M2.md#app-m2-t066) | 授权链图（不满足节点标红、上游未登记虚线） | planned | APP-M2-T047、APP-M2-T051、APP-M2-T054、APP-M2-T065 | M2-C05-F3 |
| [APP-M2-T067](../tasks/APP-M2.md#app-m2-t067) | 业绩列表与详情 | planned | APP-M2-T047、APP-M2-T051 | M2-C06-F1 |
| [APP-M2-T068](../tasks/APP-M2.md#app-m2-t068) | 业绩成员与产品 | planned | APP-M2-T047、APP-M2-T051、APP-M2-T067、APP-M2-T060 | M2-C06-F2 |
| [APP-M2-T069](../tasks/APP-M2.md#app-m2-t069) | SLA 模板（等级、变量） | planned | APP-M2-T047、APP-M2-T051 | M2-C06-F3 |
| [APP-M2-T070](../tasks/APP-M2.md#app-m2-t070) | 全局变量 | planned | APP-M2-T047、APP-M2-T051 | M2-C06-F4 |
| [APP-M2-T071](../tasks/APP-M2.md#app-m2-t071) | 资料库首页健康度卡片 | planned | APP-M2-T047 | M2-C07-F1 |
| [APP-M2-T072](../tasks/APP-M2.md#app-m2-t072) | Excel 批量导入与逐条 / 按批确认 | planned | APP-M2-T047、APP-M2-T046 | M2-C07-F2 |
| [APP-M2-T073](../tasks/APP-M2.md#app-m2-t073) | 有效期提醒与 A-04 资料库设置 | planned | APP-M2-T047 | M2-C07-F3 |
| [APP-M2-T074](../tasks/APP-M2.md#app-m2-t074) | 附件识别上传与进度 | planned | APP-M2-T047、APP-M2-T039 | M2-C08-F1 |
| [APP-M2-T075](../tasks/APP-M2.md#app-m2-t075) | 识别结果核对（“待核对”标记） | planned | APP-M2-T047、APP-M2-T039、APP-M2-T074 | M2-C08-F2 |
| [APP-M2-T076](../tasks/APP-M2.md#app-m2-t076) | 片段列表 | planned | APP-M2-T047 | M2-D01-F1 |
| [APP-M2-T077](../tasks/APP-M2.md#app-m2-t077) | 片段编辑（变量校验） | planned | APP-M2-T047、APP-M2-T076、APP-M2-T070 | M2-D01-F2 |
| [APP-M2-T078](../tasks/APP-M2.md#app-m2-t078) | 版本对比与发布（R31 拦截原因） | in-review | APP-M2-T047、APP-M2-T077、APP-M2-T238 | M2-D01-F3 |
| [APP-M2-T079](../tasks/APP-M2.md#app-m2-t079) | 同步状态与重新同步 | planned | APP-M2-T047、APP-M2-T078 | M2-D01-F4 |
| [APP-M2-T080](../tasks/APP-M2.md#app-m2-t080) | 历史标书单个 / 批量导入 | planned | APP-M2-T021 | M2-D02-F1 |
| [APP-M2-T081](../tasks/APP-M2.md#app-m2-t081) | 入库状态派生显示与摘取为片段 | planned | APP-M2-T021、APP-M2-T080 | M2-D02-F2 |
| [APP-M2-T082](../tasks/APP-M2.md#app-m2-t082) | 版本条（发布、回滚） | planned | APP-M2-T025 | M2-D03-F1 |
| [APP-M2-T083](../tasks/APP-M2.md#app-m2-t083) | 章节模板 | planned | APP-M2-T025、APP-M2-T082 | M2-D03-F2 |
| [APP-M2-T084](../tasks/APP-M2.md#app-m2-t084) | 叫法术语、语气称呼 | planned | APP-M2-T025、APP-M2-T082 | M2-D03-F3 |
| [APP-M2-T085](../tasks/APP-M2.md#app-m2-t085) | 句式规则 | planned | APP-M2-T025、APP-M2-T082 | M2-D03-F4 |
| [APP-M2-T086](../tasks/APP-M2.md#app-m2-t086) | Word 模板与导出命名 | planned | APP-M2-T025、APP-M2-T082 | M2-D03-F5 |
| [APP-M2-T087](../tasks/APP-M2.md#app-m2-t087) | 预览抽屉 | planned | APP-M2-T025、APP-M2-T083、APP-M2-T084、APP-M2-T085 | M2-D03-F6 |
| [APP-M2-T088](../tasks/APP-M2.md#app-m2-t088) | 任务卡列表与版本 | planned | APP-M2-T082 | M2-D04-F1 |
| [APP-M2-T089](../tasks/APP-M2.md#app-m2-t089) | 提示词模板编辑与发布校验 | planned | APP-M2-T082、APP-M2-T088 | M2-D04-F2 |
| [APP-M2-T090](../tasks/APP-M2.md#app-m2-t090) | 平台默认与公司覆盖对照 | planned | APP-M2-T082、APP-M2-T089 | M2-D04-F3 |
| [APP-M2-T091](../tasks/APP-M2.md#app-m2-t091) | 审查清单 | planned | APP-M2-T082 | M2-D05-F1 |
| [APP-M2-T092](../tasks/APP-M2.md#app-m2-t092) | 风格样例卡片墙（启用开关） | planned | APP-M2-T082、APP-M2-T081 | M2-D05-F2 |
| [APP-M2-T093](../tasks/APP-M2.md#app-m2-t093) | 入库脱敏扫描结果展示 | planned | APP-M2-T082、APP-M2-T092、APP-M2-T230、APP-M2-T238、APP-M2-T243 | M2-D05-F3 |
| [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094) | ProjectHeader 摘要条与页签（无“资料匹配”） | planned | APP-M1-T14 | M3-E01-F1 |
| [APP-M2-T095](../tasks/APP-M2.md#app-m2-t095) | 项目列表 | planned | APP-M1-T14 | M3-E01-F2 |
| [APP-M2-T096](../tasks/APP-M2.md#app-m2-t096) | 新建项目与 R19 提示 | planned | APP-M1-T14、APP-M2-T224 | M3-E01-F3 |
| [APP-M2-T097](../tasks/APP-M2.md#app-m2-t097) | 项目概览（待办、分册、状态操作） | planned | APP-M1-T14、APP-M2-T094 | M3-E01-F4 |
| [APP-M2-T098](../tasks/APP-M2.md#app-m2-t098) | 项目基本字段和合作方协议（成员复用T14） | planned | APP-M1-T14、APP-M2-T054 | M3-E01-F5 |
| [APP-M2-T099](../tasks/APP-M2.md#app-m2-t099) | 项目设置：拟派人员、SLA 取值、规则覆盖 | planned | APP-M1-T14、APP-M2-T060、APP-M2-T069 | M3-E01-F6 |
| [APP-M2-T100](../tasks/APP-M2.md#app-m2-t100) | 分册格式、闭环及导出设置（分工复用T14） | planned | APP-M1-T14、APP-M2-T044、APP-M2-T045、APP-M2-T086 | M3-E01-F7 |
| [APP-M2-T101](../tasks/APP-M2.md#app-m2-t101) | 招标文件上传与版本链 | planned | APP-M1-T02、APP-M2-T021 | M3-E02-F1 |
| [APP-M2-T102](../tasks/APP-M2.md#app-m2-t102) | 解析进度页（JobProgress 接入） | planned | APP-M1-T02、APP-M2-T021、APP-M2-T101 | M3-E02-F2 |
| [APP-M2-T103](../tasks/APP-M2.md#app-m2-t103) | PdfLocator（PDF.js 本地 Worker、跳页高亮） | planned | APP-M1-T02、APP-M2-T101 | M3-E04-F1 |
| [APP-M2-T104](../tasks/APP-M2.md#app-m2-t104) | 解析结果三栏布局与分类树 | planned | APP-M1-T02、APP-M2-T103 | M3-E04-F2 |
| [APP-M2-T105](../tasks/APP-M2.md#app-m2-t105) | 条目卡片编辑与逐条确认 | planned | APP-M1-T02、APP-M2-T104 | M3-E04-F3 |
| [APP-M2-T106](../tasks/APP-M2.md#app-m2-t106) | 批量确认（星号 / 废标 / 资格禁用）与置信度高亮 | planned | APP-M1-T02、APP-M2-T105 | M3-E04-F4 |
| [APP-M2-T107](../tasks/APP-M2.md#app-m2-t107) | 重抽不覆盖与补遗差异 | planned | APP-M1-T02、APP-M2-T105、APP-M2-T101 | M3-E04-F5 |
| [APP-M2-T108](../tasks/APP-M2.md#app-m2-t108) | “确认解析结果”闸门（悬停列未满足项） | planned | APP-M1-T02、APP-M2-T106、APP-M2-T107、APP-M2-T109、APP-M2-T110、APP-M2-T111 | M3-E04-F6 |
| [APP-M2-T109](../tasks/APP-M2.md#app-m2-t109) | 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换） | planned | APP-M2-T104、APP-M2-T019 | M3-E04a-F1 |
| [APP-M2-T110](../tasks/APP-M2.md#app-m2-t110) | 冲突待选定页签（并列取值、理由必填） | planned | APP-M2-T104、APP-M2-T109 | M3-E04a-F2 |
| [APP-M2-T111](../tasks/APP-M2.md#app-m2-t111) | 疑似遗漏（无批量、排除须理由）与引用未解析页签 | planned | APP-M2-T104、APP-M2-T148、APP-M2-T109 | M3-E04a-F3 |
| [APP-M2-T112](../tasks/APP-M2.md#app-m2-t112) | 矩阵表格与筛选（风险提示） | planned | APP-M1-T03 | M3-E05-F1 |
| [APP-M2-T113](../tasks/APP-M2.md#app-m2-t113) | 行编辑（响应方式、要点、负责人） | planned | APP-M1-T03、APP-M2-T112 | M3-E05-F2 |
| [APP-M2-T114](../tasks/APP-M2.md#app-m2-t114) | EvidenceDrawer | done | APP-M1-T03、APP-M2-T048、APP-M2-T204、APP-M2-T205 | M3-E05-F3 |
| [APP-M2-T115](../tasks/APP-M2.md#app-m2-t115) | 批量智能匹配与逐行确认 | planned | APP-M1-T03、APP-M2-T118 | M3-E05-F4 |
| [APP-M2-T116](../tasks/APP-M2.md#app-m2-t116) | P-18 分册分流确认 | planned | APP-M1-T03、APP-M1-T14 | M3-E05-F5 |
| [APP-M2-T117](../tasks/APP-M2.md#app-m2-t117) | Excel 导出与确认闸门 | planned | APP-M1-T03、APP-M2-T113、APP-M2-T114、APP-M2-T116 | M3-E05-F6 |
| [APP-M2-T118](../tasks/APP-M2.md#app-m2-t118) | 挂证据候选的三路显示（结构化规则匹配 / 片段检索 / 历史标书仅参考） | planned | APP-M2-T114、APP-M2-T078、APP-M2-T081 | M3-E05a-F1 |
| [APP-M2-T119](../tasks/APP-M2.md#app-m2-t119) | SLA 矩阵表与判定 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T069 | M3-E06-F1 |
| [APP-M2-T120](../tasks/APP-M2.md#app-m2-t120) | 模板取值与承诺函导出 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119 | M3-E06-F2 |
| [APP-M2-T121](../tasks/APP-M2.md#app-m2-t121) | 项目事实表 | planned | APP-M1-T10、APP-M1-T12 | M3-E06-F3 |
| [APP-M2-T122](../tasks/APP-M2.md#app-m2-t122) | “需复核”传播提示 | planned | APP-M1-T10、APP-M1-T12、APP-M2-T119、APP-M2-T121 | M3-E06-F4 |
| [APP-M2-T123](../tasks/APP-M2.md#app-m2-t123) | 大纲排序、章节类型和增值理由（分工复用T15） | planned | APP-M1-T15、APP-M2-T116 | M4-F01-F1 |
| [APP-M2-T124](../tasks/APP-M2.md#app-m2-t124) | 完整证据、片段及评分写作计划（确认复用T15） | blocked | APP-M1-T15、APP-M2-T078、APP-M2-T114 | M4-F01-F2 |
| [APP-M2-T125](../tasks/APP-M2.md#app-m2-t125) | 招标原文预览联动与 R26 提示 | planned | APP-M1-T15、APP-M2-T123、APP-M2-T232 | M4-F01-F3 |
| [APP-M2-T126](../tasks/APP-M2.md#app-m2-t126) | 按逐节确认结果启动生成（确认复用T15） | planned | APP-M1-T15、APP-M2-T124、APP-M2-T125 | M4-F01-F4 |
| [APP-M2-T127](../tasks/APP-M2.md#app-m2-t127) | 五类系统生成章节预览 | planned | APP-M1-T04、APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T194、APP-M2-T195 | M4-F09-F1 |
| [APP-M2-T128](../tasks/APP-M2.md#app-m2-t128) | 锁定提示与“去数据源修改” | planned | APP-M1-T04、APP-M2-T127、APP-M2-T163 | M4-F09-F2 |
| [APP-M2-T129](../tasks/APP-M2.md#app-m2-t129) | 章节列表（编辑台入口） | planned | APP-M2-T126、APP-M2-T021 | M4-F10-F1 |
| [APP-M2-T130](../tasks/APP-M2.md#app-m2-t130) | 章节循环进度页 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T044、APP-M2-T234、APP-M2-T237、APP-M2-T238、APP-M2-T254、APP-M2-T244、APP-M2-T245、APP-M2-T246、APP-M2-T247、APP-M2-T248、APP-M2-T249 | M4-F10-F2 |
| [APP-M2-T131](../tasks/APP-M2.md#app-m2-t131) | 轮次时间线 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | M4-F10-F3 |
| [APP-M2-T132](../tasks/APP-M2.md#app-m2-t132) | 版本对比（复用 DiffView） | planned | APP-M2-T126、APP-M2-T021、APP-M2-T175 | M4-F10-F4 |
| [APP-M2-T133](../tasks/APP-M2.md#app-m2-t133) | 人工处理队列列表 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | M4-F10-F5 |
| [APP-M2-T134](../tasks/APP-M2.md#app-m2-t134) | 队列详情单段编辑 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T133、APP-M2-T174 | M4-F10-F6 |
| [APP-M2-T135](../tasks/APP-M2.md#app-m2-t135) | 一键重新检查 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T134 | M4-F10-F7 |
| [APP-M2-T136](../tasks/APP-M2.md#app-m2-t136) | 异常中断与重试 | planned | APP-M2-T126、APP-M2-T021、APP-M2-T130 | M4-F10-F8 |
| [APP-M2-T137](../tasks/APP-M2.md#app-m2-t137) | W-03 公司级写作观察统计 | planned | APP-M2-T131、APP-M2-T189 | M4-F11-F1 |
| [APP-M2-T138](../tasks/APP-M2.md#app-m2-t138) | P-17 项目级折叠区 | planned | APP-M2-T131、APP-M2-T189 | M4-F11-F2 |
| [APP-M2-T139](../tasks/APP-M2.md#app-m2-t139) | 图表组件（AntV G2，待技术确认） | planned | APP-M2-T131、APP-M2-T189 | M4-F11-F3 |
| [APP-M2-T140](../tasks/APP-M2.md#app-m2-t140) | RuleIssueList | planned | APP-M1-T05 | M5-G04-F1 |
| [APP-M2-T141](../tasks/APP-M2.md#app-m2-t141) | 合规检查页布局与结论条 | planned | APP-M1-T05、APP-M2-T140 | M5-G04-F2 |
| [APP-M2-T142](../tasks/APP-M2.md#app-m2-t142) | 警告放行（理由必填，阻断无放行） | planned | APP-M1-T05、APP-M2-T140 | M5-G04-F3 |
| [APP-M2-T143](../tasks/APP-M2.md#app-m2-t143) | R18 段落相似度并排对比 | planned | APP-M1-T05、APP-M2-T223 | M5-G04-F4 |
| [APP-M2-T144](../tasks/APP-M2.md#app-m2-t144) | 分册检查 / 定稿 / 解锁 / 交叉复核 | planned | APP-M1-T05、APP-M2-T142、APP-M2-T228、APP-M2-T229、APP-M2-T250、APP-M2-T251、APP-M2-T252、APP-M2-T255、APP-M2-T256、APP-M2-T257、APP-M2-T258 | M5-G04-F5 |
| [APP-M2-T145](../tasks/APP-M2.md#app-m2-t145) | 全文检查与“结果已过期”提示 | planned | APP-M1-T05、APP-M2-T144 | M5-G04-F6 |
| [APP-M2-T146](../tasks/APP-M2.md#app-m2-t146) | 合规规则页签（不可关闭锁、R43 无阻断） | planned | APP-M2-T025 | M5-G06-F1 |
| [APP-M2-T147](../tasks/APP-M2.md#app-m2-t147) | 规则参数、恢复平台默认、修改历史 | planned | APP-M2-T025、APP-M2-T146 | M5-G06-F2 |
| [APP-M2-T148](../tasks/APP-M2.md#app-m2-t148) | 兜底扫描词表（草稿、试扫、发布） | planned | APP-M2-T025、APP-M2-T146 | M5-G06-F3 |
| [APP-M2-T149](../tasks/APP-M2.md#app-m2-t149) | 导出前提检查 | planned | APP-M1-T05、APP-M2-T145 | M5-H03-F1 |
| [APP-M2-T150](../tasks/APP-M2.md#app-m2-t150) | 导出类型、模板与命名 | planned | APP-M1-T05、APP-M2-T196、APP-M2-T197、APP-M2-T198 | M5-H03-F2 |
| [APP-M2-T151](../tasks/APP-M2.md#app-m2-t151) | 导出历史与下载（`export_status` 含排队） | planned | APP-M1-T05、APP-M2-T202 | M5-H03-F3 |
| [APP-M2-T152](../tasks/APP-M2.md#app-m2-t152) | 递交版：仅项目负责人可见、已确认完整值类别展示、内部稿掩码说明 | planned | APP-M2-T149、APP-M2-T100、APP-M2-T017、APP-M2-T196 | M5-H04-F1 |
| [APP-M2-T153](../tasks/APP-M2.md#app-m2-t153) | 工作台 6 张统计卡（点击即筛选） | planned | APP-M2-T095 | M5-E01b-F1 |
| [APP-M2-T154](../tasks/APP-M2.md#app-m2-t154) | 概览底部折叠区 | planned | APP-M2-T095 | M5-E01b-F2 |
| [APP-M2-T155](../tasks/APP-M2.md#app-m2-t155) | 集团管理员公司切换与只读视图 | planned | APP-M2-T016 | M5-J02-F1 |
| [APP-M2-T156](../tasks/APP-M2.md#app-m2-t156) | 集团统计 | planned | APP-M2-T016 | M5-J02-F2 |
| [APP-M2-T157](../tasks/APP-M2.md#app-m2-t157) | A-06 审计日志页 | planned | APP-M2-T014 | M5-J01-F1 |
| [APP-M2-T158](../tasks/APP-M2.md#app-m2-t158) | 云端调用审计展开 | planned | APP-M2-T014、APP-M2-T157、APP-M2-T037 | M5-J01-F2 |
| [APP-M2-T159](../tasks/APP-M2.md#app-m2-t159) | 服务健康基础与 A-11（M1-J01a）对齐 | planned | APP-M2-T014、APP-M2-T042 | M5-J01-F3 |
| [APP-M2-T160](../tasks/APP-M2.md#app-m2-t160) | 编辑台布局与三档断点（四栏 / 三栏 / 紧凑） | planned | APP-M1-T15 | M6-I01-F1 |
| [APP-M2-T161](../tasks/APP-M2.md#app-m2-t161) | 章节加载与段落键 | planned | APP-M1-T15 | M6-I01-F2 |
| [APP-M2-T162](../tasks/APP-M2.md#app-m2-t162) | SourceBar 来源标记 | planned | APP-M1-T15、APP-M2-T161 | M6-I01-F3 |
| [APP-M2-T163](../tasks/APP-M2.md#app-m2-t163) | 锁定内容 | planned | APP-M1-T15、APP-M2-T161 | M6-I01-F4 |
| [APP-M2-T164](../tasks/APP-M2.md#app-m2-t164) | 变量节点 | planned | APP-M1-T15、APP-M2-T161 | M6-I01-F5 |
| [APP-M2-T165](../tasks/APP-M2.md#app-m2-t165) | 证据节点与 `.cite` | planned | APP-M1-T15、APP-M2-T161、APP-M2-T048 | M6-I01-F6 |
| [APP-M2-T166](../tasks/APP-M2.md#app-m2-t166) | 问题标注与侧栏联动 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T140 | M6-I01-F7 |
| [APP-M2-T167](../tasks/APP-M2.md#app-m2-t167) | 选区悬浮工具条 | planned | APP-M1-T15、APP-M2-T161 | M6-I01-F8 |
| [APP-M2-T168](../tasks/APP-M2.md#app-m2-t168) | 目录树与章节切换 | planned | APP-M1-T15、APP-M2-T161 | M6-I01-F9 |
| [APP-M2-T169](../tasks/APP-M2.md#app-m2-t169) | 工具栏紧凑模式（“格式”下拉） | planned | APP-M1-T15、APP-M2-T160 | M6-I01-F10 |
| [APP-M2-T170](../tasks/APP-M2.md#app-m2-t170) | 只读态（他人编辑中） | planned | APP-M1-T15、APP-M2-T173 | M6-I01-F11 |
| [APP-M2-T171](../tasks/APP-M2.md#app-m2-t171) | 长章节性能 | planned | APP-M1-T15、APP-M2-T161、APP-M2-T166、APP-M2-T167 | M6-I01-F12 |
| [APP-M2-T172](../tasks/APP-M2.md#app-m2-t172) | 自动保存草稿 | planned | APP-M2-T161 | M6-I02-F1 |
| [APP-M2-T173](../tasks/APP-M2.md#app-m2-t173) | EditLockBadge、心跳、超时提示、接管 | planned | APP-M2-T161 | M6-I02-F2 |
| [APP-M2-T174](../tasks/APP-M2.md#app-m2-t174) | 提交版本与版本历史 | planned | APP-M2-T161、APP-M2-T172、APP-M2-T173 | M6-I02-F3 |
| [APP-M2-T175](../tasks/APP-M2.md#app-m2-t175) | 版本对比与回退 | planned | APP-M2-T161、APP-M2-T174 | M6-I02-F4 |
| [APP-M2-T176](../tasks/APP-M2.md#app-m2-t176) | 对话面板与会话列表 | planned | APP-M2-T167、APP-M2-T089 | M6-I04-F1 |
| [APP-M2-T177](../tasks/APP-M2.md#app-m2-t177) | 流式输出、模型标识、降级提示 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T040 | M6-I04-F2 |
| [APP-M2-T178](../tasks/APP-M2.md#app-m2-t178) | 建议卡片（写法、差异、来源、预检） | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T242、APP-M2-T243、APP-M2-T244、APP-M2-T248 | M6-I04-F3 |
| [APP-M2-T179](../tasks/APP-M2.md#app-m2-t179) | 自由问答（只“复制”） | planned | APP-M2-T167、APP-M2-T089、APP-M2-T181 | M6-I04-F4 |
| [APP-M2-T180](../tasks/APP-M2.md#app-m2-t180) | 上下文与样例任务卡选择 | planned | APP-M2-T167、APP-M2-T089、APP-M2-T176、APP-M2-T124 | M6-I04-F5 |
| [APP-M2-T181](../tasks/APP-M2.md#app-m2-t181) | 资料库与本项目数据答案卡 | planned | APP-M2-T176、APP-M2-T047、APP-M2-T112 | M6-I04a-F1 |
| [APP-M2-T182](../tasks/APP-M2.md#app-m2-t182) | 直查未命中与常规回答回退 | planned | APP-M2-T176、APP-M2-T047、APP-M2-T112、APP-M2-T181 | M6-I04a-F2 |
| [APP-M2-T183](../tasks/APP-M2.md#app-m2-t183) | 插入为引用：差异视图、写入、引用标记 | planned | APP-M2-T181、APP-M2-T185 | M6-I04b-F1 |
| [APP-M2-T184](../tasks/APP-M2.md#app-m2-t184) | 本项目招标文件轻量索引的检索结果展示 | planned | APP-M2-T181 | M6-E08-F1 |
| [APP-M2-T185](../tasks/APP-M2.md#app-m2-t185) | 差异确认写入 | planned | APP-M2-T167、APP-M2-T178 | M6-I05-F1 |
| [APP-M2-T186](../tasks/APP-M2.md#app-m2-t186) | “我已逐字核对”二次确认（星号 / 废标 / 偏离 / 披露） | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | M6-I05-F2 |
| [APP-M2-T187](../tasks/APP-M2.md#app-m2-t187) | 冲突校验与重新定位提示 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185 | M6-I05-F3 |
| [APP-M2-T188](../tasks/APP-M2.md#app-m2-t188) | 粘贴识别 | planned | APP-M2-T167、APP-M2-T178、APP-M2-T185、APP-M2-T242、APP-M2-T243 | M6-I05-F4 |
| [APP-M2-T189](../tasks/APP-M2.md#app-m2-t189) | 对话助手观察指标 | planned | APP-M2-T174、APP-M2-T185 | M6-I06-F1 |
| [APP-M2-T190](../tasks/APP-M2.md#app-m2-t190) | 人工修改率分项 | planned | APP-M2-T174、APP-M2-T185 | M6-I06-F2 |
| [APP-M2-T191](../tasks/APP-M2.md#app-m2-t191) | 点对点应答确定性章节 | planned | APP-M2-T113、APP-M2-T116 | PRD-v1.8-§5.7.2、5.11.8 |
| [APP-M2-T192](../tasks/APP-M2.md#app-m2-t192) | 评审索引确定性章节 | planned | APP-M2-T113、APP-M2-T123 | PRD-v1.8-§5.7.2、5.9.1、R40 |
| [APP-M2-T193](../tasks/APP-M2.md#app-m2-t193) | 偏离表确定性章节 | planned | APP-M2-T113、APP-M2-T116 | PRD-v1.8-§5.7.2、R37 |
| [APP-M2-T194](../tasks/APP-M2.md#app-m2-t194) | 年度服务计划确定性章节 | planned | APP-M2-T121、APP-M2-T113 | PRD-v1.8-§5.7.2、5.11.8 |
| [APP-M2-T195](../tasks/APP-M2.md#app-m2-t195) | 证明材料清单确定性章节 | planned | APP-M2-T114、APP-M2-T059、APP-M2-T099 | PRD-v1.8-§5.7.2、R41 |
| [APP-M2-T196](../tasks/APP-M2.md#app-m2-t196) | Word模板与正文样式渲染 | planned | APP-M2-T086、APP-M2-T161 | PRD-v1.8-§5.9.1规则1、5、6 |
| [APP-M2-T197](../tasks/APP-M2.md#app-m2-t197) | 分册封面、目录与页码 | planned | APP-M2-T196、APP-M2-T100 | PRD-v1.8-§5.9.1规则2～4 |
| [APP-M2-T198](../tasks/APP-M2.md#app-m2-t198) | 指定附件页与敏感水印 | planned | APP-M2-T196、APP-M2-T059 | PRD-v1.8-§5.9.1规则7、R14 |
| [APP-M2-T199](../tasks/APP-M2.md#app-m2-t199) | Word属性修订与批注清理 | planned | APP-M2-T196 | PRD-v1.8-§5.9.1规则10、R25 |
| [APP-M2-T200](../tasks/APP-M2.md#app-m2-t200) | 同批合标核对清单输出 | planned | APP-M2-T149、APP-M2-T197、APP-M2-T192、APP-M2-T193 | PRD-v1.8-§5.9.2 |
| [APP-M2-T201](../tasks/APP-M2.md#app-m2-t201) | 内部响应追溯Excel | planned | APP-M2-T117、APP-M2-T162、APP-M2-T165 | PRD-v1.8-§5.9.1规则12 |
| [APP-M2-T202](../tasks/APP-M2.md#app-m2-t202) | 递交批次原子输出和历史快照 | planned | APP-M2-T152、APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T200 | PRD-v1.8-§5.9.1规则13、14及异常 |
| [APP-M2-T203](../tasks/APP-M2.md#app-m2-t203) | R01 不可引用的资料禁止引用 | planned | APP-M2-T047、APP-M2-T077 | R01 |
| [APP-M2-T204](../tasks/APP-M2.md#app-m2-t204) | R02 资料来源分级与投标主体一致 | planned | APP-M2-T054、APP-M2-T098 | R02 |
| [APP-M2-T205](../tasks/APP-M2.md#app-m2-t205) | R03 有效期覆盖投标截止时间 | planned | APP-M2-T047、APP-M2-T099 | R03 |
| [APP-M2-T206](../tasks/APP-M2.md#app-m2-t206) | R04 临期与复审提醒 | planned | APP-M2-T073、APP-M2-T031 | R04 |
| [APP-M2-T207](../tasks/APP-M2.md#app-m2-t207) | R05 年审/监督审核有效 | planned | APP-M2-T056 | R05 |
| [APP-M2-T208](../tasks/APP-M2.md#app-m2-t208) | R06 持证单位与主体名称一致 | planned | APP-M2-T056、APP-M2-T075 | R06 |
| [APP-M2-T209](../tasks/APP-M2.md#app-m2-t209) | R07 原厂授权覆盖招标涉及的全部产品，授权链逐级有效，地域覆盖到地 | planned | APP-M2-T066、APP-M2-T051 | R07 |
| [APP-M2-T210](../tasks/APP-M2.md#app-m2-t210) | R08 拟派人员持有招标涉及产品的有效原厂认证 | planned | APP-M2-T062、APP-M2-T099 | R08 |
| [APP-M2-T211](../tasks/APP-M2.md#app-m2-t211) | R09 故障等级与服务时段 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | R09 |
| [APP-M2-T212](../tasks/APP-M2.md#app-m2-t212) | R09 全类别SLA及能力比较 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | R09 |
| [APP-M2-T213](../tasks/APP-M2.md#app-m2-t213) | R09 模板外承诺类事实 | planned | APP-M2-T119、APP-M2-T121、APP-M2-T069 | R09 |
| [APP-M2-T214](../tasks/APP-M2.md#app-m2-t214) | R10 手写与自然表达全文承诺 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | R10 |
| [APP-M2-T215](../tasks/APP-M2.md#app-m2-t215) | R10 结构节点及确定性输出 | planned | APP-M2-T119、APP-M2-T164、APP-M2-T193 | R10 |
| [APP-M2-T216](../tasks/APP-M2.md#app-m2-t216) | R11 本单位人员与社保核对 | planned | APP-M2-T061、APP-M2-T099 | R11 |
| [APP-M2-T217](../tasks/APP-M2.md#app-m2-t217) | R12 人员占用冲突 | planned | APP-M2-T063、APP-M2-T099 | R12 |
| [APP-M2-T218](../tasks/APP-M2.md#app-m2-t218) | R13 业绩满足资格与评分条件 | planned | APP-M2-T067、APP-M2-T068 | R13 |
| [APP-M2-T219](../tasks/APP-M2.md#app-m2-t219) | R14 必备附件齐全 | planned | APP-M2-T059、APP-M2-T195、APP-M2-T198 | R14 |
| [APP-M2-T220](../tasks/APP-M2.md#app-m2-t220) | R15 占位符与【待补】清零 | planned | APP-M2-T164、APP-M2-T165 | R15 |
| [APP-M2-T221](../tasks/APP-M2.md#app-m2-t221) | R16 主体基本资格与证明材料时效 | planned | APP-M2-T054、APP-M2-T055 | R16 |
| [APP-M2-T222](../tasks/APP-M2.md#app-m2-t222) | R17 使用提示与保密项目提醒 | planned | APP-M2-T047、APP-M2-T100 | R17 |
| [APP-M2-T223](../tasks/APP-M2.md#app-m2-t223) | R18 相似度检查 | planned | APP-M2-T095、APP-M2-T161 | R18 |
| [APP-M2-T224](../tasks/APP-M2.md#app-m2-t224) | R19 关联投标冲突 | planned | APP-M1-T01、APP-M2-T054 | R19 |
| [APP-M2-T225](../tasks/APP-M2.md#app-m2-t225) | R20 同一编写人 | planned | APP-M2-T028、APP-M2-T174 | R20 |
| [APP-M2-T226](../tasks/APP-M2.md#app-m2-t226) | R21 不同公司同一项目拟派人员为同一人 | planned | APP-M2-T061、APP-M2-T099 | R21 |
| [APP-M2-T227](../tasks/APP-M2.md#app-m2-t227) | R22 不同公司同一项目的保证金转出账户相同 | planned | APP-M2-T054、APP-M2-T100 | R22 |
| [APP-M2-T228](../tasks/APP-M2.md#app-m2-t228) | R23 星号条款、废标条款全部已确认响应 | planned | APP-M2-T105、APP-M2-T113 | R23 |
| [APP-M2-T229](../tasks/APP-M2.md#app-m2-t229) | R24 格式要求 | planned | APP-M2-T191、APP-M2-T192、APP-M2-T193、APP-M2-T197 | R24 |
| [APP-M2-T230](../tasks/APP-M2.md#app-m2-t230) | R25 名称机构残留 | planned | APP-M2-T161、APP-M2-T199 | R25 |
| [APP-M2-T231](../tasks/APP-M2.md#app-m2-t231) | R25 Word元数据残留 | planned | APP-M2-T161、APP-M2-T199 | R25 |
| [APP-M2-T232](../tasks/APP-M2.md#app-m2-t232) | R26 评分项覆盖度 | planned | APP-M2-T123、APP-M2-T113、APP-M2-T161 | R26 |
| [APP-M2-T233](../tasks/APP-M2.md#app-m2-t233) | R27 项目事实一致 | planned | APP-M2-T121、APP-M2-T164 | R27 |
| [APP-M2-T234](../tasks/APP-M2.md#app-m2-t234) | R28 章节模型评审 | planned | APP-M2-T091、APP-M2-T089、APP-M2-T044、APP-M2-T161 | R28 |
| [APP-M2-T235](../tasks/APP-M2.md#app-m2-t235) | R29 本公司查重 | planned | APP-M2-T081、APP-M2-T078、APP-M2-T073、APP-M2-T161 | R29 |
| [APP-M2-T236](../tasks/APP-M2.md#app-m2-t236) | R30 无条款段落及范围外服务 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | R30 |
| [APP-M2-T237](../tasks/APP-M2.md#app-m2-t237) | R30 额外数值承诺 | planned | APP-M2-T123、APP-M2-T121、APP-M2-T162 | R30 |
| [APP-M2-T238](../tasks/APP-M2.md#app-m2-t238) | R31 正文敏感值与真实报告 | planned | APP-M2-T161、APP-M2-T059 | R31 |
| [APP-M2-T239](../tasks/APP-M2.md#app-m2-t239) | R31 插图识别文字与报告附件 | planned | APP-M2-T161、APP-M2-T059 | R31 |
| [APP-M2-T240](../tasks/APP-M2.md#app-m2-t240) | R32 产品范围一致 | planned | APP-M2-T051、APP-M2-T099、APP-M2-T161 | R32 |
| [APP-M2-T241](../tasks/APP-M2.md#app-m2-t241) | R33 拟派人员条件 | planned | APP-M2-T061、APP-M2-T062、APP-M2-T105、APP-M2-T099 | R33 |
| [APP-M2-T242](../tasks/APP-M2.md#app-m2-t242) | R34 AI 痕迹与格式符号残留 | planned | APP-M2-T161、APP-M2-T089 | R34 |
| [APP-M2-T243](../tasks/APP-M2.md#app-m2-t243) | R35 称呼一致 | planned | APP-M2-T084、APP-M2-T098、APP-M2-T161 | R35 |
| [APP-M2-T244](../tasks/APP-M2.md#app-m2-t244) | R43 套话空泛词密度 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | R43 |
| [APP-M2-T245](../tasks/APP-M2.md#app-m2-t245) | R43 七类句式及总结策略 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | R43 |
| [APP-M2-T246](../tasks/APP-M2.md#app-m2-t246) | R43 注入风格样例照抄 | planned | APP-M2-T084、APP-M2-T085、APP-M2-T092、APP-M2-T162 | R43 |
| [APP-M2-T247](../tasks/APP-M2.md#app-m2-t247) | R44 得分要点事实密度 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | R44 |
| [APP-M2-T248](../tasks/APP-M2.md#app-m2-t248) | R44 逐事实锚点与段落归属 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | R44 |
| [APP-M2-T249](../tasks/APP-M2.md#app-m2-t249) | R44 未登记关键事实前后矛盾 | planned | APP-M2-T124、APP-M2-T162、APP-M2-T165、APP-M1-T12 | R44 |
| [APP-M2-T250](../tasks/APP-M2.md#app-m2-t250) | R36 人员资质证明跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | R36 |
| [APP-M2-T251](../tasks/APP-M2.md#app-m2-t251) | R36 偏离和证据版本跨册一致 | planned | APP-M2-T195、APP-M2-T193、APP-M2-T099、APP-M2-T116 | R36 |
| [APP-M2-T252](../tasks/APP-M2.md#app-m2-t252) | R37 偏离表一致性 | planned | APP-M2-T193、APP-M2-T113 | R37 |
| [APP-M2-T253](../tasks/APP-M2.md#app-m2-t253) | R38 证明材料与评分要点对应 | planned | APP-M2-T058、APP-M2-T059、APP-M2-T114、APP-M2-T075 | R38 |
| [APP-M2-T254](../tasks/APP-M2.md#app-m2-t254) | R39 披露类条款 | planned | APP-M2-T057、APP-M2-T105、APP-M2-T161 | R39 |
| [APP-M2-T255](../tasks/APP-M2.md#app-m2-t255) | R40 评审索引表 | planned | APP-M2-T192、APP-M2-T123 | R40 |
| [APP-M2-T256](../tasks/APP-M2.md#app-m2-t256) | R41 证明材料齐全与盖章 | planned | APP-M2-T195、APP-M2-T059、APP-M2-T099 | R41 |
| [APP-M2-T257](../tasks/APP-M2.md#app-m2-t257) | R42 暗标正文节点 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | R42 |
| [APP-M2-T258](../tasks/APP-M2.md#app-m2-t258) | R42 暗标输出全部位置 | planned | APP-M2-T197、APP-M2-T198、APP-M2-T199、APP-M2-T100 | R42 |
| [APP-M2-T259](../tasks/APP-M2.md#app-m2-t259) | 公司年度中小企业划型记录及声明取值 | planned | APP-M2-T053、APP-M2-T054、APP-M2-T047 | PRD-v1.8-§5.4.7-K08 |

## 机器可读副本

下列JSON是任务/来源/依赖关系的结构化副本，便于看板登记及审计，不是运行输出；维护时与正文共同更新。最终任务状态以看板和实际交付为准。

<!-- icg-task-map:start -->
```json
{
  "why": "供看板登记及覆盖审计，不是产品运行数据",
  "problem": "防止原47页面/44规则遗漏或重复计完成",
  "version": "icg-task-map-1",
  "date": "2026-10-11",
  "issue": "ISSUE-007",
  "task": "APP-M1-T07",
  "counts": {
    "new_tasks": 259,
    "original_subcards": 190,
    "artifact_units": 13,
    "rule_units": 56,
    "page_groups": 47,
    "rules": 44,
    "phase_1_full_rules": 36,
    "phase_1_simplified_rules": 3,
    "phase_2_rules": 5
  },
  "existing_tasks": [
    {
      "id": "APP-M1-T14",
      "title": "项目成员与分册分工",
      "status": "in-progress",
      "counts_as_new": false,
      "source": [
        "M3-E01-F5",
        "M3-E01-F7",
        "M4-F01-F1"
      ]
    },
    {
      "id": "APP-M1-T15",
      "title": "逐章分工与独立写作方案确认",
      "status": "in-progress",
      "counts_as_new": false,
      "source": [
        "M4-F01-F1",
        "M4-F01-F2",
        "M4-F01-F4",
        "M6-I01-F9"
      ]
    }
  ],
  "tasks": [
    {
      "id": "APP-M2-T001",
      "title": "ProLayout 布局、路由、权限守卫、请求层",
      "status": "in-review",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-01",
      "source_key": "P08.F1",
      "dependencies": [
        "BE-M0-T01"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T002",
      "title": "请求层细化：错误体、traceId 复制、Idempotency-Key 注入、重试策略",
      "status": "in-review",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F2",
      "source_key": "P08.F2",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T001"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T003",
      "title": "通用状态组件（骨架、空态、错误、无权限、已过期、只读）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F3",
      "source_key": "P08.F3",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T001"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T004",
      "title": "业务小组件：LevelTag、AiTag、DirectTag、Cite、SourceBar",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F4",
      "source_key": "P08.F4",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T003"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T005",
      "title": "元数据驱动表格（ProTable 封装、列合并、无横滚优先）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F5",
      "source_key": "P08.F5",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T003"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T006",
      "title": "元数据驱动表单（★ 字段、系统键两行标签、不支持字段置灰）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F6",
      "source_key": "P08.F6",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T003"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T007",
      "title": "表单通用：底部保存条、离开未保存提示、就近报错",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F7",
      "source_key": "P08.F7",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T006"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T008",
      "title": "主题运行时接口位与离线检查纳入 CI（应用级）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F8",
      "source_key": "P08.F8",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T001"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T009",
      "title": "断点与侧栏记忆（1280 / 1440 / 1680）、面包屑",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P08-F9",
      "source_key": "P08.F9",
      "dependencies": [
        "BE-M0-T01",
        "APP-M2-T001"
      ],
      "page_groups": [
        "PG01",
        "PG05",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T010",
      "title": "OIDC 登录跳转、会话续期、401 回登录并返回原页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P02-F1",
      "source_key": "P02.F1",
      "dependencies": [
        "APP-M2-T001"
      ],
      "page_groups": [
        "PG01"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T011",
      "title": "会话超时处理、用户菜单与退出登录",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P02-F2",
      "source_key": "P02.F2",
      "dependencies": [
        "APP-M2-T001",
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T012",
      "title": "Keycloak 自定义登录主题（离线；错误、锁定、超时，已有示例卡）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P02a-02",
      "source_key": "P02a.F2",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T013",
      "title": "登录主题：首次登录强制改密、公司停用提示、读取品牌设置",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P02a-F3",
      "source_key": "P02a.F3",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T014",
      "title": "路由守卫与 403 页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P03-F1",
      "source_key": "P03.F1",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01",
        "PG14",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T015",
      "title": "权限指令 `<Can>` 与按钮隐藏",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P03-F2",
      "source_key": "P03.F2",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01",
        "PG14",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T016",
      "title": "数据权限的前端表现：只读态切换（项目 / 分册 / 章节）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P03-F3",
      "source_key": "P03.F3",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG01",
        "PG14",
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T017",
      "title": "MaskedField 与“查看完整值”弹窗（原因必填）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P04-F1",
      "source_key": "P04.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG26",
        "PG43"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T018",
      "title": "掩码规则读取与查看留痕提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P04-F2",
      "source_key": "P04.F2",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T017"
      ],
      "page_groups": [
        "PG26",
        "PG43"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T019",
      "title": "JobProgress：步骤、子进度、AI 紫进度条",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P05-F1",
      "source_key": "P05.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG04",
        "PG16"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T020",
      "title": "JobProgress：SSE 订阅、断线提示与轮询回退",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P05-F2",
      "source_key": "P05.F2",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T019"
      ],
      "page_groups": [
        "PG04",
        "PG16"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T021",
      "title": "任务中心页基础 + 顶栏任务角标与抽屉",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P05-F3",
      "source_key": "P05.F3",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T019",
        "APP-M2-T020"
      ],
      "page_groups": [
        "PG04",
        "PG16"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T022",
      "title": "平台管理员脱敏视图；从失败步骤重试、取消权限",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P05a-F1",
      "source_key": "P05a.F1",
      "dependencies": [
        "APP-M2-T021"
      ],
      "page_groups": [
        "PG04"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T023",
      "title": "StatusTag 状态注册表（9.3 全部代码表）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P09-F1",
      "source_key": "P09.F1",
      "dependencies": [
        "APP-M2-T005"
      ],
      "page_groups": [
        "PG38"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T024",
      "title": "A-03 字典配置页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P09-F2",
      "source_key": "P09.F2",
      "dependencies": [
        "APP-M2-T005"
      ],
      "page_groups": [
        "PG38"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T025",
      "title": "扩展字段与公司设置键表单框架",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P09-F3",
      "source_key": "P09.F3",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T024"
      ],
      "page_groups": [
        "PG38"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T026",
      "title": "A-01 公司管理",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P10-F1",
      "source_key": "P10.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG37"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T027",
      "title": "A-02 用户列表、新增、停用前转交；“账号安全设置”面板（公司密码策略，只能调严）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P10-F2",
      "source_key": "P10.F2",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T026"
      ],
      "page_groups": [
        "PG37"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T028",
      "title": "A-02 角色分配、解锁、重置密码",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P10-F3",
      "source_key": "P10.F3",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T027"
      ],
      "page_groups": [
        "PG37"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T029",
      "title": "顶栏铃铛与未读数",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P11-F1",
      "source_key": "P11.F1",
      "dependencies": [
        "APP-M2-T010"
      ],
      "page_groups": [
        "PG02"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T030",
      "title": "提醒下拉：最近 7 条、标已读、全部已读",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P11-F2",
      "source_key": "P11.F2",
      "dependencies": [
        "APP-M2-T010",
        "APP-M2-T029"
      ],
      "page_groups": [
        "PG02"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T031",
      "title": "G-02 站内提醒列表页（筛选、已读 / 未读、合并显示）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P11a-F1",
      "source_key": "P11a.F1",
      "dependencies": [
        "APP-M2-T029"
      ],
      "page_groups": [
        "PG02"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T032",
      "title": "17 类提醒的跳转目标映射与“对象已不存在”提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P11a-F2",
      "source_key": "P11a.F2",
      "dependencies": [
        "APP-M2-T029",
        "APP-M2-T031"
      ],
      "page_groups": [
        "PG02"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T033",
      "title": "BrandProvider 运行时主题 + 品牌校验函数（对比度、ΔE）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P15-F1",
      "source_key": "P15.F1",
      "dependencies": [
        "APP-M2-T008"
      ],
      "page_groups": [
        "PG45"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T034",
      "title": "A-12 界面品牌页（表单 + 预览 + 恢复默认）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P15-F2",
      "source_key": "P15.F2",
      "dependencies": [
        "APP-M2-T008",
        "APP-M2-T033"
      ],
      "page_groups": [
        "PG45"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T035",
      "title": "全局搜索：顶栏下拉与结果页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-P16-F1",
      "source_key": "P16.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG03"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T036",
      "title": "A-08 模型列表与 `service_status`",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B01-F1",
      "source_key": "B01.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG39"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T037",
      "title": "模型登记表单（不支持字段置灰）与测试连接",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B01-F2",
      "source_key": "B01.F2",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T036"
      ],
      "page_groups": [
        "PG39"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T038",
      "title": "模型配置版本与回滚",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B01-F3",
      "source_key": "B01.F3",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T037"
      ],
      "page_groups": [
        "PG39"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T039",
      "title": "A-09 文档解析服务（云端 / 本地两组页签）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B01-F4",
      "source_key": "B01.F4",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T021"
      ],
      "page_groups": [
        "PG39"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T040",
      "title": "A-10 任务与模型对应表（首选本地 → 备用只列本地）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B02-F1",
      "source_key": "B02.F1",
      "dependencies": [
        "APP-M2-T036"
      ],
      "page_groups": [
        "PG40"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T041",
      "title": "A-05 公司模型开放",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-B02-F2",
      "source_key": "B02.F2",
      "dependencies": [
        "APP-M2-T036"
      ],
      "page_groups": [
        "PG40"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T042",
      "title": "A-11 部署与服务状态页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M1-J01a-F1",
      "source_key": "J01a.F1",
      "dependencies": [
        "APP-M2-T036"
      ],
      "page_groups": [
        "PG44"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T043",
      "title": "CrossFieldHint 组件与 9.11 规则函数",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-B06-F1",
      "source_key": "B06.F1",
      "dependencies": [
        "APP-M2-T025"
      ],
      "page_groups": [
        "PG41"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T044",
      "title": "A-05 生成闭环参数",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-B06-F2",
      "source_key": "B06.F2",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T043"
      ],
      "page_groups": [
        "PG41"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T045",
      "title": "编辑台与对话助手参数（自动保存、心跳 15～120、锁超时）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-B06-F3",
      "source_key": "B06.F3",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T043"
      ],
      "page_groups": [
        "PG41"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T046",
      "title": "资料列表通用页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C01-F1",
      "source_key": "C01.F1",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T017"
      ],
      "page_groups": [
        "PG25"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T047",
      "title": "资料详情通用页（附件槽位、来源）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C01-F2",
      "source_key": "C01.F2",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T017"
      ],
      "page_groups": [
        "PG25"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T048",
      "title": "确认 / 审核状态机界面（★ 字段重确认）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C01-F3",
      "source_key": "C01.F3",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T017",
        "APP-M2-T047",
        "APP-M2-T203"
      ],
      "page_groups": [
        "PG25"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T049",
      "title": "受限资料与转交",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C01-F4",
      "source_key": "C01.F4",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T017",
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG25"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T050",
      "title": "变更历史与被引用情况",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C01-F5",
      "source_key": "C01.F5",
      "dependencies": [
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T017",
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG25"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T051",
      "title": "厂商产品树",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C02-F1",
      "source_key": "C02.F1",
      "dependencies": [
        "APP-M2-T024"
      ],
      "page_groups": [
        "PG30"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T052",
      "title": "证书类别与附件槽位",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C02-F2",
      "source_key": "C02.F2",
      "dependencies": [
        "APP-M2-T024",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG30"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T053",
      "title": "中小企业划型标准",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C02-F3",
      "source_key": "C02.F3",
      "dependencies": [
        "APP-M2-T024",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG30"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T054",
      "title": "公司主体（含关联关系）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F1",
      "source_key": "C03.F1",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T055",
      "title": "证明材料",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F2",
      "source_key": "C03.F2",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T056",
      "title": "资质证书",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F3",
      "source_key": "C03.F3",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T057",
      "title": "安全与合规事件",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F4",
      "source_key": "C03.F4",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T058",
      "title": "工具与设备",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F5",
      "source_key": "C03.F5",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T059",
      "title": "附件库",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C03-F6",
      "source_key": "C03.F6",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T060",
      "title": "人员列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C04-F1",
      "source_key": "C04.F1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T059"
      ],
      "page_groups": [
        "PG26"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T061",
      "title": "人员详情（MaskedField）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C04-F2",
      "source_key": "C04.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T059",
        "APP-M2-T017"
      ],
      "page_groups": [
        "PG26"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T062",
      "title": "人员证书",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C04-F3",
      "source_key": "C04.F3",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T059",
        "APP-M2-T061",
        "APP-M2-T052"
      ],
      "page_groups": [
        "PG26"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T063",
      "title": "占用（R12）与离职提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C04-F4",
      "source_key": "C04.F4",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T059",
        "APP-M2-T060"
      ],
      "page_groups": [
        "PG26"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T064",
      "title": "授权列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C05-F1",
      "source_key": "C05.F1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051",
        "APP-M2-T054"
      ],
      "page_groups": [
        "PG27"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T065",
      "title": "授权详情",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C05-F2",
      "source_key": "C05.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051",
        "APP-M2-T054"
      ],
      "page_groups": [
        "PG27"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T066",
      "title": "授权链图（不满足节点标红、上游未登记虚线）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C05-F3",
      "source_key": "C05.F3",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051",
        "APP-M2-T054",
        "APP-M2-T065"
      ],
      "page_groups": [
        "PG27"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T067",
      "title": "业绩列表与详情",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C06-F1",
      "source_key": "C06.F1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG29"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T068",
      "title": "业绩成员与产品",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C06-F2",
      "source_key": "C06.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051",
        "APP-M2-T067",
        "APP-M2-T060"
      ],
      "page_groups": [
        "PG29"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T069",
      "title": "SLA 模板（等级、变量）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C06-F3",
      "source_key": "C06.F3",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG29"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T070",
      "title": "全局变量",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C06-F4",
      "source_key": "C06.F4",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG29"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T071",
      "title": "资料库首页健康度卡片",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C07-F1",
      "source_key": "C07.F1",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG24",
        "PG42"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T072",
      "title": "Excel 批量导入与逐条 / 按批确认",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C07-F2",
      "source_key": "C07.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T046"
      ],
      "page_groups": [
        "PG24",
        "PG42"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T073",
      "title": "有效期提醒与 A-04 资料库设置",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C07-F3",
      "source_key": "C07.F3",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG24",
        "PG42"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T074",
      "title": "附件识别上传与进度",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C08-F1",
      "source_key": "C08.F1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T039"
      ],
      "page_groups": [
        "PG31"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T075",
      "title": "识别结果核对（“待核对”标记）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-C08-F2",
      "source_key": "C08.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T039",
        "APP-M2-T074"
      ],
      "page_groups": [
        "PG31"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T076",
      "title": "片段列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D01-F1",
      "source_key": "D01.F1",
      "dependencies": [
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG32"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T077",
      "title": "片段编辑（变量校验）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D01-F2",
      "source_key": "D01.F2",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T076",
        "APP-M2-T070"
      ],
      "page_groups": [
        "PG32"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T078",
      "title": "版本对比与发布（R31 拦截原因）",
      "status": "in-review",
      "phase": "一期业务页面/支撑",
      "source": "M2-D01-F3",
      "source_key": "D01.F3",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T077",
        "APP-M2-T238"
      ],
      "page_groups": [
        "PG32"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T079",
      "title": "同步状态与重新同步",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D01-F4",
      "source_key": "D01.F4",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T078"
      ],
      "page_groups": [
        "PG32"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T080",
      "title": "历史标书单个 / 批量导入",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D02-F1",
      "source_key": "D02.F1",
      "dependencies": [
        "APP-M2-T021"
      ],
      "page_groups": [
        "PG33"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T081",
      "title": "入库状态派生显示与摘取为片段",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D02-F2",
      "source_key": "D02.F2",
      "dependencies": [
        "APP-M2-T021",
        "APP-M2-T080"
      ],
      "page_groups": [
        "PG33"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T082",
      "title": "版本条（发布、回滚）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F1",
      "source_key": "D03.F1",
      "dependencies": [
        "APP-M2-T025"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T083",
      "title": "章节模板",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F2",
      "source_key": "D03.F2",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T084",
      "title": "叫法术语、语气称呼",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F3",
      "source_key": "D03.F3",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T085",
      "title": "句式规则",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F4",
      "source_key": "D03.F4",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T086",
      "title": "Word 模板与导出命名",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F5",
      "source_key": "D03.F5",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T087",
      "title": "预览抽屉",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D03-F6",
      "source_key": "D03.F6",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T083",
        "APP-M2-T084",
        "APP-M2-T085"
      ],
      "page_groups": [
        "PG34"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T088",
      "title": "任务卡列表与版本",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D04-F1",
      "source_key": "D04.F1",
      "dependencies": [
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG35"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T089",
      "title": "提示词模板编辑与发布校验",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D04-F2",
      "source_key": "D04.F2",
      "dependencies": [
        "APP-M2-T082",
        "APP-M2-T088"
      ],
      "page_groups": [
        "PG35"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T090",
      "title": "平台默认与公司覆盖对照",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D04-F3",
      "source_key": "D04.F3",
      "dependencies": [
        "APP-M2-T082",
        "APP-M2-T089"
      ],
      "page_groups": [
        "PG35"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T091",
      "title": "审查清单",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D05-F1",
      "source_key": "D05.F1",
      "dependencies": [
        "APP-M2-T082"
      ],
      "page_groups": [
        "PG36"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T092",
      "title": "风格样例卡片墙（启用开关）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D05-F2",
      "source_key": "D05.F2",
      "dependencies": [
        "APP-M2-T082",
        "APP-M2-T081"
      ],
      "page_groups": [
        "PG36"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T093",
      "title": "入库脱敏扫描结果展示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M2-D05-F3",
      "source_key": "D05.F3",
      "dependencies": [
        "APP-M2-T082",
        "APP-M2-T092",
        "APP-M2-T230",
        "APP-M2-T238",
        "APP-M2-T243"
      ],
      "page_groups": [
        "PG36"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T094",
      "title": "ProjectHeader 摘要条与页签（无“资料匹配”）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F1",
      "source_key": "E01.F1",
      "dependencies": [
        "APP-M1-T14"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T095",
      "title": "项目列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F2",
      "source_key": "E01.F2",
      "dependencies": [
        "APP-M1-T14"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T096",
      "title": "新建项目与 R19 提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F3",
      "source_key": "E01.F3",
      "dependencies": [
        "APP-M1-T14",
        "APP-M2-T224"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T097",
      "title": "项目概览（待办、分册、状态操作）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F4",
      "source_key": "E01.F4",
      "dependencies": [
        "APP-M1-T14",
        "APP-M2-T094"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T098",
      "title": "项目基本字段和合作方协议（成员复用T14）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F5",
      "source_key": "E01.F5",
      "dependencies": [
        "APP-M1-T14",
        "APP-M2-T054"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": [
        "APP-M1-T14"
      ]
    },
    {
      "id": "APP-M2-T099",
      "title": "项目设置：拟派人员、SLA 取值、规则覆盖",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F6",
      "source_key": "E01.F6",
      "dependencies": [
        "APP-M1-T14",
        "APP-M2-T060",
        "APP-M2-T069"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T100",
      "title": "分册格式、闭环及导出设置（分工复用T14）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E01-F7",
      "source_key": "E01.F7",
      "dependencies": [
        "APP-M1-T14",
        "APP-M2-T044",
        "APP-M2-T045",
        "APP-M2-T086"
      ],
      "page_groups": [
        "PG05",
        "PG06",
        "PG07",
        "PG14"
      ],
      "rule": null,
      "existing_reuse": [
        "APP-M1-T14"
      ]
    },
    {
      "id": "APP-M2-T101",
      "title": "招标文件上传与版本链",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E02-F1",
      "source_key": "E02.F1",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T021"
      ],
      "page_groups": [
        "PG08"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T102",
      "title": "解析进度页（JobProgress 接入）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E02-F2",
      "source_key": "E02.F2",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T021",
        "APP-M2-T101"
      ],
      "page_groups": [
        "PG08"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T103",
      "title": "PdfLocator（PDF.js 本地 Worker、跳页高亮）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F1",
      "source_key": "E04.F1",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T101"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T104",
      "title": "解析结果三栏布局与分类树",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F2",
      "source_key": "E04.F2",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T103"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T105",
      "title": "条目卡片编辑与逐条确认",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F3",
      "source_key": "E04.F3",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T104"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T106",
      "title": "批量确认（星号 / 废标 / 资格禁用）与置信度高亮",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F4",
      "source_key": "E04.F4",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T105"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T107",
      "title": "重抽不覆盖与补遗差异",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F5",
      "source_key": "E04.F5",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T105",
        "APP-M2-T101"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T108",
      "title": "“确认解析结果”闸门（悬停列未满足项）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04-F6",
      "source_key": "E04.F6",
      "dependencies": [
        "APP-M1-T02",
        "APP-M2-T106",
        "APP-M2-T107",
        "APP-M2-T109",
        "APP-M2-T110",
        "APP-M2-T111"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T109",
      "title": "后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04a-F1",
      "source_key": "E04a.F1",
      "dependencies": [
        "APP-M2-T104",
        "APP-M2-T019"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T110",
      "title": "冲突待选定页签（并列取值、理由必填）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04a-F2",
      "source_key": "E04a.F2",
      "dependencies": [
        "APP-M2-T104",
        "APP-M2-T109"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T111",
      "title": "疑似遗漏（无批量、排除须理由）与引用未解析页签",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E04a-F3",
      "source_key": "E04a.F3",
      "dependencies": [
        "APP-M2-T104",
        "APP-M2-T148",
        "APP-M2-T109"
      ],
      "page_groups": [
        "PG09"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T112",
      "title": "矩阵表格与筛选（风险提示）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F1",
      "source_key": "E05.F1",
      "dependencies": [
        "APP-M1-T03"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T113",
      "title": "行编辑（响应方式、要点、负责人）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F2",
      "source_key": "E05.F2",
      "dependencies": [
        "APP-M1-T03",
        "APP-M2-T112"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T114",
      "title": "EvidenceDrawer",
      "status": "done",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F3",
      "source_key": "E05.F3",
      "dependencies": [
        "APP-M1-T03",
        "APP-M2-T048",
        "APP-M2-T204",
        "APP-M2-T205"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T115",
      "title": "批量智能匹配与逐行确认",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F4",
      "source_key": "E05.F4",
      "dependencies": [
        "APP-M1-T03",
        "APP-M2-T118"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T116",
      "title": "P-18 分册分流确认",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F5",
      "source_key": "E05.F5",
      "dependencies": [
        "APP-M1-T03",
        "APP-M1-T14"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T117",
      "title": "Excel 导出与确认闸门",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05-F6",
      "source_key": "E05.F6",
      "dependencies": [
        "APP-M1-T03",
        "APP-M2-T113",
        "APP-M2-T114",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG10",
        "PG13"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T118",
      "title": "挂证据候选的三路显示（结构化规则匹配 / 片段检索 / 历史标书仅参考）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E05a-F1",
      "source_key": "E05a.F1",
      "dependencies": [
        "APP-M2-T114",
        "APP-M2-T078",
        "APP-M2-T081"
      ],
      "page_groups": [
        "PG10"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T119",
      "title": "SLA 矩阵表与判定",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E06-F1",
      "source_key": "E06.F1",
      "dependencies": [
        "APP-M1-T10",
        "APP-M1-T12",
        "APP-M2-T069"
      ],
      "page_groups": [
        "PG11",
        "PG12"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T120",
      "title": "模板取值与承诺函导出",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E06-F2",
      "source_key": "E06.F2",
      "dependencies": [
        "APP-M1-T10",
        "APP-M1-T12",
        "APP-M2-T119"
      ],
      "page_groups": [
        "PG11",
        "PG12"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T121",
      "title": "项目事实表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E06-F3",
      "source_key": "E06.F3",
      "dependencies": [
        "APP-M1-T10",
        "APP-M1-T12"
      ],
      "page_groups": [
        "PG11",
        "PG12"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T122",
      "title": "“需复核”传播提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M3-E06-F4",
      "source_key": "E06.F4",
      "dependencies": [
        "APP-M1-T10",
        "APP-M1-T12",
        "APP-M2-T119",
        "APP-M2-T121"
      ],
      "page_groups": [
        "PG11",
        "PG12"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T123",
      "title": "大纲排序、章节类型和增值理由（分工复用T15）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F01-F1",
      "source_key": "F01.F1",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG15"
      ],
      "rule": null,
      "existing_reuse": [
        "APP-M1-T15"
      ]
    },
    {
      "id": "APP-M2-T124",
      "title": "完整证据、片段及评分写作计划（确认复用T15）",
      "status": "blocked",
      "phase": "一期业务页面/支撑",
      "source": "M4-F01-F2",
      "source_key": "F01.F2",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T078",
        "APP-M2-T114"
      ],
      "page_groups": [
        "PG15"
      ],
      "rule": null,
      "existing_reuse": [
        "APP-M1-T12",
        "APP-M1-T13",
        "APP-M1-T15"
      ]
    },
    {
      "id": "APP-M2-T125",
      "title": "招标原文预览联动与 R26 提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F01-F3",
      "source_key": "F01.F3",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T123",
        "APP-M2-T232"
      ],
      "page_groups": [
        "PG15"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T126",
      "title": "按逐节确认结果启动生成（确认复用T15）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F01-F4",
      "source_key": "F01.F4",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T124",
        "APP-M2-T125"
      ],
      "page_groups": [
        "PG15"
      ],
      "rule": null,
      "existing_reuse": [
        "APP-M1-T15"
      ]
    },
    {
      "id": "APP-M2-T127",
      "title": "五类系统生成章节预览",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F09-F1",
      "source_key": "F09.F1",
      "dependencies": [
        "APP-M1-T04",
        "APP-M2-T191",
        "APP-M2-T192",
        "APP-M2-T193",
        "APP-M2-T194",
        "APP-M2-T195"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T128",
      "title": "锁定提示与“去数据源修改”",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F09-F2",
      "source_key": "F09.F2",
      "dependencies": [
        "APP-M1-T04",
        "APP-M2-T127",
        "APP-M2-T163"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T129",
      "title": "章节列表（编辑台入口）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F1",
      "source_key": "F10.F1",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T130",
      "title": "章节循环进度页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F2",
      "source_key": "F10.F2",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T044",
        "APP-M2-T234",
        "APP-M2-T237",
        "APP-M2-T238",
        "APP-M2-T254",
        "APP-M2-T244",
        "APP-M2-T245",
        "APP-M2-T246",
        "APP-M2-T247",
        "APP-M2-T248",
        "APP-M2-T249"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T131",
      "title": "轮次时间线",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F3",
      "source_key": "F10.F3",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T130"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T132",
      "title": "版本对比（复用 DiffView）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F4",
      "source_key": "F10.F4",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T175"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T133",
      "title": "人工处理队列列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F5",
      "source_key": "F10.F5",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T130"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T134",
      "title": "队列详情单段编辑",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F6",
      "source_key": "F10.F6",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T133",
        "APP-M2-T174"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T135",
      "title": "一键重新检查",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F7",
      "source_key": "F10.F7",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T134"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T136",
      "title": "异常中断与重试",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F10-F8",
      "source_key": "F10.F8",
      "dependencies": [
        "APP-M2-T126",
        "APP-M2-T021",
        "APP-M2-T130"
      ],
      "page_groups": [
        "PG16",
        "PG17"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T137",
      "title": "W-03 公司级写作观察统计",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F11-F1",
      "source_key": "F11.F1",
      "dependencies": [
        "APP-M2-T131",
        "APP-M2-T189"
      ],
      "page_groups": [
        "PG19"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T138",
      "title": "P-17 项目级折叠区",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F11-F2",
      "source_key": "F11.F2",
      "dependencies": [
        "APP-M2-T131",
        "APP-M2-T189"
      ],
      "page_groups": [
        "PG19"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T139",
      "title": "图表组件（AntV G2，待技术确认）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M4-F11-F3",
      "source_key": "F11.F3",
      "dependencies": [
        "APP-M2-T131",
        "APP-M2-T189"
      ],
      "page_groups": [
        "PG19"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T140",
      "title": "RuleIssueList",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F1",
      "source_key": "G04.F1",
      "dependencies": [
        "APP-M1-T05"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T141",
      "title": "合规检查页布局与结论条",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F2",
      "source_key": "G04.F2",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T140"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T142",
      "title": "警告放行（理由必填，阻断无放行）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F3",
      "source_key": "G04.F3",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T140"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T143",
      "title": "R18 段落相似度并排对比",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F4",
      "source_key": "G04.F4",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T223"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T144",
      "title": "分册检查 / 定稿 / 解锁 / 交叉复核",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F5",
      "source_key": "G04.F5",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T142",
        "APP-M2-T228",
        "APP-M2-T229",
        "APP-M2-T250",
        "APP-M2-T251",
        "APP-M2-T252",
        "APP-M2-T255",
        "APP-M2-T256",
        "APP-M2-T257",
        "APP-M2-T258"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T145",
      "title": "全文检查与“结果已过期”提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G04-F6",
      "source_key": "G04.F6",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T144"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T146",
      "title": "合规规则页签（不可关闭锁、R43 无阻断）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G06-F1",
      "source_key": "G06.F1",
      "dependencies": [
        "APP-M2-T025"
      ],
      "page_groups": [
        "PG46"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T147",
      "title": "规则参数、恢复平台默认、修改历史",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G06-F2",
      "source_key": "G06.F2",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T146"
      ],
      "page_groups": [
        "PG46"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T148",
      "title": "兜底扫描词表（草稿、试扫、发布）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-G06-F3",
      "source_key": "G06.F3",
      "dependencies": [
        "APP-M2-T025",
        "APP-M2-T146"
      ],
      "page_groups": [
        "PG46"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T149",
      "title": "导出前提检查",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-H03-F1",
      "source_key": "H03.F1",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T145"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T150",
      "title": "导出类型、模板与命名",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-H03-F2",
      "source_key": "H03.F2",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T196",
        "APP-M2-T197",
        "APP-M2-T198"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T151",
      "title": "导出历史与下载（`export_status` 含排队）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-H03-F3",
      "source_key": "H03.F3",
      "dependencies": [
        "APP-M1-T05",
        "APP-M2-T202"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T152",
      "title": "递交版：仅项目负责人可见、已确认完整值类别展示、内部稿掩码说明",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-H04-F1",
      "source_key": "H04.F1",
      "dependencies": [
        "APP-M2-T149",
        "APP-M2-T100",
        "APP-M2-T017",
        "APP-M2-T196"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T153",
      "title": "工作台 6 张统计卡（点击即筛选）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-E01b-F1",
      "source_key": "E01b.F1",
      "dependencies": [
        "APP-M2-T095"
      ],
      "page_groups": [
        "PG05",
        "PG07"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T154",
      "title": "概览底部折叠区",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-E01b-F2",
      "source_key": "E01b.F2",
      "dependencies": [
        "APP-M2-T095"
      ],
      "page_groups": [
        "PG05",
        "PG07"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T155",
      "title": "集团管理员公司切换与只读视图",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-J02-F1",
      "source_key": "J02.F1",
      "dependencies": [
        "APP-M2-T016"
      ],
      "page_groups": [
        "PG47"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T156",
      "title": "集团统计",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-J02-F2",
      "source_key": "J02.F2",
      "dependencies": [
        "APP-M2-T016"
      ],
      "page_groups": [
        "PG47"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T157",
      "title": "A-06 审计日志页",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-J01-F1",
      "source_key": "J01.F1",
      "dependencies": [
        "APP-M2-T014"
      ],
      "page_groups": [
        "PG43"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T158",
      "title": "云端调用审计展开",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-J01-F2",
      "source_key": "J01.F2",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T157",
        "APP-M2-T037"
      ],
      "page_groups": [
        "PG43"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T159",
      "title": "服务健康基础与 A-11（M1-J01a）对齐",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M5-J01-F3",
      "source_key": "J01.F3",
      "dependencies": [
        "APP-M2-T014",
        "APP-M2-T042"
      ],
      "page_groups": [
        "PG43"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T160",
      "title": "编辑台布局与三档断点（四栏 / 三栏 / 紧凑）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F1",
      "source_key": "I01.F1",
      "dependencies": [
        "APP-M1-T15"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T161",
      "title": "章节加载与段落键",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F2",
      "source_key": "I01.F2",
      "dependencies": [
        "APP-M1-T15"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T162",
      "title": "SourceBar 来源标记",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F3",
      "source_key": "I01.F3",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T163",
      "title": "锁定内容",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F4",
      "source_key": "I01.F4",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T164",
      "title": "变量节点",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F5",
      "source_key": "I01.F5",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T165",
      "title": "证据节点与 `.cite`",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F6",
      "source_key": "I01.F6",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161",
        "APP-M2-T048"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T166",
      "title": "问题标注与侧栏联动",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F7",
      "source_key": "I01.F7",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161",
        "APP-M2-T140"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T167",
      "title": "选区悬浮工具条",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F8",
      "source_key": "I01.F8",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T168",
      "title": "目录树与章节切换",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F9",
      "source_key": "I01.F9",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T169",
      "title": "工具栏紧凑模式（“格式”下拉）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F10",
      "source_key": "I01.F10",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T160"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T170",
      "title": "只读态（他人编辑中）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F11",
      "source_key": "I01.F11",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T173"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T171",
      "title": "长章节性能",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I01-F12",
      "source_key": "I01.F12",
      "dependencies": [
        "APP-M1-T15",
        "APP-M2-T161",
        "APP-M2-T166",
        "APP-M2-T167"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T172",
      "title": "自动保存草稿",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I02-F1",
      "source_key": "I02.F1",
      "dependencies": [
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T173",
      "title": "EditLockBadge、心跳、超时提示、接管",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I02-F2",
      "source_key": "I02.F2",
      "dependencies": [
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T174",
      "title": "提交版本与版本历史",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I02-F3",
      "source_key": "I02.F3",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T172",
        "APP-M2-T173"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T175",
      "title": "版本对比与回退",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I02-F4",
      "source_key": "I02.F4",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T174"
      ],
      "page_groups": [
        "PG22"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T176",
      "title": "对话面板与会话列表",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04-F1",
      "source_key": "I04.F1",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T089"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T177",
      "title": "流式输出、模型标识、降级提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04-F2",
      "source_key": "I04.F2",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T089",
        "APP-M2-T176",
        "APP-M2-T040"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T178",
      "title": "建议卡片（写法、差异、来源、预检）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04-F3",
      "source_key": "I04.F3",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T089",
        "APP-M2-T176",
        "APP-M2-T242",
        "APP-M2-T243",
        "APP-M2-T244",
        "APP-M2-T248"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T179",
      "title": "自由问答（只“复制”）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04-F4",
      "source_key": "I04.F4",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T089",
        "APP-M2-T181"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T180",
      "title": "上下文与样例任务卡选择",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04-F5",
      "source_key": "I04.F5",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T089",
        "APP-M2-T176",
        "APP-M2-T124"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T181",
      "title": "资料库与本项目数据答案卡",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04a-F1",
      "source_key": "I04a.F1",
      "dependencies": [
        "APP-M2-T176",
        "APP-M2-T047",
        "APP-M2-T112"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T182",
      "title": "直查未命中与常规回答回退",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04a-F2",
      "source_key": "I04a.F2",
      "dependencies": [
        "APP-M2-T176",
        "APP-M2-T047",
        "APP-M2-T112",
        "APP-M2-T181"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T183",
      "title": "插入为引用：差异视图、写入、引用标记",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I04b-F1",
      "source_key": "I04b.F1",
      "dependencies": [
        "APP-M2-T181",
        "APP-M2-T185"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T184",
      "title": "本项目招标文件轻量索引的检索结果展示",
      "status": "planned",
      "phase": "一期可选（默认关闭）",
      "source": "M6-E08-F1",
      "source_key": "E08.F1",
      "dependencies": [
        "APP-M2-T181"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T185",
      "title": "差异确认写入",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I05-F1",
      "source_key": "I05.F1",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T178"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T186",
      "title": "“我已逐字核对”二次确认（星号 / 废标 / 偏离 / 披露）",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I05-F2",
      "source_key": "I05.F2",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T178",
        "APP-M2-T185"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T187",
      "title": "冲突校验与重新定位提示",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I05-F3",
      "source_key": "I05.F3",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T178",
        "APP-M2-T185"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T188",
      "title": "粘贴识别",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I05-F4",
      "source_key": "I05.F4",
      "dependencies": [
        "APP-M2-T167",
        "APP-M2-T178",
        "APP-M2-T185",
        "APP-M2-T242",
        "APP-M2-T243"
      ],
      "page_groups": [
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T189",
      "title": "对话助手观察指标",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I06-F1",
      "source_key": "I06.F1",
      "dependencies": [
        "APP-M2-T174",
        "APP-M2-T185"
      ],
      "page_groups": [
        "PG19",
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T190",
      "title": "人工修改率分项",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "M6-I06-F2",
      "source_key": "I06.F2",
      "dependencies": [
        "APP-M2-T174",
        "APP-M2-T185"
      ],
      "page_groups": [
        "PG19",
        "PG23"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T191",
      "title": "点对点应答确定性章节",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.7.2、5.11.8",
      "source_key": "GEN.POINT",
      "dependencies": [
        "APP-M2-T113",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T192",
      "title": "评审索引确定性章节",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.7.2、5.9.1、R40",
      "source_key": "GEN.INDEX",
      "dependencies": [
        "APP-M2-T113",
        "APP-M2-T123"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T193",
      "title": "偏离表确定性章节",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.7.2、R37",
      "source_key": "GEN.DEVIATION",
      "dependencies": [
        "APP-M2-T113",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T194",
      "title": "年度服务计划确定性章节",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.7.2、5.11.8",
      "source_key": "GEN.SCHEDULE",
      "dependencies": [
        "APP-M2-T121",
        "APP-M2-T113"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T195",
      "title": "证明材料清单确定性章节",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.7.2、R41",
      "source_key": "GEN.PROOFS",
      "dependencies": [
        "APP-M2-T114",
        "APP-M2-T059",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG18"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T196",
      "title": "Word模板与正文样式渲染",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则1、5、6",
      "source_key": "WORD.TEMPLATE",
      "dependencies": [
        "APP-M2-T086",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T197",
      "title": "分册封面、目录与页码",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则2～4",
      "source_key": "WORD.TOC",
      "dependencies": [
        "APP-M2-T196",
        "APP-M2-T100"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T198",
      "title": "指定附件页与敏感水印",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则7、R14",
      "source_key": "WORD.ATTACH",
      "dependencies": [
        "APP-M2-T196",
        "APP-M2-T059"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T199",
      "title": "Word属性修订与批注清理",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则10、R25",
      "source_key": "WORD.CLEAN",
      "dependencies": [
        "APP-M2-T196"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T200",
      "title": "同批合标核对清单输出",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.2",
      "source_key": "WORD.MERGE",
      "dependencies": [
        "APP-M2-T149",
        "APP-M2-T197",
        "APP-M2-T192",
        "APP-M2-T193"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T201",
      "title": "内部响应追溯Excel",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则12",
      "source_key": "WORD.TRACE",
      "dependencies": [
        "APP-M2-T117",
        "APP-M2-T162",
        "APP-M2-T165"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T202",
      "title": "递交批次原子输出和历史快照",
      "status": "planned",
      "phase": "一期业务产物",
      "source": "PRD-v1.8-§5.9.1规则13、14及异常",
      "source_key": "WORD.BATCH",
      "dependencies": [
        "APP-M2-T152",
        "APP-M2-T197",
        "APP-M2-T198",
        "APP-M2-T199",
        "APP-M2-T200"
      ],
      "page_groups": [
        "PG21"
      ],
      "rule": null,
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T203",
      "title": "R01 不可引用的资料禁止引用",
      "status": "planned",
      "phase": "一期完整",
      "source": "R01",
      "source_key": "R01.1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T077"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R01",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T204",
      "title": "R02 资料来源分级与投标主体一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R02",
      "source_key": "R02.1",
      "dependencies": [
        "APP-M2-T054",
        "APP-M2-T098"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R02",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T205",
      "title": "R03 有效期覆盖投标截止时间",
      "status": "planned",
      "phase": "一期完整",
      "source": "R03",
      "source_key": "R03.1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R03",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T206",
      "title": "R04 临期与复审提醒",
      "status": "planned",
      "phase": "一期完整",
      "source": "R04",
      "source_key": "R04.1",
      "dependencies": [
        "APP-M2-T073",
        "APP-M2-T031"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R04",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T207",
      "title": "R05 年审/监督审核有效",
      "status": "planned",
      "phase": "二期",
      "source": "R05",
      "source_key": "R05.1",
      "dependencies": [
        "APP-M2-T056"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R05",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T208",
      "title": "R06 持证单位与主体名称一致",
      "status": "planned",
      "phase": "二期",
      "source": "R06",
      "source_key": "R06.1",
      "dependencies": [
        "APP-M2-T056",
        "APP-M2-T075"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R06",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T209",
      "title": "R07 原厂授权覆盖招标涉及的全部产品，授权链逐级有效，地域覆盖到地",
      "status": "planned",
      "phase": "一期完整",
      "source": "R07",
      "source_key": "R07.1",
      "dependencies": [
        "APP-M2-T066",
        "APP-M2-T051"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R07",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T210",
      "title": "R08 拟派人员持有招标涉及产品的有效原厂认证",
      "status": "planned",
      "phase": "一期完整",
      "source": "R08",
      "source_key": "R08.1",
      "dependencies": [
        "APP-M2-T062",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R08",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T211",
      "title": "R09 故障等级与服务时段",
      "status": "planned",
      "phase": "一期完整",
      "source": "R09",
      "source_key": "R09.1",
      "dependencies": [
        "APP-M2-T119",
        "APP-M2-T121",
        "APP-M2-T069"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R09",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T212",
      "title": "R09 全类别SLA及能力比较",
      "status": "planned",
      "phase": "一期完整",
      "source": "R09",
      "source_key": "R09.2",
      "dependencies": [
        "APP-M2-T119",
        "APP-M2-T121",
        "APP-M2-T069"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R09",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T213",
      "title": "R09 模板外承诺类事实",
      "status": "planned",
      "phase": "一期完整",
      "source": "R09",
      "source_key": "R09.3",
      "dependencies": [
        "APP-M2-T119",
        "APP-M2-T121",
        "APP-M2-T069"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R09",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T214",
      "title": "R10 手写与自然表达全文承诺",
      "status": "planned",
      "phase": "一期完整",
      "source": "R10",
      "source_key": "R10.1",
      "dependencies": [
        "APP-M2-T119",
        "APP-M2-T164",
        "APP-M2-T193"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R10",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T215",
      "title": "R10 结构节点及确定性输出",
      "status": "planned",
      "phase": "一期完整",
      "source": "R10",
      "source_key": "R10.2",
      "dependencies": [
        "APP-M2-T119",
        "APP-M2-T164",
        "APP-M2-T193"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R10",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T216",
      "title": "R11 本单位人员与社保核对",
      "status": "planned",
      "phase": "一期完整",
      "source": "R11",
      "source_key": "R11.1",
      "dependencies": [
        "APP-M2-T061",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R11",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T217",
      "title": "R12 人员占用冲突",
      "status": "planned",
      "phase": "一期完整",
      "source": "R12",
      "source_key": "R12.1",
      "dependencies": [
        "APP-M2-T063",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R12",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T218",
      "title": "R13 业绩满足资格与评分条件",
      "status": "planned",
      "phase": "一期简化",
      "source": "R13",
      "source_key": "R13.1",
      "dependencies": [
        "APP-M2-T067",
        "APP-M2-T068"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R13",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T219",
      "title": "R14 必备附件齐全",
      "status": "planned",
      "phase": "一期完整",
      "source": "R14",
      "source_key": "R14.1",
      "dependencies": [
        "APP-M2-T059",
        "APP-M2-T195",
        "APP-M2-T198"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R14",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T220",
      "title": "R15 占位符与【待补】清零",
      "status": "planned",
      "phase": "一期完整",
      "source": "R15",
      "source_key": "R15.1",
      "dependencies": [
        "APP-M2-T164",
        "APP-M2-T165"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R15",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T221",
      "title": "R16 主体基本资格与证明材料时效",
      "status": "planned",
      "phase": "一期简化",
      "source": "R16",
      "source_key": "R16.1",
      "dependencies": [
        "APP-M2-T054",
        "APP-M2-T055"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R16",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T222",
      "title": "R17 使用提示与保密项目提醒",
      "status": "planned",
      "phase": "一期完整",
      "source": "R17",
      "source_key": "R17.1",
      "dependencies": [
        "APP-M2-T047",
        "APP-M2-T100"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R17",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T223",
      "title": "R18 相似度检查",
      "status": "planned",
      "phase": "一期完整",
      "source": "R18",
      "source_key": "R18.1",
      "dependencies": [
        "APP-M2-T095",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R18",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T224",
      "title": "R19 关联投标冲突",
      "status": "planned",
      "phase": "一期完整",
      "source": "R19",
      "source_key": "R19.1",
      "dependencies": [
        "APP-M1-T01",
        "APP-M2-T054"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R19",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T225",
      "title": "R20 同一编写人",
      "status": "planned",
      "phase": "二期",
      "source": "R20",
      "source_key": "R20.1",
      "dependencies": [
        "APP-M2-T028",
        "APP-M2-T174"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R20",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T226",
      "title": "R21 不同公司同一项目拟派人员为同一人",
      "status": "planned",
      "phase": "二期",
      "source": "R21",
      "source_key": "R21.1",
      "dependencies": [
        "APP-M2-T061",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R21",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T227",
      "title": "R22 不同公司同一项目的保证金转出账户相同",
      "status": "planned",
      "phase": "二期",
      "source": "R22",
      "source_key": "R22.1",
      "dependencies": [
        "APP-M2-T054",
        "APP-M2-T100"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R22",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T228",
      "title": "R23 星号条款、废标条款全部已确认响应",
      "status": "planned",
      "phase": "一期完整",
      "source": "R23",
      "source_key": "R23.1",
      "dependencies": [
        "APP-M2-T105",
        "APP-M2-T113"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R23",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T229",
      "title": "R24 格式要求",
      "status": "planned",
      "phase": "一期简化",
      "source": "R24",
      "source_key": "R24.1",
      "dependencies": [
        "APP-M2-T191",
        "APP-M2-T192",
        "APP-M2-T193",
        "APP-M2-T197"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R24",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T230",
      "title": "R25 名称机构残留",
      "status": "planned",
      "phase": "一期完整",
      "source": "R25",
      "source_key": "R25.1",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T199"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R25",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T231",
      "title": "R25 Word元数据残留",
      "status": "planned",
      "phase": "一期完整",
      "source": "R25",
      "source_key": "R25.2",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T199"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R25",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T232",
      "title": "R26 评分项覆盖度",
      "status": "planned",
      "phase": "一期完整",
      "source": "R26",
      "source_key": "R26.1",
      "dependencies": [
        "APP-M2-T123",
        "APP-M2-T113",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R26",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T233",
      "title": "R27 项目事实一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R27",
      "source_key": "R27.1",
      "dependencies": [
        "APP-M2-T121",
        "APP-M2-T164"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R27",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T234",
      "title": "R28 章节模型评审",
      "status": "planned",
      "phase": "一期完整",
      "source": "R28",
      "source_key": "R28.1",
      "dependencies": [
        "APP-M2-T091",
        "APP-M2-T089",
        "APP-M2-T044",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R28",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T235",
      "title": "R29 本公司查重",
      "status": "planned",
      "phase": "一期完整",
      "source": "R29",
      "source_key": "R29.1",
      "dependencies": [
        "APP-M2-T081",
        "APP-M2-T078",
        "APP-M2-T073",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R29",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T236",
      "title": "R30 无条款段落及范围外服务",
      "status": "planned",
      "phase": "一期完整",
      "source": "R30",
      "source_key": "R30.1",
      "dependencies": [
        "APP-M2-T123",
        "APP-M2-T121",
        "APP-M2-T162"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R30",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T237",
      "title": "R30 额外数值承诺",
      "status": "planned",
      "phase": "一期完整",
      "source": "R30",
      "source_key": "R30.2",
      "dependencies": [
        "APP-M2-T123",
        "APP-M2-T121",
        "APP-M2-T162"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R30",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T238",
      "title": "R31 正文敏感值与真实报告",
      "status": "planned",
      "phase": "一期完整",
      "source": "R31",
      "source_key": "R31.1",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T059"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R31",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T239",
      "title": "R31 插图识别文字与报告附件",
      "status": "planned",
      "phase": "一期完整",
      "source": "R31",
      "source_key": "R31.2",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T059"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R31",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T240",
      "title": "R32 产品范围一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R32",
      "source_key": "R32.1",
      "dependencies": [
        "APP-M2-T051",
        "APP-M2-T099",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R32",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T241",
      "title": "R33 拟派人员条件",
      "status": "planned",
      "phase": "一期完整",
      "source": "R33",
      "source_key": "R33.1",
      "dependencies": [
        "APP-M2-T061",
        "APP-M2-T062",
        "APP-M2-T105",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R33",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T242",
      "title": "R34 AI 痕迹与格式符号残留",
      "status": "planned",
      "phase": "一期完整",
      "source": "R34",
      "source_key": "R34.1",
      "dependencies": [
        "APP-M2-T161",
        "APP-M2-T089"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R34",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T243",
      "title": "R35 称呼一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R35",
      "source_key": "R35.1",
      "dependencies": [
        "APP-M2-T084",
        "APP-M2-T098",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R35",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T244",
      "title": "R43 套话空泛词密度",
      "status": "planned",
      "phase": "一期完整",
      "source": "R43",
      "source_key": "R43.1",
      "dependencies": [
        "APP-M2-T084",
        "APP-M2-T085",
        "APP-M2-T092",
        "APP-M2-T162"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R43",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T245",
      "title": "R43 七类句式及总结策略",
      "status": "planned",
      "phase": "一期完整",
      "source": "R43",
      "source_key": "R43.2",
      "dependencies": [
        "APP-M2-T084",
        "APP-M2-T085",
        "APP-M2-T092",
        "APP-M2-T162"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R43",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T246",
      "title": "R43 注入风格样例照抄",
      "status": "planned",
      "phase": "一期完整",
      "source": "R43",
      "source_key": "R43.3",
      "dependencies": [
        "APP-M2-T084",
        "APP-M2-T085",
        "APP-M2-T092",
        "APP-M2-T162"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R43",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T247",
      "title": "R44 得分要点事实密度",
      "status": "planned",
      "phase": "一期完整",
      "source": "R44",
      "source_key": "R44.1",
      "dependencies": [
        "APP-M2-T124",
        "APP-M2-T162",
        "APP-M2-T165",
        "APP-M1-T12"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R44",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T248",
      "title": "R44 逐事实锚点与段落归属",
      "status": "planned",
      "phase": "一期完整",
      "source": "R44",
      "source_key": "R44.2",
      "dependencies": [
        "APP-M2-T124",
        "APP-M2-T162",
        "APP-M2-T165",
        "APP-M1-T12"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R44",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T249",
      "title": "R44 未登记关键事实前后矛盾",
      "status": "planned",
      "phase": "一期完整",
      "source": "R44",
      "source_key": "R44.3",
      "dependencies": [
        "APP-M2-T124",
        "APP-M2-T162",
        "APP-M2-T165",
        "APP-M1-T12"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R44",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T250",
      "title": "R36 人员资质证明跨册一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R36",
      "source_key": "R36.1",
      "dependencies": [
        "APP-M2-T195",
        "APP-M2-T193",
        "APP-M2-T099",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R36",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T251",
      "title": "R36 偏离和证据版本跨册一致",
      "status": "planned",
      "phase": "一期完整",
      "source": "R36",
      "source_key": "R36.2",
      "dependencies": [
        "APP-M2-T195",
        "APP-M2-T193",
        "APP-M2-T099",
        "APP-M2-T116"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R36",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T252",
      "title": "R37 偏离表一致性",
      "status": "planned",
      "phase": "一期完整",
      "source": "R37",
      "source_key": "R37.1",
      "dependencies": [
        "APP-M2-T193",
        "APP-M2-T113"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R37",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T253",
      "title": "R38 证明材料与评分要点对应",
      "status": "planned",
      "phase": "一期完整",
      "source": "R38",
      "source_key": "R38.1",
      "dependencies": [
        "APP-M2-T058",
        "APP-M2-T059",
        "APP-M2-T114",
        "APP-M2-T075"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R38",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T254",
      "title": "R39 披露类条款",
      "status": "planned",
      "phase": "一期完整",
      "source": "R39",
      "source_key": "R39.1",
      "dependencies": [
        "APP-M2-T057",
        "APP-M2-T105",
        "APP-M2-T161"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R39",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T255",
      "title": "R40 评审索引表",
      "status": "planned",
      "phase": "一期完整",
      "source": "R40",
      "source_key": "R40.1",
      "dependencies": [
        "APP-M2-T192",
        "APP-M2-T123"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R40",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T256",
      "title": "R41 证明材料齐全与盖章",
      "status": "planned",
      "phase": "一期完整",
      "source": "R41",
      "source_key": "R41.1",
      "dependencies": [
        "APP-M2-T195",
        "APP-M2-T059",
        "APP-M2-T099"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R41",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T257",
      "title": "R42 暗标正文节点",
      "status": "planned",
      "phase": "一期完整",
      "source": "R42",
      "source_key": "R42.1",
      "dependencies": [
        "APP-M2-T197",
        "APP-M2-T198",
        "APP-M2-T199",
        "APP-M2-T100"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R42",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T258",
      "title": "R42 暗标输出全部位置",
      "status": "planned",
      "phase": "一期完整",
      "source": "R42",
      "source_key": "R42.2",
      "dependencies": [
        "APP-M2-T197",
        "APP-M2-T198",
        "APP-M2-T199",
        "APP-M2-T100"
      ],
      "page_groups": [
        "PG20"
      ],
      "rule": "R42",
      "existing_reuse": []
    },
    {
      "id": "APP-M2-T259",
      "title": "公司年度中小企业划型记录及声明取值",
      "status": "planned",
      "phase": "一期业务页面/支撑",
      "source": "PRD-v1.8-§5.4.7-K08",
      "source_key": "KB.CLASSIFY",
      "dependencies": [
        "APP-M2-T053",
        "APP-M2-T054",
        "APP-M2-T047"
      ],
      "page_groups": [
        "PG28"
      ],
      "rule": null,
      "existing_reuse": []
    }
  ],
  "page_groups": [
    {
      "id": "PG01",
      "title": "G-01 登录（Keycloak 主题）",
      "prd": "5.12.1",
      "original_wbs": "P02a（2）、P02（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T001",
        "APP-M2-T002",
        "APP-M2-T003",
        "APP-M2-T004",
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T007",
        "APP-M2-T008",
        "APP-M2-T009",
        "APP-M2-T010",
        "APP-M2-T011",
        "APP-M2-T012",
        "APP-M2-T013",
        "APP-M2-T014",
        "APP-M2-T015",
        "APP-M2-T016"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG02",
      "title": "G-02 站内提醒列表 + 顶栏下拉",
      "prd": "5.12.2",
      "original_wbs": "P11（2）、P11a（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T029",
        "APP-M2-T030",
        "APP-M2-T031",
        "APP-M2-T032"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG03",
      "title": "全局搜索（顶栏 + 结果页）",
      "prd": "5.12.3",
      "original_wbs": "P16（1）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T035"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG04",
      "title": "G-03 后台任务中心 + 顶栏抽屉",
      "prd": "5.12.4",
      "original_wbs": "P05（3）、P05a（1）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T019",
        "APP-M2-T020",
        "APP-M2-T021",
        "APP-M2-T022"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG05",
      "title": "P-01 项目列表（工作台）",
      "prd": "5.1.1",
      "original_wbs": "E01",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T001",
        "APP-M2-T002",
        "APP-M2-T003",
        "APP-M2-T004",
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T007",
        "APP-M2-T008",
        "APP-M2-T009",
        "APP-M2-T094",
        "APP-M2-T095",
        "APP-M2-T096",
        "APP-M2-T097",
        "APP-M2-T098",
        "APP-M2-T099",
        "APP-M2-T100",
        "APP-M2-T153",
        "APP-M2-T154"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG06",
      "title": "P-02 新建项目（含 R19）",
      "prd": "5.1.2",
      "original_wbs": "E01",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T094",
        "APP-M2-T095",
        "APP-M2-T096",
        "APP-M2-T097",
        "APP-M2-T098",
        "APP-M2-T099",
        "APP-M2-T100"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG07",
      "title": "P-03 项目概览（含 P-17 折叠区）",
      "prd": "5.1.3、5.7.13",
      "original_wbs": "E01、E01b（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T094",
        "APP-M2-T095",
        "APP-M2-T096",
        "APP-M2-T097",
        "APP-M2-T098",
        "APP-M2-T099",
        "APP-M2-T100",
        "APP-M2-T153",
        "APP-M2-T154"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG08",
      "title": "P-04 招标文件上传与解析进度",
      "prd": "5.2.1",
      "original_wbs": "E02（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T101",
        "APP-M2-T102"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG09",
      "title": "P-05 解析结果 + 抽取后处理",
      "prd": "5.2.2、5.2.4",
      "original_wbs": "E04（6）、E04a（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T103",
        "APP-M2-T104",
        "APP-M2-T105",
        "APP-M2-T106",
        "APP-M2-T107",
        "APP-M2-T108",
        "APP-M2-T109",
        "APP-M2-T110",
        "APP-M2-T111"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG10",
      "title": "P-06 响应矩阵 + 挂证据抽屉",
      "prd": "5.3.1",
      "original_wbs": "E05（6）、E05a（1）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T112",
        "APP-M2-T113",
        "APP-M2-T114",
        "APP-M2-T115",
        "APP-M2-T116",
        "APP-M2-T117",
        "APP-M2-T118"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG11",
      "title": "P-07 SLA 矩阵",
      "prd": "5.3.2",
      "original_wbs": "E06",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T119",
        "APP-M2-T120",
        "APP-M2-T121",
        "APP-M2-T122"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG12",
      "title": "P-09 项目事实表",
      "prd": "5.7.8",
      "original_wbs": "E06（与 P-07 共 4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T119",
        "APP-M2-T120",
        "APP-M2-T121",
        "APP-M2-T122"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG13",
      "title": "P-18 分册分流确认",
      "prd": "5.3.1 规则 8",
      "original_wbs": "E05",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T112",
        "APP-M2-T113",
        "APP-M2-T114",
        "APP-M2-T115",
        "APP-M2-T116",
        "APP-M2-T117"
      ],
      "existing_tasks": [
        "APP-M1-T14"
      ]
    },
    {
      "id": "PG14",
      "title": "P-16 项目设置",
      "prd": "5.1.4",
      "original_wbs": "E01",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T014",
        "APP-M2-T015",
        "APP-M2-T016",
        "APP-M2-T094",
        "APP-M2-T095",
        "APP-M2-T096",
        "APP-M2-T097",
        "APP-M2-T098",
        "APP-M2-T099",
        "APP-M2-T100"
      ],
      "existing_tasks": [
        "APP-M1-T14"
      ]
    },
    {
      "id": "PG15",
      "title": "P-10 写作方案与大纲确认",
      "prd": "5.7.2",
      "original_wbs": "F01（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T123",
        "APP-M2-T124",
        "APP-M2-T125",
        "APP-M2-T126"
      ],
      "existing_tasks": [
        "APP-M1-T15"
      ]
    },
    {
      "id": "PG16",
      "title": "P-12 章节循环进度",
      "prd": "5.7.6",
      "original_wbs": "F10",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T019",
        "APP-M2-T020",
        "APP-M2-T021",
        "APP-M2-T129",
        "APP-M2-T130",
        "APP-M2-T131",
        "APP-M2-T132",
        "APP-M2-T133",
        "APP-M2-T134",
        "APP-M2-T135",
        "APP-M2-T136"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG17",
      "title": "P-13 人工处理队列",
      "prd": "5.7.7",
      "original_wbs": "F10",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T129",
        "APP-M2-T130",
        "APP-M2-T131",
        "APP-M2-T132",
        "APP-M2-T133",
        "APP-M2-T134",
        "APP-M2-T135",
        "APP-M2-T136"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG18",
      "title": "系统生成章节预览（五类）",
      "prd": "5.7.2 规则 1、5.11.8",
      "original_wbs": "F09（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T127",
        "APP-M2-T128",
        "APP-M2-T191",
        "APP-M2-T192",
        "APP-M2-T193",
        "APP-M2-T194",
        "APP-M2-T195"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG19",
      "title": "P-17 / W-03 写作观察统计",
      "prd": "5.7.13",
      "original_wbs": "F11（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T137",
        "APP-M2-T138",
        "APP-M2-T139",
        "APP-M2-T189",
        "APP-M2-T190"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG20",
      "title": "P-14 合规检查",
      "prd": "5.8.2、5.8.3、5.8.5",
      "original_wbs": "G04（6）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T140",
        "APP-M2-T141",
        "APP-M2-T142",
        "APP-M2-T143",
        "APP-M2-T144",
        "APP-M2-T145",
        "APP-M2-T203",
        "APP-M2-T204",
        "APP-M2-T205",
        "APP-M2-T206",
        "APP-M2-T207",
        "APP-M2-T208",
        "APP-M2-T209",
        "APP-M2-T210",
        "APP-M2-T211",
        "APP-M2-T212",
        "APP-M2-T213",
        "APP-M2-T214",
        "APP-M2-T215",
        "APP-M2-T216",
        "APP-M2-T217",
        "APP-M2-T218",
        "APP-M2-T219",
        "APP-M2-T220",
        "APP-M2-T221",
        "APP-M2-T222",
        "APP-M2-T223",
        "APP-M2-T224",
        "APP-M2-T225",
        "APP-M2-T226",
        "APP-M2-T227",
        "APP-M2-T228",
        "APP-M2-T229",
        "APP-M2-T230",
        "APP-M2-T231",
        "APP-M2-T232",
        "APP-M2-T233",
        "APP-M2-T234",
        "APP-M2-T235",
        "APP-M2-T236",
        "APP-M2-T237",
        "APP-M2-T238",
        "APP-M2-T239",
        "APP-M2-T240",
        "APP-M2-T241",
        "APP-M2-T242",
        "APP-M2-T243",
        "APP-M2-T244",
        "APP-M2-T245",
        "APP-M2-T246",
        "APP-M2-T247",
        "APP-M2-T248",
        "APP-M2-T249",
        "APP-M2-T250",
        "APP-M2-T251",
        "APP-M2-T252",
        "APP-M2-T253",
        "APP-M2-T254",
        "APP-M2-T255",
        "APP-M2-T256",
        "APP-M2-T257",
        "APP-M2-T258"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG21",
      "title": "P-15 导出",
      "prd": "5.9.1、5.9.2",
      "original_wbs": "H03（3）、H04（1）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T149",
        "APP-M2-T150",
        "APP-M2-T151",
        "APP-M2-T152",
        "APP-M2-T196",
        "APP-M2-T197",
        "APP-M2-T198",
        "APP-M2-T199",
        "APP-M2-T200",
        "APP-M2-T201",
        "APP-M2-T202"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG22",
      "title": "P-11 编辑台",
      "prd": "5.11.2～5.11.10",
      "original_wbs": "I01（12）、I02（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T001",
        "APP-M2-T002",
        "APP-M2-T003",
        "APP-M2-T004",
        "APP-M2-T005",
        "APP-M2-T006",
        "APP-M2-T007",
        "APP-M2-T008",
        "APP-M2-T009",
        "APP-M2-T014",
        "APP-M2-T015",
        "APP-M2-T016",
        "APP-M2-T160",
        "APP-M2-T161",
        "APP-M2-T162",
        "APP-M2-T163",
        "APP-M2-T164",
        "APP-M2-T165",
        "APP-M2-T166",
        "APP-M2-T167",
        "APP-M2-T168",
        "APP-M2-T169",
        "APP-M2-T170",
        "APP-M2-T171",
        "APP-M2-T172",
        "APP-M2-T173",
        "APP-M2-T174",
        "APP-M2-T175"
      ],
      "existing_tasks": [
        "APP-M1-T15"
      ]
    },
    {
      "id": "PG23",
      "title": "P-11 对话助手 + 答案卡",
      "prd": "5.11.3～5.11.6、5.11.15",
      "original_wbs": "I04（5）、I04a（2）、I04b（1）、I05（4）、I06（2）、E08（1，可选）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T176",
        "APP-M2-T177",
        "APP-M2-T178",
        "APP-M2-T179",
        "APP-M2-T180",
        "APP-M2-T181",
        "APP-M2-T182",
        "APP-M2-T183",
        "APP-M2-T184",
        "APP-M2-T185",
        "APP-M2-T186",
        "APP-M2-T187",
        "APP-M2-T188",
        "APP-M2-T189",
        "APP-M2-T190"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG24",
      "title": "K-01 资料库首页",
      "prd": "5.4.2",
      "original_wbs": "C07（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T071",
        "APP-M2-T072",
        "APP-M2-T073"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG25",
      "title": "K-02 / K-03 资料列表与详情（通用框架）",
      "prd": "5.4.1、5.4.3、5.4.4",
      "original_wbs": "C01（5）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T046",
        "APP-M2-T047",
        "APP-M2-T048",
        "APP-M2-T049",
        "APP-M2-T050"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG26",
      "title": "K-04 人员与人员证书",
      "prd": "5.4.5",
      "original_wbs": "C04（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T017",
        "APP-M2-T018",
        "APP-M2-T060",
        "APP-M2-T061",
        "APP-M2-T062",
        "APP-M2-T063"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG27",
      "title": "K-05 原厂授权与授权链",
      "prd": "5.4.6",
      "original_wbs": "C05（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T064",
        "APP-M2-T065",
        "APP-M2-T066"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG28",
      "title": "K-06～K-08、K-11～K-13 公司主体、证明材料、资质、划型、附件、合规事件、工具设备",
      "prd": "5.4.7",
      "original_wbs": "C03（6）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T054",
        "APP-M2-T055",
        "APP-M2-T056",
        "APP-M2-T057",
        "APP-M2-T058",
        "APP-M2-T059",
        "APP-M2-T259"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG29",
      "title": "K-09、K-10、K-14 SLA 模板、全局变量、业绩",
      "prd": "5.4.7",
      "original_wbs": "C06（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T067",
        "APP-M2-T068",
        "APP-M2-T069",
        "APP-M2-T070"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG30",
      "title": "平台主数据（厂商产品、证书类别、附件槽位、划型标准）",
      "prd": "5.10.3",
      "original_wbs": "C02（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T051",
        "APP-M2-T052",
        "APP-M2-T053"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG31",
      "title": "附件智能识别填表",
      "prd": "5.4.4",
      "original_wbs": "C08（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T074",
        "APP-M2-T075"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG32",
      "title": "K-15 方案片段库",
      "prd": "5.5.2",
      "original_wbs": "D01（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T076",
        "APP-M2-T077",
        "APP-M2-T078",
        "APP-M2-T079"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG33",
      "title": "K-16 历史标书导入",
      "prd": "5.5.3",
      "original_wbs": "D02（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T080",
        "APP-M2-T081"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG34",
      "title": "W-01 写作档案",
      "prd": "5.6.2",
      "original_wbs": "D03（6）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T082",
        "APP-M2-T083",
        "APP-M2-T084",
        "APP-M2-T085",
        "APP-M2-T086",
        "APP-M2-T087"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG35",
      "title": "任务卡与提示词模板",
      "prd": "5.7.9、5.6.4",
      "original_wbs": "D04（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T088",
        "APP-M2-T089",
        "APP-M2-T090"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG36",
      "title": "W-02 风格样例 + 审查清单",
      "prd": "5.6.5、5.6.4（默认审查清单）",
      "original_wbs": "D05（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T091",
        "APP-M2-T092",
        "APP-M2-T093"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG37",
      "title": "A-01 公司管理、A-02 用户与角色",
      "prd": "5.10.1、5.10.2",
      "original_wbs": "P10（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T026",
        "APP-M2-T027",
        "APP-M2-T028"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG38",
      "title": "A-03 字典配置",
      "prd": "5.10.3",
      "original_wbs": "P09（3，含状态注册表）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T023",
        "APP-M2-T024",
        "APP-M2-T025"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG39",
      "title": "A-08 模型登记、A-09 文档解析服务",
      "prd": "6.6.1、6.6.2",
      "original_wbs": "B01（4）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T036",
        "APP-M2-T037",
        "APP-M2-T038",
        "APP-M2-T039"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG40",
      "title": "A-10 任务与模型对应表、A-05 模型开放",
      "prd": "6.6.3、5.10.5",
      "original_wbs": "B02（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T040",
        "APP-M2-T041"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG41",
      "title": "A-05 生成闭环与编辑台配置（联动校验）",
      "prd": "6.9、5.10.5",
      "original_wbs": "B06（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T043",
        "APP-M2-T044",
        "APP-M2-T045"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG42",
      "title": "A-04 资料库设置",
      "prd": "5.10.4",
      "original_wbs": "C07 或 C01（随资料库）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T071",
        "APP-M2-T072",
        "APP-M2-T073"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG43",
      "title": "A-06 审计日志、服务健康基础",
      "prd": "5.10.6、6.7",
      "original_wbs": "J01（3）、P04（2，含 MaskedField 查看留痕）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T017",
        "APP-M2-T018",
        "APP-M2-T157",
        "APP-M2-T158",
        "APP-M2-T159"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG44",
      "title": "A-11 部署与服务状态",
      "prd": "5.12.6",
      "original_wbs": "J01a（1）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T042"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG45",
      "title": "A-12 界面品牌",
      "prd": "5.12.7",
      "original_wbs": "P15（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T033",
        "APP-M2-T034"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG46",
      "title": "A-07 规则配置（合规规则 + 兜底扫描词表）",
      "prd": "5.12.5",
      "original_wbs": "G06（3）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T146",
        "APP-M2-T147",
        "APP-M2-T148"
      ],
      "existing_tasks": []
    },
    {
      "id": "PG47",
      "title": "集团管理员只读视图",
      "prd": "5.10、2.3",
      "original_wbs": "J02（2）",
      "status": "未完整实现",
      "tasks": [
        "APP-M2-T155",
        "APP-M2-T156"
      ],
      "existing_tasks": []
    }
  ],
  "rules": [
    {
      "id": "R01",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T203"
      ],
      "source_notes": "本轮改为以“录入人确认”为主，审核为可选开关"
    },
    {
      "id": "R02",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T204"
      ],
      "source_notes": "按字典第 6 章第 4 项结论加强"
    },
    {
      "id": "R03",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T205"
      ],
      "source_notes": "基准日改为投标截止时间（第 6 章第 7 项）"
    },
    {
      "id": "R04",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T206"
      ],
      "source_notes": "提醒发给资料负责人"
    },
    {
      "id": "R05",
      "phase": "二期",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T207"
      ],
      "source_notes": ""
    },
    {
      "id": "R06",
      "phase": "二期",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T208"
      ],
      "source_notes": "MVP 只比对录入字段，OCR 比对二期"
    },
    {
      "id": "R07",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T209"
      ],
      "source_notes": "本轮加入多级授权链"
    },
    {
      "id": "R08",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T210"
      ],
      "source_notes": "运维专项"
    },
    {
      "id": "R09",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T211",
        "APP-M2-T212",
        "APP-M2-T213"
      ],
      "source_notes": "运维专项；v1.2 范围扩展到承诺类事实（质保期、培训次数和课时、资源到位天数等），不得劣于招标要求"
    },
    {
      "id": "R10",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T214",
        "APP-M2-T215"
      ],
      "source_notes": "运维专项"
    },
    {
      "id": "R11",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T216"
      ],
      "source_notes": "按字典第 6 章第 12 项和人员归属字段"
    },
    {
      "id": "R12",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T217"
      ],
      "source_notes": "按第 6 章第 13 项结论，冲突降为提示"
    },
    {
      "id": "R13",
      "phase": "一期简化",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T218"
      ],
      "source_notes": "MVP 只检查年限、签约主体、证明材料齐全"
    },
    {
      "id": "R14",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T219"
      ],
      "source_notes": "v1.2 增加“同一附件在同一分册中插入多次”的提示"
    },
    {
      "id": "R15",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T220"
      ],
      "source_notes": ""
    },
    {
      "id": "R16",
      "phase": "一期简化",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T221"
      ],
      "source_notes": "MVP 只检查主体状态与证明材料有效天数"
    },
    {
      "id": "R17",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T222"
      ],
      "source_notes": ""
    },
    {
      "id": "R18",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T223"
      ],
      "source_notes": "见 5.8.3 节；v1.2 写明与 R29 的分工：R18 防集团内不同公司“异常一致”，R29 查本公司内部重复，文本指纹能力两条规则共用；v1.5：一期只做文本层段落相似度，结果只显示“段落相似度”，语义层放二期"
    },
    {
      "id": "R19",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T224"
      ],
      "source_notes": "依据条例第三十四条、政府采购法实施条例第十八条，见 8.3 节"
    },
    {
      "id": "R20",
      "phase": "二期",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T225"
      ],
      "source_notes": "对应条例第四十条第（一）项；需先确定跨公司识别同一自然人的口径"
    },
    {
      "id": "R21",
      "phase": "二期",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T226"
      ],
      "source_notes": "对应条例第四十条第（三）项"
    },
    {
      "id": "R22",
      "phase": "二期",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T227"
      ],
      "source_notes": "对应条例第四十条第（六）项"
    },
    {
      "id": "R23",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T228"
      ],
      "source_notes": "导出闸门；v1.2 纳入从评分项中抽出的否决子句（例如隐瞒安全隐患、行政处罚将被否决）"
    },
    {
      "id": "R24",
      "phase": "一期简化",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T229"
      ],
      "source_notes": "MVP 检查格式文件齐全和页数；字体字号等二期；v1.2：偏离表、评审索引表、点对点应答作为格式文件时纳入检查，按分册分别检查；页数按分册计；v1.5：系统在导出前无法得到 Word 排版后的准确页数，页数按估算给出，准确页数以商务合标后的 Word 为准（5.9.2 节第 2 项）"
    },
    {
      "id": "R25",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T230",
        "APP-M2-T231"
      ],
      "source_notes": "防止复制旧稿带入错误，也降低“异常一致”风险；v1.2 在已知名单比对之外增加机构名称识别（按“公司、中心、局、行、院”等机构后缀识别，后缀表由平台维护，示例），编写规范 p.30 示例中残留了其他单位名称"
    },
    {
      "id": "R26",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T232"
      ],
      "source_notes": "v1.1 新增。只判断“有没有段落回应”，“回应得是否实质”由 R28 提示"
    },
    {
      "id": "R27",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T233"
      ],
      "source_notes": "v1.1 新增。按“关键词＋取值模式”比对手写值，变量引用视为一致（实现细节由研发细化，建议）；v1.2 在全文检查中跨分册重跑"
    },
    {
      "id": "R28",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T234"
      ],
      "source_notes": "v1.1 新增。不是确定性规则，结果不可复现，只用于提示和自动修正；开关与评审模型见 6.9 节；v1.2 问题类型增加“语句不通顺”，默认审查清单增加编写规范相关条目（5.6.4 节）；v1.3 问题类型增加“空泛表态、无具体措施”，默认严重程度为“低”（5.7.4 节第 2 条）"
    },
    {
      "id": "R29",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T235"
      ],
      "source_notes": "v1.2 新增。8 个字符的规则依据公司内部编写规范（p.25）；字数和年限可由管理员调整（5.10.4 节）；见 5.8.3 节"
    },
    {
      "id": "R30",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T236",
        "APP-M2-T237"
      ],
      "source_notes": "v1.2 新增。写作方案中标为“增值”的章节不算超范围，但其中的额外数值承诺仍按②处理（neil 确认第 3 点）；v1.4：对话助手样例中的额外数值承诺在预检时标出，写入后由增量复查报出并直接转人工；额外承诺候选由本地模型找出、规则核对矩阵（6.4 节）；依据编写规范 p.27（逐条响应技术需求和技术评分即可，不要堆砌无关材料来凑页数，销售另有要求的除外）"
    },
    {
      "id": "R31",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T238",
        "APP-M2-T239"
      ],
      "source_notes": "v1.2 新增。依据编写规范 p.27（不得直接套用现成的巡检报告，即使已经脱敏）；章节循环中一律直接转人工（建议）；通过证据引用、变量插入的本公司信息不报"
    },
    {
      "id": "R32",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T240"
      ],
      "source_notes": "v1.2 新增。按厂商产品字典的别名识别；与 R08、R13 联动"
    },
    {
      "id": "R33",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T241"
      ],
      "source_notes": "v1.2 新增。不参与章节循环"
    },
    {
      "id": "R34",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T242"
      ],
      "source_notes": "v1.2 新增。由系统直接删除或转换，不调用模型；不允许公司关闭。v1.3：只处理确定的残留，套话腔、空泛表态、句式模式化由 R43 处理；R34 不删除、不改动模型服务商添加的 AI 生成标识（3.2 节）"
    },
    {
      "id": "R35",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T243"
      ],
      "source_notes": "v1.2 新增。v1.3：禁用词逐个命中、逐个警告，仍由本条负责；套话表中的条目按密度统计，由 R43 负责，两者不重复报"
    },
    {
      "id": "R43",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T244",
        "APP-M2-T245",
        "APP-M2-T246"
      ],
      "source_notes": "v1.3 新增。与 R34 分开；命中的句子交给定位修正，只改命中的句子，系统不自动删除；公司可关闭（关闭后观察指标照常计算，建议）；阈值和允许次数为示例值，试运行校准；详见 5.8.7 节"
    },
    {
      "id": "R44",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T247",
        "APP-M2-T248",
        "APP-M2-T249"
      ],
      "source_notes": "v1.3 新增。不允许公司关闭（建议）；已由 R10、R27、R30、R36 负责的数值和事实不重复报；客户系统名的候选由本地模型识别（6.4 节）；详见 5.8.7 节。v1.4：对话助手撰写的段落按模型撰写段落处理（5.11.7 节）"
    },
    {
      "id": "R36",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T250",
        "APP-M2-T251"
      ],
      "source_notes": "v1.2 新增。服务期、质保期、SLA 等事实继续由 R10、R27 负责，不重复检查；只有一个分册在系统内编制时跳过，并在合标核对清单中写明须人工核对"
    },
    {
      "id": "R37",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T252"
      ],
      "source_notes": "v1.2 新增。不允许公司关闭"
    },
    {
      "id": "R38",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T253"
      ],
      "source_notes": "v1.2 新增。截图图像内容理解放二期"
    },
    {
      "id": "R39",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T254"
      ],
      "source_notes": "v1.2 新增。依据编写规范 p.13 的评分表样例（隐瞒须披露事项的作否决处理，转述）；章节循环中相关问题一律直接转人工；资料库无记录不等于没有发生，所以不能自动判为通过（建议）；不允许公司关闭"
    },
    {
      "id": "R40",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T255"
      ],
      "source_notes": "v1.2 新增。索引表在技术分册内由系统生成；页码列留空或标“合标后由商务填写”，系统不做页码校验（neil 确认第 2 点；编写规范 p.15：先标出页码位置，待商务合标后统一修改）；招标要求索引表时不允许公司关闭"
    },
    {
      "id": "R41",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T256"
      ],
      "source_notes": "v1.2 新增"
    },
    {
      "id": "R42",
      "phase": "一期完整",
      "status": "未完整交付",
      "tasks": [
        "APP-M2-T257",
        "APP-M2-T258"
      ],
      "source_notes": "v1.2 新增。**系统补充的规则**，依据 PRD 抽取类别 8 的“暗标要求”，不是编写规范原文的要求"
    }
  ]
}
```
<!-- icg-task-map:end -->

## 核对方式和结果

本次读取原WBS与规则表核对：190个原子来源唯一且全映射；47来源组至少1实施入口；R01～R44唯一全覆盖，36/3/5期次一致；259新ID唯一、全部planned；依赖只指既有APP-M1/BE卡或计划内有效ID，无循环；T14/T15仅引用，ICG历史及59FE卡未改。

后续检查建议：从icg-task-map固定块读JSON，核对counts、各数组唯一性、每页面/规则任务非空及有效ID；对比TASK_BOARD的标题、状态和依赖，再检查done交付、代码解释和真实行为。治理检查仅验证记录一致，不替代功能验收。最终APP-M1-T08按逐页布局/真实HTTP、多角色失败恢复、完整结构化编辑和一期完整/简化规则、Word/WPS内容版式及实际清单审计；二期保持原排期。未达条件继续未完成。
