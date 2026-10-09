# 整个工作区的草稿同步

关联 ISSUE-004 / OPS-M0-T01。实现已审读并通过10项真实bare remote回归；实际启用与云端运行证据见 [本轮验证](../../docs/testing/2026-10-09-workspace-sync.md)，当前状态见工作区外的runtime/status.json。

仓库提升到 `X:\ICG CO` 后，既有 `README.md`、`docs/`、`prototypes/` 等远端路径保持不变；`ICG/` 历史资料作为同一仓库的其他项目资产。两个合同目录已由用户明确排除。主工作区只有一个 `.git`，不建立父子仓库或重复镜像。

配置使用本目录 `config.example.json` 的字段。实际配置、令牌和runtime位于工作区外的 `%LOCALAPPDATA%\CodexWorkspaceSync\Faith-Neil-if-children-have-been-grown\`，配置名settings.json。示例不含凭据。credential.dpapi采用Windows当前用户的无额外密钥加密，依据 [Microsoft DPAPI说明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/convertfrom-securestring)。启动脚本只读取加密凭据和启动进程；凭据与登录启动项由维护者单独配置。

## 使用

维护者配置完成并确认工作区根已提升后，以同一Windows用户运行：

```powershell
& 'X:\ICG CO\tools\workspace-sync\Start-WorkspaceSync.ps1'
& 'X:\ICG CO\tools\workspace-sync\Start-WorkspaceSync.ps1' -Once
```

launcher在内存解密DPAPI令牌，只传入Node子进程的 `WORKSPACE_SYNC_TOKEN` 环境变量；Git认证使用子进程环境中的临时配置，不把令牌写入URL、Git配置、命令参数或日志。运行时配置只存路径和间隔。`-Once` 使用同一检查逻辑执行一次；若文件尚未稳定，返回settling，需要以后继续执行，不会跳过10秒稳定期。

Node也支持 `node sync.cjs --config <外部配置> --once` 或 `--run`。正常运行每3秒检查本地，内容与修改时间稳定10秒后生成WIP快照并推送固定的 `codex/repository-foundation` 草稿分支，每30秒fetch。新快照是备份，不标记任何任务完成，也不代替正常PR评审、验收、合入或发布。

## 保全与冲突

- 尊重 `.gitignore`；候选文件若含合同根 `C2024-SAL0024-*` / `C2025-TCH0053-*`、凭据文件名或已识别令牌/私钥模式、单文件达到100MiB、符号链接或嵌套Git，则暂停。扫描不输出正文，不能证明全部资料已经脱敏。
- 人已暂存、存在index锁、merge/rebase/cherry-pick等操作、分支或拉取/推送URL不匹配时暂停。已有暂存与提交保留，不reset、不force push。
- 本地和远端已分叉时暂停；远端仅领先且本地干净时只允许ff-only。远端领先而本地有未提交修改时暂停。工具不自动解决冲突、不生成合并提交。
- 自动提交后网络失败会保留本地提交，5～60秒退避重试。远端拒绝快照时重新fetch并核对分叉，不强推。
- 推送前同时检查所有尚未发送的提交中的文件内容，人工提交的凭据即使在后续提交中删除，也会拦截在本地；UTF8和UTF16格式均检查。暂存或出站历史有问题时保留现场，由维护者处理。
- 单实例锁只防止多个同步进程。人工Git操作前先停止同步，避免同一路径的暂存操作发生并发；工具能发现异常暂存时保留现场，需要维护者处理。
- 暂停原因在外部 `runtime/status.json` 与 `events.jsonl` 中，只记录状态和计数；不记录Git原始输出、令牌、认证头或文件正文。

停止：在配置的runtime目录创建名为 `stop` 的文件。当前Git命令结束后会停止（命令超时45秒），保留工作树和已有快照。再次启动前由维护者移除stop文件。退出时释放所属单实例锁；已死亡进程的锁可自动回收，无法确认归属的锁保持暂停。

## 验证

```powershell
node --check tools/workspace-sync/sync.cjs
node --test tests/workspace-sync/*.test.cjs
```

回归使用真实临时bare remote，测试本地快照推送、干净快进、分叉保全、人的暂存、忽略与敏感材料阻断、分支错误和日志无令牌。测试模式允许明确标记的本地remote；生产配置只允许无凭据的GitHub HTTPS URL。

快进策略依据 [Git ff-only文档](https://git-scm.com/docs/git-pull)。单文件边界按 [GitHub文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)保守拦截达到100MiB的候选；本轮允许纳入的项目文件最大不足1MiB，不需要为合同原件配置LFS。
