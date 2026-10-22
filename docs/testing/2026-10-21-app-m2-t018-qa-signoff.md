为什么有这个文件：记录QA对APP-M2-T018（掩码规则读取与查看留痕提示）的独立复验与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行公司掩码动态规则专属单测、前端全量单测套件、生产构建打包与首屏体积门禁审计（<= 295 kB），针对性核查 PRD v1.8 §5.4.5、§5.9.1、§6.9 与设计规范 9.10 所规定的公司级掩码配置动态提取清洗、PRD §6.9 “不可设为不掩码/不提供关闭掩码开关”的合规硬拦截防线、useCompanyMaskSettings 响应式联动刷新机制（6+4 切换至 3+4 页面所有 MaskedField 自动自适应重绘）、多模式查看留痕合规警示组件（MaskNoticeBanner / AuditTraceHint，WCAG AA 4.5:1 对比度）以及全链路零 storage/URL 残留硬断言。

# APP-M2-T018 掩码规则读取与查看留痕提示独立复测与 QA 签署

- 被验任务：[APP-M2-T018](../tasks/APP-M2.md#app-m2-t018) · 掩码规则读取与查看留痕提示
- 关联审查任务：REV-M0-T59
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T018 交付](../delivery/APP-M2-T018.md)、[代码解释](../code/APP-M2-T018.md)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T017](../tasks/APP-M2.md#app-m2-t017)
- 被验核心文件：
  - `frontend/web/src/admin/company-mask-settings.ts`
  - `frontend/web/src/admin/company-mask-context.ts`
  - `frontend/web/src/admin/useCompanyMaskSettings.ts`
  - `frontend/web/src/admin/MaskNoticeBanner.tsx`
  - `frontend/web/src/admin/MaskedField.tsx`
  - `tests/frontend/company-mask-settings.test.mjs`
  - `frontend/web/tests/company-mask-settings.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T018 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 公司级掩码规则动态提取与空值安全兜底 | 通过 | `extractMaskRulesFromCompanySettings` 纯函数支持从公司整体设置对象、嵌套 `sensitive_mask_rules` 键或 JSON 字符串中动态解析脱敏规则；支持字符串快捷模式（`'strict'` / `'standard'`）；当输入为 `null`、`undefined` 或损坏的 JSON 时，无崩溃且 100% 安全回退至平台安全默认配置 `DEFAULT_MASK_RULES` |
| AC-02 PRD §6.9 合规安全清洗与防绕过硬防线 | 通过 | `sanitizeMaskRule` 严格落实 PRD §6.9 规定：“每类保留的前后位数可调，但不能设为‘不掩码’，不提供关闭掩码的开关”：① 拦截负数前缀/后缀；② 拦截企图破坏掩码的越界参数（身份证 prefix 限制最大为 8，suffix 至少 1 不超 6；手机号 prefix 限制最大为 4，suffix 至少 1 不超 4；银行卡 prefix 严格强制为 0 杜绝前缀明文）；③ 拦截空白 `maskChar` 并自动强制纠正为 `*` |
| AC-03 React 掩码上下文与动态响应式更新机制 | 通过 | `CompanyMaskContext` 与 `CompanyMaskProvider` 容器提供 `getRule(type)`、`idCardMode`、`source`（`'company'` / `'default'`）、`updateRules` 与 `resetRules`；支持在运行时通过 `updateRules('strict')` 或局部打补丁即时修改规则并触发整个上下文下游组件响应式重绘 |
| AC-04 掩码展示组件 MaskedField 自适应联动刷新 | 通过 | `MaskedField.tsx` 深度引入 `useCompanyMaskSettings()`，计算优先级满足 `maskRule || getRule(fieldType)`：当外部未显式覆写规则时，自适应消费公司上下文动态规则；当公司设置由标准 6+4 切换至严格 3+4 时，页面内所有挂载的 `MaskedField` 自动同步重新计算并刷新渲染结果，满足交接验收标准 |
| AC-05 查看留痕合规警示横幅与紧凑别名组件 | 通过 | `MaskNoticeBanner` 封装 PRD §5.4.5 与 §7.3 标准留痕警示文案（“当前页面涉及敏感个人信息，调阅完整值将被记录安全审计日志（操作人、时间、原因与网络环境）”）；支持 `banner`（默认横幅）、`inline`（内联行提示）与 `compact`（带悬停说明的紧凑图标）三种呈现模式；配套别名 `AuditTraceHint`；采用 `#fffbe6` 背景、`#ffe58f` 边框与 `#613400` 文字，完全满足 WCAG AA 4.5:1 对比度标准 |
| AC-06 零 storage 与零 URL 残留硬安全断言 | 通过 | `assertNoSensitiveLeak` 运行时断言与 AST 静态契约双重保障：动态规则提取、上下文分发与留痕组件渲染全链路严禁向 `localStorage`、`sessionStorage` 写入敏感个人信息，URL 中不携带任何脱敏前明文，杜绝旁路泄露 |
| AC-07 生产构建打包与包体积门禁（<= 295 kB） | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 619ms，0 错误 0 告警）；首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（Gzip 后 **93.90 kB**），零包体积膨胀，完全满足 **<= 295 kB** 预算红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 公司掩码配置专属单测套件 | `node --test tests/frontend/company-mask-settings.test.mjs frontend/web/tests/company-mask-settings.test.mjs` | **10 passed, 0 failed** (单元断言 6 项 + AST/契约测试 4 项) | 0.19s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **253 passed, 0 failed** (包含 10 项新增专属单测，100% 通过) | 2.63s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 619ms) | 0.62s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-fu3kmuVM.js` **294.86 kB**（gzip: 93.90 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **“不可关闭掩码”的合规硬拦截防线价值**：PRD §6.9 明确要求“每类保留的前后位数可调，但不能设为‘不掩码’，不提供关闭掩码的开关”。在前端 `sanitizeMaskRule` 中实施硬拦截，防止后端或配置中心偶发下发 `prefix=18` 等不合理参数导致个人隐私明文直接泄露，体现了纵深防御原则。
2. **响应式上下文与零刷新切换体验**：通过将规则解析为响应式 React 上下文并在 `MaskedField` 中消费 `getRule`，租户或管理员在页面内动态切换合规严格度时，无需刷新网页或重新请求数据，所有高敏字段即刻自适应完成文本掩码重绘，用户体验丝滑。
3. **首屏体积零膨胀控制**：当前主包维持在 294.86 kB，与 APP-M2-T017 保持完全相同。实现中没有引入任何额外第三方 UI 库或图标，纯利用轻量纯函数与既有 Ant Design 基础组件，完美守护了 295 kB 的包体积红线。

## 签署状态

APP-M2-T018 保持 **in-review**，**严禁标 done**。
