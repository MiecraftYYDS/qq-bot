#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 智能体核心模块 - 异步版本
基于智谱 AI，支持工具调用
"""

import json
import random
import asyncio
import ast
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from py.config import config
from py.onebot_api import onebot, send_group_msg, send_private_msg

from .search_tools import search_tools


# 线程池
_executor = ThreadPoolExecutor(max_workers=4)

# 危险模块列表
DANGEROUS_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "requests", "urllib", "ftplib", "telnetlib", "multiprocessing",
    "threading", "ctypes", "pickle"
}


def is_safe_python(code: str) -> bool:
    """检查 Python 代码是否安全"""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in DANGEROUS_MODULES:
                        return False
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in DANGEROUS_MODULES:
                    return False
        return True
    except Exception:
        return False


class AsyncAIAgent:
    """异步 AI 智能体"""
    
    def __init__(self, group_id: int = None, user_id: int = None, is_bot_admin: bool = False):
        """
        初始化智能体
        
        Args:
            group_id: 群号
            user_id: 用户 QQ 号
            is_bot_admin: 机器人是否为群管理员
        """
        self.group_id = group_id
        self.user_id = user_id
        self.is_bot_admin = is_bot_admin
        self.model = config.zhipu.model
        self.search_count = 0
        self.max_search = 7
        
        # 定义工具
        self.tools = self._build_tools()
    
    def _build_tools(self) -> List[Dict]:
        """构建工具列表"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "搜索互联网获取实时信息。当用户询问最新资讯、实时数据、具体事实等需要查询外部知识的问题时使用。(搜索限制7次/对话)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "返回结果数量，默认3",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scrape_webpage",
                    "description": "抓取指定网页的完整内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "网页 URL"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "python_code_executor",
                    "description": "执行 Python 代码进行计算或数据处理",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要执行的 Python 代码"
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "random_number",
                    "description": "生成随机整数",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "min_value": {"type": "integer", "default": 1},
                            "max_value": {"type": "integer", "default": 100}
                        },
                        "required": []
                    }
                }
            }
        ]
        
        # 如果机器人是管理员，添加禁言工具
        if self.is_bot_admin:
            tools.append({
                "type": "function",
                "function": {
                    "name": "mute_user",
                    "description": "禁言当前对话的用户。用户说'禁言我'、'ban我'时必须执行",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration_seconds": {
                                "type": "integer",
                                "description": "禁言秒数，0表示随机1-20分钟",
                                "default": 0
                            },
                            "reason": {
                                "type": "string",
                                "description": "禁言原因",
                                "default": "用户请求"
                            }
                        },
                        "required": []
                    }
                }
            })
        
        return tools
    
    async def _call_zhipu_api(self, messages: List[Dict], use_tools: bool = True) -> Dict:
        """调用智谱 API（在线程池中）"""
        def _call():
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=config.zhipu.api_key)
            
            kwargs = {
                "model": self.model,
                "messages": messages
            }
            
            if use_tools and self.tools:
                kwargs["tools"] = self.tools
            
            response = client.chat.completions.create(**kwargs)
            return response
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _call)
    
    async def _execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """执行工具函数"""
        try:
            if tool_name == "web_search":
                if self.search_count >= self.max_search:
                    return "搜索次数已达上限"
                
                self.search_count += 1
                query = arguments.get("query", "")
                max_results = arguments.get("max_results", 3)
                
                if self.group_id:
                    await send_group_msg(self.group_id, f"🔍 正在搜索: {query}")
                
                results = await search_tools.search_and_scrape(query, max_results)
                return search_tools.format_results_for_llm(results)
            
            elif tool_name == "scrape_webpage":
                url = arguments.get("url", "")
                if self.group_id:
                    await send_group_msg(self.group_id, f"📄 正在抓取: {url}")
                
                result = await search_tools.scrape_url(url)
                if result.get('error'):
                    return f"抓取失败: {result['error']}"
                return f"标题: {result.get('title')}\n内容:\n{result.get('content')}"
            
            elif tool_name == "python_code_executor":
                code = arguments.get("code", "")
                return await self._execute_python(code)
            
            elif tool_name == "random_number":
                min_val = arguments.get("min_value", 1)
                max_val = arguments.get("max_value", 100)
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                result = random.randint(min_val, max_val)
                return f"随机数: {result} (范围: {min_val}~{max_val})"
            
            elif tool_name == "mute_user":
                return await self._mute_user(
                    arguments.get("duration_seconds", 0),
                    arguments.get("reason", "用户请求")
                )
            
            else:
                return f"未知工具: {tool_name}"
                
        except Exception as e:
            return f"工具执行错误: {str(e)}"
    
    async def _execute_python(self, code: str) -> str:
        """安全执行 Python 代码"""
        if not is_safe_python(code):
            return "代码包含禁止的模块，已拒绝执行"
        
        def _run():
            import io
            import sys
            
            buffer = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buffer
            
            try:
                safe_builtins = {
                    "print": print, "range": range, "len": len,
                    "min": min, "max": max, "sum": sum, "abs": abs,
                    "enumerate": enumerate, "zip": zip, "sorted": sorted,
                    "all": all, "any": any, "map": map, "filter": filter,
                    "int": int, "float": float, "str": str, "bool": bool,
                    "list": list, "dict": dict, "set": set, "tuple": tuple,
                    "round": round, "divmod": divmod, "pow": pow,
                }
                
                local_vars = {}
                exec(code, {"__builtins__": safe_builtins}, local_vars)
                
                output = buffer.getvalue()
                result = local_vars.get("result", "")
                
                final = ""
                if output.strip():
                    final += output
                if result != "":
                    final += str(result)
                
                return final or "代码执行完成，无返回值"
                
            except Exception as e:
                return f"执行错误: {e}"
            finally:
                sys.stdout = old_stdout
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _run)
    
    async def _mute_user(self, duration: int, reason: str) -> str:
        """执行禁言"""
        if not self.group_id or not self.user_id:
            return "禁言失败：缺少群号或用户ID"
        
        if not self.is_bot_admin:
            return "禁言失败：机器人没有管理员权限"
        
        # 检查目标是否是管理员
        member_info = await onebot.get_group_member_info(self.group_id, self.user_id)
        if member_info and member_info.get('role') in ('admin', 'owner'):
            return "禁言失败：管理员无法被禁言"
        
        # 随机时间
        if duration <= 0:
            duration = random.randint(60, 1200)
        
        # 限制最大时间
        duration = min(duration, 43200)
        
        success = await onebot.set_group_ban(self.group_id, self.user_id, duration)
        
        if success:
            minutes = duration // 60
            return f"已禁言 {minutes} 分钟，原因: {reason}"
        else:
            return "禁言执行失败"
    
    async def chat(self, user_message: str, context: List[Dict] = None) -> str:
        """
        执行对话
        
        Args:
            user_message: 用户消息
            context: 上下文历史
        
        Returns:
            AI 回复
        """
        messages = context.copy() if context else []
        messages.append({"role": "user", "content": user_message})
        
        max_rounds = 10
        
        for _ in range(max_rounds):
            response = await self._call_zhipu_api(messages)
            
            choice = response.choices[0]
            message = choice.message
            
            # 检查是否有工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # 添加 assistant 消息
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # 执行所有工具调用
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except:
                        arguments = {}
                    
                    result = await self._execute_tool(func_name, arguments)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # 没有工具调用，返回结果
                return message.content or ""
        
        return "处理超时，请重试"


async def create_agent(group_id: int = None, user_id: int = None) -> AsyncAIAgent:
    """
    创建 AI 智能体实例
    
    Args:
        group_id: 群号
        user_id: 用户 QQ 号
    
    Returns:
        AsyncAIAgent 实例
    """
    is_bot_admin = False
    
    if group_id:
        # 检查机器人是否是管理员
        bot_info = await onebot.get_group_member_info(group_id, config.bot.qq_id)
        if bot_info:
            is_bot_admin = bot_info.get('role') in ('admin', 'owner')
    
    return AsyncAIAgent(group_id, user_id, is_bot_admin)
