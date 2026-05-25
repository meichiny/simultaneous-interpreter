# Electron Desktop Client UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Electron desktop client into a macOS-native-feeling app with a left sidebar, 5 inline page sections (翻译/会话设置/词库/会议/设置), and centralized session configuration.

**Architecture:** Keep Flask server-side rendering unchanged. Restructure `index.html` into a SPA-like layout with sidebar + 5 inline page sections. Move all session-related settings (language, audio, glossary, display) out of Settings tabs into a dedicated "会话设置" page. Simplify Settings to only Account + Logs.

**Tech Stack:** Electron 33, Flask/Jinja2, Vanilla JS, CSS3

---

## File Map

| File | Change Type | Responsibility |
|------|-------------|----------------|
| `electron/main.js` | Already done | Add `titleBarStyle: 'hiddenInset'` |
| `app/static/css/main.css` | Already done | macOS-native dark theme design system |
| `app/templates/index.html` | **Modify** | 5-page sidebar; add session config page; simplify settings (account + logs only, no tabs); translate page stays as pure read-only |
| `app/static/js/translator.js` | Modify | Add `loadGlossary()` glossary selection into session config page; wire glossary checkbox changes to `#ov-glossary`; preserve all existing functions |
| `app/static/js/glossary.js` | Already adapted | Guard checks for inline rendering |
| `app/static/js/meetings.js` | Already adapted | Guard checks for inline rendering |
| `app/static/js/logs.js` | Already adapted | Dual standalone/inline mode |

---

### Task 1: Configure Electron window title bar

**Already completed.** See previous commit.

---

### Task 2: Restructure index.html — session config page + simplified settings

**Files:**
- Modify: `app/templates/index.html`

**Goal:** Add 5th sidebar item for session config, create session config page with 4 sections (语言/音频/术语库/投屏样式), simplify settings page to account + logs (no tabs), keep translate page as read-only overview.

- [ ] **Step 1: Update sidebar to 5 items**

Change sidebar from 4 items to 5:
```
1. 🎤 翻译 (translate) — default, active
2. ⚙ 会话设置 (session) — NEW
3. 📖 词库 (glossary)
4. 📋 会议 (meetings)
5. 🔑 设置 (settings) — simplified
```

Each sidebar item structure:
```html
<div class="sidebar-item" data-page="session" onclick="switchPage('session')">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
  <span class="sidebar-label">会话设置</span>
</div>
```

Icons for each sidebar item:
- 翻译 (translate) — globe/translate icon
- 会话设置 (session) — gear/settings icon
- 词库 (glossary) — book icon
- 会议 (meetings) — monitor icon
- 设置 (settings) — key/lock icon

- [ ] **Step 2: Add session config page (`#page-session`)**

Insert between translate page and glossary page. 4 sections in `<div class="page-content">`:

**Section 1: 语言 / Language**
```
<div class="form-section">
  <div class="form-section-title">语言 / Language</div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">我说的 / My Speak</label>
      <select id="lang-my-speak">...</select>
    </div>
    <div class="form-group">
      <label class="form-label">对方听到的 / Their Hear</label>
      <select id="lang-their-hear">...</select>
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">对方说的 / Their Speak</label>
      <select id="lang-their-speak">...</select>
    </div>
    <div class="form-group">
      <label class="form-label">我希望听到的 / My Hear</label>
      <select id="lang-my-hear">...</select>
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">我的输出音色 / My Voice</label>
      <select id="voice-speak">...</select>
    </div>
    <div class="form-group">
      <label class="form-label">对方输出音色 / Their Voice</label>
      <select id="voice-listen">...</select>
    </div>
  </div>
</div>
```

