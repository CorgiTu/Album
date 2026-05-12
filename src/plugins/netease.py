"""
网易云音乐数据源插件

使用 pyncm 调用网易云官方 API 搜索歌手热门歌曲及官方热歌榜。
"""

import asyncio

from pyncm.apis.cloudsearch import GetSearchResult
from pyncm.apis.artist import GetArtistTracks
from pyncm.apis.login import LoginViaAnonymousAccount
from pyncm.apis.playlist import GetPlaylistAllTracks

from . import BaseCrawler, register

NETEASE_HOT_PLAYLIST_ID = 3778678


@register("网易云音乐")
class NeteaseCrawler(BaseCrawler):
    """基于 pyncm 的网易云音乐歌曲获取器"""

    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        if not target or not target.strip():
            return await self._fetch_hot_chart(count)
        try:
            songs = await asyncio.to_thread(self._fetch_hot_songs, target, count)
        except Exception as e:
            print(f"[netease] 搜索异常: {type(e).__name__}: {e}")
            return []
        return songs

    async def _fetch_hot_chart(self, top_n: int) -> list[dict]:
        try:
            songs = await asyncio.to_thread(self._do_fetch_hot_chart, top_n)
        except Exception as e:
            print(f"[netease] 热歌榜抓取异常: {type(e).__name__}: {e}")
            return []
        return songs

    def _do_fetch_hot_chart(self, top_n: int) -> list[dict]:
        LoginViaAnonymousAccount()
        data = GetPlaylistAllTracks(NETEASE_HOT_PLAYLIST_ID, limit=top_n)
        songs = data.get("songs", [])
        result = []
        for s in songs:
            anames = [a.get("name", "") for a in s.get("artists", s.get("ar", []))]
            result.append({
                "song": s.get("name", ""),
                "artist": " / ".join(anames),
            })
        return result

    def _fetch_hot_songs(self, artist: str, top_n: int) -> list[dict]:
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
