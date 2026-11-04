# 为什么有这个文件：本机产品进程只连接 MySQL，并在连不上时直接退出。
# 它解决什么问题：避免沿用内存启动脚本，把关演示页面和持久化库说成已经跑起来。
param(
    [int]$Port = 8710,
    [switch]$Install,
    [switch]$Build,
    [string]$DatabaseUrl = $env:ICG_DATABASE_URL,
    [ValidateSet('development', 'production')]
    [string]$IcgEnv = 'development'
)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port must be between 1024 and 65535' }
$workspacePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$demoPythonPath = Join-Path $workspacePath '.venv\Scripts\python.exe'
$productPath = Join-Path $workspacePath 'frontend\web'
$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
$pnpmPath = if ($pnpmCommand) { $pnpmCommand.Source } else {
    Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
}
$envFile = Join-Path $workspacePath 'deploy\.env'
if (-not $DatabaseUrl -and (Test-Path -LiteralPath $envFile)) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match '^\s*ICG_DATABASE_URL\s*=\s*(.*)$') {
            $DatabaseUrl = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}
if (-not $DatabaseUrl) {
    # 本机已有的 icg-mysql 映射。口令与验收手册相同，只用于这台工作站，不用于虚拟机。
    $DatabaseUrl = 'mysql+pymysql://root:localdev@127.0.0.1:3307/icg?charset=utf8mb4'
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
if (-not (Test-Path -LiteralPath $demoPythonPath)) { throw 'Run Start-Product.ps1 -Install first' }
$env:ICG_DATABASE_URL = $DatabaseUrl
$env:ICG_REQUIRE_MYSQL = '1'
& $demoPythonPath -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); from icg.infra.mysql_gate import mysql_gate; gate = mysql_gate(); print(gate.reason); raise SystemExit(0 if gate.action == 'pass' else 1)"
if ($LASTEXITCODE -ne 0) { throw 'MySQL is unreachable. Refusing to start a memory repository.' }
$dist = Join-Path $productPath 'dist\index.html'
if ($Build -or -not (Test-Path -LiteralPath $dist)) {
    if (-not (Test-Path -LiteralPath $pnpmPath)) { throw 'pnpm not found; run Start-Product.ps1 -Install or install Node/pnpm' }
    $env:VITE_DEMO = '0'
    & $pnpmPath --dir $productPath build
    if ($LASTEXITCODE -ne 0) { throw 'Product page build failed' }
}
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
$env:ICG_ENV = $IcgEnv
$env:ICG_ALLOW_DEMO_LOGIN = '0'
if ($IcgEnv -eq 'production' -and -not $env:ICG_ADMIN_INITIAL_PASSWORD) {
    throw 'ICG_ENV=production requires ICG_ADMIN_INITIAL_PASSWORD outside the repository.'
}
Write-Host "ICG product: http://127.0.0.1:$Port  repository=mysql  ICG_ENV=$IcgEnv  VITE_DEMO=0"
Write-Host 'Virtual machine placement: docs/operations/docker-vm-deployment.md'
& $demoPythonPath -m uvicorn icg_demo.main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port --workers 1
exit $LASTEXITCODE
