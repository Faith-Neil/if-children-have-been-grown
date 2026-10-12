为什么有这个文件：留下 ProLayout、浏览器地址和未保存离开这一轮的命令结果。

它解决什么问题：避免把构建体积或函数测试写成项目经理已经签收，或写成产品已经上线。

# 2026-10-12 布局、地址与离开保护复核

日期 2026-10-12。关联 ISSUE-009、ISSUE-014、APP-M2-T001。状态是 in-review。Node v24.21.0，pnpm 11.25.0。后台测试在本机 Python 3.12.3；GitHub Actions 使用 Python 3.13.5 和 Node 24.9.0。

## 打包体积

引入 `@ant-design/pro-layout@7.22.7` 之前，在 `frontend/web` 执行 `pnpm install --frozen-lockfile && pnpm build`：

```text
dist/assets/index-BqghTeOl.js   1,334.42 kB │ gzip: 409.62 kB
dist/assets/index-CniIfmqA.css     20.77 kB │ gzip:   5.00 kB
```

引入之后，同一目录执行 `pnpm build`（脚本是 `tsc -b && vite build`）：

```text
dist/index.html                     0.54 kB │ gzip:   0.46 kB
dist/assets/index-D3NkcTW6.css     21.02 kB │ gzip:   5.04 kB
dist/assets/index-BmV8EgUZ.js   1,564.53 kB │ gzip: 486.19 kB
✓ built in 751ms
```

Vite 仍提示单个脚本超过 500 kB。没有为这项提示再拆包。

## 前端函数测试

仓库根、Node v24.21.0：

```text
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 77
ℹ pass 77
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
```

新增 `frontend/web/tests/app-navigation.test.mjs` 5 项：路径解析、登录回原地址、push/replace/`none`、未保存才拦截刷新、取消后退时地址回到原页。原有 72 项仍通过。Node 22.14 不能直接 import `.ts`；本轮使用 24.21.0。

`frontend/web` 的 `pnpm exec tsc -b --pretty false` 无输出且退出码 0。

## 后台测试

```text
python3 -m pytest tests/backend -q
293 passed, 1 warning in 92.93s
```

警告是 Starlette 对 `httpx` TestClient 的弃用提示，不是失败。293 含原先后台、OpenAI 兼容适配器契约，以及本轮新增的产品路径测试：未知 `/api/v1` 与 `/api/demo` 仍是 JSON 404，`/workbench` 在已构建时返回 HTML。OpenAPI 不包含 `/{full_path:path}`。本机是 Python 3.12.3，不是 CI 的 3.13.5。

## 未覆盖

没有在 1280、1440、1680 宽度下做浏览器截图，也没有用真实点击走一遍离开确认框。离开规则由函数测试覆盖确认与取消，不代替页面操作。通用表单离开、侧栏记忆、OIDC、八角色、请求层重试和元数据表单都没有做。本地通过不能写成已合入或已发布。
