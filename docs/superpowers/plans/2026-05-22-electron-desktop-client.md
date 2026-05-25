# Electron Desktop Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the existing Flask-SocketIO web application into a macOS desktop client using Electron, with zero changes to existing frontend/WebSocket code.

**Architecture:** Electron main process spawns Python Flask server as child process. Chromium BrowserWindow loads `http://127.0.0.1:{PORT}`. Python backend stores data in `~/Library/Application Support/com.interpreter.simultaneous/data/`. PyInstaller `--onedir` bundles the Python runtime. No changes to JS/HTML/routes/Socket.IO.

**Tech Stack:** Electron 33, electron-builder 25, PyInstaller 6, Python 3.10+, Flask-SocketIO

---

### Task 1: Modify `app/config.py` — basedir override with env var

**Files:**
- Modify: `app/config.py`

**Goal:** Allow Electron to control where data (db, uploads, .env) is stored, instead of hardcoding to the project directory.

- [ ] **Step 1: Replace basedir assignment**

Old:
```python
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
```

New:
```python
basedir = os.environ.get('INTERPRETER_BASE_DIR')
if not basedir:
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
```

- [ ] **Step 2: Add .env fallback search path**

Old:
```python
load_dotenv(os.path.join(basedir, '.env'))
```

New:
```python
env_path = os.path.join(basedir, '.env')
if not os.path.exists(env_path):
    home_env = os.path.join(os.path.expanduser('~'), '.config', 'simultaneous-interpreter', '.env')
    if os.path.exists(home_env):
        env_path = home_env
load_dotenv(env_path)
```

- [ ] **Step 3: Make UPLOAD_FOLDER overridable**

Old:
```python
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
```

New:
```python
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
```

- [ ] **Step 4: Verify by running the app in dev mode**

Run:
```bash
python3 wsgi.py
```

Expected: App starts on `http://127.0.0.1:5004/` (note: still port 5004 for now, `0.0.0.0` changes to `127.0.0.1` come in Task 3).

- [ ] **Step 5: Commit**

```bash
git add app/config.py
git commit -m "feat: make basedir overridable via INTERPRETER_BASE_DIR env var"
```

---

### Task 2: Modify `app/__init__.py` — create_app(basedir) and log path

**Files:**
- Modify: `app/__init__.py`

**Goal:** Accept `basedir` parameter in `create_app()`, use it for log directory, ensure dirs exist safely.

- [ ] **Step 1: Update `setup_logging` to accept base_dir parameter**

Old:
```python
def setup_logging(app):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
```

New:
```python
def setup_logging(app, base_dir):
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
```

- [ ] **Step 2: Update `create_app` signature and internal logic**

Old:
```python
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    setup_logging(app)
```

New:
```python
def create_app(basedir=None):
    if basedir:
        os.environ.setdefault('INTERPRETER_BASE_DIR', basedir)

    app = Flask(__name__)
    app.config.from_object(Config)

    from app.config import basedir as config_basedir
    setup_logging(app, config_basedir)
```

- [ ] **Step 3: Make `UPLOAD_FOLDER` makedirs safe**

Old:
```python
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
```

New:
```python
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
```

- [ ] **Step 4: Verify dev mode**

Run:
```bash
python3 wsgi.py
```

Expected: App starts, no errors, `logs/translator.log` is created in project root.

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py
git commit -m "feat: create_app accepts basedir param, safe dir creation"
```

---

### Task 3: Rewrite `wsgi.py` — env var port, SIGTERM, localhost only

**Files:**
- Rewrite: `wsgi.py` (6 lines → ~22 lines)

**Goal:** Make the entry point accept PORT and DEBUG from environment, handle SIGTERM for graceful shutdown, listen only on localhost.

- [ ] **Step 1: Rewrite wsgi.py entirely**

Old content (6 lines):
```python
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5004, allow_unsafe_werkzeug=True)
```

New content:
```python
import os
import sys
import signal

from app import create_app, socketio


