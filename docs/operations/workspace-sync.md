# 云端工作区的运行与启停

日期：2026-10-09。关联：ISSUE-004 / OPS-M0-T01。

## 范围与状态入口

Git根为 `X:\ICG CO`，远端是项目GitHub私有仓库，自动快照分支固定 `feat/opencode-ICG`。`ICG/` 的34份历史资料纳入；两个银行合同目录、凭据、依赖、构建及运行输出排除。根仅保留一套Git历史，旧 `if-children-have-been-grown/` 空目录不再作为独立仓库使用。

实际配置为 `%LOCALAPPDATA%\CodexWorkspaceSync\Faith-Neil-if-children-have-been-grown\settings.json`。同目录的 `credential.dpapi` 用当前Windows用户加密；`runtime/status.json` 是最新状态，`events.jsonl` 是滚动事件记录。它们在工作区外，不能提交。

本地每3秒检测，文件稳定10秒后自动WIP提交并推送；远端每30秒检查，工作区干净且历史能快进时获取更新。它是持续版本同步，不是逐次按键即时备份；休眠、离线和退出会话期间等待恢复。两边分叉不自动合并，PR合入和产品发布另外执行。

## 手动启动、状态和停止

以下均在当前Windows用户下操作：

```powershell
$syncSettingsPath = Join-Path $env:LOCALAPPDATA 'CodexWorkspaceSync\Faith-Neil-if-children-have-been-grown\settings.json'
& 'X:\ICG CO\tools\workspace-sync\Start-WorkspaceSync.ps1' -ConfigPath $syncSettingsPath
```

前台命令持续运行；日常使用的是维护者设置的隐藏登录启动项 `CodexICGWorkspaceSync`，无需开着终端。

```powershell
$syncStateDir = Join-Path $env:LOCALAPPDATA 'CodexWorkspaceSync\Faith-Neil-if-children-have-been-grown\runtime'
Get-Content -LiteralPath (Join-Path $syncStateDir 'status.json') -Raw
# 请求停止，保留已有提交和工作树
New-Item -ItemType File -Path (Join-Path $syncStateDir 'stop') -Force
```

停止后再启动前移除该 `stop` 文件。长期关闭可移除当前用户登录启动项：

```powershell
Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'CodexICGWorkspaceSync'
```

## 暂停时怎么处理

| 状态原因 | 处理 |
|---|---|
| human-staged-changes / git-operation-active | 先停止同步，完成或检查人工暂存/Git操作，不让自动任务处理人的索引 |
| diverged / remote-ahead-with-local-changes | 保留两边与未提交文件；维护者审查差异再正常整合，禁止强推/重置解冲突 |
| branch/remote/push-url-mismatch | 核对用户当前操作及配置，回到配置分支后再启动；不自动切分支 |
| secret-pattern / sensitive-file / excluded-client-material | 检查被阻止的新增材料或出站提交；不绕过检查强推，原件留本地 |
| large-file / symbolic-link / nested-git | 处理不适合直接快照的资产/链接/子仓库，登记合适的交付方式 |
| retrying | 网络/访问失败时保留本地快照并退避；恢复网络/有效权限后重试 |

自动快照是进行中的版本，不代替任务验收与文档同步。实施代码及回归见 [工具说明](../../tools/workspace-sync/README.md)，详细验证在 [本轮运行记录](../testing/2026-10-09-workspace-sync.md)。
