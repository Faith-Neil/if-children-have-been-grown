为什么有这个文件：解释Playwright端到端检查如何运行。

它解决什么问题：说明启动顺序、用例思路与已知缺陷标记方式。

# REV-M0-T06：代码解释

- 对应：REV-M0-T06 / [ISSUE-019](../../issues/ISSUE-019.md) / [交付](../delivery/REV-M0-T06.md)；路径`frontend/web/e2e/`。

## 改了什么以及为什么

函数测试无法证明浏览器返回、刷新和弹窗的真实行为，新增Chromium端到端检查。

## 入口和调用顺序

`pnpm e2e` → `pnpm run build`生成`dist` → `playwright test --config e2e/playwright.config.ts` → `webServer`在仓库根启动`uvicorn icg_demo.main:app`（后台同时提供`dist`页面）并等待`/api/demo/accounts` → 单worker顺序执行用例 → 结束后关闭后台。

## 数据与状态

只用种子合成账号alpha-manager与`alpha-project`；后台内存状态在用例间共享，编辑权被前一用例会话持有时按产品流程“填写理由接管”，不绕过后台。截图与失败视频写到环境变量指定目录。

## 关键判断与异常

离开弹窗用未处于关闭动画的`.ant-modal-confirm`定位；取消后等待弹窗完全消失；页签按名称结尾匹配（Ant Design焦点前缀）。刷新用`beforeunload`对话框dismiss/accept。已知缺陷用`test.fail()`保留可复现步骤。

## 验证与限制

见[记录](../testing/2026-10-12-e2e-t001-signoff.md)。只覆盖Chromium；未覆盖导出过期/版本冲突页面提示和多账号并发。
