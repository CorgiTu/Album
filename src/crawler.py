"""
阶段一：核心歌曲获取逻辑
使用 pyncm 直接调用网易云 API 搜索歌手热门歌曲
完全移除 Playwright 浏览器依赖
"""

import asyncio
import json

from pyncm.apis.cloudsearch import GetSearchResult
from pyncm.apis.artist import GetArtistTracks
from pyncm.apis.login import LoginViaAnonymousAccount


class SongCrawler:
    """基于 pyncm 的歌曲获取器，通过网易云 API 获取歌手热门歌曲"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.timeout = timeout

    async def search_top_songs(self, artist: str, top_n: int = 20) -> list[dict]:
        """
        搜索指定歌手的热门歌曲

        Args:
            artist: 歌手名，如 "孙燕姿"
            top_n:  最多返回的歌曲数量

        Returns:
            [{"song": "天黑黑", "artist": "孙燕姿"}, ...]
        """
        try:
            songs = await asyncio.to_thread(self._fetch_hot_songs, artist, top_n)
        except Exception as e:
            print(f"[crawler] 搜索异常: {type(e).__name__}: {e}")
            return []
        return songs

    def _fetch_hot_songs(self, artist: str, top_n: int) -> list[dict]:
        """同步阻塞方法：通过 pyncm 获取歌手热门歌曲"""
        LoginViaAnonymousAccount()

        sr = GetSearchResult(artist, stype=100, limit=1)
        artists = sr.get("result", {}).get("artists", [])
        if not artists:
            return []

        artist_id = str(artists[0]["id"])
        tracks = GetArtistTracks(artist_id, offset=0, limit=top_n, order="hot")
        songs = tracks.get("songs", [])

        result = []
        for s in songs:
            anames = [a.get("name", "") for a in s.get("artists", s.get("ar", []))]
            result.append({
                "song": s.get("name", ""),
                "artist": " / ".join(anames),
            })

        return result


class CrawlerError(Exception):
    """爬虫操作异常"""
