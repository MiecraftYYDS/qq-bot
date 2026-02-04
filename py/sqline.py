#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异步数据库管理模块 - 基于 aiosqlite
支持多数据库连接池和 WAL 模式
"""

import os
import aiosqlite
from typing import Dict, Optional, Any, List
from contextlib import asynccontextmanager


class AsyncDB:
    """异步数据库封装类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> aiosqlite.Connection:
        """连接数据库并开启 WAL 模式"""
        if self._conn is None:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            
            # 开启 WAL 模式提高并发性能
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA synchronous=NORMAL;")
            await self._conn.execute("PRAGMA cache_size=10000;")
            await self._conn.execute("PRAGMA temp_store=MEMORY;")
            
        return self._conn
    
    async def close(self):
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """执行 SQL 语句"""
        conn = await self.connect()
        return await conn.execute(sql, params)
    
    async def executemany(self, sql: str, params_list: List[tuple]) -> aiosqlite.Cursor:
        """批量执行 SQL 语句"""
        conn = await self.connect()
        return await conn.executemany(sql, params_list)
    
    async def commit(self):
        """提交事务"""
        if self._conn:
            await self._conn.commit()
    
    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """查询单条记录"""
        async with await self.execute(sql, params) as cursor:
            return await cursor.fetchone()
    
    async def fetchall(self, sql: str, params: tuple = ()) -> List[aiosqlite.Row]:
        """查询所有记录"""
        async with await self.execute(sql, params) as cursor:
            return await cursor.fetchall()
    
    async def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据并返回 lastrowid"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        async with await self.execute(sql, tuple(data.values())) as cursor:
            await self.commit()
            return cursor.lastrowid
    
    async def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = ()) -> int:
        """更新数据并返回受影响行数"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        async with await self.execute(sql, tuple(data.values()) + where_params) as cursor:
            await self.commit()
            return cursor.rowcount


class DatabaseManager:
    """数据库连接池管理器"""
    
    # 数据库配置
    DB_CONFIG = {
        'data': 'sqline/data.db',      # 消息数据
        'set': 'sqline/set.db',        # 群设置
        'aimemory': 'sqline/aimemory.db',  # AI 记忆
        'total': 'sqline/total.db',    # 统计数据
    }
    
    def __init__(self):
        self._databases: Dict[str, AsyncDB] = {}
    
    async def get_db(self, name: str) -> AsyncDB:
        """获取数据库连接"""
        if name not in self.DB_CONFIG:
            raise ValueError(f"未知的数据库: {name}")
        
        if name not in self._databases:
            self._databases[name] = AsyncDB(self.DB_CONFIG[name])
            await self._databases[name].connect()
        
        return self._databases[name]
    
    async def init_all(self):
        """初始化所有数据库及其表结构"""
        from .config import config
        
        # 如果不保留上次设置，先删除 set.db
        if not config.database.keep_previous_settings:
            import os
            set_db_path = self.DB_CONFIG['set']
            if os.path.exists(set_db_path):
                os.remove(set_db_path)
                print("🔄 已重置群设置数据库 (keep_previous_settings=false)")
        
        # 初始化数据库
        await self._init_data_db()
        await self._init_set_db()
        await self._init_aimemory_db()
        await self._init_total_db()
    
    async def _init_data_db(self):
        """初始化消息数据库"""
        db = await self.get_db('data')
        
        # 群消息表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                text TEXT,
                create_time INTEGER
            )
        """)
        
        # 最后消息状态表 (用于复读检测)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS last_msg (
                group_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                text TEXT
            )
        """)
        
        # 复读标记表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repeated_once (
                group_id INTEGER,
                user_id INTEGER,
                text TEXT,
                done INTEGER,
                PRIMARY KEY (group_id, user_id)
            )
        """)
        
        # 入群申请表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                flag TEXT,
                random_code INTEGER,
                nickname TEXT,
                comment TEXT,
                inviter TEXT,
                create_time INTEGER,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_gm_group_time ON group_messages(group_id, create_time)")
        
        await db.commit()
    
    async def _init_set_db(self):
        """初始化设置数据库"""
        db = await self.get_db('set')
        
        # 群设置表 (扩展字段)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                group_id INTEGER PRIMARY KEY,
                broadcast_admin_changes INTEGER DEFAULT 0,
                welcome_message INTEGER DEFAULT 0,
                farewell_message INTEGER DEFAULT 0,
                broadcast_join_request INTEGER DEFAULT 0,
                wordcloud_count_english INTEGER DEFAULT 0,
                wordcloud_count_single_char INTEGER DEFAULT 0,
                jm_enabled INTEGER DEFAULT 0,
                ai_enabled INTEGER DEFAULT 1,
                repeat_enabled INTEGER DEFAULT 1,
                poke_enabled INTEGER DEFAULT 1,
                banme_enabled INTEGER DEFAULT 1,
                quote_enabled INTEGER DEFAULT 1,
                essence_enabled INTEGER DEFAULT 1,
                repeat_probability REAL DEFAULT -1,
                exclamation_probability REAL DEFAULT -1
            )
        """)
        
        # 检查并添加新列（兼容旧数据库）
        new_columns = [
            ('ai_enabled', 'INTEGER DEFAULT 1'),
            ('repeat_enabled', 'INTEGER DEFAULT 1'),
            ('poke_enabled', 'INTEGER DEFAULT 1'),
            ('banme_enabled', 'INTEGER DEFAULT 1'),
            ('quote_enabled', 'INTEGER DEFAULT 1'),
            ('essence_enabled', 'INTEGER DEFAULT 1'),
            ('repeat_probability', 'REAL DEFAULT -1'),
            ('exclamation_probability', 'REAL DEFAULT -1'),
        ]
        for col_name, col_type in new_columns:
            try:
                await db.execute(f"ALTER TABLE group_settings ADD COLUMN {col_name} {col_type}")
            except:
                pass  # 列已存在
        
        # 群消息格式表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_messages_format (
                group_id INTEGER PRIMARY KEY,
                welcome_format TEXT DEFAULT '欢迎新成员 {at} 加入本群！',
                farewell_format TEXT DEFAULT '成员 {qqid} 已退出本群，再见！'
            )
        """)
        
        # 群自定义设置表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_selfset (
                group_id INTEGER PRIMARY KEY,
                checkin_enabled INTEGER DEFAULT 0,
                wordcloud_hour INTEGER DEFAULT -1,
                ai_enabled INTEGER DEFAULT 1
            )
        """)
        
        # WebUI 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webui_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT DEFAULT 'user',
                create_time INTEGER
            )
        """)
        
        # 用户管理的群列表（一个用户可管理多个群）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                group_id INTEGER,
                create_time INTEGER,
                UNIQUE(username, group_id)
            )
        """)
        
        await db.commit()
    
    async def _init_aimemory_db(self):
        """初始化 AI 记忆数据库"""
        db = await self.get_db('aimemory')
        
        # 群聊 AI 上下文表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_ai_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                create_time INTEGER
            )
        """)
        
        # 私聊 AI 上下文表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS private_ai_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                create_time INTEGER
            )
        """)
        
        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_gac_group ON group_ai_context(group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_pac_user ON private_ai_context(user_id)")
        
        await db.commit()
    
    async def _init_total_db(self):
        """初始化统计数据库"""
        db = await self.get_db('total')
        
        # 统计数据表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                total_messages INTEGER DEFAULT 0,
                total_commands INTEGER DEFAULT 0,
                total_ai_calls INTEGER DEFAULT 0,
                start_time INTEGER
            )
        """)
        
        # 初始化统计记录
        import time
        await db.execute("""
            INSERT OR IGNORE INTO stats (id, total_messages, total_commands, total_ai_calls, start_time)
            VALUES (1, 0, 0, 0, ?)
        """, (int(time.time()),))
        
        await db.commit()
    
    async def close_all(self):
        """关闭所有数据库连接"""
        for db in self._databases.values():
            await db.close()
        self._databases.clear()