if __name__ == '__main__':
    basedir = os.environ.get('INTERPRETER_BASE_DIR')
    port = int(os.environ.get('PORT', 5004))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    app = create_app(basedir=basedir)

    def handle_sigterm(*args):
        socketio.stop()
        os._exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    socketio.run(
        app,
        debug=debug,
        host='127.0.0.1',
        port=port,
        allow_unsafe_werkzeug=debug
    )
```

- [ ] **Step 2: Verify dev mode**

Run:
```bash
python3 wsgi.py
```

Expected: App starts on `http://127.0.0.1:5004/`, open browser → page loads.

Also test:
```bash
PORT=5005 FLASK_DEBUG=1 python3 wsgi.py
```

Expected: App starts on port 5005.

- [ ] **Step 3: Verify SIGTERM handling**

```bash
python3 wsgi.py &
PID=$!
sleep 2
kill $PID
```

Expected: Process exits cleanly (no hanging).

- [ ] **Step 4: Commit**

```bash
git add wsgi.py
git commit -m "feat: wsgi.py reads PORT/DEBUG from env, SIGTERM handler, localhost only"
```

---

### Task 4: Modify `app/socket_handlers.py` — fix meetings_dir path

**Files:**
- Modify: `app/socket_handlers.py:363`

**Goal:** Store `meetings/` transcripts in the basedir (controlled by env var) instead of relative to project directory.

- [ ] **Step 1: Change import and meetings_dir construction**

Add at top of the file (with the other imports):
```python
from app.config import basedir as app_basedir
```

Replace line 363:
```python
meetings_dir = os.path.join(app.root_path, '..', 'meetings')
```

New:
```python
meetings_dir = os.path.join(app_basedir, 'meetings')
```

- [ ] **Step 2: Verify dev mode**

Run:
```bash
python3 wsgi.py
```

Expected: Start a translation session, speak, stop session. Verify `{basedir}/meetings/meeting_*.json` is created.

- [ ] **Step 3: Commit**

```bash
git add app/socket_handlers.py
git commit -m "fix: store meetings dir under INTERPRETER_BASE_DIR instead of project root"
```

---

### Task 5: Install Electron dependencies and initialize project

**Files:**
- Create: `electron/package.json`
- Create: `electron/preload.js`
- Create: `electron/main.js` (stub)
- Create: `electron/.gitignore`

**Goal:** Set up Node.js project with Electron, ready for development.

- [ ] **Step 1: Create `electron/` directory**

```bash
mkdir -p electron
```

- [ ] **Step 2: Write `electron/package.json`**

```json
{
  "name": "simultaneous-interpreter",
  "version": "1.0.0",
  "description": "同声传译 - 桌面客户端",
  "main": "main.js",
  "scripts": {
    "dev": "electron .",
    "build:python": "bash ../scripts/build_python.sh",
    "build": "npm run build:python && electron-builder",
    "build:mac": "npm run build:python && electron-builder --mac"
  },
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0"
  },
  "build": {
    "appId": "com.interpreter.simultaneous",
    "productName": "同声传译",
    "directories": {
      "output": "dist"
    },
    "extraResources": [
      {
        "from": "resources/server",
        "to": "server",
        "filter": ["**/*"]
      }
    ],
    "mac": {
      "target": ["dmg", "zip"],
      "icon": "resources/icon.icns",
      "category": "public.app-category.productivity",
      "hardenedRuntime": true,
      "gatekeeperAssess": false
    },
    "win": {
      "target": ["nsis"],
      "icon": "resources/icon.png"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true
    }
  }
}
```

- [ ] **Step 3: Write `electron/preload.js`**

```javascript
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    electron: process.versions.electron,
    chrome: process.versions.chrome,
  },
});
```

- [ ] **Step 4: Write `electron/.gitignore`**

```
node_modules/
dist/
resources/server/
```

- [ ] **Step 5: Install npm dependencies**

```bash
cd electron && npm install
```

Expected: `electron/node_modules/` and `electron/package-lock.json` created.

- [ ] **Step 6: Commit**

```bash
git add electron/
git commit -m "feat: initialize Electron project with package.json, preload.js, .gitignore"
```

---

