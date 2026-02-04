#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
机器人测试工具 - 检查各模块是否正常工作
"""

import asyncio
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def add(self, name: str, success: bool, message: str = ""):
        if success:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            print(f"  ❌ {name}: {message}")
        self.results.append((name, success, message))
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 50}")
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.failed > 0:
            print(f"失败的测试:")
            for name, success, msg in self.results:
                if not success:
                    print(f"  - {name}: {msg}")
        print(f"{'=' * 50}")
        return self.failed == 0


async def test_imports(result: TestResult):
    """测试模块导入"""
    print("\n📦 测试模块导入...")
    
    modules = [
        ("py.config", "配置模块"),
        ("py.sqline", "数据库模块"),
        ("py.onebot_api", "OneBot API 模块"),
        ("py.router", "路由模块"),
        ("py.autointime", "定时任务模块"),
        ("py.setting", "群设置模块"),
        ("py.selfset", "用户设置模块"),
        ("py.system_msg", "系统消息模块"),
        ("py.html", "WebUI 模块"),
    ]
    
    for module_name, desc in modules:
        try:
            __import__(module_name)
            result.add(f"导入 {desc} ({module_name})", True)
        except Exception as e:
            result.add(f"导入 {desc} ({module_name})", False, str(e))


async def test_plugins(result: TestResult):
    """测试插件加载"""
    print("\n🔌 测试插件加载...")
    
    plugins = [
        "py.plugins.help",
        "py.plugins.small",
        "py.plugins.cy",
        "py.plugins.qorqtp",
        "py.plugins.repeat",
        "py.plugins.poke",
        "py.plugins.banme",
        "py.plugins.jm",
        "py.plugins.ai",
    ]
    
    for plugin in plugins:
        try:
            mod = __import__(plugin, fromlist=['register'])
            if hasattr(mod, 'register'):
                result.add(f"插件 {plugin.split('.')[-1]}", True)
            else:
                result.add(f"插件 {plugin.split('.')[-1]}", False, "缺少 register 函数")
        except Exception as e:
            result.add(f"插件 {plugin.split('.')[-1]}", False, str(e))


async def test_config(result: TestResult):
    """测试配置加载"""
    print("\n⚙️ 测试配置...")
    
    try:
        from py.config import config
        
        result.add("配置文件加载", True)
        result.add(f"Bot QQ: {config.bot.qq}", config.bot.qq > 0, "QQ号无效")
        result.add(f"服务端口: {config.server.port}", 1 <= config.server.port <= 65535)
        result.add(f"OneBot URL: {config.onebot.url}", config.onebot.url.startswith("http"))
        
    except Exception as e:
        result.add("配置文件加载", False, str(e))


async def test_database(result: TestResult):
    """测试数据库"""
    print("\n💾 测试数据库...")
    
    try:
        from py.sqline import db_manager
        
        await db_manager.init_all()
        result.add("数据库初始化", True)
        
        # 测试连接
        async with db_manager.data_pool.connection() as conn:
            cursor = await conn.execute("SELECT 1")
            row = await cursor.fetchone()
            result.add("data.db 连接", row is not None and row[0] == 1)
        
        async with db_manager.set_pool.connection() as conn:
            cursor = await conn.execute("SELECT 1")
            row = await cursor.fetchone()
            result.add("set.db 连接", row is not None and row[0] == 1)
        
        await db_manager.close_all()
        result.add("数据库关闭", True)
        
    except Exception as e:
        result.add("数据库测试", False, str(e))


async def test_onebot_connection(result: TestResult):
    """测试 OneBot 连接"""
    print("\n🔗 测试 OneBot 连接...")
    
    try:
        from py.onebot_api import api
        
        info = await api.get_login_info()
        if info and "user_id" in info:
            result.add(f"OneBot 连接 (QQ: {info.get('user_id')})", True)
        else:
            result.add("OneBot 连接", False, "无法获取登录信息，请确保 OneBot 已启动")
    except Exception as e:
        result.add("OneBot 连接", False, str(e))


async def test_files(result: TestResult):
    """测试必要文件"""
    print("\n📁 测试必要文件...")
    
    required_files = [
        "config.yml",
        "resource/msyh.ttc",
        "text/fgl.txt",
        "text/gl.txt",
        "md/cat.md",
        "md/expert.md",
        "md/private.md",
        "html/home.html",
        "html/css/main.css",
    ]
    
    for f in required_files:
        exists = os.path.exists(f)
        result.add(f"文件 {f}", exists, "文件不存在" if not exists else "")


async def test_directories(result: TestResult):
    """测试目录结构"""
    print("\n📂 测试目录结构...")
    
    required_dirs = [
        "py",
        "py/plugins",
        "py/plugins/ai",
        "sqline",
        "resource",
        "text",
        "qtp",
        "html",
        "html/css",
        "md",
    ]
    
    for d in required_dirs:
        exists = os.path.isdir(d)
        result.add(f"目录 {d}", exists, "目录不存在" if not exists else "")


async def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 QQ Bot 测试工具")
    print("=" * 50)
    
    result = TestResult()
    
    # 运行所有测试
    await test_directories(result)
    await test_files(result)
    await test_imports(result)
    await test_config(result)
    await test_plugins(result)
    await test_database(result)
    
    # OneBot 连接测试（可选）
    print("\n是否测试 OneBot 连接？(需要 OneBot 已启动) [y/N]: ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            await test_onebot_connection(result)
    except:
        pass
    
    # 输出总结
    success = result.summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
