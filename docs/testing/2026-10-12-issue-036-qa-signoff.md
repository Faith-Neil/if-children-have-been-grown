为什么有这个文件：记录QA对ISSUE-036橙色标签对比度（7f5f74d）的独立签署。

它解决什么问题：确认浅底上橙色/金色/warning标签文字达到4.5:1，并写明不标done。

# ISSUE-036 橙色标签对比 QA签署（REV-M0-T25）

- 被验提交：`7f5f74d`（docs: mark T114 and REV-M0-T22 done; raise orange tag contrast）；复核基线：`ab3fbb7`（含该提交）；关联 ISSUE-036；数据：仅合成数据。
- 结论：**通过**。**ISSUE-036 与本卡均不标 done / closed**，等项目经理设置。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| AC-01 橙/金/warning 文字在浅底 ≥4.5:1 | 通过 | `#9a5608` 在 `#fff7e6` 5.31:1、`#fffbe6` 5.45:1、白底 5.66:1；改前分别为 3.34 / 2.76 / 1.83 |
| AC-02 不新增依赖，只改样式与已有对比检查 | 通过 | `frontend/web/src/styles.css` 增加 `.ant-tag.ant-tag-orange,.ant-tag.ant-tag-gold,.ant-tag.ant-tag-warning{color:#9a5608 !important}`；`e2e/app-shell.spec.ts` 纳入可见橙/金/warning；未改 `package.json` |
| 概览页可见橙色标签实测 | 通过 | Playwright `-g "meet 4.5:1"` **1 passed**（Node 24.9.0，E2E_PYTHON=qa-venv） |
| 深色主题标签 | 未要求 | AC 只覆盖浅底；E2E-D3（realDark 内容区）不在本 Issue |

## 套件与 CI

- 前端构建：`tsc -b && vite build` 通过；主块 `index-B6zjJ_g-.js` 317.76 kB；样式 `index-M8sv5qf7.css` 22.31 kB。
- 前端单测：`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`：**98 passed**。
- Playwright 焦点：`e2e/app-shell.spec.ts`「meet 4.5:1」**1 passed**（先构建再测）。
- CI [run 38229790793](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38229790793)（head `7f5f74d`）：五个 job 全绿；HEAD `ab3fbb7` 上 [run 38230197085](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38230197085) 亦全绿。

## 观察项

- O-1：未逐页打开 SLA 金色与「尚未实现」页；选择器覆盖三类标签。
- O-2：ISSUE-036 / REV-M0-T25 保持 in-review，**不标 done**。
