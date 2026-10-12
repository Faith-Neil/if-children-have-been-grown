为什么有这个文件：记录 QA 退回后，布局和浏览器历史的修复证据。

它解决什么问题：把签署不通过的缺陷和本轮 11 项端到端结果分开，避免把失败截图改写成通过。

# APP-M2-T001 布局与历史修复

日期 2026-10-12。ISSUE-009 / APP-M2-T001。状态 in-review。QA 签署不通过的原文仍是 [E2E 签署](2026-10-12-e2e-t001-signoff.md)，本文件不改那次结论。

环境：Node v24.21.0、pnpm 11.25.0、Playwright 1.64.0、Python 3.12.3。先 `pnpm --dir frontend/web exec playwright install chromium`，再 `E2E_PYTHON=python3 pnpm --dir frontend/web e2e`。脚本自己构建前端，并自启内存 uvicorn。没有改 `backend/` 或 `tests/backend/`。

## 结果

`pnpm --dir frontend/web e2e`：**11 passed**。先前标成 `test.fail()` 的 D1–D4 已去掉标记，按正常断言通过。

| 用例 | 结果 |
|---|---|
| 登录后 workbench / overview / matrix / editor / export 在 1280 / 1440 / 1680 无横向溢出 | 通过 |
| 站内切页：取消保留地址、页面和文字；确认后离开 | 通过 |
| 浏览器后退：取消保留；确认回到上一页 | 通过 |
| 浏览器前进：取消保留；确认进入下一页 | 通过 |
| 取消前进后再次前进仍弹出离开确认 | 通过（D2） |
| 取消前进后再后退并确认，落到 overview | 通过（D1） |
| 刷新：取消保留文字；确认后重新登录并回到原地址，未保存文字丢失 | 通过 |
| 全局页与项目页多次后退、前进 | 通过 |
| 工作台卡片背景不是 `rgb(20, 20, 20)` | 通过（D3） |
| 退出按钮纵坐标小于 80 | 通过（D4） |

同一环境下 `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` 为 **78 pass、0 fail**。`pnpm --dir frontend/web exec tsc -b` 随 e2e 的构建通过。

## 截图

新文件前缀 `t001-fixed-`，不覆盖 QA 的 `e2e-*.png`。15 张都在 `docs/testing/assets/`。对照原 ICG：左侧深色侧栏从视口顶部开始，白顶栏在内容列，内容底为 `#F5F7FA`。

代表图：[工作台 1680](assets/t001-fixed-workbench-1680.png)、[编辑台 1280](assets/t001-fixed-editor-1280.png)、[概览 1440](assets/t001-fixed-overview-1440.png)。

## 会话说明（D6）

演示令牌只在页面内存。刷新后必须重新登录。地址保持不变，登录成功后回到该地址。确认刷新会丢失尚未保存的编辑台文字。已保存草稿在重新登录后仍从后台读取。

## 未做

D5（`/API/...` 返回页面壳）留给后台。没有把本卡标 done，没有合入 PR #3，没有发布。导出过期和版本冲突页面仍未进入这 11 项。

## E2E-D7：展开导航可点（仍 in-review）

QA 重签见 [T001 重签](2026-10-12-qa-t001-t002-t020-recheck.md)。侧栏默认仍收起。mix 侧栏从视口顶部盖住顶栏左缘，收起时 64px 的 logo 挡住「收起或展开导航」。顶栏按侧栏宽度留出起始空白：收起 64px（顶栏原有 16px 外边距再加 48px），展开 216px。按钮落在 logo 右侧，点击不再被 `ant-pro-sider-logo` 拦截。

新用例在 1280、1440、1680，以及浅色和深色 `colorScheme` 下：先确认侧栏收起且按钮中心点到的是按钮本身，再点击，侧栏宽于 200px，菜单文字「工作台」「企业资料库」可见。默认收起不改。

`E2E_PYTHON=python3 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts`：**12 passed**。Node v24.21.0。没有改后台。本卡仍 in-review，不标 done。
