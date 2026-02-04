#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JM漫画下载插件
"""

import re
import asyncio
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.setting import GroupSettings
from py.onebot_api import send_group_msg


# 线程池执行器
_executor = ThreadPoolExecutor(max_workers=2)


def _download_jm(album_id: str) -> str:
    """
    在线程中执行JM漫画下载（同步函数）
    """
    try:
        import jmcomic
        option = jmcomic.create_option_by_file("jmoption.yml")
        jmcomic.download_album(album_id, option)
        return f"✅ JM{album_id} 下载完成"
    except Exception as e:
        return f"❌ JM{album_id} 下载失败: {str(e)}"


async def download_jm_async(album_id: str) -> str:
    """异步包装下载函数"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _download_jm, album_id)
    return result


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    
    # 检查JM命令
    jm_match = re.match(r'^[jJ][mM](\d+)$', raw_msg.strip())
    if jm_match:
        # 检查全局开关
        if not config.global_features.jm:
            return False
        
        # 检查群是否开启了JM功能
        jm_enabled = await GroupSettings.get_setting(group_id, 'jm')
        if not jm_enabled:
            await send_group_msg(group_id, "❌ 本群未开启JM功能")
            return True
        
        album_id = jm_match.group(1)
        await send_group_msg(group_id, f"⏳ 开始下载 JM{album_id}，请稍候...")
        
        # 异步下载
        result = await download_jm_async(album_id)
        await send_group_msg(group_id, result)
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("📚 JM漫画下载插件测试")
    print("=" * 50)
    
    # 检查 jmcomic 模块
    try:
        import jmcomic
        print("\n✅ jmcomic 模块已安装")
    except ImportError:
        print("\n❌ jmcomic 模块未安装，请运行: pip install jmcomic")
    
    # 检查配置文件
    if os.path.exists("jmoption.yml"):
        print("✅ jmoption.yml 配置文件存在")
    else:
        print("❌ jmoption.yml 配置文件不存在")
    
    print("\n💡 使用方法:")
    print("  JM123456 - 下载编号为 123456 的漫画")
    print("  需要先在群设置中开启 JM 功能: #settings jm on")
    
    # 测试下载（可选）
    test_id = input("\n是否测试下载？输入漫画ID或直接回车跳过: ").strip()
    if test_id and test_id.isdigit():
        print(f"\n⏳ 开始下载 JM{test_id}...")
        result = asyncio.run(download_jm_async(test_id))
        print(result)
