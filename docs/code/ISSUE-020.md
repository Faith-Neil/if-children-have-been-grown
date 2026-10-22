为什么有这个文件：说明路由分包实际怎么加载，以及离开保护为什么还在原处。

它解决什么问题：避免以后有人把动态 import 改回静态 import，又把外壳打回首屏。

# ISSUE-020：代码解释

- 对应任务、Issue、交付文档：APP-M2-T001、[ISSUE-020](../../issues/ISSUE-020.md)、[交付](../delivery/ISSUE-020.md)
- 日期、实际代码路径、提交 / PR：2026-10-12；`frontend/web/src/app/route-loaders.ts`、`lazy-routes.tsx`、`App.tsx`；PR #3 未合入

## 改了什么以及为什么

分包前 `App.tsx` 在文件顶部直接引入 `AppShell`、`ProjectPages`、`EditorPage`、`ProjectSettingsPage` 和 `SupportPages`。Vite 因此打出一个 1,564.53 kB 的入口。登录页还没显示，浏览器就要下载 ProLayout 和全部项目页。

现在这些模块只出现在 `route-loaders.ts` 的 `import()` 里。`lazy-routes.tsx` 用 `React.lazy` 包成组件。`App.tsx` 只静态引入这个懒加载表。登录成功后才渲染外壳；打开某个页签才渲染对应页面。同一模块的多次 `lazy` 共用一个进行中的 Promise，避免重复请求。

## 入口和调用顺序

`main.tsx` 仍同步挂上 `App`。没有令牌时 `App` 返回登录页，不渲染 `LazyAppShell`。登录后的 `return` 先经过外层 `Suspense`，再渲染外壳。项目页签和资料库/任务/占位页各有内层 `Suspense`，外壳和页头留在页面上，内容区显示已有的 `Spin`。

`followPath`、`commitAddress`、`requestPath`、`askLeave` 和 `beforeunload` 仍在 `App.tsx`，发生在页面组件挂载之前。编辑台的 `onDirtyChange={reportDirty}` 仍传给延迟加载的 `EditorPage`。

## 数据与状态

地址、脏标记、会话和项目工作区仍在 `App` 的 state / ref 里。延迟加载不把它们放进页面块。后台接口没有变化。

## 关键判断与异常

未保存时，确认框先决定是否调用 `followPath`。取消不会卸载编辑台。分包提交时地址由 `holdAddressForPrompt` 推回当前页；QA 退回后的前进/后退修复改为按历史序号 `history.go`，不再 `pushState`，见 [布局修复说明](APP-M2-T001.md)。页面块还在下载时，内层 `Suspense` 只替换内容区。401 仍立即退出，不经过离开确认。

## 验证与限制

构建体积和 78 项前端测试见 [验证](../testing/2026-10-12-route-chunks.md)。没有在浏览器里确认每个块的网络请求。工作台列表、新建项目和任务抽屉仍在 `App.tsx`，所以它们的 antd 组件留在首屏共享块里。这是登录后的第一屏，不是登录页本身。
