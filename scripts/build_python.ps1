#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Resolve-Path "$SCRIPT_DIR\.."
Set-Location $PROJECT_ROOT

Write-Host "=== Building Python server with PyInstaller ==="

# 清理旧构建产物
Remove-Item -Recurse -Force "build\pyinstaller", "electron\resources\server" -ErrorAction SilentlyContinue

# 使用虚拟环境的 Python（确保包含所有依赖）
$PYINSTALLER_PYTHON = Join-Path $PROJECT_ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $PYINSTALLER_PYTHON)) {
    $PYINSTALLER_PYTHON = "python"
}

& $PYINSTALLER_PYTHON -m PyInstaller `
  --name server `
  --onedir `
  --distpath electron\resources `
  --workpath build\pyinstaller `
  --add-data "app;app" `
  --add-data "wsgi.py;." `
  --add-data "python_protogen;python_protogen" `
  --add-data "app/static/glossary_template.csv;app/static" `
  --add-data "app/static/vad;app/static/vad" `
  --add-data "app/templates;app/templates" `
  --hidden-import flask `
  --hidden-import flask_socketio `
  --hidden-import flask_sqlalchemy `
  --hidden-import flask_migrate `
  --hidden-import sqlalchemy `
  --hidden-import python_dotenv `
  --hidden-import requests `
  --hidden-import bidict `
  --hidden-import tenacity `
  --hidden-import simple_websocket `
  --hidden-import websockets `
  --hidden-import werkzeug `
  --hidden-import alembic `
  --hidden-import engineio.async_drivers.threading `
  --hidden-import socketio.server `
  --hidden-import engineio.server `
  --collect-all google.protobuf `
  --collect-all python_protogen `
  wsgi.py

Write-Host "=== Build complete ==="
if (Test-Path "electron\resources\server\server.exe") {
    $file = Get-Item "electron\resources\server\server.exe"
    Write-Host "Output: $($file.FullName) ($($file.Length) bytes)"
} else {
    Write-Host "Check electron/resources/server/ for output"
}
