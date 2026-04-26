# 显示日志功能实现计划

## 需求确认

### 侧边栏日志面板（实时）
- **位置**：右侧侧边栏
- **宽度**：固定 300px
- **默认状态**：展开
- **显示内容**：INFO、WARNING、ERROR 级别
- **显示条数**：最近 50 条
- **交互**：实时自动滚动

### 新窗口页（完整日志）
- **功能**：
  - 搜索日志内容
  - 按通道过滤（全部/speak/listen）
  - 导出为 .txt
  - 清空日志
- **数据来源**：前端累积（与侧边栏共享同一数组）

### 导出按钮位置
- 侧边栏日志面板顶部

---

## 实现步骤

### 1. 后端修改

**文件**: `app/services/volcano_translator.py`
- 新增日志级别：INFO、WARNING、ERROR
- 在关键节点发送日志事件：
  - WebSocket 连接/断开
  - 会话启动/结束
  - 错误发生
  - 重连触发

**文件**: `app/socket_handlers.py`
- 新增 `log_update` Socket.IO 事件
- 可选：新增日志累积缓冲区（如选择后端存储方案）

### 2. 前端修改

**文件**: `app/templates/index.html`
- 添加右侧侧边栏结构
- 添加日志面板样式

**文件**: `app/static/js/translator.js`
- 新增 `sessionLogs` 数组累积日志
- 新增 `log()` 函数统一处理日志
- 新增 `renderSidebarLogs()` 渲染侧边栏
- 新增 `openFullLogs()` 打开新窗口

**新文件**: `app/templates/logs.html`
- 完整日志页面结构
- 搜索框、过滤下拉框
- 导出、清空按钮

**新文件**: `app/static/js/logs.js`
- 从 opener 获取日志数据
- 搜索过滤功能
- 导出 txt 功能
- 清空功能

### 3. 路由添加

**文件**: `app/routes.py`
- 新增 `/logs` 路由返回 logs.html

---

## 界面结构

```
┌─────────────────────────────────────────┬─────────────┐
│  AI Meeting Mate                        │  运行日志 ▼ │
│  [术语管理] [会议记录] [显示窗口]        │  ─────────  │
│                                         │  [📋完整日志]│
├─────────────────────────────────────────┤  ─────────  │
│  语言方向    │   设备选择                │  INFO 连接  │
│  ──────────  │   ─────────               │  INFO 开始  │
│  ...         │   ...                     │  WARN 重连  │
│              │                           │  ...滚动    │
│              │                           │             │
│              │                           │             │
│              │                           │             │
└──────────────┴───────────────────────────┴─────────────┘
```

---

## 数据流

```
后端 volcano_translator.py
    │  socketio.emit('log_update', {...})
    ▼
前端 translator.js (sessionLogs 数组累积)
    │
    ├──► 侧边栏显示 (最近50条)
    │
    └──► 新窗口 logs.js (全部日志，搜索/导出)
```

---

## 日志格式

```javascript
{
    timestamp: "2026-04-25 10:30:15",
    level: "INFO",        // INFO | WARNING | ERROR
    channel: "speak",     // speak | listen | system
    message: "WebSocket连接成功"
}
```

---

## 下一步

确认后开始实现：
1. 后端发送日志事件
2. 前端接收和显示
3. 新窗口完整日志页
