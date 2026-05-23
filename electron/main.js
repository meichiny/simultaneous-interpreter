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
    return path.join(process.resourcesPath, 'server', binaryName);
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

  const projectRoot = app.isPackaged ? app.getAppPath() : path.resolve(__dirname, '..');

  if (serverPath) {
    pythonProcess = spawn(serverPath, [], { env, stdio: ['ignore', 'pipe', 'pipe'] });
  } else {
    let pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python3');
    if (!app.isPackaged && fs.existsSync(venvPython)) {
      pythonCmd = venvPython;
    }
    pythonProcess = spawn(pythonCmd, ['wsgi.py'], {
      cwd: projectRoot,
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

// Suppress AudioContext.setSinkId / HTMLAudioElement.setSinkId errors
// that occur in Electron when passing 'default' as device ID
app.on('web-contents-created', (_event, wc) => {
  wc.on('dom-ready', async () => {
    await wc.executeJavaScript(`
      ['AudioContext','HTMLAudioElement'].forEach(function(cls) {
        var proto = window[cls]?.prototype;
        if (!proto || !proto.setSinkId) return;
        var orig = proto.setSinkId;
        proto.setSinkId = function(id) {
          return orig.call(this, id).catch(function(e) {
            console.warn(cls + '.setSinkId suppressed:', e.message);
          });
        };
      });
    `).catch(function() {});
  });
});
