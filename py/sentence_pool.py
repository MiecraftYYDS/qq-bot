#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
随机语录池 - 用于禁言等功能的随机回复
"""

import random
from pathlib import Path
import os

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent


def _load_sentences(filename: str) -> list:
    """读取文件并按 --- 分隔成句子列表"""
    file_path = ROOT_DIR / "text" / filename
    if not file_path.exists():
        return ["默认语录"]
    text = file_path.read_text(encoding="utf-8")
    sentences = [s.strip() for s in text.split('---') if s.strip()]
    return sentences if sentences else ["默认语录"]


# 延迟加载，首次调用时才加载
_gl_sentences = None
_fgl_sentences = None


def get_gl() -> str:
    """随机返回 gl.txt 中的一句（管理员被禁言时的回复）"""
    global _gl_sentences
    if _gl_sentences is None:
        _gl_sentences = _load_sentences("gl.txt")
    return random.choice(_gl_sentences)


def get_fgl() -> str:
    """随机返回 fgl.txt 中的一句（普通用户被禁言时的回复）"""
    global _fgl_sentences
    if _fgl_sentences is None:
        _fgl_sentences = _load_sentences("fgl.txt")
    return random.choice(_fgl_sentences)


def reload_sentences():
    """重新加载语录（用于热更新）"""
    global _gl_sentences, _fgl_sentences
    _gl_sentences = _load_sentences("gl.txt")
    _fgl_sentences = _load_sentences("fgl.txt")
    return len(_gl_sentences), len(_fgl_sentences)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🎲 随机语录池测试")
    print("=" * 50)
    
    gl_count, fgl_count = reload_sentences()
    print(f"✅ 加载完成: gl.txt={gl_count}条, fgl.txt={fgl_count}条")
    
    print("\n📝 GL 语录示例 (管理员):")
    for i in range(3):
        print(f"  {i+1}. {get_gl()}")
    
    print("\n📝 FGL 语录示例 (普通用户):")
    for i in range(3):
        print(f"  {i+1}. {get_fgl()}")
