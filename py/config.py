#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局配置管理模块 - 从 config.yml 加载配置
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class OneBotConfig:
    api_url: str = "http://127.0.0.1:3000"
    token: str = ""


@dataclass
class BotConfig:
    qq_id: int = 0
    admin_qq: int = 0
    version: str = "13.0.0"


@dataclass
class ZhipuConfig:
    api_key: str = ""
    model: str = "glm-4.5-air"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class DatabaseConfig:
    keep_previous_settings: bool = True


@dataclass
class AuthConfig:
    secret_key: str = "change_this_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440


@dataclass
class PathsConfig:
    font_msyh: str = "resource/msyh.ttc"
    font_tsuka: str = "resource/TsukuA.ttc"
    quote_base: str = "resource/quote_base.png"
    qtp_output: str = "qtp/"


@dataclass
class FeaturesConfig:
    report_data: bool = False
    parse_cq_code: bool = True


@dataclass
class GlobalFeaturesConfig:
    """全局功能开关"""
    ai: bool = True
    wordcloud: bool = True
    quote: bool = True
    essence: bool = True
    banme: bool = True
    repeat: bool = True
    poke: bool = True
    jm: bool = False
    welcome: bool = True
    farewell: bool = True
    checkin: bool = True


@dataclass
class RepeatSettingsConfig:
    """复读功能概率设置（全局默认值）"""
    repeat_probability: float = 0.3        # 连续相同消息复读概率
    exclamation_probability: float = 0.15  # 感叹号结尾变体复读概率


@dataclass
class DefaultGroupSettings:
    """新群默认设置"""
    broadcast_admin_changes: bool = False
    welcome_message: bool = True
    farewell_message: bool = False
    broadcast_join_request: bool = True
    wordcloud_count_english: bool = False
    wordcloud_count_single_char: bool = False
    jm_enabled: bool = False
    ai_enabled: bool = True
    repeat_enabled: bool = True
    poke_enabled: bool = True
    banme_enabled: bool = True
    quote_enabled: bool = True
    essence_enabled: bool = True


@dataclass
class Config:
    onebot: OneBotConfig = field(default_factory=OneBotConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    zhipu: ZhipuConfig = field(default_factory=ZhipuConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    global_features: GlobalFeaturesConfig = field(default_factory=GlobalFeaturesConfig)
    default_group_settings: DefaultGroupSettings = field(default_factory=DefaultGroupSettings)
    repeat_settings: RepeatSettingsConfig = field(default_factory=RepeatSettingsConfig)
    stopwords: List[str] = field(default_factory=list)


def load_config(config_path: str = "config.yml") -> Config:
    """从 YAML 文件加载配置"""
    cfg = Config()
    
    if not os.path.exists(config_path):
        print(f"⚠️ 配置文件 {config_path} 不存在，使用默认配置")
        return cfg
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # 加载各个配置段
        if 'onebot' in data:
            cfg.onebot = OneBotConfig(**data['onebot'])
        
        if 'bot' in data:
            cfg.bot = BotConfig(**data['bot'])
        
        if 'zhipu' in data:
            cfg.zhipu = ZhipuConfig(**data['zhipu'])
        
        if 'server' in data:
            cfg.server = ServerConfig(**data['server'])
        
        if 'database' in data:
            cfg.database = DatabaseConfig(**data['database'])
        
        if 'auth' in data:
            cfg.auth = AuthConfig(**data['auth'])
        
        if 'paths' in data:
            cfg.paths = PathsConfig(**data['paths'])
        
        if 'features' in data:
            cfg.features = FeaturesConfig(**data['features'])
        
        if 'global_features' in data:
            cfg.global_features = GlobalFeaturesConfig(**data['global_features'])
        
        if 'default_group_settings' in data:
            cfg.default_group_settings = DefaultGroupSettings(**data['default_group_settings'])
        
        if 'repeat_settings' in data:
            cfg.repeat_settings = RepeatSettingsConfig(**data['repeat_settings'])
        
        if 'stopwords' in data:
            cfg.stopwords = data['stopwords']
        
        print(f"✅ 配置文件 {config_path} 加载成功")
        
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
    
    return cfg


# 全局配置实例
config = load_config()
