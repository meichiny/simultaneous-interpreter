# 热词（Hot Words）功能设计文档

## 背景

在同声传译应用中，语音识别（ASR）对特定词汇（如专业术语、人名、品牌名）的识别准确率可能不理想。参考豆包语音的热词功能，通过添加热词可提高这类词汇的识别效果。

## 技术调研

### 协议分析

通过反编译项目已有的 `python_protogen/products/understanding/base/au_base_pb2.py` 和官方文档 `ast-api2.md`，确认 `ReqParams` 的 `corpus` 消息体包含以下与热词相关的字段：

`corpus` 是 `request` 层级下的 dict，其子层级 `hot_words_list` 是 `[string]`，示例：`["视频直播","赛事直播","智能家居"]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `hot_words_list` | repeated string | 内联热词列表（优先级最高），纯字符串列表 |
| `boosting_table_id` | string | 引用火山引擎控制台创建的热词词表 ID |
| `boosting_table_name` | string | 引用热词词表名称 |
| `glossary_list` | map<string,string> | 术语列表（source→target，现有已使用） |

### 与 ASR 语音识别 API 的差异

| 维度 | ASR 语音识别 API | AST 同声传译 API |
|------|------------------|-------------------|
| 传词方式 | `boosting_table_id` 引用 | `hot_words_list` 内联 string 数组 |
| 权重 | 支持 `词\|5` | 不支持权重（纯字符串列表） |
| 单次上限 | 5000 词/表 | corpus 所有字段（热词+术语）总计 ≤ 1000 条 |
| 每词长度 | ≤10 字 | 未明确说明，沿用 ≤10 保守规则 |

### 决定

采用 `corpus.hot_words_list` 内联方式发送热词，无需 AKSK 凭证，无需调用外部管理 API。

## 设计

### 数据模型

新增 `HotWordTable` 和 `HotWord` 两张表：

```
HotWordTable: id, name, created_at
HotWord:      id, word (≤10字), table_id (FK → HotWordTable.id, cascade delete)
```

- word 字段长度限制 10 个汉字
- 删除词表时级联删除其所有热词

### 后端 API

在 `app/routes/hotwords.py` 中注册 Blueprint `/api/hotwords`：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/hotwords/tables` | 获取所有词表 |
| `POST` | `/api/hotwords/tables` | 创建词表 `{name}` |
| `PUT` | `/api/hotwords/tables/<id>` | 重命名 |
| `DELETE` | `/api/hotwords/tables/<id>` | 删除词表（级联删除热词） |
| `GET` | `/api/hotwords/tables/<id>/words` | 获取词表下所有热词 |
| `POST` | `/api/hotwords/tables/<id>/words` | 添加热词 `{word}` |
| `DELETE` | `/api/hotwords/words/<id>` | 删除单个热词 |
| `POST` | `/api/hotwords/tables/<id>/import` | 批量导入 |
| `POST` | `/api/hotwords/words/delete_bulk` | 批量删除 |

**批量导入 `/import`**：接受两种格式
1. JSON 格式：`{"words": ["词1", "词2", ...]}`
2. 文本格式：`Content-Type: text/plain`，每行一个词，服务端按 `\n` 分割

**校验规则（前后端双重校验）**：

| 规则 | 说明 |
|------|------|
| 每词 ≤ 10 个汉字 | word 长度限制 |
| 无标点符号 | 仅允许中文汉字、英文字母、数字、空格 |
| 去重 | 同一词表内不允许重复词 |
| 全局上限 | 热词 + 术语合计 ≤ 1000 条（会话启动时校验） |

### 前端 UI

#### 侧边栏

在"词库"下方新增侧边栏项——**热词 / Hot Words**，指向 `#page-hotwords`。

#### 热词管理页面

布局参考现有术语管理页：

