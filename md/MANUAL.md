# 📖 QQ 机器人详细使用手册

本文档详细介绍机器人的架构设计、每个文件的功能、如何使用和维护，以及与原项目的对比。

---

## 📋 目录

1. [架构概述](#1-架构概述)
2. [与原项目对比](#2-与原项目对比)
3. [目录结构详解](#3-目录结构详解)
4. [核心模块详解](#4-核心模块详解)
5. [插件系统详解](#5-插件系统详解)
6. [配置详解](#6-配置详解)
7. [数据库设计](#7-数据库设计)
8. [部署与运行](#8-部署与运行)
9. [自定义修改指南](#9-自定义修改指南)
10. [添加新功能](#10-添加新功能)
11. [维护与故障排除](#11-维护与故障排除)

---

## 1. 架构概述

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    OneBot 实现                          │
│            (go-cqhttp / NapCatQQ / LLOneBot)            │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP POST (反向 WebSocket)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI + Uvicorn                       │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────┐    │
│  │  router   │  │   html    │  │   static files    │    │
│  │ (webhook) │  │ (WebUI)   │  │   (CSS/HTML)      │    │
│  └─────┬─────┘  └───────────┘  └───────────────────┘    │
│        │                                                │
│        ▼                                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │            Plugin Manager (插件管理器)            │    │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌──────┐       │    │
│  │  │help │ │ ai  │ │ cy  │ │banme│ │repeat│ ...   │    │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └──────┘       │    │
│  └─────────────────────────────────────────────────┘    │
│        │                                                │
│  ┌─────┴─────────────────────────────────────────┐      │
│  │              Core Modules (核心模块)           │      │
│  │  config │ sqline │ onebot_api │ setting │ ... │      │
│  └───────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   aiosqlite (SQLite)                    │
│    data.db │ set.db │ aimemory.db │ total.db            │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术特点

| 特性 | 说明 |
|------|------|
| 异步架构 | 基于 `asyncio`，所有 I/O 操作都是异步的 |
| 插件化设计 | 功能模块化，易于扩展和维护 |
| 双层开关 | 全局开关 + 群独立开关，灵活控制功能 |
| 热配置 | 部分设置可在运行时动态修改 |
| 数据持久化 | SQLite + WAL 模式，高并发性能 |

---

## 2. 与原项目对比

### 2.1 架构对比

| 方面 | 原项目 (bot.py) | 新项目 |
|------|----------------|--------|
| **Web 框架** | Flask (同步) | FastAPI (异步) |
| **HTTP 客户端** | requests (同步) | httpx (异步) |
| **数据库** | sqlite3 (同步) | aiosqlite (异步) |
| **代码结构** | 单文件 2295 行 | 模块化，多文件分离 |
| **配置管理** | 硬编码在代码中 | YAML 配置文件 |
| **功能开关** | 部分支持 | 完整的双层开关系统 |

### 2.2 功能对比

| 功能 | 原项目 | 新项目 | 差异说明 |
|------|--------|--------|----------|
| AI 对话 | ✅ | ✅ | 新增：Agent 架构，支持工具调用 |
| 词云 | ✅ | ✅ | 相同 |
| 语录图片 | ✅ | ✅ | 相同 |
| 禁言管理 | ✅ | ✅ | 新增：随机语录回复 |
| 复读 | ✅ | ✅ | 相同 |
| 戳一戳 | ✅ | ✅ | 相同 |
| 入群申请处理 | ✅ | ✅ | 相同 |
| JM 下载 | ✅ | ✅ | 新增：全局开关控制 |
| 群设置 | ✅ | ✅ | 新增：更多设置项 |
| 动态帮助 | ❌ | ✅ | **新增**：根据开关动态显示 |
| 全局开关 | ❌ | ✅ | **新增**：config.yml 控制 |
| 群独立开关 | 部分 | ✅ | **增强**：所有功能都支持 |
| WebUI | ❌ | ✅ | **新增**：Web 管理界面 |
| JWT 鉴权 | ❌ | ✅ | **新增**：API 安全认证 |

### 2.3 代码结构对比

**原项目：**
```
bot.py (2295 行，所有功能在一个文件)
├── 全局配置 (50+ 行)
├── 数据库初始化 (150+ 行)
├── 数据库操作函数 (300+ 行)
├── API 调用函数 (200+ 行)
├── 业务逻辑 (1500+ 行)
└── 定时任务 (100+ 行)
```

**新项目：**
```
py/
├── config.py        # 配置管理 (~170 行)
├── sqline.py        # 数据库管理 (~380 行)
├── onebot_api.py    # API 封装 (~200 行)
├── router.py        # 路由和插件系统 (~300 行)
├── setting.py       # 设置管理 (~220 行)
├── plugins/         # 插件目录
│   ├── help.py      # ~200 行
│   ├── ai.py        # ~280 行
│   ├── cy.py        # ~230 行
│   ├── banme.py     # ~165 行
│   └── ...
```

### 2.4 性能对比

| 指标 | 原项目 | 新项目 |
|------|--------|--------|
| 并发处理 | 单线程阻塞 | 异步非阻塞 |
| 数据库连接 | 每次操作新建 | 连接池复用 |
| 内存使用 | 较高 | 较低 |
| 响应延迟 | 较高 | 较低 |

---

## 3. 目录结构详解

```
bot/
├── start.py              # 🚀 主入口文件
├── config.yml            # ⚙️ 全局配置文件
├── requirements.txt      # 📦 Python 依赖
├── jmoption.yml          # 📚 JM 漫画下载配置
│
├── py/                   # 🐍 Python 核心模块
│   ├── __pycache__/      # Python 缓存（自动生成）
│   ├── config.py         # 配置加载模块
│   ├── router.py         # 路由和插件系统
│   ├── sqline.py         # 异步数据库管理
│   ├── onebot_api.py     # OneBot API 封装
│   ├── setting.py        # 群设置管理
│   ├── selfset.py        # 机器人管理员设置
│   ├── autointime.py     # 定时任务调度
│   ├── html.py           # WebUI 路由
│   ├── system_msg.py     # 系统消息处理
│   ├── sentence_pool.py  # 语录池
│   └── plugins/          # 插件目录
│       ├── __init__.py
│       ├── help.py       # 帮助命令
│       ├── ai.py         # AI 对话
│       ├── cy.py         # 词云生成
│       ├── qorqtp.py     # 语录图片
│       ├── banme.py      # 禁言管理
│       ├── repeat.py     # 复读机
│       ├── poke.py       # 戳一戳/互动
│       ├── jm.py         # JM 漫画
│       ├── small.py      # 小功能集合
│       └── ai/           # AI 子模块
│           └── ai_agent.py
│
├── sqline/               # 💾 数据库文件目录
│   ├── data.db           # 消息数据
│   ├── set.db            # 群设置
│   ├── aimemory.db       # AI 记忆
│   └── total.db          # 统计数据
│
├── resource/             # 📁 资源文件
│   ├── msyh.ttc          # 微软雅黑字体
│   ├── TsukuA.ttc        # 日文字体
│   └── quote_base.png    # 语录背景图
│
├── html/                 # 🌐 WebUI 静态文件
│   ├── index.html
│   └── css/
│
├── text/                 # 📝 文本资源
│   ├── fgl.txt           # 非管理员语录
│   └── gl.txt            # 管理员语录
│
├── qtp/                  # 🖼️ 生成的语录图片（自动）
│
├── md/                   # 📖 文档目录
│   ├── GIT_GUIDE.md      # Git 上传指南
│   └── MANUAL.md         # 本文档
│
├── backup/               # 📦 原版代码备份
│   └── bot.py            # 原始单文件版本
│
└── test_bot.py           # 🧪 测试文件
```

---

## 4. 核心模块详解

### 4.1 start.py - 主入口

**功能：** 应用启动入口，负责初始化和启动服务。

**关键代码：**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await db_manager.init_all()
    # 加载插件
    plugin_manager.load_all_plugins()
    # 启动定时任务
    scheduler_manager.start()
    yield
    # 关闭时清理
    scheduler_manager.shutdown()
    await db_manager.close_all()
```

**可修改点：**
- 修改 `uvicorn.run()` 参数可以改变服务器行为
- 可以在 `lifespan` 中添加更多初始化/清理逻辑

---

### 4.2 py/config.py - 配置管理

**功能：** 从 `config.yml` 加载配置，使用 dataclass 定义配置结构。

**关键数据类：**
```python
@dataclass
class GlobalFeaturesConfig:
    """全局功能开关"""
    ai: bool = True
    wordcloud: bool = True
    quote: bool = True
    # ... 更多功能开关
```

**使用方式：**
```python
from py.config import config

# 访问配置
bot_qq = config.bot.qq_id
api_key = config.zhipu.api_key
is_ai_enabled = config.global_features.ai
```

**可修改点：**
- 添加新的 dataclass 来支持新配置项
- 在 `load_config()` 函数中添加新配置段的加载逻辑

---

### 4.3 py/sqline.py - 数据库管理

**功能：** 异步 SQLite 数据库操作，支持连接池和 WAL 模式。

**数据库文件：**
| 文件 | 用途 |
|------|------|
| data.db | 群消息记录、复读状态、入群申请 |
| set.db | 群设置、消息格式、用户数据 |
| aimemory.db | AI 对话上下文 |
| total.db | 统计数据 |

**关键类：**
```python
class AsyncDB:
    """异步数据库封装"""
    async def execute(sql, params)
    async def fetchone(sql, params)
    async def fetchall(sql, params)

class DatabaseManager:
    """数据库连接池管理"""
    async def get_db(name: str) -> AsyncDB
    async def init_all()  # 初始化所有表
```

**可修改点：**
- 在 `_init_xxx_db()` 方法中添加新表
- 添加新的便捷函数（如 `add_xxx_record()`）

---

### 4.4 py/router.py - 路由和插件系统

**功能：** 接收 OneBot webhook，分发事件到插件处理。

**核心组件：**

1. **OneBotEvent** - 事件数据模型
2. **PluginManager** - 插件管理器
3. **router** - FastAPI 路由

**插件加载流程：**
```python
def load_all_plugins(self):
    plugins = ['help', 'small', 'cy', 'qorqtp', 'repeat', 'poke', 'banme', 'jm', 'ai']
    for plugin in plugins:
        self.load_plugin(plugin)
```

**事件分发流程：**
```
webhook 接收事件
    ↓
根据 post_type 分类
    ↓
调用对应的 dispatch_xxx() 方法
    ↓
遍历已注册的 handlers
    ↓
handler 返回 True 则停止分发
```

**可修改点：**
- 在 `plugins` 列表中添加新插件名
- 修改插件加载顺序（影响命令优先级）

---

### 4.5 py/onebot_api.py - OneBot API 封装

**功能：** 封装 OneBot 协议的 HTTP API 调用。

**主要方法：**
```python
class OneBotAPI:
    async def send_group_msg(group_id, message)
    async def send_private_msg(user_id, message)
    async def get_group_member_info(group_id, user_id)
    async def set_group_ban(group_id, user_id, duration)
    async def set_essence_msg(message_id)
    # ... 更多 API
```

**便捷函数：**
```python
# 直接导入使用
from py.onebot_api import send_group_msg, send_private_msg, onebot

await send_group_msg(group_id, "消息内容")
```

**可修改点：**
- 添加新的 OneBot API 方法
- 修改请求超时时间、重试逻辑

---

### 4.6 py/setting.py - 群设置管理

**功能：** 管理群级别的功能开关和设置。

**核心类：**
```python
class GroupSettings:
    # 设置项映射
    SETTING_FIELDS = {
        'ai': 'ai_enabled',
        'repeat': 'repeat_enabled',
        'banme': 'banme_enabled',
        # ...
    }
    
    # 全局开关映射
    GLOBAL_FEATURE_MAP = {
        'ai': 'ai',
        'repeat': 'repeat',
        # ...
    }
    
    @classmethod
    async def get_setting(cls, group_id, setting_name) -> bool:
        """获取设置（自动检查全局开关）"""
        
    @classmethod
    async def set_setting(cls, group_id, setting_name, value) -> bool:
        """设置群配置"""
```

**开关检查逻辑：**
```
get_setting('ai')
    ↓
检查 global_features.ai
    ↓
如果全局关闭 → 返回 False
    ↓
如果全局开启 → 检查群设置
```

**可修改点：**
- 在 `SETTING_FIELDS` 添加新设置项
- 在 `GLOBAL_FEATURE_MAP` 添加全局开关映射

---

## 5. 插件系统详解

### 5.1 插件结构规范

每个插件文件需要包含：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""插件描述"""

import sys
import os

# 支持单独运行（可选，用于测试）
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import send_group_msg
from py.setting import GroupSettings


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    
    # 检查全局开关
    if not config.global_features.xxx:
        return False
    
    # 检查群开关
    if not await GroupSettings.get_setting(group_id, 'xxx'):
        return False
    
    # 处理命令
    if raw_msg.strip() == '#mycommand':
        await send_group_msg(group_id, "响应内容")
        return True  # 返回 True 表示已处理，停止分发
    
    return False  # 返回 False 继续分发给其他插件


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# 单独运行测试（可选）
if __name__ == "__main__":
    print("插件测试")
```

### 5.2 各插件详解

#### 5.2.1 help.py - 帮助命令

**命令：** `#help`

**特点：**
- 根据 `global_features` 动态生成帮助文本
- 关闭的功能不显示在帮助中

**与原项目对比：**
- 原项目：静态帮助文本
- 新项目：动态生成，根据开关显示/隐藏

---

#### 5.2.2 ai.py - AI 对话

**命令：**
- `#js [问题]` - AI 解释
- `@机器人 [消息]` - 与 AI 对话
- `#new` (私聊) - 清除上下文

**特点：**
- 支持上下文记忆
- 群聊和私聊分别存储
- 使用 Agent 架构，支持工具调用

**与原项目对比：**
- 原项目：直接调用 API
- 新项目：Agent 架构，更灵活

---

#### 5.2.3 cy.py - 词云生成

**命令：**
- `#cy [小时数]` - 生成词云
- `#cyyy` - 统计英语
- `#cydz` - 统计单字

**与原项目对比：** 基本相同

---

#### 5.2.4 banme.py - 禁言管理

**命令：**
- `禁言我` / `#banme` - 随机禁言
- `#mute [QQ/@]` - 禁言他人
- `#jj [QQ/@]` - 解禁

**特点：**
- 管理员触发时发送专属语录
- 非管理员触发时随机禁言 + 语录

**与原项目对比：**
- 新增：从 `text/gl.txt` 和 `text/fgl.txt` 读取语录

---

#### 5.2.5 repeat.py - 复读机

**触发条件：**
- 连续两人发相同消息 → 按配置概率复读
- 感叹号结尾的短句 → 按配置概率变体复读

**概率配置（支持全局+单群）：**
- `repeat_probability` - 复读触发概率（默认 0.3 = 30%）
- `exclamation_probability` - 感叹号变体概率（默认 0.15 = 15%）

群内未设置时使用全局配置值。

**与原项目对比：** 
- 新增：可配置概率
- 新增：支持全局和单群分别设置

---

#### 5.2.6 qorqtp.py - 语录图片

**命令：**
- `#q` - 设精华 + 生成语录
- `#unq` - 取消精华
- `#tpq` - 只生成语录图片

**与原项目对比：** 基本相同

---

#### 5.2.7 small.py - 小功能

**命令：**
- `#ping` - 状态检查
- `#dzw` - 点赞
- `#settings [功能] [on|off]` - 群设置
- `#setformat` - 设置消息格式
- `#selfset` - 机器人管理员设置
- `#tx` - 设置头衔
- `#sx` (私聊) - 私信管理员

**与原项目对比：** 基本相同

---

## 6. 配置详解

### 6.1 config.yml 完整说明

```yaml
# =============================================
# 机器人全局配置文件
# =============================================

# OneBot HTTP API 配置
onebot:
  api_url: "http://127.0.0.1:3000"  # OneBot 实现的 HTTP API 地址
  token: "your_token"               # 鉴权 Token（需与 OneBot 配置一致）

# 机器人基本信息
bot:
  qq_id: 123456789        # 机器人 QQ 号
  admin_qq: 987654321     # 机器人管理员 QQ 号
  version: "13.0.0"       # 版本号

# 智谱 AI 配置
zhipu:
  api_key: "your_api_key"  # 智谱 AI API Key
  model: "glm-4.5-air"     # 模型名称

# 服务器配置
server:
  host: "0.0.0.0"   # 监听地址（0.0.0.0 表示所有网卡）
  port: 8080        # 监听端口

# 数据库设置
database:
  # true: 重启保留设置
  # false: 重启重置设置
  keep_previous_settings: true

# 全局功能开关 (关闭后所有群都不可用)
global_features:
  ai: true          # AI 对话
  wordcloud: true   # 词云
  quote: true       # 语录图片
  essence: true     # 精华消息
  banme: true       # 禁言抽奖
  repeat: true      # 复读
  poke: true        # 戳一戳
  jm: false         # JM 下载（默认关闭）
  welcome: true     # 入群欢迎
  farewell: true    # 退群提醒
  checkin: true     # 签到

# 新群默认设置
default_group_settings:
  broadcast_admin_changes: false
  welcome_message: true
  farewell_message: false
  broadcast_join_request: true
  wordcloud_count_english: false
  wordcloud_count_single_char: false
  jm_enabled: false
  ai_enabled: true
  repeat_enabled: true
  poke_enabled: true
  banme_enabled: true
  quote_enabled: true
  essence_enabled: true

# 词云停用词
stopwords:
  - "的"
  - "了"
  # ... 更多
```

### 6.2 配置优先级

```
全局开关 (config.yml global_features)
    ↓ 如果开启
群独立开关 (set.db group_settings)
    ↓ 如果开启
功能生效
```

---

## 7. 数据库设计

### 7.1 data.db - 消息数据库

**group_messages 表：**
```sql
CREATE TABLE group_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    user_id INTEGER,
    text TEXT,
    create_time INTEGER
);
```

**last_msg 表：** 复读检测用
```sql
CREATE TABLE last_msg (
    group_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    text TEXT
);
```

**join_requests 表：** 入群申请
```sql
CREATE TABLE join_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    user_id INTEGER,
    flag TEXT,
    random_code INTEGER,
    nickname TEXT,
    comment TEXT,
    inviter TEXT,
    create_time INTEGER,
    status TEXT DEFAULT 'pending'
);
```

### 7.2 set.db - 设置数据库

**group_settings 表：**
```sql
CREATE TABLE group_settings (
    group_id INTEGER PRIMARY KEY,
    broadcast_admin_changes INTEGER DEFAULT 0,
    welcome_message INTEGER DEFAULT 0,
    farewell_message INTEGER DEFAULT 0,
    broadcast_join_request INTEGER DEFAULT 0,
    wordcloud_count_english INTEGER DEFAULT 0,
    wordcloud_count_single_char INTEGER DEFAULT 0,
    jm_enabled INTEGER DEFAULT 0,
    ai_enabled INTEGER DEFAULT 1,
    repeat_enabled INTEGER DEFAULT 1,
    poke_enabled INTEGER DEFAULT 1,
    banme_enabled INTEGER DEFAULT 1,
    quote_enabled INTEGER DEFAULT 1,
    essence_enabled INTEGER DEFAULT 1
);
```

### 7.3 aimemory.db - AI 记忆

**group_ai_context 表：**
```sql
CREATE TABLE group_ai_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    user_id INTEGER,
    role TEXT,        -- 'user' 或 'assistant'
    content TEXT,
    create_time INTEGER
);
```

---

## 8. 部署与运行

### 8.1 环境准备

1. **安装 Python 3.9+**
2. **安装依赖：**
   ```bash
   pip install -r requirements.txt
   ```

3. **准备 OneBot 实现：**
   - 推荐：NapCatQQ、LLOneBot、go-cqhttp
   - 配置反向 HTTP POST 到 `http://你的IP:8080/`

### 8.2 配置文件

1. **编辑 `config.yml`：**
   - 填入机器人 QQ 号
   - 填入管理员 QQ 号
   - 填入智谱 AI API Key
   - 配置 OneBot API 地址和 Token

2. **准备资源文件：**
   - `resource/msyh.ttc` - 微软雅黑字体
   - `resource/TsukuA.ttc` - 日文字体
   - `resource/quote_base.png` - 语录背景图

### 8.3 启动

```bash
python start.py
```

看到以下输出表示启动成功：
```
==================================================
🤖 机器人启动中... 版本: 13.0.0
==================================================
✅ 数据库初始化完成
✅ 插件加载成功: help
✅ 插件加载成功: small
...
✅ 定时任务调度器启动
🌐 服务监听: http://0.0.0.0:8080
==================================================
```

### 8.4 后台运行

**Linux (使用 nohup)：**
```bash
nohup python start.py > bot.log 2>&1 &
```

**Windows (使用 pythonw)：**
```bash
pythonw start.py
```

**使用 PM2：**
```bash
pm2 start start.py --name qq-bot --interpreter python
```

### 8.5 WebUI 管理界面

机器人内置了 Web 管理界面，可以在浏览器中管理群设置。

**访问地址：** `http://你的IP:端口/html/home.html`

#### 8.5.1 群管理员登录流程

1. 访问 WebUI 首页，点击「群管登录」
2. 选择「输入群号登录」
3. 输入你管理的群号，点击「获取验证码」
4. 网页会显示一个 6 位验证码
5. **私聊机器人**，直接发送这个验证码
6. 机器人会检查：
   - 验证码是否正确
   - 你是否为该群的管理员或群主
7. 验证通过后，网页自动跳转到群设置页面

**注意事项：**
- 验证码有效期 5 分钟
- 必须**私聊**机器人发送验证码
- 只有群主或管理员才能通过验证

#### 8.5.2 WebUI 功能

- **实时统计** - 查看消息数、命令数、AI 调用数等
- **群设置管理** - 开关各项功能
- **全局管理员** - 管理所有群的设置（需密钥登录）

---

## 9. 自定义修改指南

### 9.1 修改欢迎/退群消息

在群内发送：
```
#setformat welcome 欢迎 {at} 加入！
#setformat farewell {qqid} 走了
```

支持的变量：
- `{qqid}` - QQ 号
- `{at}` - @用户

### 9.2 修改禁言语录

编辑 `text/` 目录下的文件：
- `gl.txt` - 管理员专属语录（每行一条）
- `fgl.txt` - 普通用户语录（每行一条）

### 9.3 修改词云停用词

编辑 `config.yml` 的 `stopwords` 列表。

### 9.4 修改 AI 提示词

编辑 `py/plugins/ai.py`：
```python
GROUP_SYSTEM_PROMPT = """你的自定义提示词"""
PRIVATE_SYSTEM_PROMPT = """你的自定义提示词"""
```

### 9.5 修改复读概率

编辑 `py/plugins/repeat.py`：
```python
# 复读概率（默认 30%）
if random.random() < 0.3:

# 感叹号变体概率（默认 15%）
if random.random() < 0.15:
```

---

## 10. 添加新功能

### 10.1 添加新命令

1. **创建插件文件** `py/plugins/my_plugin.py`：

```python
#!/usr/bin/env python3

from py.config import config
from py.onebot_api import send_group_msg
from py.setting import GroupSettings


async def handle_group_message(event):
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    
    if raw_msg.strip() == '#mycommand':
        await send_group_msg(group_id, "Hello World!")
        return True
    
    return False


def register(plugin_manager):
    plugin_manager.register_group_handler(handle_group_message)
```

2. **在 `py/router.py` 注册插件**：

```python
def load_all_plugins(self):
    plugins = [
        'help',
        'small',
        # ... 其他插件
        'my_plugin',  # 添加这行
    ]
```

3. **重启机器人**

### 10.2 添加新的全局开关

1. **编辑 `config.yml`：**
```yaml
global_features:
  my_feature: true
```

2. **编辑 `py/config.py`：**
```python
@dataclass
class GlobalFeaturesConfig:
    # ... 现有配置
    my_feature: bool = True
```

3. **在插件中检查：**
```python
if not config.global_features.my_feature:
    return False
```

### 10.3 添加新的群设置项

1. **编辑 `py/setting.py`：**
```python
SETTING_FIELDS = {
    # ... 现有字段
    'my_setting': 'my_setting_enabled',
}

GLOBAL_FEATURE_MAP = {
    # ... 现有映射
    'my_setting': 'my_feature',
}
```

2. **编辑 `py/sqline.py` 添加数据库字段：**
```python
async def _init_set_db(self):
    # 在 CREATE TABLE 语句中添加
    my_setting_enabled INTEGER DEFAULT 1
    
    # 在兼容性检查中添加
    new_columns = [
        # ...
        ('my_setting_enabled', 'INTEGER DEFAULT 1'),
    ]
```

---

## 11. 维护与故障排除

### 11.1 日志查看

机器人会在控制台输出日志，包括：
- 插件加载状态
- 命令处理信息
- 错误信息

### 11.2 常见问题

#### Q: 机器人不响应命令

**检查：**
1. OneBot 实现是否正常运行
2. 反向 HTTP POST 是否配置正确
3. 查看控制台是否有错误

#### Q: AI 功能不工作

**检查：**
1. `config.yml` 中 `zhipu.api_key` 是否正确
2. `global_features.ai` 是否为 `true`
3. 群设置 `ai_enabled` 是否开启

#### Q: 词云生成失败

**检查：**
1. 字体文件是否存在
2. 消息数量是否足够（至少 10 条）
3. 是否安装了 jieba 和 wordcloud

#### Q: 数据库错误

**解决：**
```bash
# 备份数据库
cp -r sqline/ sqline_backup/

# 删除问题数据库（将丢失数据）
rm sqline/set.db

# 重启机器人（会重新创建）
python start.py
```

### 11.3 数据备份

定期备份 `sqline/` 目录：
```bash
# Linux
tar -czvf sqline_backup_$(date +%Y%m%d).tar.gz sqline/

# Windows PowerShell
Compress-Archive -Path sqline -DestinationPath "sqline_backup_$(Get-Date -Format 'yyyyMMdd').zip"
```

### 11.4 版本升级

1. 备份当前代码和数据库
2. 拉取新代码
3. 比较 `config.yml` 是否有新配置项
4. 运行 `pip install -r requirements.txt` 更新依赖
5. 重启机器人

---

## 📝 附录

### A. 完整命令列表

| 命令 | 权限 | 说明 |
|------|------|------|
| `#help` | 所有人 | 显示帮助 |
| `#ping` | 所有人 | 状态检查 |
| `#dzw` | 所有人 | 点赞 |
| `#cy [小时]` | 所有人 | 生成词云 |
| `#cyyy` | 所有人 | 词云统计英语 |
| `#cydz` | 所有人 | 词云统计单字 |
| `#js [问题]` | 所有人 | AI 解释 |
| `@机器人 [消息]` | 所有人 | AI 对话 |
| `禁言我` | 所有人 | 禁言抽奖 |
| `#q` | 所有人 | 设精华+语录 |
| `#unq` | 所有人 | 取消精华 |
| `#tpq` | 所有人 | 生成语录图片 |
| `摸摸` | 所有人 | 趣味互动 |
| `ccb` | 所有人 | 踩背 |
| `#mute [QQ/@]` | 管理员 | 禁言他人 |
| `#jj [QQ/@]` | 管理员 | 解禁 |
| `同意[编号]` | 管理员 | 同意入群 |
| `拒绝[编号] [理由]` | 管理员 | 拒绝入群 |
| `#settings [功能] [on/off]` | 管理员 | 群设置 |
| `#setformat [类型] [格式]` | 管理员 | 设置消息格式 |
| `#tx [QQ/@] [头衔]` | 群主 | 设置头衔 |
| `#selfset qd [on/off]` | 机器人管理员 | 签到开关 |
| `#selfset cy [0-23/-1]` | 机器人管理员 | 定时词云 |
| `#selfset ai [on/off]` | 机器人管理员 | AI 开关 |

### B. 文件修改速查表

| 需求 | 修改文件 |
|------|---------|
| 添加新命令 | `py/plugins/` 新建文件 + `py/router.py` |
| 修改配置项 | `config.yml` + `py/config.py` |
| 添加群设置 | `py/setting.py` + `py/sqline.py` |
| 修改 AI 行为 | `py/plugins/ai.py` |
| 修改帮助文本 | `py/plugins/help.py` |
| 修改语录 | `text/gl.txt` 和 `text/fgl.txt` |
| 修改词云 | `py/plugins/cy.py` |

---

**文档版本：** 1.0  
**更新日期：** 2026-02-04  
**适用版本：** 13.0.0+
