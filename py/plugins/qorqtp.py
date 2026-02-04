#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语录图片生成插件
"""

import re
import io
import os
import sys
import time
import base64
import urllib.request
from PIL import Image, ImageFont

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import onebot, send_group_msg, send_group_image
from py.setting import GroupSettings


def gen_quote_img_base64(qq: str, text: str, name: str) -> str:
    """
    生成语录图片并返回 Base64 编码
    
    Args:
        qq: QQ号（用于获取头像）
        text: 语录文本
        name: 显示名称
    
    Returns:
        Base64 编码的 PNG 图片
    """
    # 使用 pilmoji 支持 emoji
    try:
        from pilmoji import Pilmoji
        use_pilmoji = True
    except ImportError:
        use_pilmoji = False
    
    # 路径配置
    font_path = config.paths.font_tsuka
    base_img_path = config.paths.quote_base
    output_dir = config.paths.qtp_output
    
    # 处理文本
    text = text.replace("\n", " ")
    
    # 图片尺寸
    img_width, img_height = 1200, 640
    font_size = 42
    name_font_size = 24
    
    # 加载字体
    font = ImageFont.truetype(font_path, font_size)
    name_font = ImageFont.truetype(font_path, name_font_size)
    
    # 加载背景图
    base_img = Image.open(base_img_path)
    
    # 获取头像
    avatar_url = f"http://q2.qlogo.cn/headimg_dl?dst_uin={qq}&spec=5"
    try:
        with urllib.request.urlopen(avatar_url, timeout=10) as response:
            avatar_img = Image.open(io.BytesIO(response.read()))
    except Exception as e:
        print(f"获取头像失败: {e}")
        avatar_img = Image.new("RGBA", (200, 200), (200, 200, 200, 255))
    
    # 头像尺寸调整
    min_size = 640
    w, h = avatar_img.size
    if w < min_size or h < min_size:
        scale = max(min_size / w, min_size / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        avatar_img = avatar_img.resize((new_w, new_h), Image.LANCZOS)
    
    # 创建画布
    img = Image.new("RGBA", (img_width, img_height), (255, 255, 255, 0))
    img.paste(avatar_img, (0, 0))
    img.paste(base_img, (0, 0), base_img)
    
    # 文本布局
    text_list = [text[i:i + 18] for i in range(0, len(text), 18)]
    new_text_height = font_size * len(text_list)
    new_text_width = max(font.getbbox(x)[2] - font.getbbox(x)[0] for x in text_list)
    text_x = 540 + int((560 - new_text_width) / 2)
    text_y = int((img_height - new_text_height) / 2)
    
    # 绘制文本
    if use_pilmoji:
        with Pilmoji(img) as pilmoji:
            for i, v in enumerate(text_list):
                pilmoji.text(
                    (text_x, text_y + i * font_size),
                    text=v,
                    font=font,
                    align="center",
                )
    else:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for i, v in enumerate(text_list):
            draw.text(
                (text_x, text_y + i * font_size),
                text=v,
                font=font,
                fill=(0, 0, 0)
            )
    
    # 名称布局
    left, top, right, bottom = name_font.getbbox(name)
    name_width = right - left
    name_height = bottom - top
    name_x = 600 + int((560 - name_width) / 2)
    name_y = int(img_height - name_height - 20)
    
    # 绘制名称
    if use_pilmoji:
        with Pilmoji(img) as pilmoji:
            pilmoji.text(
                (name_x, name_y),
                text=name,
                font=name_font,
                align="center",
            )
    else:
        draw = ImageDraw.Draw(img)
        draw.text((name_x, name_y), text=name, font=name_font, fill=(0, 0, 0))
    
    # 转换并保存
    buffer = io.BytesIO()
    img = img.convert("RGB")
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # 保存到本地
    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time())
    with open(f"{output_dir}q_{timestamp}.png", "wb") as f:
        f.write(buffer.getvalue())
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    user_id = event.user_id
    message_id = event.message_id
    
    # #q - 设为精华并生成语录
    if raw_msg.strip() == '#q':
        # 检查全局开关
        if not config.global_features.quote or not config.global_features.essence:
            return False
        
        # 检查群开关
        if not await GroupSettings.get_setting(group_id, 'quote'):
            return False
        if not await GroupSettings.get_setting(group_id, 'essence'):
            return False
        
        # 检查是否是回复消息
        reply_match = re.search(r'\[CQ:reply,id=(-?\d+)\]', raw_msg)
        if not reply_match:
            # 尝试从消息段中获取
            if isinstance(event.message, list):
                for seg in event.message:
                    if seg.get('type') == 'reply':
                        reply_id = seg.get('data', {}).get('id')
                        if reply_id:
                            reply_match = True
                            break
        
        if not reply_match:
            await send_group_msg(group_id, "请回复一条消息来设置精华")
            return True
        
        # 获取回复的消息ID
        if isinstance(reply_match, re.Match):
            reply_id = int(reply_match.group(1))
        else:
            reply_id = int(reply_id)
        
        # 设置精华消息
        await onebot.set_essence_msg(reply_id)
        
        # 获取原消息详情
        msg_info = await onebot.get_msg(reply_id)
        if msg_info:
            sender_id = msg_info.get('sender', {}).get('user_id', user_id)
            sender_name = await onebot.get_nickname(group_id, sender_id)
            msg_text = msg_info.get('raw_message', '') or msg_info.get('message', '')
            
            # 清理CQ码
            msg_text = re.sub(r'\[CQ:[^\]]+\]', '', msg_text).strip()
            
            if msg_text:
                # 生成语录图片
                img_base64 = gen_quote_img_base64(str(sender_id), msg_text, sender_name)
                await send_group_image(group_id, img_base64)
            else:
                await send_group_msg(group_id, "✅ 已设为精华")
        else:
            await send_group_msg(group_id, "✅ 已设为精华")
        
        return True
    
    # #unq - 取消精华
    if raw_msg.strip() == '#unq':
        # 检查全局开关
        if not config.global_features.essence:
            return False
        if not await GroupSettings.get_setting(group_id, 'essence'):
            return False
        
        reply_match = re.search(r'\[CQ:reply,id=(-?\d+)\]', raw_msg)
        if not reply_match:
            if isinstance(event.message, list):
                for seg in event.message:
                    if seg.get('type') == 'reply':
                        reply_id = seg.get('data', {}).get('id')
                        if reply_id:
                            await onebot.delete_essence_msg(int(reply_id))
                            await send_group_msg(group_id, "✅ 已取消精华")
                            return True
            await send_group_msg(group_id, "请回复一条消息来取消精华")
            return True
        
        reply_id = int(reply_match.group(1))
        await onebot.delete_essence_msg(reply_id)
        await send_group_msg(group_id, "✅ 已取消精华")
        return True
    
    # #tpq - 语录图片
    # #tpq 回复消息
    if raw_msg.strip() == '#tpq':
        # 检查全局开关
        if not config.global_features.quote:
            return False
        if not await GroupSettings.get_setting(group_id, 'quote'):
            return False
        
        reply_match = re.search(r'\[CQ:reply,id=(-?\d+)\]', raw_msg)
        reply_id = None
        
        if not reply_match:
            if isinstance(event.message, list):
                for seg in event.message:
                    if seg.get('type') == 'reply':
                        reply_id = seg.get('data', {}).get('id')
                        break
        else:
            reply_id = reply_match.group(1)
        
        if not reply_id:
            await send_group_msg(group_id, "请回复一条消息，或使用 #tpq [QQ号] [文字]")
            return True
        
        msg_info = await onebot.get_msg(int(reply_id))
        if msg_info:
            sender_id = msg_info.get('sender', {}).get('user_id', user_id)
            sender_name = await onebot.get_nickname(group_id, sender_id)
            msg_text = msg_info.get('raw_message', '') or msg_info.get('message', '')
            msg_text = re.sub(r'\[CQ:[^\]]+\]', '', msg_text).strip()
            
            if msg_text:
                img_base64 = gen_quote_img_base64(str(sender_id), msg_text, sender_name)
                await send_group_image(group_id, img_base64)
            else:
                await send_group_msg(group_id, "消息内容为空")
        else:
            await send_group_msg(group_id, "获取消息失败")
        return True
    
    # #tpq [QQ号] [文字]
    tpq_match = re.match(r'^#tpq\s+(\d+)\s+(.+)$', raw_msg.strip())
    if tpq_match:
        # 检查全局开关
        if not config.global_features.quote:
            return False
        if not await GroupSettings.get_setting(group_id, 'quote'):
            return False
        
        target_qq = tpq_match.group(1)
        text = tpq_match.group(2).strip()
        
        # 获取名称
        name = await onebot.get_nickname(group_id, int(target_qq))
        
        # 生成图片
        img_base64 = gen_quote_img_base64(target_qq, text, name)
        await send_group_image(group_id, img_base64)
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    import base64 as b64
    
    print("=" * 50)
    print("🖼️ 语录图片生成插件测试")
    print("=" * 50)
    
    # 检查依赖
    print("\n📦 检查依赖:")
    try:
        from PIL import Image
        print("  ✅ Pillow")
    except ImportError:
        print("  ❌ Pillow 未安装")
    
    try:
        from pilmoji import Pilmoji
        print("  ✅ pilmoji (emoji支持)")
    except ImportError:
        print("  ⚠️ pilmoji 未安装 (emoji可能显示异常)")
    
    # 检查资源文件
    print("\n📁 检查资源文件:")
    font_path = config.paths.font_tsuka
    base_img_path = config.paths.quote_base
    
    if os.path.exists(font_path):
        print(f"  ✅ 字体: {font_path}")
    else:
        print(f"  ❌ 字体不存在: {font_path}")
    
    if os.path.exists(base_img_path):
        print(f"  ✅ 背景图: {base_img_path}")
    else:
        print(f"  ❌ 背景图不存在: {base_img_path}")
    
    # 测试生成
    print("\n🎨 测试生成语录图片...")
    test_qq = "10086"
    test_text = "今天也是元气满满的一天！加油！"
    test_name = "测试用户"
    
    try:
        img_base64 = gen_quote_img_base64(test_qq, test_text, test_name)
        if img_base64:
            with open("test_quote.png", "wb") as f:
                f.write(b64.b64decode(img_base64))
            print("  ✅ 生成成功，已保存到 test_quote.png")
        else:
            print("  ❌ 生成失败")
    except Exception as e:
        print(f"  ❌ 生成错误: {e}")
    
    print("\n💡 命令列表:")
    print("  #q - 回复消息设为精华并生成语录")
    print("  #unq - 取消精华")
    print("  #tpq - 回复消息生成语录图片")
    print("  #tpq <QQ号> <文字> - 指定QQ和文字生成语录")