```
┌─────────────────────────────────────────────┐
│  热词 / Hot Words                            │
├──────────────────┬──────────────────────────┤
│  词表列表          │  热词明细                  │
│  ┌──────────────┐ │  ┌──────────────────────┐ │
│  │ 医疗词汇  12词│ │  │ 词1  词2  词3        │ │
│  │ 技术术语   8词│ │  │ 词4  词5  词6        │ │
│  │ [+ 新建词表]  │ │  │ [+ 添加] [批量导入]  │ │
│  └──────────────┘ │  │ [删除选中] [导入.txt] │ │
│                   │  └──────────────────────┘ │
└──────────────────┴──────────────────────────┘
```

**批量导入支持两种方式**：
1. **文本框粘贴**：每行一个词，点击提交后转为 JSON 数组发送
2. **上传 .txt 文件**：本地选择 .txt 文件，读取每行内容为热词

#### 会话配置页变更

在"术语库"区域下方新增"热词词表"选择区：

- 下拉选择框（dropdown），从所有词表中选择一张
- 选项包括 `不启用（默认）`
- 每个选项显示词表名和词数量，如 `医疗词汇 (12词)`
- 底部提示行：
  - "每次会话只能生效一张热词词表。热词与术语合计不超过 1000 条。"
  - 选中词表后动态显示当前热词数量，如 `已选择：医疗词汇（12词）`

### 数据流

```
用户创建词表并添加热词 → 存入 app.db (HotWordTable / HotWord)
                           ↓
会话配置页 → 用户从 dropdown 选择一张热词词表 → hotword_table_id
                           ↓
handle_start_session → 加载 HotWord.query.filter_by(table_id=...) → hotwords_list = [...]
  空词表不发送 hot_words_list 字段
                           ↓
doubao_translator(hotwords=hotwords_list) → corpus['hot_words_list'] = hotwords_list
                           ↓
AST API 收到 hot_words_list，优化 ASR 识别
```

#### 会话中动态更新（UpdateConfig）

参考现有 `update_glossary` 机制，新增 `update_hotwords` Socket.IO 事件：

```
前端发送 update_hotwords { table_id: xxx }
     ↓
后端加载新词表的热词
     ↓
发送 UpdateConfig 事件到 AST API，更新 corpus.hot_words_list
     ↓
热词在会话中即时生效，无需重连
```

当前会话未选择词表时，也可通过 `update_hotwords` 动态传入热词列表（不落地到 DB，仅内存中生效）。

### 错误处理

| 场景 | 处理方式 |
|------|----------|
| corpus 超限（>1000 条） | API 返回错误，最可能错误码为 45000001（请求参数无效）。后端捕获后记录日志，前端弹出提示"热词与术语合计超过 1000 条上限" |
| 网络异常 | 沿用现有 WebSocket 重试机制 |
| 校验失败 | 前端即时提示（如"词超出 10 字限制"），后端返回 400 + 错误信息 |
| 空词表 | 不发送 `hot_words_list` 字段 |

> TODO：corpus 超限的具体错误码需在实现时联调确认。文档未给出超限专属错误码。

### 与现有术语库的关系

| 维度 | 术语库（glossary） | 热词（hot words） |
|------|--------------------|--------------------|
| API 字段 | `corpus.glossary_list` | `corpus.hot_words_list` |
| 作用 | 翻译映射 + ASR 辅助 | 仅提升 ASR 识别 |
| 数据格式 | key-value 对 | 纯字符串数组 |
| 管理方式 | 分类 → 术语 | 词表 → 热词 |
| 上限 | 与热词合计 1000 条 | 与术语合计 1000 条 |

## 涉及文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `app/models.py` | 修改 | 新增 HotWordTable, HotWord 模型 |
| `app/routes/hotwords.py` | 新建 | 热词 CRUD API |
| `app/__init__.py` | 修改 | 注册 hotwords Blueprint |
| `app/socket_handlers.py` | 修改 | start_session 加载热词，新增 update_hotwords 事件 |
| `app/services/volcano_translator.py` | 修改 | 新增 hotwords 参数，写入 corpus |
| `app/templates/index.html` | 修改 | 新增热词页面、会话配置热词 dropdown |
| `app/static/js/translator.js` | 修改 | 热词管理页加载逻辑、会话配置逻辑 |
| `app/static/css/main.css` | 修改 | 热词页面样式 |
