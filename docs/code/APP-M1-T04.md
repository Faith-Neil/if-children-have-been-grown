为什么有这个文件：解释APP-M1-T04本轮代码怎样服务实际业务。

它解决什么问题：让接手者理解页面操作、后台规则和数据更新之间的关系。

# APP-M1-T04：实际代码说明

日期2026-10-10。关联[ISSUE-007](../../issues/ISSUE-007.md)和[阶段交付](../delivery/APP-M1-T04.md)。代码版本reference-1，任务仍in-progress。

## 入口与行为

编辑权绑定账号与登录会话，定期续期。草稿另存、正文提交产生新版本。恢复核对后台版本与草稿sequence后先持久保存草稿，再替换页面文字，失败不假称成功。ModelProvider仅返回建议，两个入口均核对敏感模型路由；input_snapshot.py让相关资料变化使旧候选失效。

源码位置：EditorPage.tsx、RecoveryReview.tsx、editor-recovery.ts；domain.py、input_snapshot.py、workflow.py。前端位于frontend/web/src，后台位于backend/bid-core/icg_demo；启动器在业务核心目录。

## 验证与后续

[实际验证](../testing/2026-10-10-icg-reference.md)保留网络、页面与输出证据。公司隔离、只读拒绝、旧版本冲突和重复请求保护由后台执行，不能只靠界面按钮。

仍是纯文本正文；结构化段落、引用/变量节点、选区助手、正式回滚事件和完整写作方案待实现。

当前Repository为内存实现，进程重启清空；模型为演示替身。替换数据库要保持原子提交与失败回滚，替换模型要声明是否本地、核对公司和敏感项目路由；只留接口不表示真实服务已接入。
