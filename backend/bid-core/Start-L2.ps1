# 为什么有这个文件：L2 验收用的一键持久化启动（MySQL + 关演示前端），区别于 Start-Demo.ps1 的纯内存模式。
# 它解决什么问题：避免「本地只能 memory 启动」无法做重启留证与 ICG_REQUIRE_MYSQL 门禁下的全链路人工验收。
param(
    [int]$Port = 8710,
    [switch]$Install,
    [string]$DatabaseUrl = $env:ICG_DATABASE_URL,
    [ValidateSet('development', 'production')]
    [string]$IcgEnv = 'development'
)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535' }
if (-not $DatabaseUrl) {
    throw @'
Set ICG_DATABASE_URL before Start-L2.ps1, for example:
  $env:ICG_DATABASE_URL = "mysql+pymysql://root:localdev@127.0.0.1:3307/icg?charset=utf8mb4"
Host port 3306 may already be another MySQL. Example:
  docker run -d --name icg-mysql -e MYSQL_ROOT_PASSWORD=localdev -e MYSQL_DATABASE=icg -p 3307:3306 mysql:8.0
'@
}
$workspacePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$demoPythonPath = Join-Path $workspacePath '.venv\Scripts\python.exe'
$productPath = Join-Path $workspacePath 'frontend\web'
$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
$pnpmPath = if ($pnpmCommand) { $pnpmCommand.Source } else {
    Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
}
if ($Install) {
    if (-not (Test-Path -LiteralPath $demoPythonPath)) {
        & python -m venv (Join-Path $workspacePath '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python environment' }
    }
    & $demoPythonPath -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install backend dependencies' }
    if (-not (Test-Path -LiteralPath $pnpmPath)) { throw 'Node.js and pnpm are required; see frontend/web/README.md' }
    & $pnpmPath --dir $productPath install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install frontend dependencies' }
}
if (-not (Test-Path -LiteralPath $demoPythonPath)) { throw 'Run Start-L2.ps1 -Install first' }
if (-not (Test-Path -LiteralPath $pnpmPath)) { throw 'pnpm not found; run Start-L2.ps1 -Install or install Node/pnpm' }
# 关演示 UI：须于 build 时注入 VITE_DEMO=0
$env:VITE_DEMO = '0'
& $pnpmPath --dir $productPath build
if ($LASTEXITCODE -ne 0) { throw 'Product page build failed' }
Write-Host 'Running Alembic migrations (upgrade head)...'
& $demoPythonPath -m alembic -c (Join-Path $PSScriptRoot 'alembic.ini') upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Alembic migration failed; check MySQL is up and ICG_DATABASE_URL is correct' }
if (-not $env:ICG_SECRET_KEY) {
    $keyPath = Join-Path $PSScriptRoot 'data\local-secret.key'
    if (-not (Test-Path -LiteralPath $keyPath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $keyPath) | Out-Null
        & $demoPythonPath -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode(), end='')" | Set-Content -LiteralPath $keyPath -NoNewline
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create local secret key' }
    }
    $env:ICG_SECRET_KEY = (Get-Content -LiteralPath $keyPath -Raw).Trim()
}
$env:ICG_DATABASE_URL = $DatabaseUrl
$env:ICG_REQUIRE_MYSQL = '1'
$env:ICG_ENV = $IcgEnv
if (-not $env:ICG_ALLOW_DEMO_LOGIN) { $env:ICG_ALLOW_DEMO_LOGIN = '0' }
if ($IcgEnv -eq 'production' -and -not $env:ICG_ADMIN_INITIAL_PASSWORD) {
    Write-Warning 'ICG_ENV=production: set ICG_ADMIN_INITIAL_PASSWORD (outside repo) before first admin login.'
}
Write-Host "ICG L2: http://127.0.0.1:$Port  repository=mysql  ICG_ENV=$IcgEnv  VITE_DEMO=0"
Write-Host 'Login: POST /api/v1/auth/login (development: alpha-manager / X_2026). Runbook: docs/testing/2026-11-02-l2-manual-acceptance-runbook.md'
& $demoPythonPath -m uvicorn icg_demo.main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port --workers 1
exit $LASTEXITCODE