**Section 2: 音频 / Audio**
```
<div class="form-section">
  <div class="form-section-title">音频 / Audio</div>
  <div class="form-group">
    <label class="form-label">通道模式 / Channel Mode</label>
    <select id="channel-mode" onchange="onChannelModeChange()">...</select>
  </div>
  <div id="single-channel-tip">...</div>
  <div id="dual-channel-tip" style="display:none;">...</div>
  <div class="form-group">
    <label class="form-label">麦克风 / Input (Mic)</label>
    <select id="dev-real-mic">...</select>
  </div>
  <div class="form-group" id="speaker-output-group">
    <label class="form-label">耳机 / Output (Speaker)</label>
    <select id="dev-real-spk">...</select>
  </div>
  <div class="form-group">
    <label class="checkbox-label">
      <input type="checkbox" id="tts-enable" checked onchange="onTtsToggle()">
      启用语音播放 / Enable TTS
    </label>
  </div>
  <div class="form-group">
    <button class="btn btn-secondary" id="btn-calib" onclick="calibrateNoise()">⚡ 智能校准 / Auto Calibrate</button>
  </div>
  <div class="routing-card">
    <div class="routing-card-title">内部路由检测 / Routing Check</div>
    <div>AI 听 (In): <span id="status-cable-b">扫描中...</span></div>
    <div>AI 说 (Out): <span id="status-cable-a">扫描中...</span></div>
    <div style="margin-top:6px;">Cable A: <span id="cable-a-status">检测中...</span></div>
    <div>Cable B: <span id="cable-b-status">检测中...</span></div>
  </div>
</div>
```

**Section 3: 术语库 / Glossary**
```
<div class="form-section">
  <div class="form-section-title">术语库 / Glossary</div>
  <div class="glossary-list" id="glossary-list-area">
    <!-- Loaded by loadGlossary() in translator.js -->
    <div class="placeholder" style="text-align:center;padding:16px;color:var(--text-muted);font-size:12px;">
      加载中...
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:var(--text-muted);">
    选择的术语将在开始翻译时应用到会话中。勾选多个分类可合并使用。
  </div>
</div>
```

**Section 4: 投屏样式 / Display**
```
<div class="form-section">
  <div class="form-section-title">投屏样式 / Display</div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">字号 / Font Size <span class="hint">10-72</span></label>
      <input type="number" id="display-font-size" value="24" min="10" max="72" class="form-input" onchange="updateDisplaySetting('fontSize', this.value)">
    </div>
    <div class="form-group">
      <label class="form-label">行高 / Line Height <span class="hint">1.0-3.0</span></label>
      <input type="number" id="display-line-height" value="1.6" min="1" max="3" step="0.1" class="form-input" onchange="updateDisplaySetting('lineHeight', this.value)">
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">译文颜色 / Trans Color</label>
      <input type="color" id="display-trans-color" value="#ffffff" oninput="updateDisplaySetting('transColor', this.value)">
    </div>
    <div class="form-group">
      <label class="form-label">原文颜色 / Orig Color</label>
      <input type="color" id="display-orig-color" value="#b3b3b3" oninput="updateDisplaySetting('origColor', this.value)">
    </div>
  </div>
  <div class="form-row">
    <div class="form-group">
      <label class="form-label">背景颜色 / Background</label>
      <input type="color" id="display-bg-color" value="#000000" oninput="updateDisplaySetting('bgColor', this.value)">
    </div>
    <div class="form-group">
      <label class="form-label">背景透明度 / Opacity</label>
      <select id="display-bg-opacity" class="form-input" onchange="updateDisplaySetting('bgOpacity', this.value)">...</select>
    </div>
  </div>
  <div style="display:flex;gap:8px;">
    <button class="btn btn-secondary" onclick="resetDisplaySettings()" style="flex:1;">重置默认 / Reset</button>
    <button class="btn btn-secondary" onclick="previewDisplaySettings()" style="flex:1;">预览 / Preview</button>
  </div>
</div>
```

- [ ] **Step 3: Simplify settings page — remove tabs, keep account + logs**

Remove:
- `.settings-tabs` nav (all 5 tab buttons)
- `#settings-lang` panel
- `#settings-audio` panel
- `#settings-display` panel

Keep (without tab wrapping):
```html
<div class="page" id="page-settings">
  <div class="page-header">设置 / Settings</div>
  <div class="page-content">
    <!-- Account Section -->
    <div class="form-section">
      <div class="form-section-title">账户 / Account</div>
      <div class="form-group">
        <label class="form-label">VOLCANO_APP_KEY</label>
        <input id="settings-app-key" type="password" class="form-input" placeholder="输入 API Key">
      </div>
      <div id="settings-status" style="display:none;..."></div>
      <div class="form-group">
        <button class="btn btn-primary" onclick="saveSettings()">保存 / Save</button>
      </div>
    </div>

    <!-- Logs Section -->
    <div class="form-section">
      <div class="form-section-title">日志 / Logs</div>
      <div id="settings-logs">
        <!-- Log viewer loaded by logs.js -->
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Remove `switchSettingsTab` function references and `openFullLogs` update**

Since there are no more tabs in settings, simplify `openFullLogs`:
```js
window.openFullLogs = function() {
  switchPage('settings');
};
```
(No tab switching needed — logs is the only content on settings page.)

- [ ] **Step 5: Verify HTML renders**

```bash
cd /Users/bengda0303/Desktop/ast-interpreter/simultaneous-interpreter && python3 wsgi.py
```

Open `http://127.0.0.1:5004/`. Expected:
- Sidebar with 5 items: 翻译/会话设置/词库/会议/设置
- Clicking each switches to correct page
- Session config page shows 4 form sections
- Settings page shows Account + Logs sections, no tabs
- Translate page shows read-only config overview

