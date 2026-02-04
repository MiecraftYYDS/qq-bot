#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异步 OneBot API 封装模块
基于 httpx 实现，支持指数退避重试
"""

import re
import httpx
import asyncio
from typing import Optional, Dict, Any, List, Union
from .config import config


class OneBotAPI:
    """OneBot HTTP API 异步封装"""
    
    def __init__(self, api_url: str = None, token: str = None):
        self.api_url = api_url or config.onebot.api_url
        self.token = token or config.onebot.token
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                headers=self.headers
            )
        return self._client
    
    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def call_api(self, endpoint: str, data: Dict = None, 
                       retries: int = 3, base_delay: float = 0.5) -> Optional[Dict]:
        """
        调用 OneBot API，支持指数退避重试
        
        Args:
            endpoint: API 端点
            data: 请求数据
            retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        
        Returns:
            API 返回数据，失败返回 None
        """
        client = await self._get_client()
        url = f"{self.api_url}/{endpoint}"
        
        for attempt in range(retries):
            try:
                resp = await client.post(url, json=data or {})
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('status') == 'ok':
                        return result.get('data')
                    else:
                        print(f"[OneBot API] {endpoint} 返回错误: {result}")
                        return None
            except httpx.TimeoutException:
                print(f"[OneBot API] {endpoint} 超时，重试 {attempt + 1}/{retries}")
            except Exception as e:
                print(f"[OneBot API] {endpoint} 错误: {e}")
            
            # 指数退避
            if attempt < retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        return None
    
    # ==================== 消息发送 ====================
    
    @staticmethod
    def parse_cq_code(text: str) -> List[Dict]:
        """解析 CQ 码转换为消息段数组"""
        message = []
        last_pos = 0
        pattern = r'\[CQ:(\w+)(?:,([^\]]+))?\]'
        
        for match in re.finditer(pattern, text):
            # 添加前面的纯文本
            if match.start() > last_pos:
                plain_text = text[last_pos:match.start()]
                if plain_text:
                    message.append({"type": "text", "data": {"text": plain_text}})
            
            # 解析 CQ 码
            cq_type = match.group(1)
            cq_params_str = match.group(2)
            cq_data = {}
            
            if cq_params_str:
                for param in cq_params_str.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        cq_data[key] = value
            
            message.append({"type": cq_type, "data": cq_data})
            last_pos = match.end()
        
        # 添加剩余文本
        if last_pos < len(text):
            remaining = text[last_pos:]
            if remaining:
                message.append({"type": "text", "data": {"text": remaining}})
        
        return message if message else [{"type": "text", "data": {"text": text}}]
    
    async def send_msg(self, message_type: str, target_id: int, message: Union[str, List[Dict]], 
                       auto_escape: bool = False) -> Optional[int]:
        """
        发送消息
        
        Args:
            message_type: 消息类型 ('group' 或 'private')
            target_id: 目标 ID (群号或 QQ 号)
            message: 消息内容 (字符串或消息段数组)
            auto_escape: 是否自动转义 CQ 码
        
        Returns:
            消息 ID，失败返回 None
        """
        # 处理消息格式
        if isinstance(message, str):
            if not auto_escape:
                message = self.parse_cq_code(message)
            else:
                message = [{"type": "text", "data": {"text": message}}]
        
        payload = {
            f"{'group' if message_type == 'group' else 'user'}_id": target_id,
            "message": message
        }
        
        endpoint = f"send_{message_type}_msg"
        result = await self.call_api(endpoint, payload)
        return result.get('message_id') if result else None
    
    async def send_group_msg(self, group_id: int, message: Union[str, List[Dict]]) -> Optional[int]:
        """发送群消息"""
        return await self.send_msg('group', group_id, message)
    
    async def send_private_msg(self, user_id: int, message: Union[str, List[Dict]]) -> Optional[int]:
        """发送私聊消息"""
        return await self.send_msg('private', user_id, message)
    
    async def send_group_reply(self, group_id: int, message_id: int, 
                               message: Union[str, List[Dict]]) -> Optional[int]:
        """发送群回复消息"""
        if isinstance(message, str):
            segments = self.parse_cq_code(message)
        else:
            segments = message.copy()
        
        # 在最前面插入 reply 段
        segments.insert(0, {"type": "reply", "data": {"id": str(message_id)}})
        
        return await self.send_group_msg(group_id, segments)
    
    async def send_group_image(self, group_id: int, image: str) -> Optional[int]:
        """
        发送群图片
        
        Args:
            group_id: 群号
            image: 图片 (base64 字符串、文件路径或 URL)
        """
        # 判断图片类型
        if image.startswith('base64://'):
            file = image
        elif image.startswith(('http://', 'https://')):
            file = image
        elif len(image) > 100:  # 可能是 base64
            file = f"base64://{image}"
        else:
            file = f"file:///{image}"
        
        message = [{"type": "image", "data": {"file": file}}]
        return await self.send_group_msg(group_id, message)
    
    async def send_private_image(self, user_id: int, image: str) -> Optional[int]:
        """发送私聊图片"""
        if not image.startswith(('base64://', 'http://', 'https://', 'file:///')):
            if len(image) > 100:
                image = f"base64://{image}"
            else:
                image = f"file:///{image}"
        
        message = [{"type": "image", "data": {"file": image}}]
        return await self.send_private_msg(user_id, message)
    
    # ==================== 群操作 ====================
    
    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 60) -> bool:
        """
        群禁言
        
        Args:
            group_id: 群号
            user_id: QQ 号
            duration: 禁言时长（秒），0 为解除禁言
        """
        result = await self.call_api('set_group_ban', {
            'group_id': group_id,
            'user_id': user_id,
            'duration': duration
        })
        return result is not None
    
    async def set_group_kick(self, group_id: int, user_id: int, 
                             reject_add_request: bool = False) -> bool:
        """踢出群成员"""
        result = await self.call_api('set_group_kick', {
            'group_id': group_id,
            'user_id': user_id,
            'reject_add_request': reject_add_request
        })
        return result is not None
    
    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True) -> bool:
        """设置/取消管理员"""
        result = await self.call_api('set_group_admin', {
            'group_id': group_id,
            'user_id': user_id,
            'enable': enable
        })
        return result is not None
    
    async def set_group_special_title(self, group_id: int, user_id: int, 
                                       title: str, duration: int = -1) -> bool:
        """设置群头衔"""
        result = await self.call_api('set_group_special_title', {
            'group_id': group_id,
            'user_id': user_id,
            'special_title': title,
            'duration': duration
        })
        return result is not None
    
    async def set_essence_msg(self, message_id: int) -> bool:
        """设置精华消息"""
        result = await self.call_api('set_essence_msg', {'message_id': message_id})
        return result is not None
    
    async def delete_essence_msg(self, message_id: int) -> bool:
        """取消精华消息"""
        result = await self.call_api('delete_essence_msg', {'message_id': message_id})
        return result is not None
    
    async def set_group_add_request(self, flag: str, sub_type: str, 
                                     approve: bool = True, reason: str = '') -> bool:
        """处理入群申请"""
        result = await self.call_api('set_group_add_request', {
            'flag': flag,
            'sub_type': sub_type,
            'approve': approve,
            'reason': reason
        })
        return result is not None
    
    # ==================== 信息获取 ====================
    
    async def get_group_member_info(self, group_id: int, user_id: int, 
                                     no_cache: bool = False) -> Optional[Dict]:
        """获取群成员信息"""
        return await self.call_api('get_group_member_info', {
            'group_id': group_id,
            'user_id': user_id,
            'no_cache': no_cache
        })
    
    async def get_group_member_list(self, group_id: int) -> Optional[List[Dict]]:
        """获取群成员列表"""
        return await self.call_api('get_group_member_list', {'group_id': group_id})
    
    async def get_stranger_info(self, user_id: int, no_cache: bool = False) -> Optional[Dict]:
        """获取陌生人信息"""
        return await self.call_api('get_stranger_info', {
            'user_id': user_id,
            'no_cache': no_cache
        })
    
    async def get_login_info(self) -> Optional[Dict]:
        """获取登录账号信息"""
        return await self.call_api('get_login_info')
    
    async def get_msg(self, message_id: int) -> Optional[Dict]:
        """获取消息详情"""
        return await self.call_api('get_msg', {'message_id': message_id})
    
    async def send_like(self, user_id: int, times: int = 10) -> bool:
        """点赞"""
        result = await self.call_api('send_like', {
            'user_id': user_id,
            'times': times
        })
        return result is not None
    
    async def get_nickname(self, group_id: int, user_id: int) -> str:
        """获取用户在群内的显示名称"""
        info = await self.get_group_member_info(group_id, user_id)
        if info:
            return info.get('card') or info.get('nickname') or str(user_id)
        
        # 回退到陌生人信息
        stranger = await self.get_stranger_info(user_id)
        if stranger:
            return stranger.get('nickname') or str(user_id)
        
        return str(user_id)


# 全局 API 实例
onebot = OneBotAPI()


# ==================== 便捷函数 ====================

async def send_group_msg(group_id: int, message: Union[str, List[Dict]]) -> Optional[int]:
    return await onebot.send_group_msg(group_id, message)


async def send_private_msg(user_id: int, message: Union[str, List[Dict]]) -> Optional[int]:
    return await onebot.send_private_msg(user_id, message)


async def send_group_reply(group_id: int, message_id: int, message: Union[str, List[Dict]]) -> Optional[int]:
    return await onebot.send_group_reply(group_id, message_id, message)


async def send_group_image(group_id: int, image: str) -> Optional[int]:
    return await onebot.send_group_image(group_id, image)
