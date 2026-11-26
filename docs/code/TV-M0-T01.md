为什么有这个文件：说明 TV-M0-T01 的代码改在哪里。

它解决什么问题：下次改导航或创建项目时，能看出技术分册入口收口只动了前端两处。

# TV-M0-T01 代码说明

侧栏列表在 `frontend/web/src/app/App.tsx` 的 `navigation`。去掉 `library` 和 `writing` 后，登录后的菜单不再给出这两个入口。`GlobalPagesContent` 里的页面分支还在，所以旧地址仍能打开原页面。

创建项目时，`App.tsx` 的 `POST /api/v1/projects` 不再读取表单里的编写范围，请求体里的 `volume_mode` 固定为 `technical_only`。弹窗 `CreateProjectModal.tsx` 不再渲染编写范围单选。已有项目是否两册，仍由 `project-volumes.ts` 读取项目上的 `volume_mode`，默认仍是 `both`。

后台创建接口继续接受 `both`。本卡没有改接口，避免旧测试和已有两册项目被新建规则挡住。