- [ ] **Step 6: Commit**

```bash
git add app/templates/index.html
git commit -m "feat: add session config page, simplify settings to account+logs"
```

---

### Task 3: Update translator.js — session config page + glossary selection

**Files:**
- Modify: `app/static/js/translator.js`

**Goal:** Wire up the session config page. glossary selection now works (renders into #glossary-list-area). Glossary checkbox changes update #ov-glossary. Remove switchSettingsTab references.

- [ ] **Step 1: Update hash routing in DOMContentLoaded**

Add 'session' to valid hash pages:
```js
var hash = window.location.hash.slice(1);
if (hash && ['translate', 'session', 'glossary', 'meetings', 'settings'].indexOf(hash) >= 0) {
  switchPage(hash);
}
```

- [ ] **Step 2: Wire glossary selection to config overview**

After `loadGlossary()` renders checkboxes, add event listeners to update `#ov-glossary`:

```js
function updateGlossaryOverview() {
  const checked = document.querySelectorAll('#glossary-list-area .glossary-item input:checked');
  const ovEl = document.getElementById('ov-glossary');
  if (checked.length === 0) {
    ovEl.textContent = '未选择';
  } else {
    const names = Array.from(checked).map(cb => {
      const parent = cb.closest('.glossary-item');
      return parent?.querySelector('.glossary-text')?.textContent || cb.value;
    });
    ovEl.textContent = names.join('、');
  }
}
```

Call `updateGlossaryOverview()` after `loadGlossary()` renders. Also add change listeners to checkboxes:

```js
// In loadGlossary(), after appending each item:
div.querySelector('input').addEventListener('change', updateGlossaryOverview);
```

- [ ] **Step 3: Remove `switchSettingsTab` function (no longer needed)**

Remove the switchSettingsTab function definition (lines 18-25). Settings page no longer has tabs.

- [ ] **Step 4: Update `openFullLogs` to not switch tabs**

```js
window.openFullLogs = function() {
  switchPage('settings');
};
```

- [ ] **Step 5: Update change event listeners for config overview**

The existing `updateConfigOverview()` in the DOMContentLoaded handler already listens for changes on `lang-my-speak`, `lang-their-hear`, `channel-mode`, `dev-real-mic`. Add listeners for glossary changes (handled by `updateGlossaryOverview()` in the glossary checkbox change handler).

- [ ] **Step 6: Verify JS works**

```bash
cd /Users/bengda0303/Desktop/ast-interpreter/simultaneous-interpreter && python3 wsgi.py
```

Open `http://127.0.0.1:5004/`. Expected:
- Session config page: all form controls render and are interactive
- Glossary list loads categories as checkboxes
- Checking glossary items updates the config overview on Translate page
- Language selects sync correctly
- Channel mode toggle works
- TTS toggle hides voice selects
- Display settings update projection
- Settings page: API key save works, logs load
- Start/Stop session works with selected glossary categories

- [ ] **Step 7: Commit**

```bash
git add app/static/js/translator.js
git commit -m "feat: integrate session config page, glossary selection, simplified settings"
```

---

### Task 4: Update CSS for session config page

**Files:**
- Modify: `app/static/css/main.css`

**Goal:** Add CSS for session config page layout, form sections, glossary checkbox items, routing card.

- [ ] **Step 1: Add form section styles**

```css
/* --- Form Sections --- */
.form-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
}

.form-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.form-row + .form-row {
  margin-top: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 12px;
}

.hint {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 400;
}
```

- [ ] **Step 2: Add glossary list styles**

```css
/* --- Glossary List (Session Config) --- */
.glossary-list {
  max-height: 240px;
  overflow-y: auto;
}

.glossary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.1s;
}

.glossary-item:hover {
  background: var(--bg-hover);
}

.glossary-item input[type="checkbox"] {
  margin: 0;
  flex-shrink: 0;
}

.glossary-text {
  flex: 1;
  font-size: 12px;
  color: var(--text-primary);
}

.glossary-tag {
  font-size: 10px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.05);
  padding: 1px 6px;
  border-radius: 3px;
}

.glossary-sep {
  font-size: 10px;
  color: var(--text-muted);
  padding: 8px 8px 4px;
  border-top: 1px solid var(--border);
  margin-top: 4px;
}
```

- [ ] **Step 3: Add routing card styles**

```css
/* --- Routing Check Card --- */
.routing-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  font-size: 11px;
  line-height: 1.6;
}

.routing-card-title {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
```

- [ ] **Step 4: Verify CSS**

```bash
# Check for obvious syntax issues
cd /Users/bengda0303/Desktop/ast-interpreter/simultaneous-interpreter && python3 -c "
with open('app/static/css/main.css') as f:
    content = f.read()
    # basic check: braces balance
    open_braces = content.count('{')
    close_braces = content.count('}')
    print(f'Braces: {open_braces} open, {close_braces} closed')
    assert open_braces == close_braces, 'Unbalanced braces!'
    print('CSS syntax check passed')
"
```

- [ ] **Step 5: Commit**

```bash
git add app/static/css/main.css
git commit -m "feat: add session config page and glossary selection styles"
```

---

### Task 5: Integration verification

**Files:** None (testing only)

**Goal:** Verify the complete application works end-to-end with the new 5-page layout.

- [ ] **Step 1: Start the application**

```bash
cd /Users/bengda0303/Desktop/ast-interpreter/simultaneous-interpreter && python3 wsgi.py
```

- [ ] **Step 2: Verify all 5 sidebar pages**
- **翻译 (Translate)** — config overview loads, Start button works, running view shows translation, Stop returns to stopped
- **会话设置 (Session Config)** — Language selects sync, channel mode toggles, mic devices list, glossary checkboxes load, display settings change, TTS toggle works
- **词库 (Glossary)** — category tree and terms load
- **会议 (Meetings)** — meeting list and transcript load
- **设置 (Settings)** — API key save, logs viewer with filters

- [ ] **Step 3: Verify glossary selection end-to-end**
- Go to Session Config → Glossary section
- Check one or more glossary categories
- Go to Translate page → config overview shows selected glossary names
- Click Start → session includes selected `category_ids`

- [ ] **Step 4: Verify no console errors**
- Open DevTools, check Console tab
- No "element not found" or "undefined" errors

- [ ] **Step 5: Verify macOS titleBarStyle**
- Traffic light buttons visible at top-left
- Content extends behind title bar area
- Window controls work

- [ ] **Step 6: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: integration fixes for 5-page layout and glossary selection"
```

---

## Scope Verification

| Spec Section | Task |
|-------------|------|
| §2 Window Configuration (titleBarStyle) | Task 1 (already done) |
| §3 Overall Layout (sidebar + main area) | Task 2 (HTML) |
| §3.1 Left Sidebar (5 items) | Task 2 (HTML sidebar update) |
| §4 Navigation & Page Organization | Task 3 (JS switchPage + hash routing) |
| §4.1 Translate Page | Task 2 (keep read-only config) |
| §4.2 Session Config Page | Task 2 (HTML) + Task 3 (JS) + Task 4 (CSS) |
| §4.2.1 Language Section | Task 2 (HTML move from settings-lang) |
| §4.2.2 Audio Section | Task 2 (HTML move from settings-audio) |
| §4.2.3 Glossary Section | Task 2 (HTML) + Task 3 (JS loadGlossary) |
| §4.2.4 Display Section | Task 2 (HTML move from settings-display) |
| §4.3 Glossary Page | Already done (inline rendering) |
| §4.4 Meetings Page | Already done (inline rendering) |
| §4.5 Settings Page (simplified) | Task 2 (HTML account + logs, no tabs) |
| §5 Translate Stopped State | Task 2 (keep as-is) |
| §5 Running States | Already done |
| §5.4 Projection Screen | Already done (window.open) |
| §7 Visual Design System (main.css) | Task 4 (new form/glossary styles) |