### Task 6: Create `electron/main.js` — Electron main process

**Files:**
- Create: `electron/main.js`

**Goal:** The core Electron main process that spawns Python, detects ports, waits for server, creates window, manages lifecycle.

- [ ] **Step 1: Write `electron/main.js`**

```javascript
const { app, BrowserWindow, Menu, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const net = require('net');
const fs = require('fs');

let pythonProcess = null;
let mainWindow = null;
let actualPort = null;

const DEV_PORT = 5004;
const MAX_PORT_TRIES = 20;
const STARTUP_TIMEOUT = 30000;
const POLL_INTERVAL = 500;

function getDataDir() {
  const dataDir = path.join(app.getPath('userData'), 'data');
  fs.mkdirSync(path.join(dataDir, 'uploads'), { recursive: true });
  fs.mkdirSync(path.join(dataDir, 'meetings'), { recursive: true });
  return dataDir;
}

function findAvailablePort(startPort) {
  return new Promise((resolve, reject) => {
    const tryPort = (port, attempt) => {
      if (attempt > MAX_PORT_TRIES) {
        return reject(new Error('无法找到可用端口'));
      }
      const server = net.createServer();
      server.on('error', () => {
        server.close();
        tryPort(port + 1, attempt + 1);
      });
      server.listen(port, '127.0.0.1', () => {
        server.close();
        resolve(port);
      });
    };
    tryPort(startPort, 0);
  });
}

function getPythonServerPath() {
  if (app.isPackaged) {
    const binaryName = process.platform === 'win32' ? 'server.exe' : 'server';
    return path.join(process.resourcesPath, 'server', 'server', binaryName);
  }
  return null;
}

async function startPythonServer(dataDir) {
  actualPort = await findAvailablePort(DEV_PORT);

  const env = {
    ...process.env,
    PORT: String(actualPort),
    INTERPRETER_BASE_DIR: dataDir,
    FLASK_DEBUG: app.isPackaged ? '0' : '1',
    PYTHONUNBUFFERED: '1',
  };

  const serverPath = getPythonServerPath();

  if (serverPath) {
    pythonProcess = spawn(serverPath, [], { env, stdio: ['ignore', 'pipe', 'pipe'] });
  } else {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    pythonProcess = spawn(pythonCmd, ['wsgi.py'], {
      cwd: app.getAppPath(),
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  }

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[python] ${data.toString().trim()}`);
  });
  pythonProcess.stderr.on('data', (data) => {
    console.error(`[python:err] ${data.toString().trim()}`);
  });
  pythonProcess.on('exit', (code, signal) => {
    console.log(`Python server exited (code=${code}, signal=${signal})`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      dialog.showErrorBox('服务异常', `翻译服务已停止 (code=${code})，请重启应用。`);
    }
  });
}

function waitForServer() {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const poll = () => {
      const req = http.get(`http://127.0.0.1:${actualPort}/`, (res) => resolve());
      req.on('error', () => {
        if (Date.now() - start > STARTUP_TIMEOUT) {
          reject(new Error('服务启动超时'));
        } else {
          setTimeout(poll, POLL_INTERVAL);
        }
      });
      req.setTimeout(2000, () => {
        req.destroy();
        if (Date.now() - start > STARTUP_TIMEOUT) {
          reject(new Error('服务启动超时'));
        } else {
          setTimeout(poll, POLL_INTERVAL);
        }
      });
    };
    poll();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    minWidth: 900, minHeight: 600,
    title: '同声传译',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
  });

  mainWindow.loadURL(`http://127.0.0.1:${actualPort}/`);

  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('closed', () => { mainWindow = null; });

  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools();
  }
}

function checkApiKey(dataDir) {
  const envPath = path.join(dataDir, '.env');
  if (fs.existsSync(envPath)) return true;
  if (!app.isPackaged) {
    const devEnv = path.join(app.getAppPath(), '.env');
    if (fs.existsSync(devEnv)) return true;
  }
  return false;
}

