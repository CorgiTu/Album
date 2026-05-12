"""
插件化爬虫加载器

启动时自动扫描 src/plugins/ 目录下的所有 .py 文件，
根据平台名称动态加载并调用对应插件的 fetch 方法。
"""

import importlib
import pkgutil
from pathlib import Path

import plugins
from plugins import BaseCrawler, get_crawler, get_all_platforms


def _discover_plugins():
    """扫描并导入 src/plugins/ 下的所有插件模块"""
    plugin_dir = Path(__file__).parent / "plugins"
    if not plugin_dir.is_dir():
        return
    for importer, modname, ispkg in pkgutil.iter_modules([str(plugin_dir)]):
        importlib.import_module(f"plugins.{modname}")


_discover_plugins()


async def crawl(platform: str, artist: str = "", top_n: int = 20) -> list[dict]:
    """
    多平台数据抓取入口 — 根据 platform 名称动态加载对应插件。

    Args:
        platform: 平台名称，如 "QQ音乐" / "抖音热歌榜" / "B站音乐区热门"
        artist:   歌手名（仅部分平台使用）
        top_n:    最多返回的歌曲数量

    Returns:
        [{"song": "歌名", "artist": "歌手"}, ...]
    """
    platform = platform.strip()
    crawler_inst = get_crawler(platform)
    if crawler_inst is None:
        print(f"[crawler] 未知平台: {platform}，使用 QQ音乐 作为兜底")
        crawler_inst = get_crawler("QQ音乐")
        if crawler_inst is None:
            return []
    return await crawler_inst.fetch(artist, top_n)


def filter_song(song_name: str, song_artist: str,
                target_artist: str,
                exclude_cover: bool, exclude_live: bool, exclude_inst: bool) -> bool:
    """上下文感知的歌曲过滤器

    Args:
        song_name:     歌曲名
        song_artist:   演唱者（可能包含多位，用 " / " 分隔）
        target_artist: 用户输入的歌手名；为空表示全网热歌榜模式
        exclude_cover: 是否排除翻唱（热榜模式下此参数被强制忽略）
        exclude_live:  是否排除 Live 版本
        exclude_inst:  是否排除伴奏/纯音乐版本

    Returns:
        True 表示通过过滤（保留），False 表示应被丢弃
    """
    name_lower = song_name.lower()
    artist_lower = song_artist.lower()

    if not target_artist or not target_artist.strip():
        if exclude_live:
            if any(kw in name_lower for kw in ("live", "现场", "演唱版")):
                return False
        if exclude_inst:
            if any(kw in name_lower for kw in ("伴奏", "instrumental", "inst.")):
                return False
        return True

    target_lower = target_artist.strip().lower()
    artists = [a.strip().lower() for a in artist_lower.split(" / ")]
    if not any(target_lower in a for a in artists):
        return False

    if exclude_cover:
        if any(kw in name_lower for kw in ("翻唱", "cover")):
            return False
    if exclude_live:
        if any(kw in name_lower for kw in ("live", "现场", "演唱版")):
            return False
    if exclude_inst:
        if any(kw in name_lower for kw in ("伴奏", "instrumental", "inst.")):
            return False

    return True


class CrawlerError(Exception):
    """爬虫操作异常"""


# 向下兼容：导出平台列表供 main.py 使用
PLATFORM_QQ = "QQ音乐"
PLATFORM_DOUYIN = "抖音热歌榜"
PLATFORM_BILIBILI = "B站音乐区热门"
