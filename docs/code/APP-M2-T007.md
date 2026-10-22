为什么有这个文件：说明表单通用能力（吸底保存条 FormActionFooter、离开未保存拦截 useUnsavedPrompt、服务端字段级错误就近映射与滚动定位）的设计架构、实现逻辑与集成规范。

它解决什么问题：
1. 固底保存条（Sticky Footer Bar）：避免长表单用户必须滚动至页面底部才能执行保存，且实时呈现“已修改 N 项”脏数据状态及 ★ 关键字段变更警示；
2. 离开未保存双重拦截（Unsaved Prompt）：
   - 浏览器原生级：在存在脏数据（isDirty）时，监听 beforeunload 事件阻止误刷新或直接关闭标签页；
   - 应用路由级：在用户点击取消、侧栏导航或页面链接试图离开时，通过 Ant Design Modal.confirm 弹出模态拦截对话框，提醒“当前有未保存的修改，离开将丢失已填内容”；
3. 服务端字段级错误就近映射与聚焦（Near-Field Error Mapping & Smooth Scroll）：
   - 兼容解析 FastAPI / Pydantic、统一错误体以及字典映射等不同结构的服务端 400 / 422 错误详情（details 数组或键值对）；
   - 自动映射到对应表单项展示红色错误提示，并通过 smooth scrollIntoView 将首个出错字段平滑滚动至视口中央并自动聚焦（focus）；
4. 严格控制包体积：完全基于已有轻量依赖与原生 DOM API，前端 Bundle 体积严格锁定在 289.99 kB（< 295 kB 门禁，零膨胀）。

# APP-M2-T007：代码解释

- 对应任务：[APP-M2-T007](../tasks/APP-M2.md#app-m2-t007)
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T007 交付](../delivery/APP-M2-T007.md)
- 日期：2026-10-21
- 实际代码路径：
  - `frontend/web/src/form-interactions.ts`（前端纯函数逻辑层：脏数据检测算法、服务端多格式字段错误解析映射、就近平滑滚动聚焦、离开拦截纯逻辑）
  - `frontend/web/src/FormActionFooter.tsx`（前端 React 组件层：固底吸附操作条、修改计数标签、★ 变动警示、保存/重置/取消按钮与扩展插槽）
  - `frontend/web/src/useUnsavedPrompt.ts`（前端 React Hook：beforeunload 事件生命周期管理、路由跳转 Modal 模态拦截二次确认）
  - `frontend/web/src/MetadataForm.tsx`（组件集成层：无缝连接脏数据状态、服务端错误自动监听注入、FormActionFooter 与未保存拦截 Hook）
  - `frontend/web/src/styles.css`（吸底样式 `.icg-form-sticky-footer`、毛玻璃背景、微上边框、错误项脉冲微动动画）
  - `tests/frontend/form-interactions.test.mjs`（前端纯逻辑单测：脏数据比对、FastAPI/Pydantic 错误解析、Node 环境 DOM 安全性、离开规则）
  - `frontend/web/tests/form-interactions.test.mjs`（组件与 Hook AST 结构静态断言）

## 改了什么以及为什么

在大型企业级智能投标系统（如响应矩阵、项目设置、企业主体信息、资质证明等）中，表单字段往往多达数十项，存在三大高频交互痛点：
1. **长表单保存困难与修改感知缺失**：
   - 用户滚动到表单中段或下方修改了数据后，若操作栏固定在表单最底部，用户必须大幅滑动滚动条才能找到保存按钮；
   - 用户无法直观得知自己修改了多少项，特别是若无意间触碰了 ★ 关键字段，容易遗漏合规重新核对的风险。
   - **解决方案**：引入 `FormActionFooter` 固底吸附操作条（`position: sticky; bottom: 0`），辅以毛玻璃效果与阴影，左侧实时呈现已修改项数及 ★ 关键字段警示，右侧提供保存、重置与取消按钮。
2. **误操作导致未保存数据丢失**：
   - 用户在耗时填写表单过程中，若误触浏览器刷新、关闭标签页、点击侧栏菜单或点击“取消”按钮，可能导致已填内容瞬间丢失。
   - **解决方案**：引入双层防护机制 `useUnsavedPrompt`：
     - 外层：监听原生 `beforeunload` 事件；
     - 内层：提供 `confirmNavigation` 方法，点击取消或路由跳转时弹出危险操作确认弹窗（“离开页面将丢失已修改的表单内容”），点击留在本页即可取消离开，点击放弃修改才放行。
3. **服务端报错后“就近定位”缺失**：
   - 后端在 400 / 422 参数校验拦截时，通常返回 JSON 错误详情。传统做法仅在页面顶部弹出一个全局浮层提示“验证未通过”，长表单用户往往不知道究竟是哪个输入框校验不通过，需要逐行上下翻找。
   - **解决方案**：实现 `mapServerFieldErrors` 与 `scrollFieldIntoView`：自动将服务端错误转换为 Ant Design Form 错误项注入表单，并自动计算出 `firstErrorField`，以平滑动画（smooth）将该表单项居中显示并自动聚焦，实现极致的就近定位。

