#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
禁言管理插件
"""

import re
import random
import sys
import os

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import onebot, send_group_msg
from py.sentence_pool import get_gl, get_fgl
from py.setting import GroupSettings


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    
    # 禁言我 - 随机禁言
    if raw_msg.strip() in ('禁言我', 'mute me', '#banme'):
        # 检查全局开关和群开关
        if not config.global_features.banme:
            return False
        if not await GroupSettings.get_setting(group_id, 'banme'):
            return False
        
        # 检查机器人是否有管理员权限
        bot_info = await onebot.get_group_member_info(group_id, config.bot.qq_id)
        if not bot_info or bot_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "我没有管理员权限，无法执行禁言操作")
            return True
        
        # 检查用户是否是管理员
        user_info = await onebot.get_group_member_info(group_id, user_id)
        if user_info and user_info.get('role') in ('admin', 'owner'):
            # 管理员禁言自己，发送管理员专属语录
            quote = get_gl()
            await send_group_msg(group_id, f"[CQ:reply,id={event.message_id}]{quote}")
        else:
            # 随机1-20分钟
            duration = random.randint(1, 20) * 60
            success = await onebot.set_group_ban(group_id, user_id, duration)
            if success:
                quote = get_fgl()
                msg = f"[CQ:reply,id={event.message_id}]{quote} 恭喜获得口球{duration // 60}分钟"
                await send_group_msg(group_id, msg)
            else:
                await send_group_msg(group_id, "禁言失败，可能机器人没有管理员权限")
        return True
    
    # #mute - 禁言指定用户（管理员命令，不受 banme 开关限制）
    mute_match = re.match(r'^#mute\s+(?:\[CQ:at,qq=(\d+)\]|(\d+))(?:\s+(\d+))?$', raw_msg.strip())
    if mute_match:
        # 检查机器人权限
        bot_info = await onebot.get_group_member_info(group_id, config.bot.qq_id)
        if not bot_info or bot_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "我没有管理员权限，无法执行禁言操作")
            return True
        
        # 检查用户权限
        member_info = await onebot.get_group_member_info(group_id, user_id)
        if not member_info or member_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "❌ 此命令需要管理员权限")
            return True
        
        target_id = int(mute_match.group(1) or mute_match.group(2))
        
        # 检查目标是否是管理员
        target_info = await onebot.get_group_member_info(group_id, target_id)
        if target_info and target_info.get('role') in ('admin', 'owner'):
            quote = get_gl()
            await send_group_msg(group_id, quote)
            return True
        
        duration_min = int(mute_match.group(3)) if mute_match.group(3) else random.randint(1, 20)
        duration = duration_min * 60
        
        # 限制最长禁言时间
        if duration > 30 * 24 * 60 * 60:
            duration = 30 * 24 * 60 * 60
        
        success = await onebot.set_group_ban(group_id, target_id, duration)
        if success:
            await send_group_msg(group_id, f"已给予{target_id} {duration_min}分钟口球，立刻解禁输入#jj {target_id}")
            quote = get_fgl()
            await send_group_msg(group_id, f"[CQ:at,qq={target_id}] {quote}")
        else:
            await send_group_msg(group_id, "❌ 禁言失败")
        return True
    
    # #jj - 解禁
    jj_match = re.match(r'^#jj\s+(?:\[CQ:at,qq=(\d+)\]|(\d+))$', raw_msg.strip())
    if jj_match:
        # 检查机器人权限
        bot_info = await onebot.get_group_member_info(group_id, config.bot.qq)
        if not bot_info or bot_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "我没有管理员权限，无法执行解禁操作")
            return True
        
        # 检查用户权限
        member_info = await onebot.get_group_member_info(group_id, user_id)
        if not member_info or member_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "❌ 此命令需要管理员权限")
            return True
        
        target_id = int(jj_match.group(1) or jj_match.group(2))
        
        # 检查目标是否是管理员
        target_info = await onebot.get_group_member_info(group_id, target_id)
        if target_info and target_info.get('role') in ('admin', 'owner'):
            await send_group_msg(group_id, "又来开玩笑")
            return True
        
        success = await onebot.set_group_ban(group_id, target_id, 0)
        if success:
            await send_group_msg(group_id, f"✅ 已解除 {target_id} 的禁言")
        else:
            await send_group_msg(group_id, "❌ 解禁失败")
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("🔇 禁言插件测试")
    print("=" * 50)
    
    # 测试语录
    from py.sentence_pool import get_gl, get_fgl
    print("\n📝 管理员语录 (get_gl):")
    for i in range(3):
        print(f"  {i+1}. {get_gl()}")
    
    print("\n📝 普通用户语录 (get_fgl):")
    for i in range(3):
        print(f"  {i+1}. {get_fgl()}")
    
    print("\n✅ 插件模块加载正常")
    print("\n💡 命令列表:")
    print("  禁言我 / mute me / #banme - 随机禁言自己1-20分钟")
    print("  #mute <QQ/@> [分钟] - 禁言指定用户")
    print("  #jj <QQ/@> - 解除禁言")
