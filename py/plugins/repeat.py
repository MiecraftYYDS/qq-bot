#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
复读机插件
"""

import re
import random
import sys
import os

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.sqline import db_manager
from py.onebot_api import send_group_msg
from py.config import config
from py.setting import GroupSettings, get_repeat_probability, get_exclamation_probability


async def get_last_msg(group_id: int):
    """获取群最后一条消息状态"""
    db = await db_manager.get_db('data')
    row = await db.fetchone(
        "SELECT user_id, text FROM last_msg WHERE group_id = ?",
        (group_id,)
    )
    if row:
        return {'user_id': row[0], 'text': row[1]}
    return None


async def set_last_msg(group_id: int, user_id: int, text: str):
    """设置群最后一条消息"""
    db = await db_manager.get_db('data')
    await db.execute(
        "INSERT OR REPLACE INTO last_msg (group_id, user_id, text) VALUES (?, ?, ?)",
        (group_id, user_id, text)
    )
    await db.commit()


async def get_repeated(group_id: int):
    """获取复读状态"""
    db = await db_manager.get_db('data')
    row = await db.fetchone(
        "SELECT text, done FROM repeated_once WHERE group_id = ? AND user_id = 0",
        (group_id,)
    )
    if row:
        return {'text': row[0], 'done': bool(row[1])}
    return None


async def set_repeated(group_id: int, text: str):
    """设置已复读"""
    db = await db_manager.get_db('data')
    await db.execute(
        "INSERT OR REPLACE INTO repeated_once (group_id, user_id, text, done) VALUES (?, 0, ?, 1)",
        (group_id, text)
    )
    await db.commit()


async def clear_repeated(group_id: int):
    """清除复读状态"""
    db = await db_manager.get_db('data')
    await db.execute(
        "DELETE FROM repeated_once WHERE group_id = ? AND user_id = 0",
        (group_id,)
    )
    await db.commit()


def transform_exclamation(text: str) -> str:
    """变换感叹号结尾的句子"""
    # 随机变换方式
    transforms = [
        lambda t: t[:-1] + '？',  # 换成问号
        lambda t: t[:-1] + '~',   # 换成波浪号
        lambda t: t + t[-1] * random.randint(1, 3),  # 重复感叹号
        lambda t: t.upper() if t.isascii() else t,  # 大写（英文）
    ]
    
    return random.choice(transforms)(text)


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    
    # 检查全局开关
    if not config.global_features.repeat:
        return False
    
    # 检查群开关
    if not await GroupSettings.get_setting(group_id, 'repeat'):
        return False
    
    # 忽略命令
    if raw_msg.startswith('#'):
        return False
    
    # 忽略空消息
    if not raw_msg.strip():
        return False
    
    # 获取上一条消息
    last_msg = await get_last_msg(group_id)
    
    # 检查是否需要复读
    if last_msg and last_msg['text'] == raw_msg and last_msg['user_id'] != user_id:
        # 检查是否已经复读过
        repeated = await get_repeated(group_id)
        
        if not repeated or repeated['text'] != raw_msg:
            # 随机决定是否复读（使用可配置概率）
            repeat_prob = await get_repeat_probability(group_id)
            if random.random() < repeat_prob:
                await send_group_msg(group_id, raw_msg)
                await set_repeated(group_id, raw_msg)
                await set_last_msg(group_id, user_id, raw_msg)
                return True
    
    # 检查感叹号结尾的短句（触发变体复读）
    if len(raw_msg) <= 20 and raw_msg.endswith(('!', '！')):
        exclamation_prob = await get_exclamation_probability(group_id)
        if random.random() < exclamation_prob:
            transformed = transform_exclamation(raw_msg)
            await send_group_msg(group_id, transformed)
            await set_last_msg(group_id, user_id, raw_msg)
            return True
    
    # 更新最后消息
    await set_last_msg(group_id, user_id, raw_msg)
    
    # 如果消息改变，清除复读状态
    if last_msg and last_msg['text'] != raw_msg:
        await clear_repeated(group_id)
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("🔁 复读机插件测试")
    print("=" * 50)
    
    print("\n📝 感叹号变换测试:")
    test_texts = ["好厉害！", "太棒了！", "Amazing!", "哇！"]
    for text in test_texts:
        print(f"  原文: {text}")
        for i in range(3):
            print(f"    变换{i+1}: {transform_exclamation(text)}")
    
    print("\n📊 概率配置:")
    print(f"  默认复读概率: {config.repeat_settings.repeat_probability}")
    print(f"  默认感叹号触发概率: {config.repeat_settings.exclamation_probability}")
    
    print("\n💡 功能说明:")
    print("  - 当连续两人发送相同消息时，按配置概率触发复读")
    print("  - 以!或！结尾的短句，按配置概率触发变体复读")
    print("  - 群内可单独设置概率，未设置则使用全局配置")
    
    print("\n✅ 插件模块加载正常")
