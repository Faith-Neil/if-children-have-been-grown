为什么有这个文件：记录 APP-M2-T017 MaskedField 与“查看完整值”弹窗（原因必填）的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现表格驱动高敏脱敏规则（身份证 3+4/6+4、手机号 3+4、银行账号后 4 位）、调阅原因强校验、8系统角色调阅权限矩阵隔离、零 storage/URL 明文残留安全断言、首屏 Bundle 体积控制（<= 295 kB）与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T017：MaskedField 与“查看完整值”弹窗（原因必填）交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T017 |
| 代码解释 | [docs/code/APP-M2-T017.md](../code/APP-M2-T017.md) |
| 验收 | 10 项专属自动化单测通过；全量 243 项前端单测通过；生产构建首屏产物 294.86 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T017 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T017](../tasks/APP-M2.md#app-m2-t017)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **高敏脱敏与原因强校验层 (`frontend/web/src/admin/sensitive-mask.ts`)**：
   - 实现了纯函数 `maskSensitiveValue(value, type, options)`，支持基于表格驱动配置的脱敏规则；
   - 身份证号支持标准 6+4（`110101********2345`）与严格 3+4（`110***********2345`，契合 PRD v1.8 §5.4.5 示例）；
   - 手机号支持 3+4（`138****5678`），银行账号仅保留后 4 位（`***************0123`），邮箱保留前 2 位及域名（`zh***@company.com`），姓名智能脱敏；
   - 实现了调阅原因强校验 `validateRevealReason(reason, minLength)`：空字符串、纯空白字符（空格/制表符/换行）、不足 5 字符一律拦截，保障业务调阅留痕真实有效；
   - 实现了零泄密安全断言引擎 `assertNoSensitiveLeak(plaintext, targets)`，自动核验 `localStorage`、`sessionStorage` 与 URL，确保高敏明文零残留。
2. **调阅完整值合规弹窗 (`frontend/web/src/admin/RevealFieldModal.tsx`)**：
   - `<RevealFieldModal>`：基于 Ant Design Modal 封装；
   - 顶部提供醒目的合规安全审计告警横幅（`data-testid="reveal-security-alert"`），警示每一次查看均记录操作人、时间、原因及网络环境；
   - 必填原因受控文本域（`data-testid="reveal-reason-input"`），实时检验并拦截空理由；
   - 提交通过后短暂展示等宽高对比度明文（`data-testid="revealed-plaintext-value"`），提供一键复制明文与重新遮蔽；
   - 弹窗关闭即刻调用 `destroyOnClose` 并重置内部状态，彻底销毁明文内存，严禁写入任何 storage 或 URL。
3. **掩码展示与权限集成组件 (`frontend/web/src/admin/MaskedField.tsx`)**：
   - `<MaskedField>`：通用高敏字段呈现组件；
   - 默认直接展示脱敏掩码文本（`data-testid="masked-value-text"`）；
   - 深度集成 `useCan('id_card:view')` 权限判定：严格遵循 PRD v1.8 §2.3 规范，**仅限 `company_admin` 与 `data_admin`** 渲染“查看完整值”触发按钮；
   - 无权限角色（编写人、项目负责人、只读成员等）默认在 DOM 中完全不渲染查看按钮（零 DOM 残留），或在 `unauthorizedMode="disabled"` 时渲染置灰并 Tooltip 悬浮解释无权限原因。

### 2. 变更文件清单
- `frontend/web/src/admin/sensitive-mask.ts` (新增): 高敏脱敏算法、原因强校验、表格规则与防泄露断言
- `frontend/web/src/admin/RevealFieldModal.tsx` (新增): 调阅高敏弹窗组件、合规审计告警横幅与短暂展示
- `frontend/web/src/admin/MaskedField.tsx` (新增): 掩码展示与权限判定集成组件
- `tests/frontend/masked-field.test.mjs` (新增): 7 项表格驱动脱敏、原因校验、8角色权限与 storage/URL 零泄露单测
- `frontend/web/tests/masked-field.test.mjs` (新增): 3 项 AST 静态契约与零 storage 写入断言测试
- `docs/code/APP-M2-T017.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T017.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单元测试（100% 通过）
运行命令：
```powershell
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
测试输出：
```text
ℹ tests 243
ℹ suites 0
ℹ pass 243
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2521.8492
```
全量 243 项测试全部绿色通过（包含新增的 10 项脱敏掩码、原因强校验与安全断言专属测试）。

### 2. 构建产物体积审计（<= 295 kB 门禁达标）
运行命令：
```powershell
pnpm --dir frontend/web build
```
构建输出：
```text
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-DxiuVLoO.css                30.10 kB │ gzip:   6.82 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/popover-Dy7Y8T45.js                5.30 kB │ gzip:   2.18 kB
dist/assets/collapse-BH52iPNU.js              10.50 kB │ gzip:   3.85 kB
dist/assets/SupportPages-DqWKE_n6.js          11.32 kB │ gzip:   4.52 kB
dist/assets/ProjectSettingsPage--1v7SuLB.js   22.57 kB │ gzip:   8.92 kB
dist/assets/result-BJ4tHomv.js                33.86 kB │ gzip:  10.39 kB
dist/assets/SlaPages-Aj8HgBbd.js              36.52 kB │ gzip:  12.05 kB
dist/assets/zh_CN-vK_Yfa8y.js                 39.18 kB │ gzip:  11.28 kB
dist/assets/EditorPage-Dqyc6Hf0.js            98.74 kB │ gzip:  32.03 kB
dist/assets/ProjectPages-fK2lnAZv.js         116.10 kB │ gzip:  34.97 kB
dist/assets/AppShell-5zcXhWSv.js             223.69 kB │ gzip:  73.43 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip:  90.01 kB
dist/assets/index-fu3kmuVM.js                294.86 kB │ gzip:  93.90 kB
dist/assets/jsx-runtime-DNp14iXa.js          437.98 kB │ gzip: 144.54 kB
✓ built in 648ms
```
首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（gzip 93.90 kB），严格保持在 **295.00 kB 红线以内**。

### 3. 工程治理与零泄密安全审计
- 运行 `node scripts/check-project-governance.cjs` 确保文档索引与链接一致性 100% 达标；
- 自动化单测与 AST 契约双重断言：
  1. `RevealFieldModal` 与 `MaskedField` 绝无调用 `localStorage.setItem`、`sessionStorage.setItem` 或向 URL 追加参数；
  2. `assertNoSensitiveLeak` 运行时核验通过；
  3. 未输入满 5 个非空白字符时强行拦截調阅并呈现错误警告。

---

## 结论与待决事项
- `APP-M2-T017` 前端高敏脱敏、调阅弹窗、原因强校验与安全防护全部完成，提交代码审查；
- 状态更新为 **in-review**，关联 ISSUE-007 保持开启，等待 QA 与主 Agent 联合评审。