## 入口和调用顺序

### 1. 组件与模块导出
- `frontend/web/src/form-interactions.ts`：
  - `detectDirtyFields`：比对初始值与当前值，输出 `FieldChangeSummary`（`isDirty`、`modifiedCount`、`modifiedKeys`、`starredModifiedCount`、`summaryText`）；
  - `mapServerFieldErrors`：多格式服务端错误体解析器，输出 `fieldErrors`、`firstErrorField`、`generalMessage`；
  - `scrollFieldIntoView`：安全平滑滚动聚焦函数；
  - `shouldBlockNavigation` / `applyBeforeUnloadEvent`：离开拦截纯逻辑；
  - `FORM_LEAVE_COPY`：标准提示文案常量。
- `frontend/web/src/FormActionFooter.tsx`：
  - `FormActionFooter`：吸底操作栏组件（具名与默认导出）。
- `frontend/web/src/useUnsavedPrompt.ts`：
  - `useUnsavedPrompt`：未保存离开拦截 Hook。
- `frontend/web/src/MetadataForm.tsx`：
  - 增强 `MetadataForm`，原生支持 `stickyFooter`、`promptOnUnsaved`、`serverErrors`、`autoScrollToError`、`onReset`、`onCancel`。

### 2. 状态流与时序图
```mermaid
sequenceDiagram
  autonumber
  participant User as 用户交互
  participant Form as MetadataForm.tsx
  participant Logic as form-interactions.ts (纯逻辑层)
  participant Footer as FormActionFooter.tsx (吸底栏)
  participant Hook as useUnsavedPrompt.ts (离开保护)
  participant AntD as Ant Design (Form/Modal)

  User->>Form: 输入修改某个字段
  Form->>Logic: detectDirtyFields(initialValues, currentFormValues, starredKeys)
  Logic-->>Form: { isDirty: true, modifiedCount: 1, starredModifiedCount: 0, summaryText: "已修改 1 项" }
  Form->>Hook: useUnsavedPrompt({ isDirty: true, enabled: promptOnUnsaved })
  Note over Hook: 激活 window.addEventListener('beforeunload')
  Form->>Footer: <FormActionFooter isDirty={true} modifiedCount={1} sticky={true} />
  Footer-->>User: 吸底栏左侧呈现 "已修改 1 项" 标签，重置按钮高亮可用

  alt 用户尝试离开或取消
    User->>Footer: 点击取消按钮 (onCancel)
    Footer->>Form: 触发 handleCancel
    Form->>Hook: confirmNavigation(onCancel)
    Hook->>AntD: Modal.confirm("当前页面有未保存的修改", "离开将丢失已填内容...")
    alt 用户选择留在本页
      User->>AntD: 点击“留在本页继续编辑”
      AntD-->>User: 关闭弹窗，维持表单当前输入
    else 用户选择放弃
      User->>AntD: 点击“放弃修改并离开”
      AntD->>Form: 执行 onCancel 回调放行离开
    end
  end

  alt 用户提交表单，服务端返回 422 校验失败
    User->>Footer: 点击保存提交 (onSubmit)
    Form->>Form: 发起后端保存请求
    Note over Form: 服务端返回 422 错误体 { details: [{ field: "credit_code", message: "统一社会信用代码格式不正确" }] }
    Form->>Form: 接收到 serverErrors
    Form->>Logic: mapServerFieldErrors(serverErrors)
    Logic-->>Form: { fieldErrors: [{ name: "credit_code", errors: [...] }], firstErrorField: "credit_code" }
    Form->>AntD: form.setFields(mapped.fieldErrors)
    AntD-->>User: 表单项 credit_code 呈现红框与红色错误提示文字
    Form->>Logic: scrollFieldIntoView("credit_code", { behavior: 'smooth', block: 'center' })
    Note over Logic: 执行 targetElement.scrollIntoView() 并 focus 输入框
    Logic-->>User: 视口平滑滚动将 credit_code 居中，光标自动进入该输入框
  end
```

## 改动文件清单

1. `frontend/web/src/form-interactions.ts`（新增）：
   - 定义 `FieldChangeSummary`、`ServerFieldError`、`AntFormFieldError`、`MappedServerErrors` 等核心契约类型；
   - 实现了 `detectDirtyFields` 脏数据与修改项统计纯函数，集成 `areValuesEquivalent` 严谨比对；
   - 实现了 `mapServerFieldErrors` 服务端错误解析器，兼容 details 数组（含 `loc` 路径提取）、字典映射、直接字段对象与嵌套 error 结构；
   - 实现了 `scrollFieldIntoView` 安全定位函数，支持选择器多级降级查找、平滑居中滚动与内部输入框延迟自动聚焦；
   - 实现了 `shouldBlockNavigation` 与 `applyBeforeUnloadEvent` 离开拦截纯逻辑。

