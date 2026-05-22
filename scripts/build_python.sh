#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Python server with PyInstaller ==="

rm -rf build/pyinstaller electron/resources/server

pyinstaller \
  --name server \
  --onedir \
  --distpath electron/resources \
  --workpath build/pyinstaller \
  --add-data "app:app" \
  --add-data "wsgi.py:." \
  --add-data "python_protogen:python_protogen" \
  --add-data "app/static/glossary_template.csv:app/static" \
  --add-data "app/static/vad:app/static/vad" \
  --add-data "app/templates:app/templates" \
  --hidden-import flask \
  --hidden-import flask_socketio \
  --hidden-import flask_sqlalchemy \
  --hidden-import flask_migrate \
  --hidden-import sqlalchemy \
  --hidden-import python_dotenv \
  --hidden-import requests \
  --hidden-import bidict \
  --hidden-import tenacity \
  --hidden-import protobuf \
  --hidden-import simple_websocket \
  --hidden-import websockets \
  --hidden-import werkzeug \
  --hidden-import alembic \
  --collect-all python_protogen \
  wsgi.py

echo "=== Build complete ==="
ls -lh electron/resources/server/server/server 2>/dev/null || \
  ls -lh electron/resources/server/server/server.exe 2>/dev/null || \
  echo "Check electron/resources/server/ for output"