# 全局数据库管理器实例
db_manager = DatabaseManager()


# ==================== 便捷数据操作函数 ====================

async def add_group_message(group_id: int, user_id: int, text: str) -> int:
    """添加群消息记录"""
    import time
    db = await db_manager.get_db('data')
    return await db.insert('group_messages', {
        'group_id': group_id,
        'user_id': user_id,
        'text': text,
        'create_time': int(time.time())
    })


async def get_group_messages(group_id: int, hours: Optional[int] = None, 
                             exclude_bot: bool = False, bot_id: int = 0) -> List[Dict]:
    """获取群消息记录"""
    import time
    db = await db_manager.get_db('data')
    
    sql = "SELECT user_id, text, create_time FROM group_messages WHERE group_id = ?"
    params = [group_id]
    
    if hours is not None:
        since = int(time.time() - hours * 3600)
        sql += " AND create_time >= ?"
        params.append(since)
    
    if exclude_bot and bot_id:
        sql += " AND user_id != ?"
        params.append(bot_id)
    
    sql += " ORDER BY create_time DESC"
    
    rows = await db.fetchall(sql, tuple(params))
    return [{'user_id': r[0], 'text': r[1], 'create_time': r[2]} for r in rows]


async def update_stats(field: str, increment: int = 1):
    """更新统计数据"""
    db = await db_manager.get_db('total')
    await db.execute(f"UPDATE stats SET {field} = {field} + ? WHERE id = 1", (increment,))
    await db.commit()


async def get_stats() -> Dict:
    """获取统计数据"""
    db = await db_manager.get_db('total')
    row = await db.fetchone("SELECT * FROM stats WHERE id = 1")
    if row:
        return dict(row)
    return {}
