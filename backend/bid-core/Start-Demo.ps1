# 为什么有这个文件：提供在Windows上安装和启动后端demo的统一入口。
# 它解决什么问题：避免开发者手动拼接路径，导致用错Python环境或启动方式。
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
}
if (-not (Test-Path -LiteralPath $demoPythonPath)) { throw 'Run Start-Demo.ps1 -Install first' }
Write-Host "Demo: http://127.0.0.1:$Port (memory data, one process)"
& $demoPythonPath -m uvicorn icg_demo.main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port --workers 1
exit $LASTEXITCODE
