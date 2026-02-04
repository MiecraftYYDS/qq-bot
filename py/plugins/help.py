#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
帮助命令插件 - 根据全局开关动态显示帮助
"""

import sys
import os

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import send_group_msg, send_private_msg


def build_help_text() -> str:
    """根据全局开关构建帮助文本"""
    gf = config.global_features
    
    sections = []
    
    # 基础功能（总是显示）
    sections.append("""【🤖 机器人功能列表】

【基础功能】
#ping - 检查机器人状态和版本
#dzw - 给自己点赞10个""")
    
    # AI 功能
    if gf.ai:
        sections.append("""
【AI功能】
#js [问题] - 让AI解释问题
直接艾特机器人 可以让ai像猫娘一样回复你""")
    
    # 词云功能
    if gf.wordcloud:
        sections.append("""
【词云功能】
#cy [小时数] - 生成词云（可选：指定小时数）
#cyyy - 词云统计英语
#cydz - 词云统计单字""")
    
    # 语录图片
    if gf.quote:
        sections.append("""
【语录图片】
#tpq - 将引用的消息设为语录图片并发送
#tpq [QQ号] [文字] - 生成指定QQ号和文字的语录图片[需要白名单,可寻找QQ管理员添加]""")
    
    # 精华消息
    if gf.essence:
        sections.append("""
【精华消息】（QQ机器人需要群管理员权限,用户不需要管理员权限）
#q - 将回复的消息设为精华消息,并发出一条群语录
#unq - 取消精华消息""")
    
    # 禁言管理
    if gf.banme:
        sections.append("""
【禁言管理】(需要管理员权限)
禁言我 - 获得随机1-20分钟禁言
#mute [qq号或@] - 禁言指定用户
#jj [qq号或@] - 解禁指定用户""")
    
    # 申请处理（总是显示）
    sections.append("""
【申请处理】(需要管理员权限)
同意[数字] - 同意对应编号的入群申请
拒绝[数字] [理由] - 拒绝入群申请（可选填理由）""")
    
    # 群设置 - 动态构建可用设置项
    settings_items = ["  - broadcast - 权限变更广播"]
    if gf.welcome:
        settings_items.append("  - welcome - 入群欢迎")
    if gf.farewell:
        settings_items.append("  - farewell - 退群公告")
    settings_items.append("  - join_request - 入群申请广播")
    if gf.wordcloud:
        settings_items.append("  - cyyy - 词云统计英语")
        settings_items.append("  - cydz - 词云统计单字")
    if gf.jm:
        settings_items.append("  - jm - JM 功能开关")
    if gf.ai:
        settings_items.append("  - ai - AI 功能开关")
    if gf.repeat:
        settings_items.append("  - repeat - 复读功能")
    if gf.poke:
        settings_items.append("  - poke - 戳一戳/互动")
    if gf.banme:
        settings_items.append("  - banme - 禁言抽奖")
    if gf.quote:
        settings_items.append("  - quote - 语录功能")
    if gf.essence:
        settings_items.append("  - essence - 精华消息")
    
    sections.append(f"""
【群设置】(需要管理员权限)
#settings [功能] [on|off]
{chr(10).join(settings_items)}

#setformat [welcome|farewell] [格式文本]
  - {{qqid}} - 成员QQ号
  - {{at}} - @成员""")
    
    # 群主特权
    sections.append("""
【群主特权】(需要群主权限)
#tx [qq号或@] [头衔] - 设置成员头衔""")
    
    # 机器人管理员命令
    admin_cmds = ["#selfset qd [on|off] - 开启/关闭群签到"]
    if gf.wordcloud:
        admin_cmds.append("#selfset cy [0-23或-1] - 设置自动词云时间(-1为关闭)")
    if gf.ai:
        admin_cmds.append("#selfset ai [on|off] - 开启/关闭群AI")
    
    sections.append(f"""
【机器人管理员命令】
{chr(10).join(admin_cmds)}""")
    
    # 趣味互动
    if gf.poke or gf.repeat:
        poke_items = []
        if gf.poke:
            poke_items.append("摸摸 - 触发摸摸回复")
            poke_items.append("ccb - 踩背")
        if gf.repeat:
            poke_items.append("以!或！结尾的短句 - 触发复读变体")
        sections.append(f"""
【趣味互动】
{chr(10).join(poke_items)}""")
    
    # 私聊功能
    private_cmds = [
        "#help - 获取帮助信息",
        "#ping - 检查机器人状态和版本",
        "#dzw - 给自己点赞10个",
    ]
    if gf.ai:
        private_cmds.append("#new - 新建AI对话（清除上下文）")
    private_cmds.append("#sx [内容] - 向机器人管理员私信（支持图片）")
    if gf.ai:
        private_cmds.append("直接发送消息 - 与AI对话（支持上下文）")
    
    sections.append(f"""
【私聊功能】
{chr(10).join(private_cmds)}""")
    
    return ''.join(sections)


# 缓存帮助文本（启动时生成）
HELP_TEXT = build_help_text()


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    
    if raw_msg.strip() == '#help':
        await send_group_msg(group_id, HELP_TEXT)
        return True
    
    return False


async def handle_private_message(event):
    """处理私聊消息"""
    raw_msg = event.raw_message or ''
    user_id = event.user_id
    
    if raw_msg.strip() == '#help':
        await send_private_msg(user_id, HELP_TEXT)
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)
    plugin_manager.register_private_handler(handle_private_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("📖 帮助插件测试")
    print("=" * 50)
    print("\n" + HELP_TEXT)
    print("\n✅ 插件模块加载正常")
