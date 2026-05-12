"""
酷狗音乐数据源插件

使用 requests 调用酷狗音乐公开 API。
当前为框架实现，返回测试数据保证流程可跑通。
正式接入时替换 _real_fetch 方法中的实现即可。
"""

import asyncio

from . import BaseCrawler, register

# 酷狗音乐 API 基础 URL 及请求头模板
KUGOU_API_BASE = "https://songsearch.kugou.com/song_search_v2"
KUGOU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.kugou.com/",
}

HOT_SONGS_FALLBACK = [
    {"song": "起风了", "artist": "买辣椒也用券"},
    {"song": "孤勇者", "artist": "陈奕迅"},
    {"song": "早安隆回", "artist": "袁树雄"},
    {"song": "空心", "artist": "光泽"},
    {"song": "错位时空", "artist": "艾辰"},
    {"song": "半生雪", "artist": "七叔（叶泽浩）"},
    {"song": "踏山河", "artist": "七叔（叶泽浩）"},
    {"song": "白月光与朱砂痣", "artist": "大籽"},
    {"song": "可可托海的牧羊人", "artist": "王琪"},
    {"song": "天外来物", "artist": "薛之谦"},
    {"song": "星辰大海", "artist": "黄霄雲"},
    {"song": "赤伶", "artist": "HITA"},
    {"song": "雾里", "artist": "姚六一"},
    {"song": "浪子闲话", "artist": "花僮"},
    {"song": "执迷不悟", "artist": "小乐哥（王惟宁）"},
    {"song": "一路生花", "artist": "温奕心"},
    {"song": "海市蜃楼", "artist": "三叔说"},
    {"song": "年少的你啊", "artist": "杨大勇"},
    {"song": "我会等", "artist": "承桓"},
    {"song": "笼", "artist": "张碧晨"},
]


@register("酷狗音乐")
class KugouCrawler(BaseCrawler):
    """酷狗音乐歌曲获取器"""

    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        if not target or not target.strip():
            return self._get_fallback(count)
        try:
            songs = await asyncio.to_thread(self._real_fetch, target, count)
        except Exception as e:
            print(f"[kugou] 抓取异常: {type(e).__name__}: {e}")
            songs = self._get_fallback(count)
        return songs

    def _real_fetch(self, keyword: str, top_n: int) -> list[dict]:
        import requests

        params = {
            "keyword": keyword,
            "page": 1,
            "pagesize": top_n,
            "platform": "WebFilter",
        }
        resp = requests.get(
            KUGOU_API_BASE,
            params=params,
            headers=KUGOU_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = []
        songs = (
            data.get("data", {})
            .get("lists", [])
        )
        for s in songs[:top_n]:
            result.append({
                "song": s.get("SongName", ""),
                "artist": s.get("ChorusSinger", ""),
            })
        return result if result else self._get_fallback(top_n)

    def _get_fallback(self, top_n: int) -> list[dict]:
        return HOT_SONGS_FALLBACK[:top_n]
