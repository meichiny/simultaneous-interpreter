# AI 同声传译桌面客户端 | AI Simultaneous Interpreter Desktop

[中文](#中文) | [English](#english)

---

## 关于本项目

本项目 fork 自 [masichong408-afk/simultaneous-interpreter](https://github.com/masichong408-afk/simultaneous-interpreter)，在原项目核心功能基础上，重构为 **Electron 桌面客户端**，并进行了大量 UI 和体验优化。

GitHub: [meichiny/simultaneous-interpreter](https://github.com/meichiny/simultaneous-interpreter)

---

## 中文

基于火山引擎同声传译 API 的实时翻译桌面客户端，支持双通道会议翻译、术语管理和会议记录。

### 功能亮点

#### 桌面客户端
- **macOS 原生风格**：`titleBarStyle: hiddenInset`，`backdrop-filter` 毛玻璃暗色主题，窗口可拖拽移动
- **5 项侧边栏导航**：翻译 / 会话设置 / 词库 / 会议 / 设置，内嵌切换无需整页跳转
- **会话设置页**：集中配置语言方向、音频设备、术语库选择、显示设置，附带配置概览卡片
- **独立投屏窗口**：通过原生 BrowserWindow 打开，支持预设字体/颜色/背景/透明度
- **术语库/会议内嵌面板**：与独立页面功能一致，支持分类管理、导入导出、JSON 导出
- **USB 声卡热插拔**：插拔设备自动刷新麦克风列表

#### 翻译核心
- **实时同声传译**：基于火山引擎 AST API，支持中英日法德西葡印尼等多语言互译
- **单/双通道模式**：单通道无需虚拟声卡，双通道需要 VB-Cable
- **TTS 语音输出（可开关）**：PCM 流式播放，支持预设音色和声音克隆
- **音频美化**：低通滤波 + 高频衰减 + 动态压缩
- **术语管理**：分类管理、CSV 导入导出、批量删除/移动、冲突检查
- **会议记录**：自动保存双语转写，支持导出
- **断线自动恢复**：网络中断后自动重连并恢复翻译会话
- **实时日志**：INFO/WARNING/ERROR 级别日志，支持搜索过滤导出
- **Token 计费显示**：实时显示 API token 消耗

### 快速开始

#### 方式一：下载安装包（推荐）

从 [Releases](https://github.com/meichiny/simultaneous-interpreter/releases) 下载最新 `.dmg`，打开后拖入 Applications 即可使用。

#### 方式二：从源码运行

##### 1. 环境要求

- Python 3.10+
- Node.js 18+ (如需打包 Electron)
- 火山引擎账号，开通[同声传译 API](https://www.volcengine.com/product/ast)

##### 2. 克隆并安装

```bash
git clone https://github.com/meichiny/simultaneous-interpreter.git
cd simultaneous-interpreter
pip install -r requirements.txt
```

##### 3. 申请火山引擎 API 密钥

本项目需要 `VOLCANO_APP_KEY`（API Key），按以下步骤获取：

1. 访问 [火山引擎官网](https://www.volcengine.com/)，注册并完成实名认证
2. 进入 [豆包语音控制台](https://console.volcengine.com/speech/app)，开通「**豆包同声传译 2.0 大模型**」
3. 在「API key 管理」中创建并复制 **Api Key**

配置到项目：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
VOLCANO_APP_KEY=your_api_key_here
```

##### 4. 启动

```bash
python wsgi.py
```

浏览器打开 `http://127.0.0.1:5004` 即可使用。

### 使用说明

#### 单通道模式（无需虚拟声卡）

适合个人使用、演讲翻译。通道模式选择「单通道」，选择麦克风，点击开始。

#### 双通道模式（需要 VB-Cable）

适合双向会议。安装 VB-Cable A+B 后，会议软件扬声器设为 `Cable B`、麦克风设为 `Cable A`，系统自动检测并完成路由。

#### 虚拟声卡安装

- **Windows / macOS**：[VB-Audio Cable A+B](https://vb-audio.com/Cable/)，需安装 Cable A 和 Cable B 两个驱动

### 技术架构

```
浏览器 / Electron (Web Audio API + AudioWorklet)
  ↕ Socket.IO
Flask 后端 (本地 Python 进程)
  ↕ WebSocket (Protobuf)
火山引擎 AST API (同声传译 + TTS)
```

- **前端**：原生 JS，AudioWorklet PCM 流式播放，Silero VAD 语音检测
- **后端**：Flask + Flask-SocketIO，SQLite 存储术语和会议记录
- **桌面壳**：Electron 33，titleBarStyle hiddenInset，原生 BrowserWindow 投屏
- **通信**：Socket.IO 双向实时通信，Protobuf 编码与 API 交互

### 项目结构

```
simultaneous-interpreter/
├── app/
│   ├── __init__.py              # Flask 应用工厂
│   ├── config.py                # 配置（从 .env 读取）
│   ├── models.py                # 数据模型（术语、会议）
│   ├── socket_handlers.py       # Socket.IO 事件处理
│   ├── routes/                  # HTTP 路由
│   ├── services/                # 火山引擎翻译服务
│   ├── templates/
│   │   ├── index.html           # 主页面（含全部内嵌面板）
│   │   ├── display.html         # 独立显示窗口
│   │   ├── glossary.html        # 术语管理（独立版，向后兼容）
│   │   └── meetings.html        # 会议记录（独立版，向后兼容）
│   └── static/
│       ├── css/main.css         # 设计系统样式
│       └── js/
│           ├── translator.js    # 主逻辑
│           ├── glossary.js      # 术语管理
│           ├── meetings.js      # 会议记录
│           ├── logs.js          # 日志
│           ├── audio-processor.js
│           └── pcm-player-processor.js
├── electron/
│   ├── main.js                  # Electron 主进程
│   ├── preload.js               # 预加载脚本
│   ├── package.json             # Electron 构建配置
│   └── resources/               # 图标 + 编译后的服务端
├── python_protogen/             # Protobuf 生成文件
├── install.sh                   # 开发环境安装脚本
├── CHANGELOG.md
├── .env.example
├── requirements.txt
└── wsgi.py                      # 入口
```

### 常见问题

#### 点击开始后显示"连接AI服务失败：python-socks is required"

电脑上开启了网络代理工具（Clash、Surge 等）。`websockets` 检测到系统 SOCKS 代理但缺少 `python-socks` 依赖。

**解决**：关闭代理系统代理功能，或在代理工具的「绕过」列表中添加 `openspeech.bytedance.com`

### 许可证

MIT License

---

## English

A real-time translation Electron desktop client built on the Volcano Engine Simultaneous Translation API, supporting dual-channel meeting translation, glossary management, and meeting transcription.

Forked from [masichong408-afk/simultaneous-interpreter](https://github.com/masichong408-afk/simultaneous-interpreter).

### Features

#### Desktop Client
- **macOS Native Style**: `titleBarStyle: hiddenInset`, `backdrop-filter` blur dark theme, draggable window
- **5-Item Sidebar Navigation**: Translate / Session Config / Glossary / Meetings / Settings, inline page switching
- **Session Config Page**: Centralized language, audio, glossary, and display settings with config overview card
- **Projection Window**: Native BrowserWindow with customizable font, color, background, and opacity
- **Inline Glossary/Meetings Panels**: Full functionality including categories, CSV import/export, JSON export
- **USB Hotplug**: Auto-refresh microphone list on device plug/unplug

#### Translation Core
- **Real-time Translation**: Powered by Volcano Engine AST API, multi-language support
- **Single/Dual Channel Mode**: Single channel requires no virtual audio cable
- **TTS Toggle**: PCM streaming playback with preset voices and voice cloning
- **Audio Enhancement**: Low-pass filter + high-frequency attenuation + dynamic compression
- **Glossary Management**: Categorized management, CSV import/export, bulk operations, conflict detection
- **Meeting Transcription**: Automatic bilingual transcription with export support
- **Auto-reconnection**: Automatic reconnection and session recovery
- **Real-time Logs**: INFO/WARNING/ERROR levels with search, filter, and export
- **Token Billing**: Real-time API token consumption display

### Quick Start

#### Option 1: Download Installer (Recommended)

Download the latest `.dmg` from [Releases](https://github.com/meichiny/simultaneous-interpreter/releases).

#### Option 2: Run from Source

```bash
git clone https://github.com/meichiny/simultaneous-interpreter.git
cd simultaneous-interpreter
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your VOLCANO_APP_KEY
python wsgi.py
```

Open `http://127.0.0.1:5004` in your browser.

### License

MIT License
