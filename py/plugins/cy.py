#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
词云生成插件
"""

import re
import io
import base64
import sys
import os
from collections import Counter
from wordcloud import WordCloud
import jieba

# 支持单独运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.config import config
from py.onebot_api import send_group_msg, send_group_image
from py.sqline import get_group_messages
from py.setting import GroupSettings


# 默认停用词
DEFAULT_STOPWORDS = set([
    '的', '了', '在', '是', '我', '你', '他', '她', '它', '我们', '你们', '他们',
    '就', '都', '而', '及', '与', '或', '也', '还', '又', '不', '没', '有', '能',
    '会', '可以', '要', '将', '把', '被', '让', '和', '跟', '同', '对', '对于',
    '关于', '之', '这', '那', '此', '彼', '上', '下', '前', '后', '左', '右',
    '里', '外', '中', '间', '个', '只', '支', '本', '台', '件', '条', '张',
    '回复', '引用', '图片', '语音', '视频', '文件', '链接', 'cy', 'cyyy', 'cydz',
    'settings', 'selfset', 'mute', 'jj', 'tx', 'ping', 'help', '吗', '啊',
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'or', 'that', 'the',
    'to', 'was', 'will', 'with', 'i', 'me', 'my', 'we', 'you', 'your',
])


def clean_text(text: str) -> str:
    """清理文本，移除CQ码和特殊字符"""
    # 移除CQ码
    text = re.sub(r'\[CQ:[^\]]+\]', '', text)
    # 移除URL
    text = re.sub(r'https?://\S+', '', text)
    # 移除@
    text = re.sub(r'@\S+', '', text)
    return text.strip()


def generate_wordcloud(texts: list, count_english: bool = False, 
                       count_single_char: bool = False) -> str:
    """
    生成词云图片
    
    Args:
        texts: 文本列表
        count_english: 是否统计英文
        count_single_char: 是否统计单字
    
    Returns:
        Base64 编码的图片
    """
    # 合并和清理文本
    all_text = ' '.join([clean_text(t) for t in texts])
    
    if not all_text.strip():
        return None
    
    # 分词
    words = list(jieba.cut(all_text))
    
    # 过滤
    stopwords = DEFAULT_STOPWORDS | set(config.stopwords)
    filtered_words = []
    
    for word in words:
        word = word.strip()
        if not word:
            continue
        if word.lower() in stopwords:
            continue
        
        # 单字过滤
        if len(word) == 1 and not count_single_char:
            if not word.isdigit():  # 保留数字
                continue
        
        # 英文过滤
        if word.isascii() and word.isalpha() and not count_english:
            continue
        
        filtered_words.append(word)
    
    if not filtered_words:
        return None
    
    # 统计词频
    word_freq = Counter(filtered_words)
    
    # 生成词云
    wc = WordCloud(
        font_path=config.paths.font_msyh,
        width=800,
        height=600,
        background_color='white',
        max_words=200,
        max_font_size=150,
        random_state=42
    )
    
    wc.generate_from_frequencies(word_freq)
    
    # 转为 Base64
    buffer = io.BytesIO()
    wc.to_image().save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


async def generate_and_send_wordcloud(group_id: int, hours: int = 24,
                                       count_english: bool = None,
                                       count_single_char: bool = None):
    """生成并发送词云"""
    # 获取群设置
    if count_english is None:
        count_english = await GroupSettings.get_setting(group_id, 'cyyy')
    if count_single_char is None:
        count_single_char = await GroupSettings.get_setting(group_id, 'cydz')
    
    # 获取消息
    messages = await get_group_messages(
        group_id, hours=hours, 
        exclude_bot=True, bot_id=config.bot.qq_id
    )
    
    if not messages:
        await send_group_msg(group_id, f"最近{hours}小时内没有足够的消息记录")
        return
    
    texts = [m['text'] for m in messages if m.get('text')]
    
    if len(texts) < 10:
        await send_group_msg(group_id, f"消息数量不足（{len(texts)}条），无法生成词云")
        return
    
    # 生成词云
    img_base64 = generate_wordcloud(texts, count_english, count_single_char)
    
    if not img_base64:
        await send_group_msg(group_id, "词云生成失败，可能是有效词汇不足")
        return
    
    # 发送
    await send_group_msg(group_id, f"📊 最近{hours}小时词云 (共{len(texts)}条消息)")
    await send_group_image(group_id, img_base64)


async def handle_group_message(event):
    """处理群消息"""
    raw_msg = event.raw_message or ''
    group_id = event.group_id
    
    # 检查全局开关
    if not config.global_features.wordcloud:
        return False
    
    # #cy [小时数] - 生成词云
    cy_match = re.match(r'^#cy(?:\s+(\d+))?$', raw_msg.strip())
    if cy_match:
        hours = int(cy_match.group(1) or 24)
        hours = min(max(hours, 1), 168)  # 限制1-168小时
        
        await send_group_msg(group_id, f"⏳ 正在生成词云，请稍候...")
        await generate_and_send_wordcloud(group_id, hours)
        return True
    
    # #cyyy - 词云统计英语
    if raw_msg.strip() == '#cyyy':
        await send_group_msg(group_id, f"⏳ 正在生成词云（含英文），请稍候...")
        await generate_and_send_wordcloud(group_id, 24, count_english=True)
        return True
    
    # #cydz - 词云统计单字
    if raw_msg.strip() == '#cydz':
        await send_group_msg(group_id, f"⏳ 正在生成词云（含单字），请稍候...")
        await generate_and_send_wordcloud(group_id, 24, count_single_char=True)
        return True
    
    return False


def register(plugin_manager):
    """注册插件"""
    plugin_manager.register_group_handler(handle_group_message)


# ==================== 单独运行测试 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("☁️ 词云插件测试")
    print("=" * 50)
    
    # 测试词云生成
    test_texts = [
        "今天天气真好",
        "我喜欢编程",
        "Python是最好的语言",
        "机器人很有趣",
        "大家好才是真的好",
        "学习使我快乐",
        "代码改变世界",
    ]
    
    print(f"\n📝 测试文本: {len(test_texts)} 条")
    
    img_base64 = generate_wordcloud(test_texts)
    if img_base64:
        # 保存测试图片
        import base64 as b64
        with open("test_wordcloud.png", "wb") as f:
            f.write(b64.b64decode(img_base64))
        print("✅ 词云生成成功，已保存到 test_wordcloud.png")
    else:
        print("❌ 词云生成失败")
    
    print("\n💡 命令列表:")
    print("  #cy [小时数] - 生成词云")
    print("  #cyyy - 词云统计英语")
    print("  #cydz - 词云统计单字")
