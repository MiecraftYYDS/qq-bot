#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统消息处理模块
处理入群、退群、管理员变更等通知
"""

import time
from py.config import config
from py.onebot_api import onebot, send_group_msg
from py.setting import GroupSettings, get_group_setting
from py.sqline import db_manager


async def handle_member_increase(event):
    """处理成员加入事件"""
    group_id = event.group_id
    user_id = getattr(event, 'user_id', None)
    
    if not user_id:
        return False
    
    # 检查是否开启欢迎消息
    welcome_enabled = await get_group_setting(group_id, 'welcome')
    if not welcome_enabled:
        return False
    
    # 获取欢迎格式
    welcome_format = await GroupSettings.get_format(group_id, 'welcome')
    
    # 替换变量
    message = welcome_format.replace('{qqid}', str(user_id))
    message = message.replace('{at}', f'[CQ:at,qq={user_id}]')
    
    await send_group_msg(group_id, message)
    return True


async def handle_member_decrease(event):
    """处理成员退出事件"""
    group_id = event.group_id
    user_id = getattr(event, 'user_id', None)
    
    if not user_id:
        return False
    
    # 检查是否开启退群公告
    farewell_enabled = await get_group_setting(group_id, 'farewell')
    if not farewell_enabled:
        return False
    
    # 获取退群格式
    farewell_format = await GroupSettings.get_format(group_id, 'farewell')
    
    # 获取用户昵称
    nickname = await onebot.get_nickname(group_id, user_id)
    
    # 替换变量
    message = farewell_format.replace('{qqid}', str(user_id))
    message = message.replace('{nickname}', nickname)
    
    await send_group_msg(group_id, message)
    return True


async def handle_admin_change(event):
    """处理管理员变更事件"""
    group_id = event.group_id
    user_id = getattr(event, 'user_id', None)
    sub_type = getattr(event, 'sub_type', None)
    
    if not user_id:
        return False
    
    # 检查是否开启广播
    broadcast_enabled = await get_group_setting(group_id, 'broadcast')
    if not broadcast_enabled:
        return False
    
    nickname = await onebot.get_nickname(group_id, user_id)
    
    if sub_type == 'set':
        message = f"🎉 {nickname}({user_id}) 已被设为管理员"
    elif sub_type == 'unset':
        message = f"📢 {nickname}({user_id}) 已被取消管理员"
    else:
        return False
    
    await send_group_msg(group_id, message)
    return True


async def handle_group_request(event):
    """处理入群申请"""
    group_id = event.group_id
    user_id = getattr(event, 'user_id', None)
    flag = getattr(event, 'flag', None)
    comment = getattr(event, 'comment', '')
    sub_type = getattr(event, 'sub_type', None)
    
    if sub_type != 'add' or not user_id or not flag:
        return False
    
    # 检查是否开启入群申请广播
    broadcast_enabled = await get_group_setting(group_id, 'join_request')
    if not broadcast_enabled:
        return False
    
    # 生成随机编号
    import random
    random_code = random.randint(1000, 9999)
    
    # 获取用户昵称
    stranger_info = await onebot.get_stranger_info(user_id)
    nickname = stranger_info.get('nickname', str(user_id)) if stranger_info else str(user_id)
    
    # 保存申请记录
    db = await db_manager.get_db('data')
    await db.execute(
        """INSERT INTO join_requests 
           (group_id, user_id, flag, random_code, nickname, comment, create_time, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (group_id, user_id, flag, random_code, nickname, comment, int(time.time()))
    )
    await db.commit()
    
    # 发送通知
    message = f"📥 新入群申请\n"
    message += f"编号: {random_code}\n"
    message += f"用户: {nickname}({user_id})\n"
    message += f"验证信息: {comment or '(无)'}\n"
    message += f"回复「同意{random_code}」或「拒绝{random_code} 理由」处理"
    
    await send_group_msg(group_id, message)
    return True


async def handle_request_response(event):
    """处理申请回复"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    
    # 检查权限
    member_info = await onebot.get_group_member_info(group_id, user_id)
    if not member_info or member_info.get('role') not in ('admin', 'owner'):
        return False
    
    # 同意申请
    agree_match = re.match(r'^同意\s*(\d+)$', raw_msg.strip())
    if agree_match:
        code = int(agree_match.group(1))
        
        db = await db_manager.get_db('data')
        row = await db.fetchone(
            "SELECT flag, nickname FROM join_requests WHERE group_id = ? AND random_code = ? AND status = 'pending'",
            (group_id, code)
        )
        
        if not row:
            await send_group_msg(group_id, f"❌ 未找到编号 {code} 的待处理申请")
            return True
        
        flag, nickname = row
        
        # 同意申请
        success = await onebot.set_group_add_request(flag, 'add', True)
        
        if success:
            await db.execute(
                "UPDATE join_requests SET status = 'approved' WHERE group_id = ? AND random_code = ?",
                (group_id, code)
            )
            await db.commit()
            await send_group_msg(group_id, f"✅ 已同意 {nickname} 的入群申请")
        else:
            await send_group_msg(group_id, "❌ 处理失败")
        
        return True
    
    # 拒绝申请
    reject_match = re.match(r'^拒绝\s*(\d+)\s*(.*)$', raw_msg.strip())
    if reject_match:
        code = int(reject_match.group(1))
        reason = reject_match.group(2).strip() or "管理员拒绝"
        
        db = await db_manager.get_db('data')
        row = await db.fetchone(
            "SELECT flag, nickname FROM join_requests WHERE group_id = ? AND random_code = ? AND status = 'pending'",
            (group_id, code)
        )
        
        if not row:
            await send_group_msg(group_id, f"❌ 未找到编号 {code} 的待处理申请")
            return True
        
        flag, nickname = row
        
        # 拒绝申请
        success = await onebot.set_group_add_request(flag, 'add', False, reason)
        
        if success:
            await db.execute(
                "UPDATE join_requests SET status = 'rejected' WHERE group_id = ? AND random_code = ?",
                (group_id, code)
            )
            await db.commit()
            await send_group_msg(group_id, f"✅ 已拒绝 {nickname} 的入群申请")
        else:
            await send_group_msg(group_id, "❌ 处理失败")
        
        return True
    
    return False


import re


async def handle_notice(event):
    """处理通知事件"""
    notice_type = event.notice_type
    
    if notice_type == 'group_increase':
        return await handle_member_increase(event)
    
    elif notice_type == 'group_decrease':
        return await handle_member_decrease(event)
    
    elif notice_type == 'group_admin':
        return await handle_admin_change(event)
    
    return False


async def handle_request(event):
    """处理请求事件"""
    request_type = event.request_type
    
    if request_type == 'group':
        return await handle_group_request(event)
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_notice_handler(handle_notice)
    plugin_manager.register_request_handler(handle_request)
    plugin_manager.register_group_handler(handle_request_response)
