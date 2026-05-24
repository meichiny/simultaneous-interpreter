# Electron Desktop Client UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Electron desktop client into a macOS-native-feeling app with a left sidebar, inline page navigation, and reorganized settings.

**Architecture:** Keep Flask server-side rendering unchanged. Restructure `index.html` into a SPA-like layout with sidebar + 4 inline page sections. Create a dedicated `main.css` for macOS-native dark theme. Adapt existing JS files to work in inline context. Minor Electron main process config change for `titleBarStyle`.

**Tech Stack:** Electron 33, Flask/Jinja2, Vanilla JS, CSS3

---

## File Map

| File | Change Type | Responsibility |
|------|-------------|----------------|
| `electron/main.js` | Modify | Add `titleBarStyle: 'hiddenInset'`, projection screen as BrowserWindow |
| `electron/preload.js` | Modify | Expose IPC for projection screen |
| `app/static/css/main.css` | **Create** | Complete macOS-native dark theme design system |
| `app/templates/index.html` | Modify | Sidebar + 4 inline page sections, remove old layout |
| `app/static/js/translator.js` | Modify | Sidebar navigation, config overview, updated labels |
| `app/static/js/glossary.js` | Modify | Adapt for inline rendering on index.html |
| `app/static/js/meetings.js` | Modify | Adapt for inline rendering on index.html |
| `app/static/js/logs.js` | Modify | Adapt for inline rendering under Settings tab |

---

### Task 1: Configure Electron window title bar

**Files:**
- Modify: `electron/main.js:121-132`
- Modify: `electron/preload.js`

**Goal:** Enable macOS `titleBarStyle: 'hiddenInset'` so traffic light buttons display while the title bar area is reclaimed by web content. No functionality changes.

- [ ] **Step 1: Update BrowserWindow options in main.js**

Find the `createWindow()` function and add `titleBarStyle` to the options:

```js
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    minWidth: 900, minHeight: 600,
    title: '同声传译',
    titleBarStyle: 'hiddenInset',   // ← add this line
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
  });
  // ... rest unchanged
}
```

- [ ] **Step 2: Verify dev mode works**

```bash
cd /Users/bengda0303/Desktop/ast-interpreter/simultaneous-interpreter
python3 wsgi.py &
cd electron
npm run dev
```

Expected: Electron window shows traffic light buttons at top-left, web content extends behind them. The red/yellow/green buttons work normally.

- [ ] **Step 3: Commit**

```bash
git add electron/main.js
git commit -m "feat: add titleBarStyle hiddenInset for macOS native feel"
```

---

### Task 2: Add projection screen as Electron BrowserWindow

**Files:**
- Modify: `electron/main.js`
- Modify: `electron/preload.js`

**Goal:** Replace `window.open('/display')` with an Electron BrowserWindow for the projection screen, providing a frameless fullscreen window.

- [ ] **Step 1: Add IPC handler and openDisplayWindow function in main.js**

Add after the `createWindow()` function (before `buildMenu()`):

```js
const { ipcMain, BrowserWindow } = require('electron'); // ensure BrowserWindow is already imported

let displayWindow = null;

function openDisplayWindow(port) {
  if (displayWindow && !displayWindow.isDestroyed()) {
    displayWindow.focus();
    return;
  }
  displayWindow = new BrowserWindow({
    width: 800,
    height: 600,
    fullscreenable: true,
    frame: false,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });
  displayWindow.loadURL(`http://127.0.0.1:${port}/display`);
  displayWindow.on('closed', () => { displayWindow = null; });
}

// Register IPC handler
ipcMain.handle('open-display', () => {
  if (actualPort) openDisplayWindow(actualPort);
});
```

Make `actualPort` accessible by declaring it at module level (it already is — line 11: `let actualPort = null;`).

- [ ] **Step 2: Update preload.js to expose the IPC channel**

Replace the current preload.js content:

```js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    electron: process.versions.electron,
    chrome: process.versions.chrome,
  },
  openDisplay: () => ipcRenderer.invoke('open-display'),
});
```

- [ ] **Step 3: Update main.js to pass port to renderer**

In `createWindow()`, after loading the URL, inject the port or pass it somehow. The simplest approach: pass port via the URL query param, or expose it via preload.

Actually, the port is already known. We can expose it via preload too:

```js
// in preload.js, add:
displayPort: null, // will be set by main process
```

Better approach: use `webContents.executeJavaScript` after page loads to set a global variable, or simply let the renderer use `window.opener.postMessage` like current. Since we're keeping the Flask `/display` route unchanged, the display window can still work with postMessage.

**Simplest approach:** Keep the "open display" button as a web UI button that uses `window.open('/display')` as before. Don't change this in the first iteration. The projection screen already works.

**Decision:** Skip this task for now — the current `window.open('/display')` approach works and changing it adds complexity without user-facing benefit. The `titleBarStyle` change in Task 1 is sufficient.

- [ ] **Step 4: Mark projection screen BrowserWindow as future work**

- [ ] **Step 5: Commit preload changes**

```bash
git add electron/preload.js
git commit -m "chore: update preload.js for future IPC use"
```

---

### Task 3: Create CSS design system

**Files:**
- Create: `app/static/css/main.css`

**Goal:** Define the complete macOS-native dark theme design system as CSS custom properties. All visual styles for the redesigned UI go here.

- [ ] **Step 1: Write `app/static/css/main.css`**

```css
/* =========================================
   Electron Desktop Client — Design System
   macOS-native dark theme
   ========================================= */

