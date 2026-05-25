# Electron Desktop Client UI Redesign

> **Goal:** Transform the Electron desktop client from a web-in-a-window appearance to a macOS-native-feeling desktop app, with reorganized information architecture.

**Date:** 2026-05-24 (updated 2026-05-24)
**Status:** Design approved

---

## 1. Architecture (No Change)

The backend architecture remains untouched:

```
Electron (BrowserWindow) → loads http://127.0.0.1:{PORT}/ → Flask server-side rendered HTML
```

All changes are on the **frontend layer** (HTML templates, CSS, JS) and **Electron shell configuration**. Flask routes, Socket.IO handlers, Python services are NOT modified.

---

## 2. Window Configuration

**File:** `electron/main.js`

| Change | Value |
|--------|-------|
| `titleBarStyle` | `'hiddenInset'` (macOS keeps traffic light buttons, hides title) |
| `frame` | `true` (keeps native window chrome minus title) |
| `minWidth` | `900` |
| `minHeight` | `600` |

The `createWindow()` function is updated to add `titleBarStyle: 'hiddenInset'` for macOS platform. The native application menu (Menu.buildFromTemplate) is retained.

---

## 3. Overall Layout

```
┌──────────────────────────────────────────────────────────────┐
│ [traffic light buttons (macOS native)]  同声传译             │
├──────┬───────────────────────────────────────────────────────┤
│      │                                                       │
│  侧  │                  主内容区域                             │
│  边  │                                                       │
│  栏  │  [页面标题栏]                                          │
│      │  ┌───────────────────────────────────────────────────┐│
│  🎤  │  │                                                   ││
│  翻  │  │    当前页面内容                                     ││
│  译  │  │    (翻译 / 会话设置 / 术语 / 会议 / 设置)           ││
│      │  │                                                   ││
│  ⚙   │  │                                                   ││
│  会   │  │                                                   ││
│  话   │  └───────────────────────────────────────────────────┘│
│  设   │                                                       │
│  置   │                                                       │
│      │                                                       │
│  📖  │                                                       │
│  词   │                                                       │
│  库   │                                                       │
│      │                                                       │
│  📋  │                                                       │
│  会   │                                                       │
│  议   │                                                       │
│      │                                                       │
│  🔑  │                                                       │
│  设   │                                                       │
│  置   │                                                       │
│      │                                                       │
├──────┴───────────────────────────────────────────────────────┤
└──────────────────────────────────────────────────────────────┘
```

### 3.1 Left Sidebar
- **Width:** 76px
- **Background:** Deep dark with subtle gradient/blur effect (`backdrop-filter: blur(20px)`)
- **Items:** 5 items, icon + Chinese label below, vertically centered
  1. 🎤 翻译 (Translate — default view, read-only config + start/stop)
  2. ⚙ 会话设置 (Session Config — language, audio, glossary, display settings)
  3. 📖 词库 (Glossary — term management)
  4. 📋 会议 (Meetings — meeting history)
  5. 🔑 设置 (Settings — API key + logs)
- **Active state:** Highlighted icon + left accent bar
- **Hover state:** Slight background lightening
- Each item: column flex layout (icon above, 9px label below)

### 3.2 Main Content Area
- Fills remaining space
- Contains a **page-level title bar** (thin, ~32px) with the page name
- Below title bar: the page content (fills remaining height)
- Page switching is handled client-side (show/hide divs), no server roundtrip

### 3.3 Bottom Status Bar
- **Height:** ~32px
- Shows: server connection status (green/red dot), latency, token usage
- Only visible during/after translation session; hidden when idle

---

## 4. Navigation & Page Organization

5 sidebar pages, all present in `index.html` as `<div>` sections toggled by visibility.

### 4.1 Page: Translate (🎤 翻译) — Default
Pure **read-only** dashboard. Shows:
- **Config overview card** — language direction, channel mode, mic, glossary status, server status, API key
- **Start button** — large, centered, calls `startSession()`
- **Translation output** — appears during runtime (dual-pane speak/listen layout)
- **Running bar** — status, latency, tokens, projection screen button, stop button

