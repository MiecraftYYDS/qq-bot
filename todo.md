# 🤖 机器人重构待办事项清单 (FastAPI + 异步架构)

## 第一阶段：环境与基础结构搭建
- [ ] **数据与备份**
    - [ ] 将当前目录下所有文件备份到 `backup/` 目录(除了文件树.md和todo.md)。
    - [ ] 导出旧数据库（如需迁移历史数据）或准备全新初始化的 SQL 脚本。
- [ ] **创建文件目录结构**
    - [ ] 创建 `py/` 及其子目录: `py/plugins/` (业务), `py/plugins/ai/` (AI核心), `py/plugins/ai/ddgs/` (搜索修复版).
    - [ ] 创建资源目录: `md/`, `resource/`, `sqline/`, `qtp/`, `html/` (含 `html/css/`), `text/`.
- [ ] **依赖管理**
    - [ ] 创建 `requirements.txt`。
    - [ ] 核心依赖: `fastapi`, `uvicorn`, `httpx`, `aiosqlite`, `apscheduler`, `pydantic`, `pyyaml`.
    - [ ] 业务依赖: `pillow`, `jieba`, `wordcloud`, `zhipuai`, `jmcomic`.

## 第二阶段：核心框架实现
- [ ] **入口与配置**
    - [ ] 编写 `start.py` (FastAPI + Uvicorn).
    - [ ] 配置 `os.chdir` 锁定工作目录.
    - [ ] 编写 `option.yml` 和 `jmoption.yml` 模板。
    - [ ] 编写 `py/setting.py` (群设置封装) 和 `py/selfset.py` (全局设置封装).
- [ ] **数据库层 (`py/sqline.py`)**
    - [ ] 封装 `AsyncDB` 类 (aiosqlite).
    - [ ] 初始化连接池管理 (`sqline/data.db`, `sqline/set.db`, `sqline/aimemory.db`, `sqline/total.db`).
    - [ ] 开启 WAL 模式 (`PRAGMA journal_mode=WAL;`).
- [ ] **OneBot API (`py/onebot_api.py`)**
    - [ ] 封装异步 `send_msg` 和 `call_api` (httpx).
    - [ ] 实现指数退避重试机制.
- [ ] **业务分发 (`py/router.py`)**
    - [ ] 实现 `POST /webhook` 路由.
    - [ ] 实现插件动态加载机制.
    - [ ] 实现事件分发过滤器.

## 第三阶段：通用工具与资源迁移
- [ ] **资源迁移**
    - [ ] 移动字体/图片到 `resource/`, 文本到 `text/`, HTML到 `html/`.
    - [ ] 确保 `resource/` 中包含 `quote_base.png`(语录背景), `TsukuA.ttc`(语录字体), `msyh.ttc`(词云字体).
    - [ ] 确保 `text/` 中包含 `gl.txt`, `fgl.txt` 等文本资源.
    - [ ] 配置 `qtp/` 为语录图片输出目录(如 `q_群号.png`).
- [ ] **功能模块迁移**
    - [ ] 语录生成 (`py/plugins/qorqtp.py`): 迁移绘图逻辑.
    - [ ] 词云生成 (`py/plugins/cy.py`): 迁移分词与绘图逻辑.
    - [ ] 小功能 (`py/plugins/samll.py`): 迁移小功能逻辑.
    - [ ] 复读 (`py/plugins/repeat.py`): 迁移复读逻辑.
    - [ ] 戳一戳 (`py/plugins/poke.py`): 迁移戳一戳逻辑.
    - [ ] 帮助 (`py/plugins/help.py`): 迁移帮助逻辑.
    - [ ] 禁言 (`py/plugins/banme.py`): 迁移禁言逻辑.
    - [ ] 漫画 (`py/plugins/jm.py`): 迁移漫画功能.
    - [ ] 定时任务 (`py/autointime.py`): 迁移定时任务.
    - [ ] 系统消息 (`py/system_msg.py`): 迁移系统消息处理.

## 第四阶段：AI 智能体重构
- [ ] **AI 核心 (`py/plugins/ai/`)**
    - [ ] 创建 `py/plugins/ai/__init__.py`.
    - [ ] 协程化 `py/plugins/ai/ai_agent.py`.
    - [ ] 上下文管理 (`py/plugins/ai/ai_fulltokens.py`, `py/plugins/ai/ai_lowtokens.py`).
