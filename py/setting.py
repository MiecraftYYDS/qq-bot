#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
群设置管理模块 - 封装群级别设置的读写
"""

from typing import Optional, Dict, Any
from .sqline import db_manager
from .config import config


class GroupSettings:
    """群设置管理类"""
    
    # 设置项与数据库字段的映射
    SETTING_FIELDS = {
        'broadcast': 'broadcast_admin_changes',
        'welcome': 'welcome_message',
        'farewell': 'farewell_message',
        'join_request': 'broadcast_join_request',
        'cyyy': 'wordcloud_count_english',
        'cydz': 'wordcloud_count_single_char',
        'jm': 'jm_enabled',
        'ai': 'ai_enabled',
        'repeat': 'repeat_enabled',
        'poke': 'poke_enabled',
        'banme': 'banme_enabled',
        'quote': 'quote_enabled',
        'essence': 'essence_enabled',
    }
    
    # 设置项对应的全局开关映射
    GLOBAL_FEATURE_MAP = {
        'ai': 'ai',
        'cyyy': 'wordcloud',
        'cydz': 'wordcloud',
        'jm': 'jm',
        'repeat': 'repeat',
        'poke': 'poke',
        'banme': 'banme',
        'quote': 'quote',
        'essence': 'essence',
        'welcome': 'welcome',
        'farewell': 'farewell',
    }
    
    @classmethod
    def is_global_enabled(cls, feature_name: str) -> bool:
        """检查全局功能是否开启"""
        global_key = cls.GLOBAL_FEATURE_MAP.get(feature_name)
        if global_key:
            return getattr(config.global_features, global_key, True)
        return True
    
    @classmethod
    async def get_setting(cls, group_id: int, setting_name: str) -> bool:
        """获取群的某项设置（同时检查全局开关）"""
        # 先检查全局开关
        if not cls.is_global_enabled(setting_name):
            return False
        
        field = cls.SETTING_FIELDS.get(setting_name)
        if not field:
            return False
        
        db = await db_manager.get_db('set')
        row = await db.fetchone(
            f"SELECT {field} FROM group_settings WHERE group_id = ?",
            (group_id,)
        )
        if row:
            return bool(row[0])
        
        # 返回默认值
        return cls.get_default_value(setting_name)
    
    @classmethod
    def get_default_value(cls, setting_name: str) -> bool:
        """获取设置项的默认值"""
        field = cls.SETTING_FIELDS.get(setting_name)
        if field:
            return getattr(config.default_group_settings, field, False)
        return False
    
    @classmethod
    async def set_setting(cls, group_id: int, setting_name: str, value: bool) -> bool:
        """设置群的某项设置"""
        field = cls.SETTING_FIELDS.get(setting_name)
        if not field:
            return False
        
        db = await db_manager.get_db('set')
        
        # 确保记录存在
        await db.execute(
            "INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)",
            (group_id,)
        )
        
        # 更新设置
        await db.execute(
            f"UPDATE group_settings SET {field} = ? WHERE group_id = ?",
            (1 if value else 0, group_id)
        )
        await db.commit()
        return True
    
    @classmethod
    async def get_all_settings(cls, group_id: int) -> Dict[str, bool]:
        """获取群的所有设置（结合全局开关）"""
        db = await db_manager.get_db('set')
        
        fields = ', '.join(cls.SETTING_FIELDS.values())
        row = await db.fetchone(
            f"SELECT {fields} FROM group_settings WHERE group_id = ?",
            (group_id,)
        )
        
        result = {}
        field_list = list(cls.SETTING_FIELDS.items())
        
        for i, (name, _) in enumerate(field_list):
            # 先检查全局开关
            if not cls.is_global_enabled(name):
                result[name] = False
            elif row:
                result[name] = bool(row[i])
            else:
                result[name] = cls.get_default_value(name)
        
        return result
    
    @classmethod
    async def init_group_settings(cls, group_id: int):
        """为新群初始化默认设置"""
        db = await db_manager.get_db('set')
        
        # 检查是否已存在
        row = await db.fetchone(
            "SELECT 1 FROM group_settings WHERE group_id = ?",
            (group_id,)
        )
        if row:
            return  # 已存在
        
        # 插入默认设置
        defaults = config.default_group_settings
        await db.execute("""
            INSERT INTO group_settings (
                group_id, broadcast_admin_changes, welcome_message, farewell_message,
                broadcast_join_request, wordcloud_count_english, wordcloud_count_single_char,
                jm_enabled, ai_enabled, repeat_enabled, poke_enabled, banme_enabled,
                quote_enabled, essence_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            group_id,
            int(defaults.broadcast_admin_changes),
            int(defaults.welcome_message),
            int(defaults.farewell_message),
            int(defaults.broadcast_join_request),
            int(defaults.wordcloud_count_english),
            int(defaults.wordcloud_count_single_char),
            int(defaults.jm_enabled),
            int(defaults.ai_enabled),
            int(defaults.repeat_enabled),
            int(defaults.poke_enabled),
            int(defaults.banme_enabled),
            int(defaults.quote_enabled),
            int(defaults.essence_enabled),
        ))
        await db.commit()
    
    @classmethod
    async def get_format(cls, group_id: int, format_type: str) -> str:
        """获取格式化文本 (welcome/farewell)"""
        db = await db_manager.get_db('set')
        
        field = f'{format_type}_format'
        row = await db.fetchone(
            f"SELECT {field} FROM group_messages_format WHERE group_id = ?",
            (group_id,)
        )
        if row:
            return row[0]
        
        # 默认格式
        defaults = {
            'welcome': "欢迎新成员 {at} 加入本群！",
            'farewell': "成员 {qqid} 已退出本群，再见！"
        }
        return defaults.get(format_type, "")
    
    @classmethod
    async def set_format(cls, group_id: int, format_type: str, text: str) -> bool:
        """设置格式化文本"""
        db = await db_manager.get_db('set')
        
        field = f'{format_type}_format'
        
        # 确保记录存在
        await db.execute(
            "INSERT OR IGNORE INTO group_messages_format (group_id) VALUES (?)",
            (group_id,)
        )
        
        # 更新格式
        await db.execute(
            f"UPDATE group_messages_format SET {field} = ? WHERE group_id = ?",
            (text, group_id)
        )
        await db.commit()
        return True


