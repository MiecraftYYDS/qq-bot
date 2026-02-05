#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
小功能插件 - ping, 点赞, 设置等
"""

import re
import sys
import os

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import onebot, send_group_msg, send_private_msg
from py.setting import GroupSettings
from py.selfset import SelfSettings


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    message_id = event.message_id
    self_id = event.self_id
    
    # #ping - 状态检查
    if raw_msg.strip() == '#ping':
        await send_group_msg(group_id, f"🤖 机器人运行中\n📦 版本: {config.bot.version}")
        return True
    
    # #dzw - 点赞
    if raw_msg.strip() == '#dzw':
        success = await onebot.send_like(user_id, 10)
        if success:
            await send_group_msg(group_id, f"[CQ:at,qq={user_id}] 已为你点赞10次！")
        else:
            await send_group_msg(group_id, f"[CQ:at,qq={user_id}] 点赞失败，可能今日已达上限")
        return True
    
    # #settings - 群设置
    settings_match = re.match(r'^#settings\s+(\w+)\s+(on|off)$', raw_msg.strip())
    if settings_match:
        # 检查权限（需要管理员）
        member_info = await onebot.get_group_member_info(group_id, user_id)
        if not member_info or member_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "❌ 此命令需要管理员权限")
            return True
        
        setting_name = settings_match.group(1)
        value = settings_match.group(2) == 'on'
        
        if setting_name not in GroupSettings.SETTING_FIELDS:
            await send_group_msg(group_id, f"❌ 未知设置项: {setting_name}")
            return True
        
        success = await GroupSettings.set_setting(group_id, setting_name, value)
        if success:
            status = "开启" if value else "关闭"
            await send_group_msg(group_id, f"✅ 已{status} {setting_name}")
        else:
            await send_group_msg(group_id, "❌ 设置失败")
        return True
    
    # #setformat - 设置消息格式
    format_match = re.match(r'^#setformat\s+(welcome|farewell)\s+(.+)$', raw_msg.strip(), re.DOTALL)
    if format_match:
        member_info = await onebot.get_group_member_info(group_id, user_id)
        if not member_info or member_info.get('role') not in ('admin', 'owner'):
            await send_group_msg(group_id, "❌ 此命令需要管理员权限")
            return True
        
        format_type = format_match.group(1)
        format_text = format_match.group(2).strip()
        
        success = await GroupSettings.set_format(group_id, format_type, format_text)
        if success:
            await send_group_msg(group_id, f"✅ 已设置 {format_type} 格式")
        else:
            await send_group_msg(group_id, "❌ 设置失败")
        return True
    
    # #selfset - 机器人管理员设置
    selfset_match = re.match(r'^#selfset\s+(\w+)\s+(.+)$', raw_msg.strip())
    if selfset_match:
        if user_id != config.bot.admin_qq:
            await send_group_msg(group_id, "❌ 此命令仅限机器人管理员使用")
            return True
        
        cmd = selfset_match.group(1)
        value = selfset_match.group(2).strip()
        
        if cmd == 'qd':
            enabled = value.lower() == 'on'
            await SelfSettings.set_checkin_enabled(group_id, enabled)
            status = "开启" if enabled else "关闭"
            await send_group_msg(group_id, f"✅ 已{status}群签到功能")
            return True
        
        if cmd == 'cy':
            try:
                hour = int(value)
                if hour < -1 or hour > 23:
                    raise ValueError()
                await SelfSettings.set_wordcloud_hour(group_id, hour)
                if hour == -1:
                    await send_group_msg(group_id, "✅ 已关闭自动词云")
                else:
                    await send_group_msg(group_id, f"✅ 已设置自动词云时间为 {hour}:00")
            except ValueError:
                await send_group_msg(group_id, "❌ 参数错误，请输入 -1 到 23 之间的整数")
            return True
        
        if cmd == 'ai':
            enabled = value.lower() == 'on'
            await SelfSettings.set_ai_enabled(group_id, enabled)
            status = "开启" if enabled else "关闭"
            await send_group_msg(group_id, f"✅ 已{status}群AI功能")
            return True
    
    # #tx - 设置头衔（仅群主）
    tx_match = re.match(r'^#tx\s+(?:\[CQ:at,qq=(\d+)\]|(\d+))\s*(.*)$', raw_msg.strip())
    if tx_match:
        member_info = await onebot.get_group_member_info(group_id, self_id)
        if not member_info or member_info.get('role') != 'owner':
            await send_group_msg(group_id, "❌ 此命令仅限群主使用")
            return True
        
        target_id = int(tx_match.group(1) or tx_match.group(2))
        title = tx_match.group(3).strip() or ""
        
        success = await onebot.set_group_special_title(group_id, target_id, title)
        if success:
            await send_group_msg(group_id, f"✅ 已设置 {target_id} 的头衔为: {title or '(空)'}")
        else:
            await send_group_msg(group_id, "❌ 设置头衔失败")
        return True
    
    return False


async def handle_private_message(event):
    """处理私聊消息"""
    raw_msg = event.raw_message or ''
    user_id = event.user_id
    
    # #ping
    if raw_msg.strip() == '#ping':
        await send_private_msg(user_id, f"🤖 机器人运行中\n📦 版本: {config.bot.version}")
        return True
    
    # #dzw
    if raw_msg.strip() == '#dzw':
        success = await onebot.send_like(user_id, 10)
        if success:
            await send_private_msg(user_id, "已为你点赞10次！")
        else:
            await send_private_msg(user_id, "点赞失败，可能今日已达上限")
        return True
    
    # #sx - 私信管理员
    sx_match = re.match(r'^#sx\s+(.+)$', raw_msg.strip(), re.DOTALL)
    if sx_match:
        content = sx_match.group(1)
        admin_msg = f"📨 来自 {user_id} 的私信:\n{content}"
        await send_private_msg(config.bot.admin_qq, admin_msg)
        await send_private_msg(user_id, "✅ 消息已发送给管理员")
        return True
    
    # WebUI 验证码验证 - 检测6位纯数字
    code = raw_msg.strip()
    if re.match(r'^\d{6}$', code):
        from py.html import verify_group_admin_code
        result = await verify_group_admin_code(user_id, code)
        if result["success"]:
            await send_private_msg(user_id, f"✅ {result['message']}")
        else:
            await send_private_msg(user_id, f"❌ {result['message']}")
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)
    plugin_manager.register_private_handler(handle_private_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("⚙️ 小功能插件测试")
    print("=" * 50)
    
    print(f"\n📦 版本: {config.bot.version}")
    print(f"🤖 Bot QQ: {config.bot.qq}")
    print(f"👤 管理员 QQ: {config.bot.admin_qq}")
    
    print("\n💡 群命令列表:")
    print("  #ping - 检查状态")
    print("  #dzw - 点赞10次")
    print("  #settings <功能> <on|off> - 群设置")
    print("  #setformat <welcome|farewell> <格式> - 设置消息格式")
    print("  #selfset qd <on|off> - 开关签到")
    print("  #selfset cy <-1~23> - 设置词云时间")
    print("  #selfset ai <on|off> - 开关AI")
    print("  #tx <QQ/@> <头衔> - 设置头衔(仅群主)")
    
    print("\n💡 私聊命令列表:")
    print("  #ping - 检查状态")
    print("  #dzw - 点赞10次")
    print("  #sx <内容> - 私信管理员")
    
    print("\n✅ 插件模块加载正常")
