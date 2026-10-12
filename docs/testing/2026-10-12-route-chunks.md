为什么有这个文件：留下路由分包前后每一个构建产物的体积。

它解决什么问题：避免只说“变小了”，却对不上入口块和延迟块。

# 路由级分包复核

日期 2026-10-12。关联 ISSUE-020、APP-M2-T001。状态是 in-review。Node v24.21.0，pnpm 11.25.0。命令在 `frontend/web` 为 `pnpm build`（`tsc -b && vite build`）。没有新增依赖。没有改 `backend/` 或 `tests/backend/`。

引入 ProLayout 前的历史主包是 `index-BqghTeOl.js` 1,334.42 kB / gzip 409.62 kB。本轮对比的“之前”是分包前同一工作区重新构建的结果，不是那份历史文件名。

## 分包前

只有一个脚本块。它同时包含登录页、ProLayout 和全部页面。

| 产物 | 原始 | gzip | 何时下载 |
|---|---:|---:|---|
| `dist/index.html` | 0.54 kB | 0.46 kB | 首屏 |
| `dist/assets/index-D3NkcTW6.css` | 21.02 kB | 5.04 kB | 首屏 |
| `dist/assets/index-BmV8EgUZ.js` | 1,564.53 kB | 486.19 kB | 首屏主块 |

## 分包后

入口脚本是 `index-BXy7CunM.js`，315.94 kB / gzip 101.00 kB，低于 1,334.42 kB。`index.html` 还预加载了运行时、共享块和中文文案。这些加上入口脚本的原始体积合计 1,080.17 kB，gzip 合计 345.08 kB，同样低于 1,334.42 kB。外壳和各页面不在这份 HTML 里，打开对应路由时才请求。

| 产物 | 原始 | gzip | 何时下载 |
|---|---:|---:|---|
| `dist/index.html` | 0.86 kB | 0.55 kB | 首屏 |
| `dist/assets/index-D3NkcTW6.css` | 21.02 kB | 5.04 kB | 首屏 |
| `dist/assets/rolldown-runtime-8BhlS34s.js` | 0.80 kB | 0.47 kB | 首屏预加载 |
| `dist/assets/jsx-runtime-CoO3AFfp.js` | 431.47 kB | 142.66 kB | 首屏预加载 |
| `dist/assets/project-team-DImcaK6u.js` | 301.24 kB | 91.87 kB | 首屏预加载 |
| `dist/assets/zh_CN-CW6Acanq.js` | 30.72 kB | 9.08 kB | 首屏预加载 |
| `dist/assets/index-BXy7CunM.js` | 315.94 kB | 101.00 kB | 首屏主块 |
| `dist/assets/sla-form-a6AqMBie.js` | 2.78 kB | 1.42 kB | 打开资料/模板相关页 |
| `dist/assets/collapse-D71feMj7.js` | 10.50 kB | 3.84 kB | 随项目页或设置页 |
| `dist/assets/SupportPages-B9irBFRs.js` | 11.32 kB | 4.53 kB | 资料库、任务或占位页 |
| `dist/assets/ProjectSettingsPage-BlUG2r70.js` | 22.57 kB | 8.92 kB | 项目设置 |
| `dist/assets/SlaPages-BpT0LCNi.js` | 36.52 kB | 12.06 kB | 资料模板或项目页中的承诺表 |
| `dist/assets/EditorPage-Ct935obt.js` | 82.36 kB | 26.66 kB | 编辑台 |
| `dist/assets/ProjectPages-DfHdebbd.js` | 110.69 kB | 33.28 kB | 概览、招标、解析、矩阵、事实、检查、导出 |
| `dist/assets/AppShell-CyAq7zB_.js` | 221.47 kB | 72.97 kB | 登录后的外壳 |

CSS 文件名和体积与分包前相同。ProLayout 的脚本在 `AppShell-CyAq7zB_.js`，不在首屏主块。

## 测试

在仓库根目录：

`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`

结果：

```
ℹ tests 78
ℹ pass 78
ℹ fail 0
```

其中 `frontend/web/tests/route-chunks.test.mjs` 确认 `App.tsx` 不再静态引入外壳和页面，`route-loaders.ts` 使用 `import()`。离开保护和历史路由的原有 5 项测试仍在这 78 项里。

没有在浏览器里逐个打开延迟块，也没有做 1280 / 1440 / 1680 截图。后台测试本轮没有改代码，所以没有在本地重跑 pytest；推送后的离线检查仍会跑后台作业。
