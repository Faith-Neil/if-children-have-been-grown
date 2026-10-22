为什么有这个文件：说明共同页面底座第一阶段的真实前后端调用关系。

它解决什么问题：让协作者分清可信会话已经接入的行为与尚未完成的布局、地址和完整权限。

# APP-M2-T001代码解释（阶段一）

日期2026-10-11；ISSUE-009 / application-foundation-1；本卡仍in-progress。对应[阶段交付](../delivery/APP-M2-T001.md)、[会话契约](../architecture/application-session-contract.md)。完整范围按[任务卡](../tasks/APP-M2.md#app-m2-t001)，未缩减。

## 为什么修改

以前页面用登录时的旧角色判断菜单，打开项目直接请求整个工作区。现在先从同一后台读取当前会话，检查它给出的入口和操作，再请求业务数据。会话就是后台此刻确认的“谁在使用、属于哪家公司、可以做什么”；不是由页面自己传角色或公司来授权。

## 后台入口

`backend/bid-core/icg_demo/main.py`注册`GET /api/v1/session`（getSession）。只接受Bearer及可选唯一project_id；额外角色/公司/账号查询、重复项目ID、请求正文均422。`session_navigation.py`从当前仓储快照重新找会话、账号、角色和公司，并与项目权限使用同一快照，不采用登录响应或旧Principal中的身份内容。`schemas.py`明确响应模型，OpenAPI由实际代码导出，现49路径57操作。

三种演示角色显式映射为项目负责人、投标编写人和只读成员；公司经理没有公司管理员入口。原八角色导航矩阵是后续适配的共同定义，当前没有模拟全部八角色的账号。选项目时调用原公司/成员权限和章节权限计算，返回最小权限摘要，不返回正文或个人草稿。业务接口仍独立再次授权；导航允许不等于保存一定成功。

## 页面入口与读取顺序

`frontend/web/src/shared/types.ts`定义契约类型；`session-navigation.ts`检查身份模式、公司一致性、入口路径白名单及服务端动作。`App.tsx`实际调用这些函数：登录→getSession→允许的公司集合；打开项目→getSession(project_id)→获准的项目页→workspace。项目正文不会在目标页权限确认前请求。

资料和模板各保留自己的GET内容及版本，避免把并行请求的另一份版本配给旧资料。全局读还需要对应导航与allowedActions同时允许。401退出并清理身份、公司数据；无权入口明确显示403。项目撤权时保留已经填写的文字，停止写入；所有保存仍受后台权限、版本及编辑权约束。

独立复核发现的三个采纳路径遗漏均已修复：`readTrustedSession`核对页面/会话请求序号；`workspaceWithSessionPermissions`立即收紧缓存项目/章节权限，保留正文/草稿，条款权限待新的workspace读回再恢复；`readSessionCollection`在前后核对同一授权对象及T16账号/公司序号，拒绝后迟到结果不能回填；`readAuthorizedProject`在workspace前后再检查授权是否仍当前。实际App使用这些函数，导航也推进请求序号。快捷入口403保留原组件和文字，提示暂停写入，不误说整个项目不可见。证据见[本次验证](../testing/2026-10-11-application-session.md)。

## 验证与限制

新增后台专项33项，全后台262项通过；前端72项（会话14项）、独立复核、真实会话HTTP16项及GUI通过，最终类型/构建通过。两册导出继续由同一后台读取正式提交正文，实际文件内容/包已核对；模型仍为替身、存储仍为内存，重启清空。网络/角色变更竞态只做函数与调用路径验证，正式Word版式仍未验收。

下面一节是 2026-10-12 提交复核的布局和地址。阶段一结束时这些还没有做。原八角色业务授权和正式身份仍未完成。当前框架不等于完整资料列表/详情、审核、附件或正式投标递交。

## 布局、地址和离开保护

入口仍是 `frontend/web/src/app/App.tsx`。登录成功后 `routeAfterLogin` 看当前地址：`/` 换成会话首页，已知全局路径和项目页签保持原样，未知地址留在未知页。`followPath` 再交给原来的 `requireSessionRoute` 或 `readAuthorizedProject`。未知路径走 `showMissing`，只改地址和 404，不请求工作区。

`commitAddress` 在路径已经一致或模式为 `none` 时不改历史。站内点击用 `push`。登录后的第一次定位用 `replace`。每次 `push` / `replace` 写入 `{ app: true, idx }`。浏览器 `popstate` 已经改过地址。页面干净时直接 `followPath(..., 'none')` 并记下新序号。页面有未保存文字时，用目标序号减当前序号得到步长，先 `history.go(-step)` 回到原页再询问；确认后 `history.go(step)` 并 `followPath(..., 'none')`。取消不新增历史，前进记录还在。恢复用的那次 `popstate` 由 `ignorePop` 吃掉，避免再弹一次。

未保存信号只有编辑台的 `editorDirty`。`armedLeave` 在离开过程中忽略编辑台再次报脏，避免还没卸下的编辑器把脏标记写回来。真正离开编辑台时 `arrived(false)` 才清掉脏标记。401 仍立即 `logout`，不弹确认。退出按钮走 `requestDiscard`。

`AppShell.tsx` 调用 `ProLayout`：`layout="mix"`、`navTheme="light"`、`siderWidth={216}`、默认收起、`breakpoint={false}`、`disableMobile`。`headerTitleRender={false}` 避免顶栏再放一次标志；`menuHeaderRender` 把标志留在深色侧栏。公司、用户和退出走 `actionsRender`，因此出现在顶栏而不是 64px 侧栏。样式把 mix 侧栏拉回视口顶部并保持 `#0F1C3F`，顶栏保持白色，内容区保持 `#F5F7FA`。收起时外壳带 `icg-shell-collapsed`，顶栏 `padding-inline-start` 为 48px，加上顶栏自己的 16px 外边距，按钮从 64px 侧栏右侧开始。展开后内边距改为 200px，按钮从 216px 侧栏右侧开始。这样 logo 不再挡住「收起或展开导航」。次要文字 `--muted` 与主题 `colorTextSecondary` 为 `#4e5969`；待办「○」和 `.orange` 正文为 `#9a5608`。高亮边框仍用 `#e08a1e`。菜单用 `<a href>`，普通左键阻止默认并走站内导航，带修饰键的点击留给浏览器。`backend/bid-core/icg_demo/main.py` 在全部接口之后注册 `/{full_path:path}`，`include_in_schema=False`，因此 OpenAPI 仍是 49 路径 57 操作。`api/`、`static/`、`assets/` 继续 404。

演示登录令牌只放在页面内存。刷新后会话丢失，需要重新登录；地址还在，登录成功后 `routeAfterLogin` 回到该地址。确认刷新会丢掉尚未保存的编辑台文字。

直接依赖只有 `@ant-design/pro-layout@7.22.7`。`app-route.ts` 用 `./session-navigation.ts` 带扩展名，这样 Node 24 的测试可以直接 import。三断点没有实机截图。通用表单离开、侧栏记忆、OIDC 和请求层重试不在这几个文件里。

2026-10-12 的 ISSUE-020 把外壳和页面改成动态 import，离开保护仍留在本节描述的 `App.tsx`。加载顺序见 [路由分包说明](ISSUE-020.md)。
