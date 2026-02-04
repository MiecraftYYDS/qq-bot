#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
机器人自定义设置模块 - 封装群自定义设置的读写
"""

from typing import Optional
from .sqline import db_manager


class SelfSettings:
    """群自定义设置管理类"""
    
    @classmethod
    async def get_checkin_enabled(cls, group_id: int) -> bool:
        """获取群签到是否开启"""
        db = await db_manager.get_db('set')
        async with db.execute(
            "SELECT checkin_enabled FROM group_selfset WHERE group_id = ?",
            (group_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return bool(row[0])
        return False
    
    @classmethod
    async def set_checkin_enabled(cls, group_id: int, enabled: bool) -> bool:
        """设置群签到开关"""
        db = await db_manager.get_db('set')
        
        await db.execute(
            "INSERT OR IGNORE INTO group_selfset (group_id) VALUES (?)",
            (group_id,)
        )
        
        await db.execute(
            "UPDATE group_selfset SET checkin_enabled = ? WHERE group_id = ?",
            (1 if enabled else 0, group_id)
        )
        await db.commit()
        return True
    
    @classmethod
    async def get_wordcloud_hour(cls, group_id: int) -> int:
        """获取自动词云时间 (-1 为关闭)"""
        db = await db_manager.get_db('set')
        async with db.execute(
            "SELECT wordcloud_hour FROM group_selfset WHERE group_id = ?",
            (group_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
        return -1
    
    @classmethod
    async def set_wordcloud_hour(cls, group_id: int, hour: int) -> bool:
        """设置自动词云时间 (-1 为关闭, 0-23 为具体小时)"""
        if hour < -1 or hour > 23:
            return False
        
        db = await db_manager.get_db('set')
        
        await db.execute(
            "INSERT OR IGNORE INTO group_selfset (group_id) VALUES (?)",
            (group_id,)
        )
        
        await db.execute(
            "UPDATE group_selfset SET wordcloud_hour = ? WHERE group_id = ?",
            (hour, group_id)
        )
        await db.commit()
        return True
    
    @classmethod
    async def get_ai_enabled(cls, group_id: int) -> bool:
        """获取群 AI 是否开启"""
        db = await db_manager.get_db('set')
        async with db.execute(
            "SELECT ai_enabled FROM group_selfset WHERE group_id = ?",
            (group_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return bool(row[0])
        return True  # 默认开启
    
    @classmethod
    async def set_ai_enabled(cls, group_id: int, enabled: bool) -> bool:
        """设置群 AI 开关"""
        db = await db_manager.get_db('set')
        
        await db.execute(
            "INSERT OR IGNORE INTO group_selfset (group_id) VALUES (?)",
            (group_id,)
        )
        
        await db.execute(
            "UPDATE group_selfset SET ai_enabled = ? WHERE group_id = ?",
            (1 if enabled else 0, group_id)
        )
        await db.commit()
        return True
    
    @classmethod
    async def get_all_auto_wordcloud_groups(cls) -> list:
        """获取所有开启自动词云的群及其时间"""
        db = await db_manager.get_db('set')
        async with db.execute(
            "SELECT group_id, wordcloud_hour FROM group_selfset WHERE wordcloud_hour >= 0"
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]


# 便捷函数
async def get_selfset_qd(group_id: int) -> bool:
    return await SelfSettings.get_checkin_enabled(group_id)


async def set_selfset_qd(group_id: int, enabled: bool) -> bool:
    return await SelfSettings.set_checkin_enabled(group_id, enabled)


async def get_selfset_cy(group_id: int) -> int:
    return await SelfSettings.get_wordcloud_hour(group_id)


async def set_selfset_cy(group_id: int, hour: int) -> bool:
    return await SelfSettings.set_wordcloud_hour(group_id, hour)
