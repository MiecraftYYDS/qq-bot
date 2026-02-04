#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
机器人主入口 - FastAPI + Uvicorn 异步架构
"""

import os
import sys

# 锁定工作目录为脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from py.config import config
from py.sqline import db_manager
from py.router import router
from py.autointime import scheduler_manager
from py.html import html_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("=" * 50)
    print(f"🤖 机器人启动中... 版本: {config.bot.version}")
    print("=" * 50)
    
    # 初始化数据库
    await db_manager.init_all()
    print("✅ 数据库初始化完成")
    
    # 加载插件
    from py.router import plugin_manager
    plugin_manager.load_all_plugins()
    
    # 启动定时任务调度器
    scheduler_manager.start()
    print("✅ 定时任务调度器启动")
    
    print(f"🌐 服务监听: http://{config.server.host}:{config.server.port}")
    print("=" * 50)
    
    yield
    
    # 关闭时清理
    print("\n🛑 机器人关闭中...")
    scheduler_manager.shutdown()
    await db_manager.close_all()
    print("👋 机器人已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="QQ Bot API",
    description="基于 FastAPI 的 QQ 机器人服务",
    version=config.bot.version,
    lifespan=lifespan
)

# 注册路由
app.include_router(router)
app.include_router(html_router)

# 挂载静态文件
app.mount("/css", StaticFiles(directory="html/css"), name="css")
app.mount("/", StaticFiles(directory="html", html=True), name="html")


def main():
    """主函数"""
    uvicorn.run(
        "start:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
