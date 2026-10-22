为什么有这个文件：记录QA对APP-M2-T017（MaskedField 与“查看完整值”弹窗，原因必填）的独立复验与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行掩码字段专属单测、前端全量单测套件、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 PRD v1.8 §5.4.5、§2.3 与 §5.9.1 所规定的高敏个人信息脱敏规则（身份证标准 6+4 与严格 3+4、手机 3+4、银行卡仅保留后 4 位）、查看原因强校验（拦截空串、纯空格与不足 5 字符）、8系统角色调阅权限矩阵强隔离（仅限 company_admin 与 data_admin，其余角色默认零 DOM 残留）、零 storage/URL 明文残留硬断言以及关闭弹窗即刻销毁明文内存的安全生命周期。

# APP-M2-T017 MaskedField 与“查看完整值”弹窗（原因必填）独立复测与 QA 签署

- 被验任务：[APP-M2-T017](../tasks/APP-M2.md#app-m2-t017) · MaskedField 与“查看完整值”弹窗（原因必填）
- 关联审查任务：REV-M0-T58
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T017 交付](../delivery/APP-M2-T017.md)、[代码解释](../code/APP-M2-T017.md)
- 被验核心文件：`frontend/web/src/admin/sensitive-mask.ts`、`frontend/web/src/admin/RevealFieldModal.tsx`、`frontend/web/src/admin/MaskedField.tsx`、`tests/frontend/masked-field.test.mjs`、`frontend/web/tests/masked-field.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T017 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 表格驱动高敏脱敏规则 | 通过 | `maskSensitiveValue`、`maskIdCard`、`maskPhone`、`maskBankCard`：① 身份证号支持标准 6+4（`110101********2345`）与严格 3+4（`110***********2345`）；② 手机号支持 3+4（`138****5678`）；③ 银行账号严格仅保留后 4 位（`***************0123`）；④ 邮箱（`zh***@company.com`）与姓名（`张*` / `诸**`）智能掩码 |
| AC-02 调阅原因强校验门禁 | 通过 | `validateRevealReason(reason, minLength=5)`：针对调阅理由实施强约束，空串、纯空白字符（空格/制表符/换行）及不足 5 字符理由（如“看看”、“测试一下”）一律被强行拦截，必须提供具体业务调阅理由 |
| AC-03 8角色调阅权限矩阵隔离 | 通过 | `MaskedField.tsx` 深度集成 `useCan('id_card:view')`：仅限 `company_admin` 与 `data_admin` 渲染“查看完整值”按钮；普通编写人（`bid_writer`）、项目负责人（`project_lead`）、只读成员（`viewer`）等无权角色默认零 DOM 残留（不渲染任何查看按钮节点），或在 `unauthorizedMode="disabled"` 呈现禁用并 Tooltip 解释 |
| AC-04 零 storage 与 URL 明文残留硬安全断言 | 通过 | `assertNoSensitiveLeak` 运行时与静态 AST 验证：高敏明文调阅期间及关闭后，绝不写入 `localStorage`、`sessionStorage` 与浏览器 URL，杜绝通过前端缓存或页面跳转造成的脱敏旁路穿透泄露 |
| AC-05 合规安全审计告警横幅 | 通过 | `RevealFieldModal.tsx` 弹窗顶部呈现高警示合规审计横幅（`data-testid="reveal-security-alert"`），明确提示调阅行为将记入系统审计日志（记录人、时间、理由与网络环境），警示信息安全合规责任 |
| AC-06 明文短暂展示与关闭内存即刻销毁 | 通过 | 弹窗提交通过后等宽展示明文（`data-testid="revealed-plaintext-value"`），支持一键复制；弹窗开启 `destroyOnClose` 并在 `onCancel` / `handleRemask` 中立即清空 `setRevealedValue(null)` 与 `setReason('')`，确保明文在组件卸载或关闭时完全从内存销毁 |
| AC-07 生产构建打包与包体积门禁（<= 295 kB） | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 1.03s，0 错误 0 告警）；首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（Gzip 后 **93.90 kB**），完全满足 **<= 295 kB** 预算红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 掩码脱敏专属单测套件 | `node --test tests/frontend/masked-field.test.mjs frontend/web/tests/masked-field.test.mjs` | **10 passed, 0 failed** (表格驱动 7 项 + AST/契约断言 3 项) | 0.47s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **243 passed, 0 failed** (包含 10 项掩码字段专属单测) | 2.74s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 1.03s) | 1.03s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-fu3kmuVM.js` **294.86 kB**（gzip: 93.90 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **“原因必填且大于 5 字符”对防止特权滥用的价值**：拥有 `company_admin` 或 `data_admin` 的特权用户如果不加约束随意点击查看，极易导致隐私数据滥用。通过强制前端输入不少于 5 字符的具体业务理由，并在提交时连同审计日志记录，构建了强有力的法律责任与操作可追溯性防线。
2. **“关闭即刻销毁明文内存”的安全防御深度**：明文数据只在 `revealedValue` 局部 state 中暂存，只要用户点击“重新遮蔽”或“取消/关闭”，该 state 立即置为 `null`，配合 Modal 的 `destroyOnClose`，防止页面在后台挂起时通过内存 dump 扫描明文。
3. **主包体积已逼近预算红线**：当前主包体积稳定在 294.86 kB，余量仅 0.14 kB。由于 APP-M2-T017 充分利用了既有 Ant Design 弹窗与图标，未引入新第三方依赖，未增加首屏负担。后续功能必须继续维持严格的零包膨胀策略。

## 签署状态

APP-M2-T017 保持 **in-review**，**严禁标 done**。