- [ ] **搜索增强 (`py/plugins/ai/ddgs/`)**
    - [ ] 将已修复的 `ddgs` 源码完整复制到 `py/plugins/ai/ddgs/` 目录(覆盖原有实现, 保留代理支持修复).
    - [ ] 封装 `py/plugins/ai/ddgs_search_tools.py`.
- [ ] **人设管理**
    - [ ] 迁移 `md/cat.md`, `md/expert.md`, `md/private.md`.

## 第五阶段：WebUI 与鉴权模块 (高安全 & 实时监控)
- [ ] **鉴权基础架构**
    - [ ] 引入 `PyJWT` 和 `passlib`.
    - [ ] 实现 JWT 签发与解析 (区分 role: `admin`, `user`, `temp`).
    - [ ] 实现密码哈希 (bcrypt).
    - [ ] 实现 FastAPI 依赖 `get_current_user` (自动校验 Token).
    - [ ] **[核心]** 实现权限守卫：校验 `token.group_id` 与请求参数是否一致.
- [ ] **访客链路 (Path A - SSE)**
    - [ ] **后端 (`py/html.py`)**: 实现内存 Pub/Sub 事件总线 (asyncio.Queue).
    - [ ] **后端**: 路由 `GET /api/stats/init` (读取 total.db).
    - [ ] **后端**: 路由 `GET /api/stats/stream` (SSE 挂载点).
    - [ ] **联动 (`py/router.py`)**: 消息处理完成后异步触发 `broadcast({"type": "recv"})`.
    - [ ] **前端 (`html/visitor_view.html`)**: 实现 `EventSource` 监听与 DOM 增量更新.
- [ ] **WebUI 页面与样式**
    - [ ] **前端 (`html/home.html`)**: 首页入口与导航布局.
    - [ ] **前端 (`html/feedback.html`)**: 反馈机器人问题的表单与展示页面.
    - [ ] **前端 (`html/css/main.css`)**: 公共基础样式(布局、字体、通用组件).
    - [ ] **前端 (`html/css/light.css`, `html/css/dark.css`)**: 浅色/深色主题样式与切换适配.
- [ ] **超级管理员链路 (Path C)**
    - [ ] **后端**: 路由 `POST /api/auth/admin-login` (校验全局 Key -> 签发 Admin JWT).
    - [ ] **后端**: 路由 `GET/POST /api/admin/*` (仅限 Admin JWT 访问).
    - [ ] **前端 (`html/a_login.html`)**: 登录页实现与 Token 存储.
    - [ ] **前端 (`html/admin.html`)**: 全局配置管理页.
- [ ] **群管链路 (Path B - 验证码流程)**
    - [ ] **后端**: 路由 `POST /api/auth/gen-code` (输入群号 -> 生成6位码 -> 存入内存 `verifications`).
    - [ ] **后端**: 路由 `GET /api/auth/check-status` (轮询验证码状态 -> 成功则签发 Temp JWT).
    - [ ] **联动 (`py/router.py`)**: 监听私聊事件 -> 校验发送人是否为该群管理员 (调用 OneBot API 获取群成员列表/信息) -> 匹配6位码 -> 更新内存状态为 "Verified".
    - [ ] **前端 (`html/g_loginmode.html`)**: 输入群号与验证码显示逻辑.
- [ ] **群管链路 (Path B - 注册与持久化)**
    - [ ] **后端**: 路由 `POST /api/auth/register` (校验 Temp JWT -> 存入 set.db -> 签发 User JWT).
    - [ ] **后端**: 路由 `POST /api/auth/group-login` (账号密码登录 -> 签发 User JWT).
    - [ ] **后端**: 路由 `GET/POST /api/groups/*` (校验 User/Temp JWT + GroupID).
    - [ ] **前端 (`html/groups.html`)**: 群设置页 & 注册弹窗逻辑.
    - [ ] **前端 (`html/g_login.html`, `html/g_groupid.html`)**: 实现相关页面逻辑.

## 第六阶段：测试交付
- [ ] **测试**
    - [ ] 连通性测试 (OneBot).
    - [ ] 压力测试 (高并发/内存).
    - [ ] 功能回归验证.
- [ ] **收尾**
    - [ ] 清理旧代码.
