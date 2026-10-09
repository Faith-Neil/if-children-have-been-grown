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

同步完整复验、真实GitHub持续进程、出站/入站和停启结果在收尾后登记；当前不宣称已全部通过。

## 局限

测试使用合成仓库，未运行业务后端、实际招标解析、AI、数据库或Word服务。同步工具与目录迁移不能证明业务就绪。原型本轮未修改，既有6项编辑锁证据保留，不重复充作同步验证。历史来源旧环境链接保留原样；活动维护文档仍验证路径、索引与状态。