/* --- CSS Custom Properties --- */
:root {
  /* Backgrounds */
  --bg-app: #1a1a1a;
  --bg-sidebar: rgba(30, 30, 30, 0.85);
  --bg-card: #222222;
  --bg-input: #2a2a2a;
  --bg-hover: rgba(255, 255, 255, 0.06);

  /* Borders */
  --border: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.15);

  /* Accent */
  --accent: #3b82f6;
  --accent-hover: #2563eb;
  --accent-muted: rgba(59, 130, 246, 0.15);

  /* Text */
  --text-primary: #f0f0f0;
  --text-secondary: #999999;
  --text-muted: #666666;

  /* Status */
  --green: #34d399;
  --yellow: #fbbf24;
  --red: #f87171;

  /* Spacing & Sizing */
  --sidebar-width: 60px;
  --titlebar-height: 32px;
  --statusbar-height: 32px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
}

/* --- Reset --- */
*, *::before, *::after { box-sizing: border-box; }
html, body {
  height: 100%; margin: 0; overflow: hidden;
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  background-color: var(--bg-app);
  color: var(--text-primary);
  font-size: 12px;
  -webkit-font-smoothing: antialiased;
}

/* --- Layout Container --- */
.app-layout {
  display: flex;
  height: 100vh;
  padding-top: 38px; /* macOS traffic light area */
}

/* --- Left Sidebar --- */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-sidebar);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 12px;
  gap: 4px;
  z-index: 10;
}

.sidebar-item {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 18px;
  transition: all 0.15s ease;
  position: relative;
  user-select: none;
}

.sidebar-item:hover {
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.sidebar-item.active {
  color: var(--text-primary);
  background: var(--accent-muted);
}

.sidebar-item.active::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}

.sidebar-label {
  font-size: 9px;
  color: var(--text-muted);
  text-align: center;
  margin-top: -2px;
}

/* --- Main Content Area --- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.page-header {
  height: var(--titlebar-height);
  min-height: var(--titlebar-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border);
  background: var(--bg-app);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

/* --- Page Visibility --- */
.page { display: none; }
.page.active { display: flex; flex-direction: column; height: 100%; }

/* --- Settings Tabs --- */
.settings-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}

.settings-tab {
  padding: 8px 16px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s ease;
  user-select: none;
}

.settings-tab:hover {
  color: var(--text-primary);
}

.settings-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.settings-panel { display: none; }
.settings-panel.active { display: block; }

/* --- Form Controls --- */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

select, .form-input {
  width: 100%;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border);
  padding: 8px 10px;
  border-radius: var(--radius-md);
  font-size: 12px;
  transition: border-color 0.15s ease;
}

select:focus, .form-input:focus {
  border-color: var(--accent);
  outline: none;
}

input[type="color"] {
  width: 100%;
  height: 32px;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: 0;
}

input[type="checkbox"] {
  accent-color: var(--accent);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
  user-select: none;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
}

/* --- Config Overview Card --- */
.config-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 20px;
}

.config-card-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.config-row + .config-row {
  border-top: 1px solid var(--border);
  margin-top: 4px;
  padding-top: 8px;
}

.config-label {
  color: var(--text-secondary);
  min-width: 80px;
  flex-shrink: 0;
}

.config-value {
  color: var(--text-primary);
  font-weight: 500;
}

