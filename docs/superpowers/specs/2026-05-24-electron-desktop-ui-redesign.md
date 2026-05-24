# Electron Desktop Client UI Redesign

> **Goal:** Transform the Electron desktop client from a web-in-a-window appearance to a macOS-native-feeling desktop app, with reorganized information architecture.

**Date:** 2026-05-24
**Status:** Design approved, pending implementation

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
│  译  │  │    (翻译 / 术语 / 会议 / 设置)                      ││
│      │  │                                                   ││
│  📖  │  │                                                   ││
│  术  │  │                                                   ││
│  语  │  └───────────────────────────────────────────────────┘│
│      │                                                       │
│  📋  │                                                       │
│  会  │                                                       │
│  议  │                                                       │
│      │                                                       │
│  ⚙   │                                                       │
│  设  │                                                       │
│  置  │                                                       │
│      │                                                       │
├──────┴───────────────────────────────────────────────────────┤
│  [状态栏: 服务器状态 · 延迟 · tokens]                         │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 Left Sidebar
- **Width:** 60px
- **Background:** Deep dark with subtle gradient/blur effect (`backdrop-filter: blur(20px)`)
- **Items:** 4 icon-only navigation items, vertically centered
  - 🎤 Translate (default view)
  - 📖 Glossary
  - 📋 Meetings
  - ⚙ Settings
- **Active state:** Highlighted icon + left accent bar
- **Hover state:** Slight background lightening

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

Sidebar switches between 4 inline views. All pages are present in `index.html` as `<div>` sections, toggled by visibility. No page reloads.

### 4.1 Page: Translate (🎤) — Default
See Section 5.

### 4.2 Page: Glossary (📖)
Replaces the current `/glossary` independent page. Shows:
- Category tree (left sub-panel, ~200px)
- Term list (center)
- Term editor (right panel or modal)
- Import/export buttons

The glossary page retains all current functionality but is rendered inline instead of as a separate route.

### 4.3 Page: Meetings (📋)
Replaces the current `/meetings` independent page. Shows:
- Meeting list (left panel)
- Transcript viewer (right panel, dual-column: original + translation)
- Export buttons (TXT/MD)

### 4.4 Page: Settings (⚙)
See Section 6.

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

**Configuration overview** is a read-only summary card showing:
- Language direction (source → target)
- Channel mode (single/dual)
- Mic device name
- Glossary status ("未选择" / category name with count)
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
- **Top bar:** Status indicator, latency, token count, projection screen button
- **Projection button** "📺 打开投屏" opens an Electron BrowserWindow (replacing window.open popup)
- **Logs** are accessible via Settings → 日志 tab (not shown during runtime)

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

Two side-by-side panes: ME (speak channel) and OTHERS (listen channel). Each has dual sub-rows (translation + original). **Logs** are accessible via Settings → 日志 tab (not shown during runtime).

### 5.4 Projection Screen

- **Keeps current `display.html` content** — intentionally minimal, designed for projector/screen
- **Opened via Electron `BrowserWindow`** instead of `window.open()` — managed by main process, creates a frameless fullscreen window
- **Display settings** (font size, colors, opacity) are configured in Settings → Display tab, sent via Socket.IO or postMessage
- **Behavior unchanged:** Shows translation (top) + original (bottom) as before

---

## 6. Settings Page (⚙)

### 6.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  设置 / Settings                                             │
│                                                              │
│  [语言]  [音频]  [显示]  [日志]  [账户]                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                                                          ││
│  │         当前 Tab 的内容区域                                ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

5 tabs, each with a form layout. All settings persist to localStorage or backend as currently implemented.

### 6.2 Tab: 语言 / Language