2. `frontend/web/src/FormActionFooter.tsx`（新增）：
   - 实现表单吸底操作条组件 `FormActionFooter`；
   - 容器支持 `sticky` 吸附切换，辅以毛玻璃效果与柔和阴影（`0 -4px 12px rgba(0,0,0,0.06)`）；
   - 左侧自适应展示修改项计数标签（`Tag color="blue"` / `Tag color="warning"`），关键字段变动时展示醒目警示文案；
   - 右侧排列取消、重置、保存按钮与扩展插槽，重置按钮在无脏数据时自动禁用，文字对比度符合 WCAG AA 4.5:1。

3. `frontend/web/src/useUnsavedPrompt.ts`（新增）：
   - 实现通用 React Hook `useUnsavedPrompt`；
   - 监听 `beforeunload` 原生事件并在组件卸载时安全清理；
   - 封装 `confirmNavigation`，通过 Ant Design `Modal.confirm` 拦截路由跳转并以红色警示按钮（`okButtonProps: { danger: true }`）强化警示。

4. `frontend/web/src/MetadataForm.tsx`（修改）：
   - 增加 `stickyFooter`、`showCancelButton`、`cancelText`、`resetText`、`promptOnUnsaved`、`serverErrors`、`autoScrollToError`、`onReset`、`onCancel` 属性；
   - 接入 `detectDirtyFields` 实时计算修改项；
   - 接入 `useUnsavedPrompt` 离开保护；
   - 接入 `serverErrors` 监听与 `scrollFieldIntoView` 首错字段自动滚动聚焦；
   - 底部操作区接入 `FormActionFooter`。

5. `frontend/web/src/styles.css`（修改）：
   - 增加 `.icg-form-sticky-footer` 及 `.is-sticky` 样式；
   - 增加 `.icg-footer-inner`、`.icg-footer-left-info`、`.icg-footer-modified-tag`、`.icg-footer-right-actions` 弹性排版样式；
   - 增加 `@keyframes icg-field-error-pulse` 错误字段高亮微动动画。

6. `tests/frontend/form-interactions.test.mjs`（新增）：
   - 7 大测试套件，全面覆盖脏数据检测、★ 关键字段变更统计、FastAPI/Pydantic details 数组与字典映射解析、嵌套错误结构、Node.js 环境 DOM 安全性与离开拦截纯逻辑。

7. `frontend/web/tests/form-interactions.test.mjs`（新增）：
   - 4 大静态 AST 结构断言套件，全面断言 `FormActionFooter` 组件导出与吸底容器声明、`useUnsavedPrompt` Hook 的 beforeunload 绑定与 Modal 拦截、`MetadataForm` 深度集成以及 `styles.css` 动画声明。

## 关键判断与异常分支处理

1. **脏数据误判防护（Falsy 值与空白符归一化）**：
   - 纯比对算法在处理 `null` 与 `undefined`、`""` 与 `"   "` 时视为等价，避免用户在某输入框中点击聚焦后离开、或原本为空的字段被表单赋值为空串时触发虚假脏数据提示。
2. **服务端错误结构多样性容错**：
   - 后端框架可能采用多种错误格式：FastAPI 常见 `details: [{ loc: ["body", "field_name"], msg: "..." }]`，普通 RESTful 常见 `{ field: "...", message: "..." }`，业务字典常见 `details: { field_name: "..." }`。
   - `mapServerFieldErrors` 内置 4 层格式探测，无论哪种格式均能精准提取首错字段名与错误信息，空值或非对象输入优雅返回兜底空数组，绝不引发运行时异常。
3. **DOM 与非浏览器环境安全性**：
   - `scrollFieldIntoView` 在调用前严格检查 `typeof document !== 'undefined'`，且对 `querySelector` 使用 try-catch 保护，保证在 Node.js 自动化测试、CI 环境与服务端渲染（SSR）环境下安全执行。
4. **长表单聚焦延迟与平滑体验**：
   - 字段滚动至视口中央后，输入框聚焦采用 `setTimeout(..., 100)` 微延迟，确保在 Ant Design 滚动动画执行期间不会因瞬间夺取焦点而发生视口剧烈跳动或闪烁。

## 限制与后续演进

1. **复杂子表格与动态列表项就近定位**：当前错误定位主要针对顶层标量字段名（如 `entity_name`）。后续若引入嵌套动态表单列表（Form.List，字段路径如 `members[0].role`），可扩展字段选择器规则支持深层嵌套定位。
2. **表单草稿定时自动保存**：吸底栏为后续扩展“自动保存中 / 上次自动保存于 10:30”提供了天然的状态呈现容器，可供后续编辑台高阶需求无缝复用。