function showSetupDialog(dataDir) {
  const setupWin = new BrowserWindow({
    width: 520, height: 460,
    resizable: false,
    parent: mainWindow,
    modal: true,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>首次配置</title>
<style>
  body { font-family: -apple-system, sans-serif; padding: 32px; line-height: 1.6; }
  h2 { margin-top: 0; } label { display: block; margin: 12px 0 4px; font-weight: 600; }
  input { width: 100%; padding: 8px; box-sizing: border-box; font-size: 14px; }
  button { margin-top: 20px; padding: 10px 24px; font-size: 14px; cursor: pointer; }
  .hint { color: #888; font-size: 12px; margin: 4px 0; }
</style></head>
<body>
  <h2>首次使用配置</h2>
  <p>请填写火山引擎 API 密钥以启用翻译服务。</p>
  <label>VOLCANO_APP_KEY</label>
  <input id="appKey" type="text" placeholder="输入 AppKey" />
  <label>VOLCANO_ACCESS_KEY</label>
  <input id="accessKey" type="text" placeholder="输入 AccessKey" />
  <div class="hint">可在火山引擎控制台 > 密钥管理 中获取</div>
  <button onclick="save()">保存并启动</button>
  <script>
    async function save() {
      const appKey = document.getElementById('appKey').value.trim();
      const accessKey = document.getElementById('accessKey').value.trim();
      if (!appKey || !accessKey) return alert('请填写完整');
      await fetch('/api/save_env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_key: appKey, access_key: accessKey }),
      });
      window.location.href = '/';
    }
  </script>
</body></html>`;

  setupWin.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function buildMenu() {
  const template = [
    {
      label: '同声传译',
      submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
    },
    {
      label: '编辑',
      submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }],
    },
    {
      label: '视图',
      submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }, { type: 'separator' }, { role: 'togglefullscreen' }],
    },
    {
      label: '窗口',
      submenu: [{ role: 'minimize' }, { role: 'zoom' }, { role: 'close' }],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(async () => {
  buildMenu();
  const dataDir = getDataDir();
  try {
    await startPythonServer(dataDir);
    await waitForServer();
    createWindow();
    if (!checkApiKey(dataDir)) {
      showSetupDialog(dataDir);
    }
  } catch (err) {
    dialog.showErrorBox('启动失败', err.message);
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        pythonProcess.kill('SIGKILL');
      }
    }, 3000).unref();
  }
});

app.on('window-all-closed', () => app.quit());
app.on('activate', () => {
  if (mainWindow === null && actualPort) createWindow();
});
```

- [ ] **Step 2: Verify Electron dev mode works**

Terminal 1 (start Flask):
```bash
python3 wsgi.py
```

Terminal 2 (start Electron):
```bash
cd electron && npm run dev
```

Expected: Electron window opens, shows the app UI, WebSocket/Socket.IO works.

- [ ] **Step 3: Kill and test clean shutdown**

Close Electron window.

```bash
ps aux | grep python | grep -v grep
```

Expected: No `wsgi.py` or `server` process remains.

- [ ] **Step 4: Commit**

```bash
git add electron/main.js
git commit -m "feat: Electron main process with Python sidecar, port detection, lifecycle"
```

---

### Task 7: Add `POST /api/save_env` endpoint in `app/routes/main.py`

**Files:**
- Modify: `app/routes/main.py`

**Goal:** Provide a backend endpoint for saving API keys both from the Electron setup dialog and the Web UI settings.

- [ ] **Step 1: Add imports and route**

Append to `app/routes/main.py`:

```python
import json
import os
from flask import request, jsonify
from app.config import basedir


@main_bp.route('/api/save_env', methods=['POST'])
def save_env():
    data = request.get_json()
    app_key = data.get('app_key')
    access_key = data.get('access_key')
    if not app_key or not access_key:
        return jsonify({'error': '参数不完整'}), 400

    env_path = os.path.join(basedir, '.env')
    with open(env_path, 'w') as f:
        f.write(f"VOLCANO_APP_KEY={app_key}\n")
        f.write(f"VOLCANO_ACCESS_KEY={access_key}\n")
        f.write(f"FLASK_SECRET_KEY={os.urandom(24).hex()}\n")

    # Update running config immediately
    os.environ['VOLCANO_APP_KEY'] = app_key
    os.environ['VOLCANO_ACCESS_KEY'] = access_key

    return jsonify({'success': True})
```

- [ ] **Step 2: Verify endpoint works**

```bash
python3 wsgi.py &
sleep 2

curl -s -X POST http://127.0.0.1:5004/api/save_env \
  -H 'Content-Type: application/json' \
  -d '{"app_key":"test_key","access_key":"test_secret"}'

# Stop server
kill %1
```

Expected: `{"success":true}`

- [ ] **Step 3: Commit**

```bash
git add app/routes/main.py
git commit -m "feat: add POST /api/save_env endpoint for API key configuration"
```

---

### Task 8: Add settings UI in `index.html` and `translator.js`

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/static/js/translator.js`

**Goal:** Add a settings button in the header toolbar and a modal dialog for modifying API keys.

- [ ] **Step 1: Add settings button to the header**

In `index.html`, find:
```html
<div class="header-center">
    <a href="/glossary"><button class="btn-nav">术语管理 / Glossary Mgr</button></a>
    <a href="/meetings"><button class="btn-nav">会议记录 / Meetings</button></a>
```

Add after the meetings button:
```html
    <button class="btn-nav" onclick="showSettingsModal()" style="margin-left:auto;">⚙ 设置</button>
```

- [ ] **Step 2: Add settings modal HTML** before closing `</body>` tag

In `index.html`, add before `</body>`:
```html
<div id="settings-modal" class="modal-overlay" style="display:none;">
  <div class="modal-content" style="width:460px;">
    <div class="modal-header">
      <span>API 密钥设置</span>
      <button class="modal-close" onclick="hideSettingsModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label class="form-label">VOLCANO_APP_KEY</label>
        <input id="settings-app-key" type="text" class="form-input" placeholder="输入 AppKey" />
      </div>
      <div class="form-group">
        <label class="form-label">VOLCANO_ACCESS_KEY</label>
        <input id="settings-access-key" type="text" class="form-input" placeholder="输入 AccessKey" />
      </div>
      <div id="settings-status" class="tip-box" style="display:none;"></div>
    </div>
    <div class="modal-footer">
      <button class="btn-nav" onclick="saveSettings()" style="padding:6px 20px;">保存</button>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add settings modal CSS** in the `<style>` section

Add anywhere in the existing `<style>` block:
```css
.modal-overlay {
  position: fixed; top:0; left:0; width:100%; height:100%;
  background: rgba(0,0,0,0.7); z-index:1000;
  display:flex; align-items:center; justify-content:center;
}
.modal-content {
  background:var(--bg-card); border:1px solid var(--border);
  border-radius:8px; padding:20px; max-width:90%;
}
.modal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; font-size:15px; font-weight:600; }
.modal-close { background:none; border:none; color:var(--text-sub); font-size:22px; cursor:pointer; }
.modal-close:hover { color:white; }
.modal-footer { margin-top:15px; text-align:right; }
.form-input { width:100%; background:var(--bg-input); color:white; border:1px solid var(--border); padding:8px; border-radius:4px; font-size:13px; }
```

- [ ] **Step 4: Add JS functions in `translator.js`**

Add at the end of the IIFE (before the closing `})()`):
```javascript
  // --- Settings modal (API Key) ---
  window.showSettingsModal = function() {
    document.getElementById('settings-modal').style.display = 'flex';
  };

  window.hideSettingsModal = function() {
    document.getElementById('settings-modal').style.display = 'none';
    document.getElementById('settings-status').style.display = 'none';
  };

  window.saveSettings = async function() {
    const appKey = document.getElementById('settings-app-key').value.trim();
    const accessKey = document.getElementById('settings-access-key').value.trim();
    const statusEl = document.getElementById('settings-status');

    if (!appKey || !accessKey) {
      statusEl.className = 'tip-box tip-warning';
      statusEl.textContent = '请填写完整';
      statusEl.style.display = 'block';
      return;
    }

    try {
      const res = await fetch('/api/save_env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_key: appKey, access_key: accessKey }),
      });
      const data = await res.json();
      if (data.success) {
        statusEl.className = 'tip-box tip-success';
        statusEl.textContent = '保存成功，密钥已生效';
        statusEl.style.display = 'block';
      } else {
        statusEl.className = 'tip-box tip-warning';
        statusEl.textContent = '保存失败：' + (data.error || '未知错误');
        statusEl.style.display = 'block';
      }
    } catch (err) {
      statusEl.className = 'tip-box tip-warning';
      statusEl.textContent = '网络错误：' + err.message;
      statusEl.style.display = 'block';
    }
  };
```

- [ ] **Step 5: Verify UI works in browser**

```bash
python3 wsgi.py
```

Open browser → navigate to `http://127.0.0.1:5004/`.
Click the "⚙ 设置" button in the header.
Expected: Modal appears with empty AppKey/AccessKey fields.
Fill in test values, click "保存".
Expected: Green success message appears.

- [ ] **Step 6: Commit**

```bash
git add app/templates/index.html app/static/js/translator.js
git commit -m "feat: add API key settings modal in Web UI"
```

---

### Task 9: Create `scripts/build_python.sh` — PyInstaller build

**Files:**
- Create: `scripts/build_python.sh`

**Goal:** Build the Python Flask server into a standalone binary using PyInstaller `--onedir`.

- [ ] **Step 1: Write `scripts/build_python.sh`**

```bash
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
echo "Binary: electron/resources/server/server/server"
ls -lh electron/resources/server/server/server 2>/dev/null || \
  ls -lh electron/resources/server/server/server.exe 2>/dev/null || \
  echo "(check dist directory for binary)"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/build_python.sh
```

- [ ] **Step 3: Add `build/pyinstaller/` and `electron/resources/server/` to `.gitignore`**

Append to `.gitignore`:
```
# PyInstaller build
build/pyinstaller/
electron/resources/server/

# Electron build
electron/dist/
electron/node_modules/
```

- [ ] **Step 4: Commit**

```bash
git add scripts/build_python.sh .gitignore
git commit -m "feat: add PyInstaller build script for Python server"
```

---

### Task 10: Verify build (optional — run Python bundle)

**Files:** None (build artifacts only)

**Goal:** Verify the PyInstaller binary works standalone — it can be done as a dry run to confirm the build pipeline is sound.

- [ ] **Step 1: Build the binary**

```bash
bash scripts/build_python.sh
```

Expected: PyInstaller completes without error. Output shows `electron/resources/server/server/server` (macOS executable).

- [ ] **Step 2: Quick-test the binary**

```bash
unset PORT
INTERPRETER_BASE_DIR=/tmp/test-interpreter electron/resources/server/server/server &
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5004/
kill %1
```

Expected: HTTP status 200.

---

### Scope Verification

| Spec Requirement | Covered By |
|-----------------|------------|
| Python data dir controlled by env var | Task 1 (config.py `basedir`) |
| .env fallback search (userData) | Task 1 (fallback path) |
| `create_app()` accepts `basedir` | Task 2 |
| Log path follows basedir | Task 2 |
| Safe dir creation (exist_ok) | Task 2 |
| PORT from env var | Task 3 |
| SIGTERM graceful shutdown | Task 3 |
| Host `127.0.0.1` only | Task 3 |
| DEBUG off in production | Task 3 |
| meetings/ stored in basedir | Task 4 |
| Electron main process | Task 6 |
| Port detection (conflict avoidance) | Task 6 |
| Python sidecar: dev (python3) + prod (binary) | Task 6 |
| Wait-for-server with timeout | Task 6 |
| Clean shutdown (SIGTERM→SIGKILL) | Task 6 |
| Native menu bar | Task 6 |
| First-time API key dialog | Task 6 |
| API Key save endpoint | Task 7 |
| Settings UI in web page | Task 8 |
| PyInstaller build script | Task 9 |
| electron-builder config | Task 5 (package.json) |
| macOS .dmg output | Task 2 (build step) |
