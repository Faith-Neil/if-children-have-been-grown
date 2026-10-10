为什么有这个文件：解释APP-M1-T02本轮代码怎样服务实际业务。

它解决什么问题：让接手者理解页面操作、后台规则和数据更新之间的关系。

# APP-M1-T02：实际代码说明

日期2026-10-10。关联[ISSUE-007](../../issues/ISSUE-007.md)和[阶段交付](../delivery/APP-M1-T02.md)。代码版本reference-1，任务仍in-progress。

## 入口与行为

上传保存实际字节和摘要。ParserProvider读取文字分块，保留页码方式；本地规则抽取后要求逐条人工确认。事务提交确认、文件和任务版本；扫描PDF明确拒绝OCR缺失。DELETE只移除无来源的未解析/失败文件，已解析来源仍不能删。

源码位置：ProjectPages.tsx TenderPage/ParsePage；parsing.py、workflow.py、workflow_routes.py。前端位于frontend/web/src，后台位于backend/bid-core/icg_demo；启动器在业务核心目录。

## 验证与后续

[实际验证](../testing/2026-10-10-icg-reference.md)保留网络、页面与输出证据。公司隔离、只读拒绝、旧版本冲突和重复请求保护由后台执行，不能只靠界面按钮。

复杂版式/OCR、疑似遗漏和完整抽取后处理尚未交付；已解析原件替换/清理仍需完整来源迁移任务。

当前Repository为内存实现，进程重启清空；模型为演示替身。替换数据库要保持原子提交与失败回滚，替换模型要声明是否本地、核对公司和敏感项目路由；只留接口不表示真实服务已接入。
