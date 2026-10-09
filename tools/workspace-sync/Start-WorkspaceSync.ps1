param(
    [string]$ConfigPath = (Join-Path $env:LOCALAPPDATA 'CodexWorkspaceSync\Faith-Neil-if-children-have-been-grown\settings.json'),
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
$syncExitCode = 1
$syncSecret = $null
$syncBstr = [IntPtr]::Zero
$syncProcess = $null
try {
    $syncConfig = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    foreach ($syncField in @('repoPath', 'nodePath', 'tokenFile', 'runtimeDir')) {
        $syncConfig.$syncField = [Environment]::ExpandEnvironmentVariables([string]$syncConfig.$syncField)
    }
    $syncRepoPath = [IO.Path]::GetFullPath($syncConfig.repoPath).TrimEnd('\', '/')
    $syncExternalPath = [IO.Path]::GetFullPath($ConfigPath)
    foreach ($syncCandidate in @($syncExternalPath, $syncConfig.tokenFile, $syncConfig.runtimeDir)) {
        $syncAbsolute = [IO.Path]::GetFullPath($syncCandidate)
        if ($syncAbsolute.Equals($syncRepoPath, [StringComparison]::OrdinalIgnoreCase) -or $syncAbsolute.StartsWith($syncRepoPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Configuration, token and runtime must stay outside the workspace.'
        }
    }
    if (-not (Test-Path -LiteralPath $syncConfig.nodePath -PathType Leaf)) { throw 'Configured Node.js is unavailable.' }
    # ConvertFrom-SecureString默认格式由Windows当前用户DPAPI保护；不使用-Key。
    $syncEncrypted = (Get-Content -LiteralPath $syncConfig.tokenFile -Raw).Trim()
    $syncSecret = ConvertTo-SecureString -String $syncEncrypted
    $syncBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($syncSecret)
    $syncStart = New-Object Diagnostics.ProcessStartInfo
    $syncStart.FileName = $syncConfig.nodePath
    $syncStart.UseShellExecute = $false
    $syncStart.CreateNoWindow = $true
    $syncStart.WorkingDirectory = $syncConfig.repoPath
    $syncStart.EnvironmentVariables['WORKSPACE_SYNC_TOKEN'] = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($syncBstr)
    # 写外部的展开配置，避免把凭据或运行状态加入Git。
    New-Item -ItemType Directory -Path $syncConfig.runtimeDir -Force | Out-Null
    $syncResolvedConfig = Join-Path $syncConfig.runtimeDir 'config.resolved.json'
    [IO.File]::WriteAllText($syncResolvedConfig, ($syncConfig | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    $syncScript = Join-Path $PSScriptRoot 'sync.cjs'
    $syncMode = if ($Once) { '--once' } else { '--run' }
    # 固定选项和经过Windows参数转义的路径；不启动shell解释命令。
    function ConvertTo-SyncArgument([string]$Value) {
        return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
    }
    $syncStart.Arguments = (ConvertTo-SyncArgument $syncScript) + ' --config ' + (ConvertTo-SyncArgument $syncResolvedConfig) + ' ' + $syncMode
    $syncProcess = New-Object Diagnostics.Process
    $syncProcess.StartInfo = $syncStart
    $syncProcess.Start() | Out-Null
    # 子进程已取得环境副本后，立即清除启动对象中的明文值。
    $syncStart.EnvironmentVariables.Remove('WORKSPACE_SYNC_TOKEN')
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($syncBstr)
    $syncBstr = [IntPtr]::Zero
    $syncProcess.WaitForExit()
    $syncExitCode = $syncProcess.ExitCode
} catch {
    # 异常对象可能含路径或内部参数，不打印其正文。
    Write-Error 'Workspace sync launcher failed. Check external configuration, current-user DPAPI credential and instance status.'
} finally {
    if ($syncBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($syncBstr) }
    if ($syncSecret) { $syncSecret.Dispose() }
    if ($syncProcess) { $syncProcess.Dispose() }
}
exit $syncExitCode