No settings controls here — all session configuration is done in the Session Config page.

### 4.2 Page: Session Config (⚙ 会话设置)
Centralized place for all "before each session" configuration. Organized into 4 sections:

#### 4.2.1 语言 / Language
| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| 我说的 / My Speak | `lang-my-speak` | `<select>` | zh/en/ja/fr/de/es/pt/id/zhen |
| 对方听到的 / Their Hear | `lang-their-hear` | `<select>` | en/zh/ja/fr/de/es/pt/id/zhen |
| 对方说的 / Their Speak | `lang-their-speak` | `<select>` | en/zh/ja/fr/de/es/pt/id/zhen |
| 我希望听到的 / My Hear | `lang-my-hear` | `<select>` | zh/en/ja/fr/de/es/pt/id/zhen |
| 我的输出音色 / My Voice | `voice-speak` | `<select>` | Clone / Female / Male |
| 对方输出音色 / Their Voice | `voice-listen` | `<select>` | Clone / Female / Male |

Language direction validation: `syncLangOptions()` pairs source→target, allows passthrough (source=target), shows validation.

#### 4.2.2 音频 / Audio
| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| 通道模式 / Channel Mode | `channel-mode` | `<select>` | Single / Dual, triggers `onChannelModeChange()` |
| 麦克风 / Input (Mic) | `dev-real-mic` | `<select>` | Device list from `navigator.mediaDevices` |
| 耳机 / Output (Speaker) | `dev-real-spk` | `<select>` | Device list, hidden in single mode |
| 启用语音播放 / Enable TTS | `tts-enable` | `<checkbox>` | Triggers `onTtsToggle()` to hide/show voice selects |
| 智能校准 / Auto Calibrate | `btn-calib` | `<button>` | Calls `calibrateNoise()` |
| Cable A status | `cable-a-status` | read-only | Virtual cable detection status |
| Cable B status | `cable-b-status` | read-only | Virtual cable detection status |
| 内部路由检测 / Routing Check | `status-cable-a` / `status-cable-b` | read-only | AI in/out routing status |

Channel mode tips (green/yellow dashed borders) indicate current mode info. Single-channel mode hides speaker output group and listen pane.

#### 4.2.3 术语库 / Glossary
Checkbox list of available glossary categories. Each item:
- `<input type="checkbox" value="{category_id}">` — check to include in session
- `<span class="glossary-text">` — category name
- `<span class="glossary-tag">` — type label ("私有 Private")

Selected categories are sent as `speak_config.category_ids` when starting a session. Loading via `loadGlossary()` fetches `GET /api/glossary/categories`.

The config overview on the Translate page shows current selection (e.g., "信息技术" or "未选择").

#### 4.2.4 投屏样式 / Display
| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| 字号 / Font Size | `display-font-size` | `<input type="number">` | 10-72, default 24 |
| 行高 / Line Height | `display-line-height` | `<input type="number">` | 1.0-3.0, step 0.1 |
| 译文颜色 / Trans Color | `display-trans-color` | `<input type="color">` | |
| 原文颜色 / Orig Color | `display-orig-color` | `<input type="color">` | |
| 背景颜色 / Background | `display-bg-color` | `<input type="color">` | |
| 背景透明度 / Opacity | `display-bg-opacity` | `<select>` | 0-100% |
| 重置默认 | | `<button>` | Calls `resetDisplaySettings()` |
| 预览 | | `<button>` | Calls `previewDisplaySettings()` |

All display settings affect the projection screen. Persisted to `localStorage`.

### 4.3 Page: Glossary (📖 词库)
Unchanged — standalone page loaded in sidebar. Shows:
- Category tree (left sub-panel, ~200px)
- Term list (center)
- Term editor (right panel or modal)
- Import/export buttons

Full glossary management functionality.

### 4.4 Page: Meetings (📋 会议)
Unchanged — standalone page loaded in sidebar. Shows:
- Meeting list (left panel)
- Transcript viewer (right panel, dual-column: original + translation)
- Export buttons (TXT/MD)

### 4.5 Page: Settings (🔑 设置)
Simplified — no tab navigation. Two sections stacked vertically:

#### 4.5.1 账户 / Account
| Field | Element ID | Type | Notes |
|-------|-----------|------|-------|
| VOLCANO_APP_KEY | `settings-app-key` | `<input type="password">` | Masked field |
| Status | `settings-status` | read-only | Validation result display |
| Save button | | `<button>` | Calls `saveSettings()`, POST `/api/save_env` |

Uses the new Volcano Engine console authentication (single API key, not legacy pair).

#### 4.5.2 日志 / Logs
Consolidated log viewer (replaces runtime log sidebar + standalone `/logs` page):
- Filter by channel (speak/listen/system)
- Filter by level (info/warning/error/debug)
- Search bar
- Export button
- Clear button
- Auto-scroll to latest on new entries

---

## 5. Translate Page (Default View)

### 5.1 Stopped State

```
┌──────────────────────────────────────────────────────────────┐
│  翻译 / Translate                                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  当前配置 / Configuration                                 ││
│  │                                                          ││
│  │  中文 → 英语     ·    单通道模式                           ││
│  │  Mic: MacBook Pro Microphone                              ││
│  │  📖 术语库: 信息技术 (12条)                                 ││
│  │                                                          ││
│  │  🟢 服务器已连接      延迟: 20ms                            ││
│  │  🟢 API 密钥已配置                                         ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│              ┌──────────────────────────┐                    │
│              │     ▶  开始运行 / Start    │                    │
│              └──────────────────────────┘                    │
│                                                              │
│  ┌─ 翻译输出 ──────────────────────────────────────────────┐│
│  │                                                          ││
│  │           (停止状态，开始后将在此显示翻译内容)              ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**Configuration overview** is a pure read-only summary card showing:
- Language direction (source → target)
- Channel mode (single/dual)
- Mic device name
- Glossary status ("未选择" / selected category names)
- Connection status + latency
- API key status

The "开始运行" button is large and centered. Below it is a reserved area for translation output (shown during runtime).

### 5.2 Running State — Single Channel (Speech/Lecture)

```
┌──────────────────────────────────────────────────────────────┐
│  [顶栏] 🟢 运行中   延迟: 320ms   tokens: 1,234   [📺 投屏]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ 音源 / Audio Source ────────────────────────────────┐   │
│  │  ┌──────────────────────────────────────────────────┐│   │
│  │  │  翻译 / Translation (高亮, 对方语言)              ││   │
│  │  │  Today we're going to discuss the trends          ││   │
│  │  │  of artificial intelligence development...        ││   │
│  │  ├──────────────────────────────────────────────────┤│   │
│  │  │  原文 / Original (稍暗, 演讲者语言)               ││   │
│  │  │  今天我们来讨论一下人工智能的发展趋势...             ││   │
│  │  └──────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Features:
- **Single pane** labeled "音源 / Audio Source" with two sub-rows: Translation (top, highlighted) and Original (bottom, dimmed)
- **Top bar:** Status indicator, latency, token count, projection screen button, stop button
- **Projection button** "📺 打开投屏" opens a projection BrowserWindow via `window.open('/display')`
- **Logs** are accessible via Settings → 日志 tab

### 5.3 Running State — Dual Channel (Meeting)

```
┌──────────────────────────────────────────────────────────────┐
│  [顶栏] 🟢 运行中   延迟: 320ms   tokens: 2,345   [📺 投屏]  │
├───────────────────┬──────────────────────────────────────────┤
│                   │                                          │
│  我的发言 / ME    │    他人发言 / OTHERS                      │
│  ┌──────────────┐│    ┌──────────────┐                      │
│  │ 译文 (高亮)   ││    │ 译文 (高亮)   │                      │
│  │ Today we...   ││    │ 是的，我同意  │                      │
│  ├──────────────┤│    ├──────────────┤                      │
│  │ 原文 (稍暗)   ││    │ 原文 (稍暗)   │                      │
│  │ 我们来讨论一下 ││    │ Yes, I agree │                      │
│  └──────────────┘│    └──────────────┘                      │
│                   │                                          │
└───────────────────┴──────────────────────────────────────────┘
```

