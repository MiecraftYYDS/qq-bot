#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时任务管理模块 - 基于 APScheduler
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional
import asyncio


class SchedulerManager:
    """定时任务调度管理器"""
    
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._jobs = {}
    
    def start(self):
        """启动调度器"""
        if not self._scheduler.running:
            self._scheduler.start()
            self._init_default_jobs()
    
    def shutdown(self):
        """关闭调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown()
    
    def _init_default_jobs(self):
        """初始化默认定时任务"""
        # 每日词云任务将在群设置中动态添加
        pass
    
    def add_job(self, job_id: str, func: Callable, trigger: str, **kwargs):
        """
        添加定时任务
        
        Args:
            job_id: 任务 ID
            func: 任务函数
            trigger: 触发器类型 ('cron', 'interval', 'date')
            **kwargs: 触发器参数
        """
        if job_id in self._jobs:
            self.remove_job(job_id)
        
        job = self._scheduler.add_job(func, trigger, id=job_id, **kwargs)
        self._jobs[job_id] = job
        return job
    
    def add_cron_job(self, job_id: str, func: Callable, 
                     hour: int = 0, minute: int = 0, **kwargs):
        """添加每日定时任务"""
        return self.add_job(
            job_id, func, 'cron',
            hour=hour, minute=minute, **kwargs
        )
    
    def add_interval_job(self, job_id: str, func: Callable, 
                         seconds: int = 60, **kwargs):
        """添加间隔执行任务"""
        return self.add_job(
            job_id, func, 'interval',
            seconds=seconds, **kwargs
        )
    
    def remove_job(self, job_id: str) -> bool:
        """移除定时任务"""
        if job_id in self._jobs:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
            del self._jobs[job_id]
            return True
        return False
    
    def get_job(self, job_id: str):
        """获取任务"""
        return self._jobs.get(job_id)
    
    def list_jobs(self):
        """列出所有任务"""
        return list(self._jobs.keys())


# 全局调度管理器实例
scheduler_manager = SchedulerManager()


# ==================== 定时任务函数 ====================

async def auto_wordcloud_task(group_id: int):
    """自动词云任务"""
    from .plugins.cy import generate_and_send_wordcloud
    try:
        await generate_and_send_wordcloud(group_id)
    except Exception as e:
        print(f"[定时词云] 群 {group_id} 执行失败: {e}")


async def setup_wordcloud_schedules():
    """设置词云定时任务"""
    from .selfset import SelfSettings
    
    groups = await SelfSettings.get_all_auto_wordcloud_groups()
    
    for group_id, hour in groups:
        job_id = f"wordcloud_{group_id}"
        scheduler_manager.add_cron_job(
            job_id,
            lambda gid=group_id: asyncio.create_task(auto_wordcloud_task(gid)),
            hour=hour,
            minute=0
        )
        print(f"[定时词云] 群 {group_id} 已设置在 {hour}:00 执行")
