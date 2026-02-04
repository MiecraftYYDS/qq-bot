# 🤖 QQ 群聊机器人

基于 **FastAPI + Uvicorn** 异步架构的 QQ 群聊机器人，支持 OneBot 协议。

## ✨ 功能特性

- 🚀 **现代异步架构** - 基于 FastAPI + Uvicorn，高性能处理并发请求
- 🔌 **插件化设计** - 易于扩展和维护，每个功能独立成插件
- 🎛️ **双层开关控制** - 全局开关 + 群独立开关，灵活管理功能
- 🤖 **AI 对话** - 集成智谱 AI，支持群聊和私聊
- ☁️ **词云生成** - 基于群聊记录生成词云图片
- 🖼️ **语录图片** - 生成精美的语录卡片
- 📊 **WebUI 管理** - 提供 Web 管理界面
- 🔒 **JWT 鉴权** - 安全的 API 认证机制

## 📦 技术栈

| 组件 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | aiosqlite (异步 SQLite) |
| HTTP 客户端 | httpx (异步) |
| 定时任务 | APScheduler |
| AI | 智谱 AI (zhipuai) |
| 图像处理 | Pillow + pilmoji |
| 分词 | jieba |
| 词云 | wordcloud |

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- OneBot 协议实现 (如 go-cqhttp、NapCatQQ、LLOneBot 等)

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

复制并编辑配置文件：

```bash
# 编辑 config.yml，填入你的配置
```

主要配置项：
- `onebot.api_url` - OneBot HTTP API 地址
- `bot.qq_id` - 机器人 QQ 号
- `bot.admin_qq` - 管理员 QQ 号
- `zhipu.api_key` - 智谱 AI API Key

### 4. 启动

```bash
python start.py
```

机器人将在 `http://0.0.0.0:8080` 启动，需要在 OneBot 实现中配置反向 HTTP POST 到此地址。

## 📁 项目结构

```
bot/
├── start.py              # 主入口
├── config.yml            # 全局配置
├── requirements.txt      # Python 依赖
├── py/                   # 核心模块目录
│   ├── config.py         # 配置加载
│   ├── router.py         # 路由和插件系统
│   ├── sqline.py         # 异步数据库管理
│   ├── onebot_api.py     # OneBot API 封装
│   ├── setting.py        # 群设置管理
│   ├── selfset.py        # 机器人管理员设置
│   ├── autointime.py     # 定时任务
│   ├── html.py           # WebUI 路由
│   ├── system_msg.py     # 系统消息处理
│   ├── sentence_pool.py  # 语录池
│   └── plugins/          # 插件目录
│       ├── help.py       # 帮助命令
│       ├── ai.py         # AI 对话
│       ├── cy.py         # 词云
│       ├── qorqtp.py     # 语录图片
│       ├── banme.py      # 禁言管理
│       ├── repeat.py     # 复读
│       ├── poke.py       # 戳一戳/互动
│       ├── jm.py         # JM 漫画
│       └── small.py      # 小功能
├── sqline/               # 数据库文件目录
├── resource/             # 资源文件
├── html/                 # WebUI 静态文件
└── backup/               # 原版代码备份
```

## ⚙️ 配置说明

### 全局功能开关

在 `config.yml` 中配置 `global_features`，可以全局开启/关闭功能：

```yaml
global_features:
  ai: true          # AI 对话
  wordcloud: true   # 词云
  quote: true       # 语录图片
  essence: true     # 精华消息
  banme: true       # 禁言抽奖
  repeat: true      # 复读
  poke: true        # 戳一戳
  jm: false         # JM 下载（默认关闭）
```

### 复读概率设置

```yaml
repeat_settings:
  repeat_probability: 0.3         # 复读触发概率 (30%)
  exclamation_probability: 0.15   # 感叹号变体概率 (15%)
```

群内可单独设置，未设置则使用全局值。

### 群独立设置

每个群可以通过 `#settings [功能] [on|off]` 命令单独设置功能开关。

## 🌐 WebUI 管理

访问 `http://你的IP:端口/html/home.html` 进入 Web 管理界面。

### 群管理员登录

1. 点击「群管登录」→「输入群号登录」
2. 输入群号，获取验证码
3. **私聊**机器人发送验证码
4. 验证通过后自动跳转设置页面

**注意：** 仅群主/管理员可通过验证

## 📖 命令列表

### 基础功能
- `#help` - 获取帮助信息
- `#ping` - 检查机器人状态
- `#dzw` - 给自己点赞

### AI 功能
- `#js [问题]` - AI 解释问题
- `@机器人 [消息]` - 与 AI 对话

### 词云功能
- `#cy [小时数]` - 生成词云
- `#cyyy` - 词云统计英语
- `#cydz` - 词云统计单字

### 更多命令请使用 `#help` 查看

## 🔧 开发指南

### 添加新插件

1. 在 `py/plugins/` 下创建新文件，如 `my_plugin.py`
2. 实现处理函数和 `register` 函数
3. 在 `py/router.py` 的 `load_all_plugins()` 中添加插件名

示例：

```python
async def handle_group_message(event):
    if event.raw_message == '#mycommand':
        # 处理逻辑
        return True
    return False

def register(plugin_manager):
    plugin_manager.register_group_handler(handle_group_message)
```

## 📄 许可证

MIT License

## 🙏 致谢

- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) - OneBot 协议实现
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [智谱 AI](https://www.zhipuai.cn/) - AI 能力提供
