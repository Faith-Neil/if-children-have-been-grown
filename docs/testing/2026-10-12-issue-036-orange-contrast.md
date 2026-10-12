为什么有这个文件：记下橙色标签对比的核对方式和还没点开的页面。

它解决什么问题：避免把色值计算写成已经逐页看过每一个警告标签。

# 2026-10-12 ISSUE-036 橙色标签对比

日期 2026-10-12。关联 [ISSUE-036](../../issues/ISSUE-036.md)。数据只用合成登录。不新增依赖。

## 色值

Ant Design 默认色板：橙色文字 `#d46b08`、浅底 `#fff7e6`；金色文字 `#d48806`、浅底 `#fffbe6`；warning 文字 `#faad14`、浅底 `#fffbe6`。本轮文字改为项目已有的 `#9a5608`。

相对亮度按 sRGB 计算，对比为 (较亮 + 0.05) / (较暗 + 0.05)。

| 前景 | 背景 | 对比 |
|---|---|---|
| `#d46b08` | `#fff7e6` | 3.34:1 |
| `#d48806` | `#fffbe6` | 2.76:1 |
| `#faad14` | `#fffbe6` | 1.83:1 |
| `#9a5608` | `#fff7e6` | 5.31:1 |
| `#9a5608` | `#fffbe6` | 5.45:1 |
| `#9a5608` | `#ffffff` | 5.66:1 |

门槛是 4.5:1。改后的三行过线。改前的三行不过。

## 浏览器

`frontend/web/e2e/app-shell.spec.ts` 的“overview steps, pending mark and editor meta meet 4.5:1”在概览页读取可见的 `.ant-tag-orange`、`.ant-tag-gold`、`.ant-tag-warning`，最低对比须 ≥ 4.5。顶栏“示例数据 · 非真实业务”是橙色标签。

| 命令 | 结果 |
|---|---|
| `pnpm --dir frontend/web build` | `tsc -b` 与 vite 8.3.4 通过。主块 `index-B6zjJ_g-.js` 317.76 kB。样式 `index-M8sv5qf7.css` 22.31 kB |
| `E2E_PYTHON=python3 pnpm --dir frontend/web exec playwright test --config e2e/playwright.config.ts e2e/app-shell.spec.ts -g "meet 4.5:1"` | 1 passed。先构建再测，因为端到端读取 `frontend/web/dist`。未重跑全部 14 项 |

构建产物不入库。

## 局限

没有逐页打开 SLA 未量化（金色）和支撑页“尚未实现”。选择器覆盖这三类标签。未改后台，未合入，未发布。本 Issue 保持 in-review。
