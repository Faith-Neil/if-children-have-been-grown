# 为什么有这个文件：统一安装、构建和启动同一套ICG产品页面与后台。
# 它解决什么问题：避免前端没构建、环境不一致，或误把开发验证页当产品入口。
param([int]$Port = 8710, [switch]$Install)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535' }
$workspacePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$demoPythonPath = Join-Path $workspacePath '.venv\Scripts\python.exe'
if ($Install) {
    if (-not (Test-Path -LiteralPath $demoPythonPath)) {
        & python -m venv (Join-Path $workspacePath '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create demo Python environment' }
    }
    & $demoPythonPath -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install demo dependencies' }
    $productPath = Join-Path $workspacePath 'frontend\web'
    $pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
    $pnpmPath = if ($pnpmCommand) { $pnpmCommand.Source } else {
        # Codex已有的依赖运行时可用时复用；其他机器安装标准Node.js/pnpm即可。
        Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
    }
    if (-not (Test-Path -LiteralPath $pnpmPath)) { throw 'Node.js and pnpm are required; see frontend/web/README.md' }
    & $pnpmPath --dir $productPath install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install product page dependencies' }
    & $pnpmPath --dir $productPath build
    if ($LASTEXITCODE -ne 0) { throw 'Product page build failed' }
}
if (-not (Test-Path -LiteralPath $demoPythonPath)) { throw 'Run Start-Demo.ps1 -Install first' }
if (-not (Test-Path -LiteralPath (Join-Path $workspacePath 'frontend\web\dist\index.html'))) { throw 'Build frontend/web first or run Start-Demo.ps1 -Install' }
Write-Host "ICG: http://127.0.0.1:$Port (memory data, one process; developer tool: /demo)"
& $demoPythonPath -m uvicorn icg_demo.main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port --workers 1
exit $LASTEXITCODE