| Field | Type | Notes |
|-------|------|-------|
| 我说的 / My Speak | `<select>` | zh/en/ja/fr/de/es/pt/id/zhen |
| 翻译为 / Translate to | `<select>` | en/zh/ja/fr/de/es/pt/id/zhen |
| 对方说的 / Their Speak | `<select>` | en/zh/ja/fr/de/es/pt/id/zhen |
| 翻译为 / Translate to | `<select>` | zh/en/ja/fr/de/es/pt/id/zhen |
| 我的输出音色 / My Voice | `<select>` | Clone / Female / Male |
| 对方输出音色 / Their Voice | `<select>` | Clone / Female / Male |

Same content as current card 1, but in a structured form layout.

### 6.3 Tab: 音频 / Audio

| Field | Type | Notes |
|-------|------|-------|
| 通道模式 / Channel Mode | `<select>` | Single / Dual |
| 麦克风 / Input (Mic) | `<select>` | Device list |
| 耳机 / Output (Speaker) | `<select>` | Device list |
| TTS 开关 / Enable TTS | `<checkbox>` | |
| 智能校准 / Auto Calibrate | `<button>` | |
| 路由检测 / Routing Check | read-only status | |

Same content as current card 2, plus the calibration button and routing check.

### 6.4 Tab: 显示 / Display

| Field | Type | Notes |
|-------|------|-------|
| 字号 / Font Size | `<input type="number">` | 10-72, default 24 (for projection) |
| 行高 / Line Height | `<input type="number">` | 1.0-3.0, step 0.1 |
| 译文颜色 / Trans Color | `<input type="color">` | |
| 原文颜色 / Orig Color | `<input type="color">` | |
| 背景颜色 / Background | `<input type="color">` | |
| 背景透明度 / Opacity | `<select>` | 0-100% |

Same content as current card 4, plus Reset/Preview buttons. These settings affect the projection screen.

### 6.5 Tab: 日志 / Logs

Consolidated log viewer (replaces both the runtime log sidebar and the standalone `/logs` page):
- Filter by channel (speak/listen/system)
- Filter by level (info/warning/error/debug)
- Search bar
- Export button
- Clear button
- Auto-scroll to latest on new entries

### 6.6 Tab: 账户 / Account

| Field | Type | Notes |
|-------|------|-------|
| VOLCANO_APP_KEY | `<input>` | Masked password field (新版控制台单 Key 鉴权) |
| Save button | | |

Replaces the current modal-dialog API key settings. Uses the new Volcano Engine console authentication (single API key), not the legacy app_key + access_key pair.

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
- **Transitions:** `all 0.2s ease` on hover/active states
- **Title bar:** macOS `titleBarStyle: 'hiddenInset'` — red/yellow/green buttons at top-left, content extends behind them

### 7.4 Layout Constants
- Sidebar: 60px width
- Page title bar: 32px height
- Status bar: 32px height (shown during runtime)
- Card padding: 20px
- Border radius: 8px (cards), 6px (inputs), 4px (buttons)

---

## 8. Files to Modify

| File | Change |
|------|--------|
| `electron/main.js` | Add `titleBarStyle: 'hiddenInset'` to BrowserWindow options; handle projection screen as BrowserWindow |
| `electron/preload.js` | Expose IPC for window controls, projection screen management |
| `app/templates/index.html` | Restructure: add sidebar nav HTML, inline page sections (translate/glossary/meetings/settings), remove current 4-card layout, header nav, and runtime log sidebar |
| `app/static/css/main.css` | **New file** — complete CSS rewrite for macOS-native dark theme |
| `app/static/js/translator.js` | Add sidebar navigation logic, page switching; remove settings modal code |
| `app/static/js/glossary.js` | Adapt for inline rendering (no separate page) |
| `app/static/js/meetings.js` | Adapt for inline rendering (no separate page) |

---

## 9. Out of Scope (This Iteration)

- System tray / global shortcuts / auto-start
- Application auto-update (electron-updater)
- Dark/light mode toggle
- Window position/size persistence
- Windows-specific title bar handling
- Any backend Python changes