/* --- Start Button --- */
.start-btn-container {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.btn-start {
  background: var(--accent);
  color: white;
  border: none;
  padding: 12px 48px;
  border-radius: var(--radius-lg);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
}

.btn-start:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.btn-start:disabled {
  background: var(--bg-input);
  color: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* --- Running State Top Bar --- */
.running-bar {
  height: 36px;
  min-height: 36px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid var(--border);
  font-size: 11px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-dot.green { background: var(--green); }
.status-dot.yellow { background: var(--yellow); }
.status-dot.red { background: var(--red); }

.running-bar .stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.running-bar .spacer {
  flex: 1;
}

/* --- Translation Pane --- */
.translation-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 12px;
  gap: 12px;
}

.translation-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.translation-pane.active-green {
  border-color: var(--green);
  background: rgba(16, 185, 129, 0.03);
}

.translation-pane.active-yellow {
  border-color: var(--yellow);
  background: rgba(245, 158, 11, 0.03);
}

.pane-header {
  padding: 6px 12px;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  letter-spacing: 0.3px;
}

.pane-tag {
  opacity: 0;
  transition: opacity 0.2s;
  font-weight: 800;
}

.translation-pane.active-green .pane-tag { opacity: 1; color: var(--green); }
.translation-pane.active-yellow .pane-tag { opacity: 1; color: var(--yellow); }

.pane-split {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pane-trans {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px 6px;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  line-height: 1.5;
  word-wrap: break-word;
}

.pane-orig {
  flex: 1;
  overflow-y: auto;
  padding: 6px 12px 10px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  word-wrap: break-word;
}

.pane-divider {
  height: 1px;
  background: var(--border);
  margin: 0 12px;
  flex-shrink: 0;
}

/* --- Single Channel Mode --- */
.translation-container.single-channel .translation-pane#pane-speak {
  flex: 1;
  width: 100%;
}

.translation-container.single-channel .translation-pane#pane-listen {
  display: none;
}

/* --- Log Viewer (in Settings) --- */
.log-viewer {
  font-family: "SF Mono", "Consolas", monospace;
  font-size: 11px;
  line-height: 1.5;
}

.log-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.log-filter-select {
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
}

.log-search-input {
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  flex: 1;
  min-width: 120px;
}

.log-content {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  height: 400px;
  overflow-y: auto;
}

.log-item {
  margin-bottom: 4px;
  line-height: 1.4;
  word-break: break-word;
}

.log-time { color: var(--text-muted); margin-right: 6px; }
.log-level-info { color: var(--green); }
.log-level-warning { color: var(--yellow); }
.log-level-error { color: var(--red); }
.log-level-debug { color: var(--text-muted); }
.log-channel { color: var(--accent); margin-right: 4px; }

/* --- Glossary Inline --- */
.glossary-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.glossary-categories {
  width: 200px;
  min-width: 200px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  overflow-y: auto;
}

.glossary-terms {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  overflow-y: auto;
}

.glossary-editor {
  width: 300px;
  min-width: 300px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
  overflow-y: auto;
}

/* --- Meetings Inline --- */
.meetings-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.meetings-list {
  width: 280px;
  min-width: 280px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  overflow-y: auto;
}

.meetings-transcript {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  overflow-y: auto;
}

/* --- Scrollbar Styling --- */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
```

- [ ] **Step 2: Verify CSS syntax**

Run: `npx stylelint app/static/css/main.css` (if stylelint available) or just visually inspect.

Expected: No syntax errors.

- [ ] **Step 3: Commit**

```bash
git add app/static/css/main.css
git commit -m "feat: add macOS-native dark theme CSS design system"
```

---

### Task 4: Restructure index.html

**Files:**
- Modify: `app/templates/index.html`

**Goal:** Add sidebar HTML, inline page sections, settings tabs. Remove old 4-card layout, header nav, runtime log sidebar, settings modal. Link new CSS file.

- [ ] **Step 1: Read current index.html**

```bash
cat app/templates/index.html | wc -l
```
Expected: ~716 lines

- [ ] **Step 2: Add new CSS link in `<head>`**

After the existing `<style>` block (or replacing it), add:
```html
<link rel="stylesheet" href="/static/css/main.css">
```
Keep only essential existing CSS that is NOT covered by main.css (e.g., animations, channel-specific styles). Remove all layout/color/typography styles that are now in main.css.

- [ ] **Step 3: Build the new HTML structure**

Replace the entire `<body>` content with:

```html
<body>
  <div class="app-layout">
    <!-- Left Sidebar -->
    <div class="sidebar">
      <div class="sidebar-item active" data-page="translate" onclick="switchPage('translate')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      </div>
      <div class="sidebar-item" data-page="glossary" onclick="switchPage('glossary')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
      </div>
      <div class="sidebar-item" data-page="meetings" onclick="switchPage('meetings')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
      </div>
      <div class="sidebar-item" data-page="settings" onclick="switchPage('settings')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="main-area" id="mainArea">
      <!-- Page: Translate -->
      <div class="page active" id="page-translate">
        <div class="page-header">翻译 / Translate</div>
        <div class="page-content" id="translate-content">
          <!-- Config Overview (stopped state) -->
          <div id="translate-stopped">
            <div class="config-card">
              <div class="config-card-title">当前配置 / Configuration</div>
              <div class="config-row"><span class="config-label">语言方向</span><span class="config-value" id="ov-language">中文 → 英语</span></div>
              <div class="config-row"><span class="config-label">通道模式</span><span class="config-value" id="ov-channel">单通道</span></div>
              <div class="config-row"><span class="config-label">麦克风</span><span class="config-value" id="ov-mic">未选择</span></div>
              <div class="config-row"><span class="config-label">术语库</span><span class="config-value" id="ov-glossary">未选择</span></div>
              <div class="config-row" style="border-top-color: var(--border-strong); margin-top: 8px; padding-top: 12px;">
                <span class="config-label">服务器</span>
                <span class="config-value" id="ov-server"><span class="status-dot yellow" style="display:inline-block;margin-right:6px;vertical-align:middle"></span>连接中...</span>
              </div>
              <div class="config-row"><span class="config-label">API 密钥</span><span class="config-value" id="ov-apikey">未配置</span></div>
            </div>

            <div class="start-btn-container">
              <button class="btn-start" id="startBtn" disabled>▶ 开始运行 / Start</button>
            </div>

            <div style="text-align:center;color:var(--text-muted);font-size:11px;padding:20px;">
              开始后将在此显示翻译内容
            </div>
          </div>

          <!-- Running state -->
          <div id="translate-running" style="display:none;flex:1;display:none;flex-direction:column;">
            <div class="running-bar" id="running-bar">
              <span class="status-dot green" id="run-status-dot"></span>
              <span class="stat-item" id="run-status-text">运行中 / Running</span>
              <span class="stat-item" style="border-left:1px solid var(--border);padding-left:12px;">
                <span id="run-latency">-- ms</span>
              </span>
              <span class="stat-item">
                <span id="run-billing">-- tokens</span>
              </span>
              <span class="spacer"></span>
              <button class="btn btn-secondary" onclick="openDisplayWindow()" style="font-size:10px;padding:4px 10px;">📺 打开投屏</button>
              <button class="btn btn-secondary" onclick="stopSession()" style="font-size:10px;padding:4px 10px;color:var(--red);">停止 / Stop</button>
            </div>

            <div class="translation-container" id="translation-container">
              <div class="translation-pane" id="pane-speak">
                <div class="pane-header">
                  <span>音源 / Audio Source</span>
                  <span class="pane-tag">正在听 / LISTENING</span>
                </div>
                <div class="pane-split">
                  <div class="pane-trans" id="pane-trans-speak"><span class="pending-text" id="pending-trans-speak">...</span></div>
                  <div class="pane-divider"></div>
                  <div class="pane-orig" id="pane-orig-speak"><span class="pending-text" id="pending-orig-speak" style="font-size:11px;">Ready</span></div>
                </div>
              </div>
              <div class="translation-pane" id="pane-listen">
                <div class="pane-header">
                  <span>他人发言 / OTHERS</span>
                  <span class="pane-tag">正在读 / PLAYING</span>
                </div>
                <div class="pane-split">
                  <div class="pane-trans" id="pane-trans-listen"><span class="pending-text" id="pending-trans-listen">...</span></div>
                  <div class="pane-divider"></div>
                  <div class="pane-orig" id="pane-orig-listen"><span class="pending-text" id="pending-orig-listen" style="font-size:11px;">Ready</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Page: Glossary -->
      <div class="page" id="page-glossary">
        <div class="page-header">术语管理 / Glossary</div>
        <div class="page-content">
          <div class="glossary-layout">
            <div class="glossary-categories" id="glossary-categories">
              <!-- Category tree loaded by glossary.js -->
            </div>
            <div class="glossary-terms" id="glossary-terms">
              <!-- Term list loaded by glossary.js -->
            </div>
            <div class="glossary-editor" id="glossary-editor">
              <!-- Term editor loaded by glossary.js -->
            </div>
          </div>
        </div>
      </div>

      <!-- Page: Meetings -->
      <div class="page" id="page-meetings">
        <div class="page-header">会议记录 / Meetings</div>
        <div class="page-content">
          <div class="meetings-layout">
            <div class="meetings-list" id="meetings-list">
              <!-- Meeting list loaded by meetings.js -->
            </div>
            <div class="meetings-transcript" id="meetings-transcript">
              <!-- Transcript viewer loaded by meetings.js -->
            </div>
          </div>
        </div>
      </div>

      <!-- Page: Settings -->
      <div class="page" id="page-settings">
        <div class="page-header">设置 / Settings</div>
        <div class="page-content">
          <div class="settings-tabs" id="settings-tabs">
            <div class="settings-tab active" onclick="switchSettingsTab('lang')">语言</div>
            <div class="settings-tab" onclick="switchSettingsTab('audio')">音频</div>
            <div class="settings-tab" onclick="switchSettingsTab('display')">显示</div>
            <div class="settings-tab" onclick="switchSettingsTab('logs')">日志</div>
            <div class="settings-tab" onclick="switchSettingsTab('account')">账户</div>
          </div>

          <!-- Language Tab -->
          <div class="settings-panel active" id="settings-lang">
            <!-- language settings content from old card 1 -->
            <div class="form-group">
              <label class="form-label">我说的 / My Speak</label>
              <select id="lang-my-speak">
                <option value="zh" selected>中文 Chinese</option>
                <option value="en">英语 English</option>
                <option value="ja">日语 Japanese</option>
                <option value="fr">法语 French</option>
                <option value="de">德语 German</option>
                <option value="es">西语 Spanish</option>
                <option value="pt">葡语 Portuguese</option>
                <option value="id">印尼语 Indonesian</option>
                <option value="zhen">中英混说 Mixed</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" style="color:var(--accent)">对方听到的 / Their Hear</label>
              <select id="lang-their-hear">
                <option value="en" selected>英语 English</option>
                <option value="zh">中文 Chinese</option>
                <option value="ja">日语 Japanese</option>
                <option value="fr">法语 French</option>
                <option value="de">德语 German</option>
                <option value="es">西语 Spanish</option>
                <option value="pt">葡语 Portuguese</option>
                <option value="id">印尼语 Indonesian</option>
                <option value="zhen">中英混说 Mixed</option>
              </select>
            </div>
            <div style="border-top:1px solid var(--border);padding-top:16px;margin-top:16px;">
              <div class="form-group">
                <label class="form-label">对方说的 / Their Speak</label>
                <select id="lang-their-speak">
                  <option value="en" selected>英语 English</option>
                  <option value="zh">中文 Chinese</option>
                  <option value="ja">日语 Japanese</option>
                  <option value="fr">法语 French</option>
                  <option value="de">德语 German</option>
                  <option value="es">西语 Spanish</option>
                  <option value="pt">葡语 Portuguese</option>
                  <option value="id">印尼语 Indonesian</option>
                  <option value="zhen">中英混说 Mixed</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label" style="color:var(--accent)">我希望听到的 / My Hear</label>
                <select id="lang-my-hear">
                  <option value="zh" selected>中文 Chinese</option>
                  <option value="en">英语 English</option>
                  <option value="ja">日语 Japanese</option>
                  <option value="fr">法语 French</option>
                  <option value="de">德语 German</option>
                  <option value="es">西语 Spanish</option>
                  <option value="pt">葡语 Portuguese</option>
                  <option value="id">印尼语 Indonesian</option>
                  <option value="zhen">中英混说 Mixed</option>
                </select>
              </div>
            </div>
            <div style="border-top:1px solid var(--border);padding-top:16px;margin-top:16px;">
              <div class="form-group">
                <label class="form-label">我的输出音色 / My Voice</label>
                <select id="voice-speak">
                  <option value="">本人音色（克隆） / Clone</option>
                  <option value="zh_female_vv_uranus_bigtts">预设女声（推荐） / Female</option>
                  <option value="zh_male_jingqiangkanye_emo_mars_bigtts">预设男声（推荐） / Male</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">对方输出音色 / Their Voice</label>
                <select id="voice-listen">
                  <option value="">本人音色（克隆） / Clone</option>
                  <option value="zh_female_vv_uranus_bigtts">预设女声（推荐） / Female</option>
                  <option value="zh_male_jingqiangkanye_emo_mars_bigtts">预设男声（推荐） / Male</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Audio Tab -->
          <div class="settings-panel" id="settings-audio">
            <div class="form-group">
              <label class="form-label">通道模式 / Channel Mode</label>
              <select id="channel-mode" onchange="onChannelModeChange()">
                <option value="single" selected>单通道 / Single (仅麦克风输入)</option>
                <option value="dual">双通道 / Dual (需要虚拟声卡)</option>
              </select>
            </div>
            <div id="single-channel-tip" class="config-card" style="border-color:var(--green);">
              <div style="color:var(--green);font-weight:bold;margin-bottom:5px;font-size:12px;">当前模式：单通道 / Single Channel</div>
              <div style="font-size:11px;color:var(--text-secondary);">只需真实麦克风，无需安装虚拟声卡。适合单向翻译场景（如演讲）。</div>
            </div>
            <div id="dual-channel-tip" class="config-card" style="border-color:var(--yellow);display:none;">
              <div style="color:var(--yellow);font-weight:bold;margin-bottom:5px;font-size:12px;">当前模式：双通道 / Dual Channel</div>
              <div style="font-size:11px;color:var(--text-secondary);">需要安装 VB-Cable 虚拟声卡。适合双向对话场景（如会议）。</div>
              <div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;">
                <div>Cable A (输出到会议): <span id="cable-a-status">检测中...</span></div>
                <div>Cable B (从会议输入): <span id="cable-b-status">检测中...</span></div>
              </div>
            </div>
            <div class="form-group"><label class="form-label">麦克风 / Input (Mic)</label><select id="dev-real-mic"><option>扫描中...</option></select></div>
            <div class="form-group" id="speaker-output-group"><label class="form-label">耳机 / Output (Speaker)</label><select id="dev-real-spk"><option>扫描中...</option></select></div>
            <div class="form-group" style="border-top:1px solid var(--border);padding-top:16px;">
              <label class="form-label">语音输出 / TTS Output</label>
              <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;">
                <input type="checkbox" id="tts-enable" checked onchange="onTtsToggle()">
                <span>启用语音播放 / Enable TTS</span>
              </label>
            </div>
            <div class="form-group">
              <button class="btn btn-secondary" onclick="calibrateNoise()">⚡ 智能校准 / Auto Calibrate</button>
              <div style="font-size:10px;color:var(--text-muted);margin-top:4px;">校准请保持安静 / Please keep silent during calibration</div>
            </div>
            <div class="config-card" style="margin-top:12px;">
              <div class="config-card-title">内部路由检测 / Routing Check</div>
              <div class="config-row"><span class="config-label">AI 听 (In)</span><span id="status-cable-b" class="config-value">扫描中...</span></div>
              <div class="config-row"><span class="config-label">AI 说 (Out)</span><span id="status-cable-a" class="config-value">扫描中...</span></div>
            </div>
          </div>

          <!-- Display Tab -->
          <div class="settings-panel" id="settings-display">
            <div class="form-group">
              <label class="form-label">字号 / Font Size <span style="color:var(--text-muted);font-size:10px;">10-72</span></label>
              <input type="number" id="display-font-size" value="24" min="10" max="72" class="form-input" onchange="updateDisplaySetting('fontSize', this.value)">
            </div>
            <div class="form-group">
              <label class="form-label">行高 / Line Height <span style="color:var(--text-muted);font-size:10px;">1.0-3.0</span></label>
              <input type="number" id="display-line-height" value="1.6" min="1" max="3" step="0.1" class="form-input" onchange="updateDisplaySetting('lineHeight', this.value)">
            </div>
            <div class="form-group">
              <label class="form-label">译文颜色 / Trans Color</label>
              <input type="color" id="display-trans-color" value="#ffffff" oninput="updateDisplaySetting('transColor', this.value)">
            </div>
            <div class="form-group">
              <label class="form-label">原文颜色 / Orig Color</label>
              <input type="color" id="display-orig-color" value="#b3b3b3" oninput="updateDisplaySetting('origColor', this.value)">
            </div>
            <div class="form-group">
              <label class="form-label">背景颜色 / Background</label>
              <input type="color" id="display-bg-color" value="#000000" oninput="updateDisplaySetting('bgColor', this.value)">
            </div>
            <div class="form-group">
              <label class="form-label">背景透明度 / Opacity</label>
              <select id="display-bg-opacity" class="form-input" onchange="updateDisplaySetting('bgOpacity', this.value)">
                <option value="0">0% (完全透明)</option>
                <option value="20">20%</option>
                <option value="40">40%</option>
                <option value="60">60%</option>
                <option value="80">80%</option>
                <option value="100" selected>100% (不透明)</option>
              </select>
            </div>
            <div style="display:flex;gap:8px;">
              <button class="btn btn-secondary" onclick="resetDisplaySettings()" style="flex:1;">重置默认 / Reset</button>
              <button class="btn btn-secondary" onclick="previewDisplaySettings()" style="flex:1;">预览 / Preview</button>
            </div>
          </div>

          <!-- Logs Tab -->
          <div class="settings-panel" id="settings-logs">
            <!-- Log viewer loaded by logs.js -->
          </div>

          <!-- Account Tab -->
          <div class="settings-panel" id="settings-account">
            <div class="form-group">
              <label class="form-label">VOLCANO_APP_KEY</label>
              <input id="settings-app-key" type="password" class="form-input" placeholder="输入 API Key" />
            </div>
            <div id="settings-status" style="display:none;padding:8px 12px;border-radius:var(--radius-md);font-size:11px;margin-bottom:12px;"></div>
            <div class="form-group">
              <button class="btn btn-primary" onclick="saveSettings()">保存 / Save</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <audio id="player-for-cable-a" style="display:none"></audio>
  <audio id="player-for-headset" style="display:none"></audio>

  <script src="/static/vad/ort.js"></script>
  <script src="/static/vad/my_vad.js"></script>
  <script src="/static/js/utils.js"></script>
  <script src="/static/js/translator.js"></script>
  <script src="/static/js/glossary.js"></script>
  <script src="/static/js/meetings.js"></script>
  <script src="/static/js/logs.js"></script>

  <script>window.__HAS_API_KEY__ = {{ 'true' if has_api_key else 'false' }};</script>
</body>
```

**Key removals from old index.html:**
- `.header` (old nav bar with logo + buttons)
- `.main-body` (old 4-column card layout: #card-lang, #card-audio, #card-glossary, #card-display)
- `.footer` (old footer with status + start/stop)
- `#section-dashboard` wrapper
- `#section-action` (old action mode)
- `.log-sidebar` and `.log-toggle-btn`
- `#settings-modal` (old modal)
- All old inline CSS that is now in main.css (keep only animation keyframes and channel-specific styles not covered)

- [ ] **Step 4: Verify HTML renders**

```bash
python3 wsgi.py
```
Open `http://127.0.0.1:5004/`. Expected: Sidebar visible, translate page shows config overview, Start button disabled. No JS errors yet (functions will be added in next task).

- [ ] **Step 5: Commit**

```bash
git add app/templates/index.html
git commit -m "feat: restructure index.html with sidebar and inline page sections"
```

---

### Task 5: Update translator.js — navigation, config overview, running view

**Files:**
- Modify: `app/static/js/translator.js`

**Goal:** Add sidebar page switching, config overview rendering, update running view labels, remove settings modal functions.

- [ ] **Step 1: Add page switching function**

Add to the global scope (outside the IIFE if it's inside one):
```js
// --- Sidebar Navigation ---
function switchPage(pageName) {
  // Update sidebar items
  document.querySelectorAll('.sidebar-item').forEach(item => {
    item.classList.toggle('active', item.dataset.page === pageName);
  });
  // Update pages
  document.querySelectorAll('.page').forEach(page => {
    page.classList.toggle('active', page.id === 'page-' + pageName);
  });
}

// --- Settings Tab Switching ---
function switchSettingsTab(tabName) {
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.classList.toggle('active', tab.textContent.includes(tabName) || tab.dataset.tab === tabName);
  });
  document.querySelectorAll('.settings-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === 'settings-' + tabName);
  });
}
```

Note: For `.settings-tab`, the matching by `tabName` against text content is fragile. Better approach: add `data-tab` attributes:

In index.html, change settings tabs from `onclick="switchSettingsTab('lang')"` to add `data-tab="lang"`:
```html
<div class="settings-tab active" data-tab="lang" onclick="switchSettingsTab('lang')">语言</div>
<div class="settings-tab" data-tab="audio" onclick="switchSettingsTab('audio')">音频</div>
<div class="settings-tab" data-tab="display" onclick="switchSettingsTab('display')">显示</div>
<div class="settings-tab" data-tab="logs" onclick="switchSettingsTab('logs')">日志</div>
<div class="settings-tab" data-tab="account" onclick="switchSettingsTab('account')">账户</div>
```

And update switchSettingsTab:
```js
function switchSettingsTab(tabName) {
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.tab === tabName);
  });
  document.querySelectorAll('.settings-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === 'settings-' + tabName);
  });
}
```

- [ ] **Step 2: Update config overview on page load and settings change**

Add a function to refresh the config overview:
```js
function updateConfigOverview() {
  const mySpeak = document.getElementById('lang-my-speak');
  const theirHear = document.getElementById('lang-their-hear');
  if (mySpeak && theirHear) {
    document.getElementById('ov-language').textContent =
      mySpeak.options[mySpeak.selectedIndex].text.split(' ')[0] + ' → ' +
      theirHear.options[theirHear.selectedIndex].text.split(' ')[0];
  }

  const channelMode = document.getElementById('channel-mode');
  if (channelMode) {
    document.getElementById('ov-channel').textContent =
      channelMode.value === 'single' ? '单通道' : '双通道';
  }

  const mic = document.getElementById('dev-real-mic');
  if (mic && mic.value) {
    document.getElementById('ov-mic').textContent = mic.options[mic.selectedIndex]?.text || '未选择';
  }

  // Glossary status
  updateGlossaryOverview();

  // Server status
  updateServerStatus();

  // API key status
  const hasKey = window.__HAS_API_KEY__;
  document.getElementById('ov-apikey').textContent = hasKey ? '✅ 已配置' : '❌ 未配置';
}
```

Call `updateConfigOverview()` after the app initializes and whenever settings change (add event listeners to settings selects).

- [ ] **Step 3: Update running view labels**

The current code uses `#section-action` with `#ab-speak` and `#ab-listen`. With the new structure, the translation panes are `#pane-speak` and `#pane-listen`. Update the session start/stop logic to work with the new DOM structure.

Find the code that shows/hides `#section-dashboard` and `#section-action` and replace with code that shows/hides `#translate-stopped` and `#translate-running`:

```js
// Show running state
document.getElementById('translate-stopped').style.display = 'none';
document.getElementById('translate-running').style.display = 'flex';

// Show stopped state
document.getElementById('translate-stopped').style.display = 'block';
document.getElementById('translate-running').style.display = 'none';
```

- [ ] **Step 4: Remove settings modal functions**

Remove `showSettingsModal()`, `hideSettingsModal()`, `saveSettings()` from the IIFE. The `saveSettings()` function is retained but should be moved to work with the new inline form (the input ID `settings-app-key` stays the same).

- [ ] **Step 5: Channel mode switching**

Update `onChannelModeChange()` to toggle between single/dual channel in the new DOM:
```js
function onChannelModeChange() {
  const mode = document.getElementById('channel-mode').value;
  const container = document.getElementById('translation-container');
  if (mode === 'single') {
    container.classList.add('single-channel');
  } else {
    container.classList.remove('single-channel');
  }
  // Show/hide tips
  document.getElementById('single-channel-tip').style.display = mode === 'single' ? 'block' : 'none';
  document.getElementById('dual-channel-tip').style.display = mode === 'dual' ? 'block' : 'none';
  document.getElementById('speaker-output-group').style.display = mode === 'dual' ? 'block' : 'none';
}
```

- [ ] **Step 6: Add openDisplayWindow function**

The current code uses `window.open('/display')`. Add a fallback that also checks `window.electronAPI?.openDisplay`:
```js
function openDisplayWindow() {
  if (window.electronAPI?.openDisplay) {
    window.electronAPI.openDisplay();
  } else {
    window.open('/display', 'projection', 'width=800,height=600');
  }
}
```

- [ ] **Step 7: Verify JS works**

```bash
python3 wsgi.py
```
Open `http://127.0.0.1:5004/`. Expected:
- Sidebar items switch pages correctly
- Config overview shows current settings
- Clicking Start shows running view
- Clicking Stop returns to stopped state
- Settings tabs switch correctly
- Audio tab channel mode switching works

- [ ] **Step 8: Commit**

```bash
git add app/static/js/translator.js
git commit -m "feat: update translator.js with sidebar navigation and new layout"
```

---

### Task 6: Adapt glossary.js and meetings.js for inline rendering

**Files:**
- Modify: `app/static/js/glossary.js`
- Modify: `app/static/js/meetings.js`

**Goal:** Make these JS files work when loaded on `index.html` instead of their standalone pages. The DOM element IDs remain the same, but the parent page structure changes.

- [ ] **Step 1: Read current glossary.js**

```bash
wc -l app/static/js/glossary.js
```

Check if the file uses `document.getElementById` or `document.querySelector` with IDs that exist in the new glossary section of index.html. The new glossary section uses:
- `#glossary-categories` (category tree)
- `#glossary-terms` (term list)
- `#glossary-editor` (term editor)

If the original glossary.html uses different IDs, map them. For example, if glossary.html uses `<div id="categories">`, it should be updated to `#glossary-categories`.

The strategy: glossary.js is already loaded at the bottom of index.html (added in Task 4). It should work if the DOM elements it references are present. The key change is that glossary.js should only initialize its page when the glossary page is shown (lazy init). Add a check:

```js
// At the top of glossary.js initialization code
if (!document.getElementById('glossary-categories')) return; // Not on this page
```

- [ ] **Step 2: Verify glossary page works inline**

```bash
python3 wsgi.py
```
Open `http://127.0.0.1:5004/`. Click Glossary in sidebar. Expected: Category tree and terms load correctly.

- [ ] **Step 3: Read current meetings.js**

Same approach as glossary.js. Check DOM element IDs match. The new meetings section uses:
- `#meetings-list`
- `#meetings-transcript`

- [ ] **Step 4: Verify meetings page works inline**

```bash
python3 wsgi.py
```
Open `http://127.0.0.1:5004/`. Click Meetings in sidebar. Expected: Meeting list loads.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/glossary.js app/static/js/meetings.js
git commit -m "feat: adapt glossary.js and meetings.js for inline rendering"
```

---

### Task 7: Adapt logs.js for Settings tab

**Files:**
- Modify: `app/static/js/logs.js`

**Goal:** Make the log viewer work when loaded inside the Settings → 日志 tab instead of the standalone `/logs` page.

- [ ] **Step 1: Read current logs.js**

```bash
wc -l app/static/js/logs.js
```

The logs.js file needs to render its content into `#settings-logs` div. If it currently expects to be on a standalone page with `<body>` containing the log HTML, we need to change it to render into the settings-logs panel.

The simplest approach: logs.js detects whether it's on the standalone page or inline. On the standalone page, it renders full-page. On inline, it renders within `#settings-logs`.

```js
// At initialization
const container = document.getElementById('settings-logs') || document.body;
// Render log toolbar and content into container
```

- [ ] **Step 2: Verify logs tab works**

```bash
python3 wsgi.py
```
Open `http://127.0.0.1:5004/`. Click Settings → 日志. Expected: Log viewer with filters, search, log entries.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/logs.js
git commit -m "feat: adapt logs.js for inline rendering in Settings tab"
```

---

### Task 8: Final integration verification

**Files:** None (testing only)

**Goal:** Verify the complete application works end-to-end.

- [ ] **Step 1: Start the application in Electron dev mode**

Terminal 1:
```bash
python3 wsgi.py
```

Terminal 2:
```bash
cd electron && npm run dev
```

- [ ] **Step 2: Verify all pages work**
- Translate page: config overview loads, Start button works, running view shows translation output, Stop returns to stopped state ✅
- Glossary page: category tree and terms load ✅
- Meetings page: meeting list and transcript load ✅
- Settings → 语言: language direction selects change ✅
- Settings → 音频: channel mode switching, device scanning ✅
- Settings → 显示: display settings changes ✅
- Settings → 日志: log viewer with filters, search ✅
- Settings → 账户: API key save (if credentials exist in .env) ✅

- [ ] **Step 3: Verify macOS titleBarStyle**
- Traffic light buttons visible at top-left ✅
- Content extends behind title bar area ✅
- Window controls (minimize/maximize/close) work ✅

- [ ] **Step 4: Verify old routes still work (backward compatibility)**
- `/glossary` — loads standalone glossary page ✅
- `/meetings` — loads standalone meetings page ✅
- `/logs` — loads standalone log viewer ✅
- `/display` — loads projection screen ✅

- [ ] **Step 5: Verify no console errors**
Open DevTools (Cmd+Opt+I) and check Console tab. Fix any errors.

- [ ] **Step 6: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: final integration fixes"
```

---

## Scope Verification

| Spec Section | Task |
|-------------|------|
| §2 Window Configuration (titleBarStyle) | Task 1 |
| §3 Overall Layout (sidebar + main area) | Task 4 |
| §3.1 Left Sidebar | Task 4 (HTML) + Task 5 (JS nav) |
| §3.2 Main Content Area | Task 4 |
| §3.3 Bottom Status Bar | Task 4 (simplified — status in running bar) |
| §4 Navigation & Page Organization | Task 5 (switchPage) |
| §4.2 Glossary inline | Task 6 |
| §4.3 Meetings inline | Task 6 |
| §5.1 Translate Stopped State (config overview) | Task 5 |
| §5.2 Single Channel Running State | Task 4 (HTML) + Task 5 (JS labels) |
| §5.3 Dual Channel Running State | Task 4 (HTML) + Task 5 (JS) |
| §5.4 Projection Screen | Task 2 (partial — window.open fallback) |
| §6 Settings Page (5 tabs) | Task 4 (HTML) + Task 5 (tab switching) |
| §6.2 Language Tab | Task 4 |
| §6.3 Audio Tab | Task 4 |
| §6.4 Display Tab | Task 4 |
| §6.5 Logs Tab | Task 7 |
| §6.6 Account Tab | Task 4 + retained saveSettings() |
| §7 Visual Design System (main.css) | Task 3 |
