#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行时全局开关状态，供管理面板与业务逻辑共享。"""

from dataclasses import dataclass

@dataclass
class AdminState:
    enabled: bool = True
    ai_enabled: bool = True
    debug: bool = False

admin_state = AdminState()
