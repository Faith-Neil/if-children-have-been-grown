# 工作区同步与接手审查验证

日期：2026-10-09（UTC+8）。关联：ISSUE-004 / OPS-M0-T01 / REV-M0-T01。

## 环境与迁移

Windows、Node.js v24.19.0、Git。根从X:\ICG CO\if-children-have-been-grown提升到X:\ICG CO，12个顶层入口移动；HEAD仍8e23e36，分支仍codex/repository-foundation。两个客户合同根由git check-ignore确认排除，未读其内容。ICG34份资料总8,950,036字节，保留本地内容与来源指纹。

访问令牌已成功核对GitHub私有仓库权限，并存入工作区外、用户访问控制的DPAPI加密文件；repo URL不含凭据。main ce064f6、xqr 9427568；PR #1/#3均为草稿待合入。该结果为本轮查询快照。

## 检查入口与结果

```powershell
node --test tests/workspace-sync/*.test.cjs
node --test tests/governance/*.test.cjs
node --check tools/workspace-sync/sync.cjs
node scripts/check-project-governance.cjs
```

治理回归11项通过；Node及PowerShell启动器语法通过。同步回归使用真实临时bare remote；首次9/10通过，第10项远端更新已经快进，但Windows工作树CRLF导致文本断言不同，已改按规范化换行验证并重新执行。

完整复验10/10通过（0失败）；治理回归11/11通过。活动记录检查通过：57份Markdown、61任务、5Issue。Git差异检查通过。34份ICG源文件指纹34/34保持，敏感路径未进入版本候选。

## 真实GitHub与持续运行验证

- 67cb162：PowerShell启动器使用用户DPAPI文件解密，在工具真实出站历史检查后推送工作区与审查交付；status为synced/snapshot-pushed，ahead/behind均0。
- 9bd036a：隐藏持续进程自动提交并推送本地合成探针，证明稳定期后的自动保存生效。
- 92b4813：通过GitHub API只改同一合成探针，工具自动fetch/pull ff-only；本地HEAD与文件内容更新，事件记录fast-forwarded。
- ce6e6d7：本地移除合成探针，工具自动快照并推送删除；无探针残留，分支差异0/0。
- Windows当前用户登录启动项CodexICGWorkspaceSync已设置，进程隐藏运行；stop请求验证有序停止及锁释放，人工收尾提交后恢复同一配置。

真实验证未强推、未创建合并提交、未触及main/xqr或两个客户原件根。运行状态和日志在工作区外，只记录固定状态字段，无令牌、认证头或正文。登录项存在与当前运行已验证；跨未来登录的实际启动取决于当前用户会话、X盘和运行依赖可用性。

## 局限

测试使用合成仓库，未运行业务后端、实际招标解析、AI、数据库或Word服务。同步工具与目录迁移不能证明业务就绪。原型本轮未修改，既有6项编辑锁证据保留，不重复充作同步验证。历史来源旧环境链接保留原样；活动维护文档仍验证路径、索引与状态。
