#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 插件包初始化
"""

from .ai_agent import AsyncAIAgent


def register(router):
    """
    注册 AI 插件到路由
    
    Args:
        router: 消息路由器实例
    """
    # AI 插件通过 ai_agent.py 中的 AsyncAIAgent 类提供功能
    # 实际的消息处理逻辑在 router 中调用 AsyncAIAgent
    pass
