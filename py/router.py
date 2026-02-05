#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
业务路由模块 - 实现 webhook 接收和事件分发
支持动态插件加载
"""

import importlib
import asyncio
from typing import Dict, Any, List, Callable, Optional
from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel

from .config import config
from .sqline import add_group_message, update_stats
from .onebot_api import onebot
from .admin_state import admin_state


# 创建路由器
router = APIRouter()


# ==================== 数据模型 ====================

class OneBotEvent(BaseModel):
    """OneBot 事件基础模型"""
    time: int
    self_id: int
    post_type: str
    
    # 消息事件
    message_type: Optional[str] = None
    sub_type: Optional[str] = None
    message_id: Optional[int] = None
    user_id: Optional[int] = None
    group_id: Optional[int] = None
    message: Optional[Any] = None
    raw_message: Optional[str] = None
    sender: Optional[Dict] = None
    
    # 通知事件
    notice_type: Optional[str] = None
    operator_id: Optional[int] = None
    target_id: Optional[int] = None
    
    # 请求事件
    request_type: Optional[str] = None
    flag: Optional[str] = None
    comment: Optional[str] = None
    
    class Config:
        extra = 'allow'


# ==================== 插件系统 ====================

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._group_handlers: List[Callable] = []
        self._private_handlers: List[Callable] = []
        self._notice_handlers: List[Callable] = []
        self._request_handlers: List[Callable] = []
        self._meta_handlers: List[Callable] = []
        self._loaded_plugins: List[str] = []
    
    def register_group_handler(self, handler: Callable):
        """注册群消息处理器"""
        self._group_handlers.append(handler)
    
    def register_private_handler(self, handler: Callable):
        """注册私聊消息处理器"""
        self._private_handlers.append(handler)
    
    def register_notice_handler(self, handler: Callable):
        """注册通知事件处理器"""
        self._notice_handlers.append(handler)
    
    def register_request_handler(self, handler: Callable):
        """注册请求事件处理器"""
        self._request_handlers.append(handler)
    
    def register_meta_handler(self, handler: Callable):
        """注册元事件处理器"""
        self._meta_handlers.append(handler)
    
    def load_plugin(self, plugin_name: str) -> bool:
        """加载插件模块"""
        try:
            module = importlib.import_module(f'py.plugins.{plugin_name}')
            
            # 调用插件的 register 函数
            if hasattr(module, 'register'):
                module.register(self)
                self._loaded_plugins.append(plugin_name)
                print(f"✅ 插件加载成功: {plugin_name}")
                return True
            else:
                print(f"⚠️ 插件 {plugin_name} 没有 register 函数")
                return False
                
        except Exception as e:
            print(f"❌ 插件加载失败 {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self):
        """加载所有插件"""
        # 插件加载顺序（按优先级）
        plugins = [
            'help',       # 帮助命令
            'small',      # 小功能
            'cy',         # 词云
            'qorqtp',     # 语录
            'repeat',     # 复读
            'poke',       # 戳一戳
            'banme',      # 禁言
            'jm',         # 漫画
            'ai',         # AI (最后加载)
        ]
        
        for plugin in plugins:
            self.load_plugin(plugin)
        
        # 加载系统消息处理（作为模块导入）
        try:
            from py import system_msg
            system_msg.register(self)
            print("✅ 系统消息处理模块加载成功")
        except Exception as e:
            print(f"❌ 系统消息处理模块加载失败: {e}")
        
        print(f"📦 已加载 {len(self._loaded_plugins)} 个插件")
    
    async def dispatch_group_message(self, event: OneBotEvent) -> bool:
        """分发群消息事件"""
        for handler in self._group_handlers:
            try:
                result = await handler(event)
                if result:  # 如果处理器返回 True，停止继续分发
                    return True
            except Exception as e:
                print(f"[插件错误] 群消息处理: {e}")
        return False
    
    async def dispatch_private_message(self, event: OneBotEvent) -> bool:
        """分发私聊消息事件"""
        for handler in self._private_handlers:
            try:
                result = await handler(event)
                if result:
                    return True
            except Exception as e:
                print(f"[插件错误] 私聊消息处理: {e}")
        return False
    
    async def dispatch_notice(self, event: OneBotEvent) -> bool:
        """分发通知事件"""
        for handler in self._notice_handlers:
            try:
                result = await handler(event)
                if result:
                    return True
            except Exception as e:
                print(f"[插件错误] 通知事件处理: {e}")
        return False
    
    async def dispatch_request(self, event: OneBotEvent) -> bool:
        """分发请求事件"""
        for handler in self._request_handlers:
            try:
                result = await handler(event)
                if result:
                    return True
            except Exception as e:
                print(f"[插件错误] 请求事件处理: {e}")
        return False


# 全局插件管理器
plugin_manager = PluginManager()


# ==================== 事件总线 (SSE 支持) ====================

class EventBus:
    """内存事件总线，用于 SSE 推送"""
    
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
    
    def subscribe(self) -> asyncio.Queue:
        """订阅事件"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def broadcast(self, event: Dict):
        """广播事件"""
        for queue in self._subscribers:
            try:
                await queue.put(event)
            except Exception:
                pass


# 全局事件总线
event_bus = EventBus()


# ==================== 路由处理 ====================

async def process_event(event: OneBotEvent):
    """处理 OneBot 事件"""
    # 全局运行时开关：关闭时直接忽略
    if not admin_state.enabled:
        return
    post_type = event.post_type
    
    if post_type == 'message':
        # 消息事件
        message_type = event.message_type
        
        if message_type == 'group':
            # 记录群消息
            raw_msg = event.raw_message or ''
            if event.group_id and event.user_id:
                await add_group_message(event.group_id, event.user_id, raw_msg)
            
            # 分发给插件
            await plugin_manager.dispatch_group_message(event)
            
            # 更新统计
            await update_stats('total_messages')
            
            # SSE 广播
            await event_bus.broadcast({"type": "recv", "group_id": event.group_id})
            
        elif message_type == 'private':
            await plugin_manager.dispatch_private_message(event)
            await update_stats('total_messages')
    
    elif post_type == 'notice':
        # 通知事件
        await plugin_manager.dispatch_notice(event)
    
    elif post_type == 'request':
        # 请求事件
        await plugin_manager.dispatch_request(event)
    
    elif post_type == 'meta_event':
        # 元事件（心跳等）
        pass


@router.post("/webhook")
@router.post("/onebot")
@router.post("/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    OneBot 事件接收端点
    支持多个路径: /webhook, /onebot, /
    """
    # Token 验证
    if config.onebot.token:
        auth_header = request.headers.get("Authorization", "")
        expected = f"Bearer {config.onebot.token}"
        if auth_header != expected:
            # 也检查 X-Signature 方式（某些 OneBot 实现使用）
            signature = request.headers.get("X-Signature", "")
            if not signature:
                return {"status": "error", "message": "Unauthorized"}
    
    try:
        data = await request.json()
        event = OneBotEvent(**data)
        
        # 异步处理事件
        background_tasks.add_task(process_event, event)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"[Webhook 错误] {e}")
        return {"status": "error", "message": str(e)}


@router.get("/")
async def root():
    """根路由"""
    return {
        "name": "QQ Bot",
        "version": config.bot.version,
        "status": "running"
    }


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


# ==================== 初始化 ====================

def init_plugins():
    """初始化插件系统"""
    plugin_manager.load_all_plugins()


# 在模块加载时初始化插件
# 注意：实际初始化在 start.py 的 lifespan 中调用
