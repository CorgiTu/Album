"""
酷我音乐数据源插件

使用 requests 调用酷我音乐公开 API。
当前为框架实现，返回测试数据保证流程可跑通。
正式接入时替换 _real_fetch 方法中的实现即可。
"""

import asyncio

from . import BaseCrawler, register

# 酷我音乐 API 基础 URL 及请求头模板
KUWO_API_SEARCH = "http://search.kuwo.cn/r.s"
KUWO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.kuwo.cn/",
}

HOT_SONGS_FALLBACK = [
    {"song": "我记得", "artist": "赵雷"},
    {"song": "向云端", "artist": "黄绮珊 / 海洋Bo"},
    {"song": "可能", "artist": "程响"},
    {"song": "三生三幸", "artist": "海来阿木"},
    {"song": "人间烟火", "artist": "程响"},
    {"song": "想你的风吹到了我这里", "artist": "洋澜一"},
    {"song": "遇见", "artist": "孙燕姿"},
    {"song": "黄昏", "artist": "周传雄"},
    {"song": "海阔天空", "artist": "Beyond"},
    {"song": "千千阙歌", "artist": "陈慧娴"},
    {"song": "后来", "artist": "刘若英"},
    {"song": "小情歌", "artist": "苏打绿"},
    {"song": "挪威的森林", "artist": "伍佰"},
    {"song": "突然好想你", "artist": "五月天"},
    {"song": "泡沫", "artist": "邓紫棋"},
    {"song": "倒带", "artist": "蔡依林"},
    {"song": "七里香", "artist": "周杰伦"},
    {"song": "平凡之路", "artist": "朴树"},
    {"song": "光年之外", "artist": "邓紫棋"},
    {"song": "漠河舞厅", "artist": "柳爽"},
]


@register("酷我音乐")
class KuwoCrawler(BaseCrawler):
    """酷我音乐歌曲获取器"""

    async def fetch(self, target: str = "", count: int = 20, search_type: str = "artist") -> list[dict]:
        if not target or not target.strip():
            return self._get_fallback(count)
        try:
            songs = await asyncio.to_thread(self._real_fetch, target, count)
        except Exception as e:
            print(f"[kuwo] 抓取异常: {type(e).__name__}: {e}")
            songs = self._get_fallback(count)
        return songs

    def _real_fetch(self, keyword: str, top_n: int) -> list[dict]:
        import requests

        params = {
            "all": keyword,
            "ft": "music",
            "itemset": "web_2013",
            "pn": 0,
            "rn": top_n,
            "rformat": "json",
            "encoding": "utf8",
        }
        resp = requests.get(
            KUWO_API_SEARCH,
            params=params,
            headers=KUWO_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        result = []
        songs = data.get("abslist", [])
        for s in songs[:top_n]:
            result.append({
                "song": s.get("NAME", ""),
                "artist": s.get("ARTIST", ""),
            })
        return result if result else self._get_fallback(top_n)

    def _get_fallback(self, top_n: int) -> list[dict]:
        return HOT_SONGS_FALLBACK[:top_n]
