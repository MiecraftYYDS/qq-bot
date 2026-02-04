#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
搜索工具模块 - 异步版本
提供网页搜索、内容抓取等功能
"""

import httpx
from bs4 import BeautifulSoup
import html2text
from typing import List, Dict, Optional
from urllib.parse import urlparse
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 线程池用于运行同步代码
_executor = ThreadPoolExecutor(max_workers=4)


class AsyncSearchTools:
    """异步搜索工具类"""
    
    def __init__(self, proxy: str = None):
        self.proxy = proxy or "http://127.0.0.1:7891"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._html_converter = html2text.HTML2Text()
        self._html_converter.ignore_links = False
        self._html_converter.ignore_images = True
    
    async def duckduckgo_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        使用 DuckDuckGo 搜索（在线程池中运行）
        """
        def _search():
            try:
                from .ddgs import DDGS
                results = []
                with DDGS(proxy=self.proxy) as ddgs:
                    for r in ddgs.text(query, max_results=max_results):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")
                        })
                return results
            except Exception as e:
                print(f"DuckDuckGo 搜索失败: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _search)
    
    async def scrape_url(self, url: str, extract_main: bool = True) -> Dict:
        """
        异步抓取网页内容
        
        Args:
            url: 网页 URL
            extract_main: 是否只提取主要内容
        
        Returns:
            包含 title, content, url 的字典
        """
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}"}
                
                html = response.text
                soup = BeautifulSoup(html, 'lxml')
                
                # 提取标题
                title = soup.title.string if soup.title else ""
                
                # 移除脚本和样式
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                
                # 提取主要内容
                if extract_main:
                    # 尝试找到主要内容区域
                    main_content = (
                        soup.find('main') or
                        soup.find('article') or
                        soup.find('div', class_=re.compile(r'content|main|article', re.I)) or
                        soup.body
                    )
                    
                    if main_content:
                        content = self._html_converter.handle(str(main_content))
                    else:
                        content = self._html_converter.handle(str(soup))
                else:
                    content = self._html_converter.handle(str(soup))
                
                # 清理内容
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
                
                # 限制长度
                if len(content) > 8000:
                    content = content[:8000] + "\n...(内容已截断)"
                
                return {
                    "title": title,
                    "url": url,
                    "content": content
                }
                
        except Exception as e:
            return {"error": str(e), "url": url}
    
    async def search_and_scrape(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        搜索并抓取结果页面内容
        """
        # 搜索
        search_results = await self.duckduckgo_search(query, max_results)
        
        if not search_results:
            return []
        
        # 并行抓取
        tasks = [self.scrape_url(r['url']) for r in search_results]
        scraped = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = []
        for i, item in enumerate(scraped):
            if isinstance(item, dict) and not item.get('error'):
                results.append({
                    **search_results[i],
                    'content': item.get('content', '')
                })
            else:
                results.append(search_results[i])
        
        return results
    
    def format_results_for_llm(self, results: List[Dict]) -> str:
        """格式化搜索结果供 LLM 使用"""
        if not results:
            return "未找到相关搜索结果。"
        
        formatted = []
        for i, r in enumerate(results, 1):
            text = f"【结果 {i}】\n"
            text += f"标题: {r.get('title', '无标题')}\n"
            text += f"链接: {r.get('url', '')}\n"
            
            if r.get('content'):
                content = r['content'][:2000]
                text += f"内容:\n{content}\n"
            elif r.get('snippet'):
                text += f"摘要: {r['snippet']}\n"
            
            formatted.append(text)
        
        return "\n---\n".join(formatted)


# 全局搜索工具实例
search_tools = AsyncSearchTools()
