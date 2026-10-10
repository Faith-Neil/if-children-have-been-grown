为什么有这个文件：解释APP-M1-T01本轮代码怎样服务实际业务。

它解决什么问题：让接手者理解页面操作、后台规则和数据更新之间的关系。

# APP-M1-T01：实际代码说明

日期2026-10-10。关联[ISSUE-007](../../issues/ISSUE-007.md)和[阶段交付](../delivery/APP-M1-T01.md)。代码版本reference-1，任务仍in-progress。

## 入口与行为

App.tsx从登录取得临时凭据，再加载公司项目、资料和任务。进入项目后读取workspace；所有页签共享此状态。project-form.ts在创建前解释并校验北京时间，防止先建项目再因非法日期半途失败。main.py从dist提供根页面，旧小验证页移到/demo。

源码位置：App.tsx、project-form.ts、main.tsx、styles.css；main.py、Start-Demo.ps1。前端位于frontend/web/src，后台位于backend/bid-core/icg_demo；启动器在业务核心目录。

## 验证与后续

[实际验证](../testing/2026-10-10-icg-reference.md)保留网络、页面与输出证据。公司隔离、只读拒绝、旧版本冲突和重复请求保护由后台执行，不能只靠界面按钮。

完整项目统计、成员分配、项目状态和正式登录尚未齐；未把外壳当完整工作台。

当前Repository为内存实现，进程重启清空；模型为演示替身。替换数据库要保持原子提交与失败回滚，替换模型要声明是否本地、核对公司和敏感项目路由；只留接口不表示真实服务已接入。
