为什么有这个文件：记录QA对APP-M2-T004（业务小组件封装：LevelTag、AiTag、DirectTag、Cite、SourceBar）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行前端单测全量回归、生产环境打包构建与体积审计，深度核查 5 类业务小组件规范、AI 紫色彩隔离门禁机制与 WCAG 4.5:1 对比度。

# APP-M2-T004 业务小组件封装独立复验与 QA 签署（REV-M0-T41）

- 被验任务：[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004) · 业务小组件封装
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T004 交付](../delivery/APP-M2-T004.md)、[代码解释](../code/APP-M2-T004.md)
- 被验核心文件：`frontend/web/src/BusinessTags.tsx`、`frontend/web/src/business-tags.ts`、`frontend/web/tests/business-tags.test.mjs`、`tests/frontend/business-tags.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T004 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 LevelTag 条款级别支持 | 通过 | `resolveLevelTag handles clause categories and solid/subtle modes`：支持 8 类条款级别（阻断 blocker、废标 void、星号 star、警告 warning、加分 bonus、评分 scoring、资格 qualification、提示 hint、一般 general）；阻断默认实心红底白字（#D9363E / #FFFFFF），星号采用加粗红字，一般条款中性灰；支持 solid/subtle 切换 |
| AC-02 AiTag 语义变体与专用锁定 | 通过 | `resolveAiTag properly sets AI purple palette and variant labels`：支持 6 类语义变体（suggestion、generated、candidate、model、assistant、demo）；严格锁定 AI 主紫 `#6E4BD8` 与助手紫 `#A23CC8`，浅紫底色 `#F2EEFC`，深紫文字 `#5329B3`；支持 solid 实心模式与 `aria-label="AI辅助标识：..."` |
| AC-03 DirectTag 系统直查深蓝 | 通过 | `resolveDirectTag uses system direct blue and rejects AI purple`：支持 4 类变体（direct、adopt、response、struct）；默认呈现“系统直查 · 未经模型”；使用系统深蓝 `#1E4DB7` 与浅蓝底 `#EEF3FC`；内置 `assertNotAiColor`，严禁使用 AI 紫色阶 |
| AC-04 Cite 引用标注与溯源 Popover | 通过 | `resolveCite handles evidence, snippet, tender, fact, and none types`：支持 5 类引用类型（evidence 资料证据、snippet 方案片段、tender 招标原文、fact 变量事实高亮、none 无知识库来源）；支持上标展示，悬浮 Popover 卡片展示标题、版本号、有效期、确认状态、责任人、依据指纹与摘录引用 |
| AC-05 SourceBar 段落色条与指纹卡片 | 通过 | `resolveSourceBar and formatFingerprint handle provenance metadata and stale status`：支持 7 类来源（evidence、snippet、tender、model、assistant、manual、system）；支持 paragraph（3px 侧边条）、bottom（底部条）与 inline 布局；指纹缩略 `formatFingerprint`（`fp:xxxx...`）；支持“来源已变化待核对”黄底预警与“核对最新来源”行动按钮 |
| AC-06 WCAG 4.5:1 对比度全面达标 | 通过 | `WCAG 4.5:1 text contrast compliance for all business tag colors`：阻断实心（4.66:1）、阻断浅底（7.10:1）、星号条款（5.86:1）、警告黄色（5.12:1）、加分青色（7.82:1）、资格极客蓝（5.53:1）、一般灰条款（5.88:1）、AI 紫实心（5.73:1）、AI 紫浅底（7.86:1）、DirectTag 直查蓝（6.88:1）、变量黄底（4.95:1）、人工编写绿（6.20:1）、方案片段青（8.00:1），全部 ≥ 4.5:1 |
| AC-07 AI 紫色彩隔离门禁机制 | 通过 | `strict AI purple isolation rule: AI purple only appears on AiTag`：`isAiColor` 精确识别所有 AI 紫色阶；`assertNotAiColor` 在非 AI 标签误用紫色时强制抛出 `[ICG 色彩规范违规]` 异常；DirectTag 等组件在运行时配置与单测中严格断言防守 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 前端全量单测 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **141 passed, 0 failed** (含 14 项业务小组件专项断言) | 1.38s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，无报错无告警) | 0.71s |
| 产物体积与分包审计 | 检查 `frontend/web/dist/assets/` | `index.js` **289.99 kB** (gzip: 92.21 kB)，Popover 独立抽离分包 `popover-DhI_cfxl.js` (5.29 kB)，主包无反弹 | — |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (355 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **AI 紫色防混用设计优秀**：通过纯函数断言 `assertNotAiColor`，在代码层形成了防误用的硬约束门禁，确保未来无论何种业务迭代，AI 紫均不会被误借用到人工、系统或资格标签中。
2. **Popover 独立懒加载**：悬浮卡片 Popover 被打包工具干净抽离为 5.29 kB 的异步代码块，确保常规页面渲染保持极速，符合高性能规范。
3. **已与 EditorPage 对接准备**：在 `EditorPage.tsx` 中已引入这批标签用于章节段落侧边条与段落来源标记，无缝支持后续工作区渲染。

## 签署状态

APP-M2-T004 保持 **in-review**，**严禁标 done**。
