#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebUI API 模块
提供 Web 界面的后端接口
"""

import time
import asyncio
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import bcrypt

from py.config import config
from py.sqline import db_manager, get_stats
from py.onebot_api import onebot
from py.router import event_bus


# 创建路由器
html_router = APIRouter(prefix="/api", tags=["WebUI"])

# 安全依赖
security = HTTPBearer(auto_error=False)

# 内存验证码存储 {code: {"group_id": int, "status": str, "create_time": int}}
verifications: Dict[str, Dict] = {}


# ==================== 数据模型 ====================

class AdminLoginRequest(BaseModel):
    key: str


class GroupCodeRequest(BaseModel):
    group_id: int


class RegisterRequest(BaseModel):
    username: str
    password: str


class GroupLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    group_id: Optional[int] = None


# ==================== JWT 工具 ====================

def create_token(data: dict, expires_delta: timedelta = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.auth.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, config.auth.secret_key, algorithm=config.auth.algorithm)


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, config.auth.secret_key, algorithms=[config.auth.algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息"
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期"
        )
    
    return payload


def require_role(required_role: str):
    """角色权限装饰器"""
    async def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") != required_role and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return user
    return role_checker


# ==================== 公开接口 ====================

@html_router.get("/stats/init")
async def get_initial_stats():
    """获取初始统计数据"""
    stats = await get_stats()
    return {
        "total_messages": stats.get("total_messages", 0),
        "total_commands": stats.get("total_commands", 0),
        "total_ai_calls": stats.get("total_ai_calls", 0),
        "start_time": stats.get("start_time", 0),
        "bot_version": config.bot.version
    }


@html_router.get("/stats/stream")
async def stats_stream():
    """SSE 统计数据流"""
    async def event_generator():
        queue = event_bus.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f": heartbeat\n\n"
        finally:
            event_bus.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ==================== 管理员认证 ====================

@html_router.post("/auth/admin-login", response_model=TokenResponse)
async def admin_login(request: AdminLoginRequest):
    """管理员登录"""
    # 验证全局密钥（这里简单使用配置中的 secret_key）
    if request.key != config.auth.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密钥错误"
        )
    
    token = create_token({"role": "admin", "sub": "admin"})
    return TokenResponse(access_token=token, role="admin")


# ==================== 群管验证码流程 ====================

@html_router.post("/auth/gen-code")
async def generate_code(request: GroupCodeRequest):
    """生成群验证码"""
    # 生成 6 位验证码
    code = str(secrets.randbelow(900000) + 100000)
    
    verifications[code] = {
        "group_id": request.group_id,
        "status": "pending",
        "create_time": int(time.time())
    }
    
    # 清理过期验证码（5分钟）
    current_time = int(time.time())
    expired = [k for k, v in verifications.items() if current_time - v["create_time"] > 300]
    for k in expired:
        del verifications[k]
    
    return {
        "code": code,
        "message": f"请让群 {request.group_id} 的管理员私聊机器人发送此验证码"
    }


@html_router.get("/auth/check-status")
async def check_code_status(code: str):
    """检查验证码状态"""
    if code not in verifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="验证码不存在或已过期"
        )
    
    info = verifications[code]
    
    if info["status"] == "verified":
        # 验证成功，生成临时 Token
        token = create_token({
            "role": "temp",
            "group_id": info["group_id"],
            "sub": f"temp_{info['group_id']}"
        }, timedelta(minutes=30))
        
        # 删除已使用的验证码
        del verifications[code]
        
        return TokenResponse(
            access_token=token,
            role="temp",
            group_id=info["group_id"]
        )
    
    return {"status": info["status"]}


async def verify_group_admin_code(user_id: int, code: str) -> dict:
    """
    验证群管理员发送的验证码
    （在私聊消息处理中调用）
    
    返回:
        {"success": True, "message": "验证成功", "group_id": xxx}
        {"success": False, "message": "错误原因"}
    """
    if code not in verifications:
        return {"success": False, "message": "验证码不存在或已过期"}
    
    info = verifications[code]
    group_id = info["group_id"]
    
    # 检查是否已过期（5分钟）
    if int(time.time()) - info["create_time"] > 300:
        del verifications[code]
        return {"success": False, "message": "验证码已过期，请重新获取"}
    
    # 检查用户是否是该群的管理员
    member_info = await onebot.get_group_member_info(group_id, user_id)
    if not member_info:
        return {"success": False, "message": f"无法获取你在群 {group_id} 的信息，请确认群号正确且机器人在群内"}
    
    if member_info.get("role") not in ("admin", "owner"):
        return {"success": False, "message": f"你不是群 {group_id} 的管理员，无权验证"}
    
    # 验证成功
    verifications[code]["status"] = "verified"
    return {"success": True, "message": "验证成功！网页将自动跳转。", "group_id": group_id}


# ==================== 群管注册与登录 ====================

@html_router.post("/auth/register", response_model=TokenResponse)
async def register_group_user(request: RegisterRequest, user: dict = Depends(get_current_user)):
    """群管注册（需要临时 Token）"""
    if user.get("role") != "temp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要临时验证 Token"
        )
    
    group_id = user.get("group_id")
    
    # 检查用户名是否已存在
    db = await db_manager.get_db('set')
    existing = await db.fetchone(
        "SELECT id FROM webui_users WHERE username = ?",
        (request.username,)
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建用户
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await db.execute(
        """INSERT INTO webui_users (group_id, username, password_hash, role, create_time)
           VALUES (?, ?, ?, 'user', ?)""",
        (group_id, request.username, password_hash, int(time.time()))
    )
    
    # 将注册时的群添加到用户管理列表
    await db.execute(
        "INSERT OR IGNORE INTO user_groups (username, group_id, create_time) VALUES (?, ?, ?)",
        (request.username, group_id, int(time.time()))
    )
    await db.commit()
    
    # 生成正式 Token
    token = create_token({
        "role": "user",
        "group_id": group_id,
        "sub": request.username
    })
    
    return TokenResponse(access_token=token, role="user", group_id=group_id)


@html_router.post("/auth/group-login", response_model=TokenResponse)
async def group_login(request: GroupLoginRequest):
    """群管账号密码登录"""
    db = await db_manager.get_db('set')
    
    user = await db.fetchone(
        "SELECT password_hash, group_id, role FROM webui_users WHERE username = ?",
        (request.username,)
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not bcrypt.checkpw(request.password.encode('utf-8'), user[0].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    token = create_token({
        "role": user[2],
        "group_id": user[1],
        "sub": request.username
    })
    
    return TokenResponse(access_token=token, role=user[2], group_id=user[1])


# ==================== 群设置接口 ====================

async def check_group_permission(user: dict, group_id: int) -> bool:
    """检查用户是否有权限管理指定群"""
    if user.get("role") == "admin":
        return True
    
    # 检查用户是否管理该群
    db = await db_manager.get_db('set')
    username = user.get("sub")
    row = await db.fetchone(
        "SELECT 1 FROM user_groups WHERE username = ? AND group_id = ?",
        (username, group_id)
    )
    return row is not None


@html_router.get("/groups/{group_id}/settings")
async def get_group_settings(group_id: int, user: dict = Depends(get_current_user)):
    """获取群设置"""
    # 权限校验
    if not await check_group_permission(user, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此群设置"
        )
    
    from py.setting import GroupSettings
    settings = await GroupSettings.get_all_settings(group_id)
    
    return {"group_id": group_id, "settings": settings}


@html_router.post("/groups/{group_id}/settings")
async def update_group_settings(group_id: int, settings: dict, user: dict = Depends(get_current_user)):
    """更新群设置"""
    if not await check_group_permission(user, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此群设置"
        )
    
    from py.setting import GroupSettings
    
    for key, value in settings.items():
        if key in GroupSettings.SETTING_FIELDS:
            await GroupSettings.set_setting(group_id, key, bool(value))
    
    return {"status": "ok"}


# ==================== 管理员接口 ====================

@html_router.get("/admin/groups")
async def admin_get_groups(user: dict = Depends(require_role("admin"))):
    """获取所有群列表"""
    db = await db_manager.get_db('set')
    rows = await db.fetchall("SELECT DISTINCT group_id FROM group_settings")
    return {"groups": [r[0] for r in rows]}


@html_router.get("/admin/stats")
async def admin_get_stats(user: dict = Depends(require_role("admin"))):
    """获取全局统计"""
    stats = await get_stats()
    return stats


# ==================== 用户接口 ====================

@html_router.get("/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "role": user.get("role"),
        "username": user.get("sub"),
        "group_id": user.get("group_id")
    }


@html_router.get("/user/groups")
async def get_user_groups(user: dict = Depends(get_current_user)):
    """获取用户管理的群列表"""
    if user.get("role") == "admin":
        # 管理员可以管理所有群
        db = await db_manager.get_db('set')
        rows = await db.fetchall("SELECT DISTINCT group_id FROM group_settings")
        return {"groups": [r[0] for r in rows]}
    
    # 普通用户返回关联的群
    db = await db_manager.get_db('set')
    username = user.get("sub")
    rows = await db.fetchall(
        "SELECT group_id FROM user_groups WHERE username = ?",
        (username,)
    )
    return {"groups": [r[0] for r in rows]}


@html_router.post("/user/add-group")
async def add_user_group(request: GroupCodeRequest, user: dict = Depends(get_current_user)):
    """为用户添加管理群"""
    if user.get("role") == "admin":
        return {"status": "ok", "message": "管理员可以管理所有群"}
    
    db = await db_manager.get_db('set')
    username = user.get("sub")
    group_id = request.group_id
    
    # 检查是否已添加
    existing = await db.fetchone(
        "SELECT 1 FROM user_groups WHERE username = ? AND group_id = ?",
        (username, group_id)
    )
    if existing:
        return {"status": "ok", "message": "群已在管理列表中"}
    
    # 添加群
    await db.execute(
        "INSERT INTO user_groups (username, group_id, create_time) VALUES (?, ?, ?)",
        (username, group_id, int(time.time()))
    )
    await db.commit()
    
    return {"status": "ok", "message": "添加成功"}
