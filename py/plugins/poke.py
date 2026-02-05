#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""戳一戳和趣味互动插件

对齐旧版 bot.py 行为：
- 文本触发："摸摸"/"ccb"
- 戳一戳：被戳时回戳，戳别人时帮忙回戳
"""

import random
import re
import sys
import os

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.onebot_api import send_group_msg, send_group_reply, onebot
from py.config import config
from py.setting import GroupSettings
from .ai.ai_agent import create_agent


# 摸摸回复列表
MOMO_REPLIES = [
    "喵~",
    "蹭蹭~",
    "咕噜咕噜~",
    "嗯嗯~舒服~",
    "再摸摸~",
    "喵呜~",
    "（满足地眯起眼睛）",
    "你的手好温暖~",
]



# 戳一戳回复列表
POKE_REPLIES = [
    "别戳啦！",
    "戳什么戳！",
    "再戳我就要生气了！",
    "干嘛戳我 >_<",
    "好痒！",
    "有什么事吗？",
    "？",
    "喵？",
]


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    message_id = event.message_id
    
    # 检查全局开关
    if not config.global_features.poke:
        return False
    
    # 检查群开关
    if not await GroupSettings.get_setting(group_id, 'poke'):
        return False
    
    # 摸摸
    if raw_msg.strip() in ('摸摸', '摸', 'momo', '摸摸头'):
        # 复刻 bot.py 行为：优先引用同条消息或 @ 的目标
        # 如果包含回复 CQ，引用同一条
        reply_match = re.search(r"\[CQ:reply,id=(\d+)\]", raw_msg)
        at_match = re.search(r"\[CQ:at,qq=(\d+)\]", raw_msg)
        text = "摸摸贴贴抱抱揉揉捏捏舔舔亲亲吃吃踩踩蹭蹭入入草草"
        if reply_match:
            try:
                reply_id = int(reply_match.group(1))
                await send_group_reply(group_id, reply_id, text)
            except Exception:
                await send_group_reply(group_id, message_id, text)
        elif at_match:
            at_user = at_match.group(1)
            await send_group_msg(group_id, f"[CQ:at,qq={at_user}] {text}")
        else:
            await send_group_reply(group_id, message_id, text)
        return True
    
    # 踩背
    if raw_msg.strip() in ('ccb', 'CCB', '踩踩背'):
        await send_group_msg(group_id, "踩背！")
        return True

    
    return False


async def handle_notice(event):
    """处理通知事件"""
    notice_type = event.notice_type
    
    # 戳一戳
    if notice_type == 'notify':
        sub_type = getattr(event, 'sub_type', None)
        if sub_type == 'poke':
            # 检查全局开关
            if not config.global_features.poke:
                return False
            
            target_id = getattr(event, 'target_id', None)
            group_id = event.group_id
            
            # 戳到机器人：回戳并回复（优先 AI 回复）
            if target_id == config.bot.qq_id and group_id:
                if not await GroupSettings.get_setting(group_id, 'poke'):
                    return False

                # 先回戳来源用户（OneBot V11 动作名 group_poke）
                try:
                    await onebot.call_api('group_poke', {"group_id": group_id, "user_id": event.user_id})
                except Exception:
                    pass

                # AI 回复，失败则用固定回复
                try:
                    agent = await create_agent(group_id, event.user_id)
                    context = [{"role": "system", "content": f"你是可爱的猫娘，被群友(昵称:{event.sender.nickname})戳了一下，请用简短亲和的口吻回复。不要暴露你是AI。"}]
                    reply = await agent.chat("有人戳了你，回应一下", context)
                except Exception:
                    reply = random.choice(POKE_REPLIES)

                await send_group_msg(group_id, reply)
                return True
    
            # 戳别人：如果不是机器人自己戳别人，帮忙回戳目标
            if group_id and target_id and event.user_id != config.bot.qq_id:
                try:
                    await onebot.call_api('group_poke', {"group_id": group_id, "user_id": target_id})
                except Exception:
                    pass
                return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)
    plugin_manager.register_notice_handler(handle_notice)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("👆 戳一戳/趣味互动插件测试")
    print("=" * 50)
    
    print("\n📝 摸摸回复列表:")
    for i, reply in enumerate(MOMO_REPLIES, 1):
        print(f"  {i}. {reply}")
    
    
    
    print("\n📝 戳一戳回复列表:")
    for i, reply in enumerate(POKE_REPLIES, 1):
        print(f"  {i}. {reply}")
    
    print("\n🎲 随机测试:")
    print(f"  摸摸: {random.choice(MOMO_REPLIES)}")
    print(f"  戳一戳: {random.choice(POKE_REPLIES)}")
    print(f"  踩背: 踩背!")
    
    print("\n✅ 插件模块加载正常")