# 便捷函数
async def get_group_setting(group_id: int, setting_name: str) -> bool:
    return await GroupSettings.get_setting(group_id, setting_name)


async def set_group_setting(group_id: int, setting_name: str, value: bool) -> bool:
    return await GroupSettings.set_setting(group_id, setting_name, value)


async def get_repeat_probability(group_id: int) -> float:
    """获取群的复读概率（群设置优先，否则使用全局配置）"""
    db = await db_manager.get_db('set')
    row = await db.fetchone(
        "SELECT repeat_probability FROM group_settings WHERE group_id = ?",
        (group_id,)
    )
    if row and row[0] is not None and row[0] >= 0:
        return float(row[0])
    # 使用全局配置
    return config.repeat_settings.repeat_probability


async def get_exclamation_probability(group_id: int) -> float:
    """获取群的感叹号触发概率（群设置优先，否则使用全局配置）"""
    db = await db_manager.get_db('set')
    row = await db.fetchone(
        "SELECT exclamation_probability FROM group_settings WHERE group_id = ?",
        (group_id,)
    )
    if row and row[0] is not None and row[0] >= 0:
        return float(row[0])
    # 使用全局配置
    return config.repeat_settings.exclamation_probability


async def set_repeat_probability(group_id: int, probability: float) -> bool:
    """设置群的复读概率（-1表示使用全局配置）"""
    db = await db_manager.get_db('set')
    await db.execute(
        "INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)",
        (group_id,)
    )
    await db.execute(
        "UPDATE group_settings SET repeat_probability = ? WHERE group_id = ?",
        (probability, group_id)
    )
    await db.commit()
    return True


async def set_exclamation_probability(group_id: int, probability: float) -> bool:
    """设置群的感叹号触发概率（-1表示使用全局配置）"""
    db = await db_manager.get_db('set')
    await db.execute(
        "INSERT OR IGNORE INTO group_settings (group_id) VALUES (?)",
        (group_id,)
    )
    await db.execute(
        "UPDATE group_settings SET exclamation_probability = ? WHERE group_id = ?",
        (probability, group_id)
    )
    await db.commit()
    return True