Two side-by-side panes: ME (speak channel) and OTHERS (listen channel). Each has dual sub-rows (translation + original).

### 5.4 Projection Screen

- **Keeps current `display.html` content** — intentionally minimal, designed for projector/screen
- **Opened via `window.open('/display')`** — standard browser popup (not Electron BrowserWindow)
- **Display settings** (font size, colors, opacity) are configured in Session Config → 投屏样式, sent via postMessage
- **Behavior unchanged:** Shows translation (top) + original (bottom) as before

---

## 6. Settings Page (🔑)

No tabs. Two sections stacked vertically in a simple form layout.

### 6.1 Section: 账户 / Account

| Field | Type | Notes |
|-------|------|-------|
| 我说的 / My Speak | `<select>` | zh/en/ja/fr/de/es/pt/id/zhen |

API key management:
- Password-masked input for `VOLCANO_APP_KEY`
- Save button triggers `POST /api/save_env` which tests the key against Volcano Engine API
- Shows success/failure status message
- Updates `window.__HAS_API_KEY__` and config overview

### 6.2 Section: 日志 / Logs

Consolidated log viewer:
- Filter by channel (speak/listen/system)
- Filter by level (info/warning/error/debug)
- Search bar
- Export button
- Clear button
- Auto-scroll to latest on new entries

---

## 7. Visual Design System

### 7.1 Typography
- **Font family:** `-apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif`
- **Scale:** 11px (labels) / 12px (body) / 13px (titles) / 14px+ (headings)
- **Monospace:** `"SF Mono", "Consolas", monospace` for log content

### 7.2 Color Palette (Dark Theme)
```
--bg-app:        #1a1a1a       (window background)
--bg-sidebar:    rgba(30,30,30,0.85)  (sidebar with blur)
--bg-card:       #222222       (card/section background)
--bg-input:      #2a2a2a       (input background)
--border:        rgba(255,255,255,0.08)  (subtle borders)
--accent:        #3b82f6       (blue accent)
--text-primary:  #f0f0f0       (primary text)
--text-secondary: #999999      (secondary/label text)
--text-muted:    #666666       (placeholder/disabled)
--green:         #34d399       (success/connected)
--yellow:        #fbbf24       (warning)
--red:           #f87171       (error/disconnected)
```

### 7.3 Effects
- **Sidebar blur:** `backdrop-filter: blur(20px)` for native vibrancy feel
- **Transitions:** `all 0.15s ease` on hover/active states
- **Title bar:** macOS `titleBarStyle: 'hiddenInset'` — red/yellow/green buttons at top-left, content extends behind them

### 7.4 Layout Constants
- Sidebar: 76px width
- Page title bar: 32px height
- Card padding: 20px
- Border radius: 8px (cards), 6px (inputs), 4px (buttons)

---

## 8. Files to Modify

| File | Change |
|------|--------|
| `electron/main.js` | Add `titleBarStyle: 'hiddenInset'` to BrowserWindow options |
| `app/static/css/main.css` | **Create** — complete CSS rewrite for macOS-native dark theme; add session config form styles, glossary checkbox styles |
| `app/templates/index.html` | Restructure: 5-page sidebar (翻译/会话设置/词库/会议/设置); session config page with 4 sections (语言/音频/术语库/投屏样式); settings page simplified (账户+日志, no tabs); translate page as pure read-only config overview |
| `app/static/js/translator.js` | Add sidebar navigation, hash routing, session config page integration; glossary selection wiring (`loadGlossary()` + `#ov-glossary` updates); all existing functions preserved by element ID |
| `app/static/js/glossary.js` | Already adapted for inline rendering (unchanged) |
| `app/static/js/meetings.js` | Already adapted for inline rendering (unchanged) |
| `app/static/js/logs.js` | Already adapted for inline rendering under Settings (unchanged) |

---

## 9. Out of Scope (This Iteration)

- System tray / global shortcuts / auto-start
- Application auto-update (electron-updater)
- Dark/light mode toggle
- Window position/size persistence
- Windows-specific title bar handling
- Any backend Python changes
