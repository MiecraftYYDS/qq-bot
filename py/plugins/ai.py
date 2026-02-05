#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 对话插件
支持群聊和私聊 AI 对话
"""

import re
import sys
import os
import time
from typing import Dict, List

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import send_group_msg, send_private_msg
from py.sqline import db_manager
from py.selfset import SelfSettings
from py.setting import GroupSettings
from py.admin_state import admin_state

from .ai.ai_agent import create_agent


# 群聊系统提示词
GROUP_SYSTEM_PROMPT = """你是一只可爱的猫娘助手，名叫小喵。你会用可爱的语气回答问题，偶尔加入"喵~"等语气词。
你博学多才，可以回答各种问题，同时保持友好和可爱的态度。
如果用户问的问题需要最新信息，可以使用搜索工具。
回复要简洁，不要太长。"""

# 私聊系统提示词  
PRIVATE_SYSTEM_PROMPT = """你是一个智能助手，可以帮助用户解答各种问题。
你可以使用搜索工具获取最新信息，使用代码执行工具进行计算。
请用清晰、专业的语言回答问题。"""


class AIContextManager:
    """AI 上下文管理器"""
    
    MAX_CONTEXT_LENGTH = 20  # 最大上下文轮数
    
    @classmethod
    async def get_group_context(cls, group_id: int) -> List[Dict]:
        """获取群聊上下文"""
        db = await db_manager.get_db('aimemory')
        rows = await db.fetchall(
            """SELECT role, content FROM group_ai_context 
               WHERE group_id = ? ORDER BY id DESC LIMIT ?""",
            (group_id, cls.MAX_CONTEXT_LENGTH * 2)
        )
        
        context = [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        return context
    
    @classmethod
    async def add_group_context(cls, group_id: int, role: str, content: str):
        """添加群聊上下文"""
        db = await db_manager.get_db('aimemory')
        await db.execute(
            """INSERT INTO group_ai_context (group_id, user_id, role, content, create_time)
               VALUES (?, 0, ?, ?, ?)""",
            (group_id, role, content, int(time.time()))
        )
        await db.commit()
        
        # 清理旧上下文
        await db.execute(
            """DELETE FROM group_ai_context WHERE group_id = ? AND id NOT IN
               (SELECT id FROM group_ai_context WHERE group_id = ? ORDER BY id DESC LIMIT ?)""",
            (group_id, group_id, cls.MAX_CONTEXT_LENGTH * 2)
        )
        await db.commit()
    
    @classmethod
    async def clear_group_context(cls, group_id: int):
        """清除群聊上下文"""
        db = await db_manager.get_db('aimemory')
        await db.execute("DELETE FROM group_ai_context WHERE group_id = ?", (group_id,))
        await db.commit()
    
    @classmethod
    async def get_private_context(cls, user_id: int) -> List[Dict]:
        """获取私聊上下文"""
        db = await db_manager.get_db('aimemory')
        rows = await db.fetchall(
            """SELECT role, content FROM private_ai_context 
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, cls.MAX_CONTEXT_LENGTH * 2)
        )
        
        context = [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        return context
    
    @classmethod
    async def add_private_context(cls, user_id: int, role: str, content: str):
        """添加私聊上下文"""
        db = await db_manager.get_db('aimemory')
        await db.execute(
            """INSERT INTO private_ai_context (user_id, role, content, create_time)
               VALUES (?, ?, ?, ?)""",
            (user_id, role, content, int(time.time()))
        )
        await db.commit()
        
        # 清理旧上下文
        await db.execute(
            """DELETE FROM private_ai_context WHERE user_id = ? AND id NOT IN
               (SELECT id FROM private_ai_context WHERE user_id = ? ORDER BY id DESC LIMIT ?)""",
            (user_id, user_id, cls.MAX_CONTEXT_LENGTH * 2)
        )
        await db.commit()
    
    @classmethod
    async def clear_private_context(cls, user_id: int):
        """清除私聊上下文"""
        db = await db_manager.get_db('aimemory')
        await db.execute("DELETE FROM private_ai_context WHERE user_id = ?", (user_id,))
        await db.commit()


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    
    # #js 命令 - AI 解释
    js_match = re.match(r'^#js\s+(.+)$', raw_msg.strip(), re.DOTALL)
    if js_match:
        question = js_match.group(1)
        
        # 检查全局开关
        if not config.global_features.ai or not admin_state.ai_enabled:
            await send_group_msg(group_id, "❌ AI 功能已关闭")
            return True
        
        # 检查群开关
        if not await GroupSettings.get_setting(group_id, 'ai'):
            await send_group_msg(group_id, "❌ 本群 AI 功能已关闭")
            return True
        
        await send_group_msg(group_id, "🤔 思考中...")
        
        try:
            agent = await create_agent(group_id, user_id)
            context = [{"role": "system", "content": "你是一个专业的解释助手，请详细解释用户的问题。"}]
            
            reply = await agent.chat(question, context)
            await send_group_msg(group_id, reply)
        except Exception as e:
            await send_group_msg(group_id, f"❌ AI 处理失败: {str(e)}")
        
        return True
    
    # 检查是否 @ 了机器人
    at_pattern = rf'\[CQ:at,qq={config.bot.qq_id}\]'
    if re.search(at_pattern, raw_msg):
        # 检查全局开关
        if not config.global_features.ai or not admin_state.ai_enabled:
            return False
        
        # 检查群开关
        if not await GroupSettings.get_setting(group_id, 'ai'):
            return False
        
        # 提取消息内容（移除 @ 部分）
        message = re.sub(at_pattern, '', raw_msg).strip()
        
        if not message:
            await send_group_msg(group_id, "喵？有什么事吗？")
            return True
        
        try:
            # 获取上下文
            context = await AIContextManager.get_group_context(group_id)
            context.insert(0, {"role": "system", "content": GROUP_SYSTEM_PROMPT})
            
            # 创建 agent 并对话
            agent = await create_agent(group_id, user_id)
            reply = await agent.chat(message, context)
            
            # 保存上下文
            await AIContextManager.add_group_context(group_id, "user", message)
            await AIContextManager.add_group_context(group_id, "assistant", reply)
            
            await send_group_msg(group_id, reply)
        except Exception as e:
            await send_group_msg(group_id, f"喵呜...出错了: {str(e)}")
        
        return True
    
    return False


async def handle_private_message(event):
    """处理私聊消息"""
    raw_msg = event.raw_message or ''
    user_id = event.user_id
    
    # #new - 新建对话
    if raw_msg.strip() == '#new':
        await AIContextManager.clear_private_context(user_id)
        await send_private_msg(user_id, "✨ 已创建新对话，上下文已清除")
        return True
    
    # 跳过命令消息
    if raw_msg.startswith('#'):
        return False
    
    # 普通消息 - AI 对话
    try:
        # 获取上下文
        context = await AIContextManager.get_private_context(user_id)
        context.insert(0, {"role": "system", "content": PRIVATE_SYSTEM_PROMPT})
        
        # 创建 agent 并对话
        agent = await create_agent(None, user_id)
        reply = await agent.chat(raw_msg, context)
        
        # 保存上下文
        await AIContextManager.add_private_context(user_id, "user", raw_msg)
        await AIContextManager.add_private_context(user_id, "assistant", reply)
        
        await send_private_msg(user_id, reply)
    except Exception as e:
        await send_private_msg(user_id, f"处理失败: {str(e)}")
    
    return True


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)
    plugin_manager.register_private_handler(handle_private_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("🤖 AI 对话插件测试")
    print("=" * 50)
    
    print("\n📦 检查依赖:")
    try:
        from zhipuai import ZhipuAI
        print("  ✅ zhipuai SDK")
    except ImportError:
        print("  ❌ zhipuai 未安装，请运行: pip install zhipuai")
    
    print(f"\n⚙️ 配置:")
    print(f"  API Key: {config.ai.api_key[:10]}***" if config.ai.api_key else "  ❌ API Key 未配置")
    print(f"  Model: {config.ai.model}")
    
    print("\n📝 系统提示词预览:")
    print("  [群聊] " + GROUP_SYSTEM_PROMPT[:50] + "...")
    print("  [私聊] " + PRIVATE_SYSTEM_PROMPT[:50] + "...")
    
    print("\n💡 命令列表:")
    print("  [群聊] #js <问题> - AI 解释问题")
    print("  [群聊] @机器人 <消息> - 与 AI 对话")
    print("  [私聊] 直接发消息 - 与 AI 对话")
    print("  [私聊] #new - 清除上下文，开始新对话")
    
    # 交互测试
    print("\n" + "=" * 50)
    test_input = input("输入测试问题 (直接回车跳过): ").strip()
    if test_input:
        print("\n⏳ 正在调用 AI...")
        
        async def test_ai():
            try:
                agent = await create_agent(None, 0)
                context = [{"role": "system", "content": "你是一个智能助手，请简洁回答问题。"}]
                reply = await agent.chat(test_input, context)
                print(f"\n🤖 AI 回复:\n{reply}")
            except Exception as e:
                print(f"\n❌ 错误: {e}")
        
        asyncio.run(test_ai())
    
    print("\n✅ 插件模块加载正常")
