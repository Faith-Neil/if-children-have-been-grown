# 代码说明：APP-M2-T164 变量节点

为什么有这个文件：说明变量节点的解析、显示与写入拦截点。

它解决什么问题：以后新增写正文的路径或换编辑器时，知道变量取值从哪来、在哪里拒绝失效变量。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T164 |
| 交付文件 | `docs/delivery/APP-M2-T164.md` |
| 影响模块 | `icg/domain/variable_nodes.py`、`icg/api/chapter_versions.py`、`icg/domain/domain.py`、`icg/domain/version_rollback.py`、`frontend/web/src/editor/variable-nodes.ts`、`VariableChip.tsx`、`CiteCapsule.tsx`、`EditorPage.tsx`、`editor-conflict.ts` |
<!-- code-explanation:end -->

## 解析
`variable_nodes.nodes(state, project_id, content)` 用与生成、导出相同的正则找出 `{{fact:id}}` 与 `{{sla:key}}`，另用 `BROKEN` 找出残缺写法。每个变量单独调用 `generation_context.resolve_fact_variables`（它会再调 `sla.resolve_variables`），与导出走同一套校验：
- 先带上变量后面同一行最多 12 个字符一起解析，用来发现单位不符或重复单位；
- 再只解析变量本身，得到显示值；
- 显示值经 `ExportServiceMixin._mask` 掩码，`masked` 表示是否被掩码。

失败时 `DomainError.code` 原样作为节点的 `code`，`status` 为 `invalid`；数据源里找不到为 `unknown`。`source` 指明去哪改：普通事实为 `facts`，服务承诺为 `matrix`。

## 写入拦截
`refuse_new_invalid(state, chapter, new_content)`：新正文里的失效节点减去当前正文里同样写法的失效节点（按 `Counter` 逐个扣减），剩下的就是本次新写入的，非空即 409，错误码取第一个的 `code`，details.variables 列出每个。调用处：`DemoService.commit_version`（锁定段落核对之后、来源指纹核对之前）、`VersionRollbackService.rollback`。原有失效变量不挡提交，是为了不让数据源后来的变化把编写人卡在无法保存的状态；检查（`check_orchestrator` 调 `resolve_fact_variables`）与导出仍会拦截。

草稿保存不做这项核对：草稿不进入检查和导出。

## 接口
`POST /api/v1/projects/{p}/chapters/{c}/variables`，body `{content?}`；不传 content 解析已提交正文。权限同读取章节（`_chapter`），只读成员可用，不写任何数据。

## 前端
`EditorPage` 在正文文字停顿 400ms 后请求解析；章节版本或来源指纹变化时重新请求。`nodesMatch` 核对返回的位置与当前文字一致才显示，避免输入过程中标错位置。只读与未持锁视图由 `RichParagraphWithCites` 按 `lineSegments` 把每行切成文字与变量，变量渲染为 `VariableChip`；持锁编辑时在文本框下方显示变量栏和失效提示。提交返回 `VARIABLE_ERROR_CODES` 中的错误时显示后台原文并打开“去数据源”提示；`editor-conflict.NOT_A_REVISION_CONFLICT` 增加这些错误码与来源类错误码，不再进入版本冲突合并。
