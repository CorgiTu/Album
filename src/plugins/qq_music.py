"""
QQ 音乐数据源插件

使用 pyncm 调用网易云 API 搜索歌手热门歌曲（路由层标记为 QQ 音乐）。
当接入真正的 QQ 音乐 API 时，替换此文件中的实现即可。
"""

import asyncio

from pyncm.apis.cloudsearch import GetSearchResult
from pyncm.apis.artist import GetArtistTracks
from pyncm.apis.login import LoginViaAnonymousAccount
from pyncm.apis.playlist import GetPlaylistAllTracks

from . import BaseCrawler, register

HOT_SONG_PLAYLIST_ID = 3778678


@register("QQ音乐")
class QQMusicCrawler(BaseCrawler):
    """基于 pyncm 的歌曲获取器，通过网易云 API 获取歌手热门歌曲"""

    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        if not target or not target.strip():
            return await self._fetch_hot_chart(count)
        try:
            songs = await asyncio.to_thread(self._fetch_hot_songs, target, count)
        except Exception as e:
            print(f"[qq_music] 搜索异常: {type(e).__name__}: {e}")
            return []
        return songs

    async def _fetch_hot_chart(self, top_n: int) -> list[dict]:
        try:
            songs = await asyncio.to_thread(self._do_fetch_hot_chart, top_n)
        except Exception as e:
            print(f"[qq_music] 热歌榜抓取异常: {type(e).__name__}: {e}")
            return []
        return songs

    def _do_fetch_hot_chart(self, top_n: int) -> list[dict]:
        LoginViaAnonymousAccount()
        data = GetPlaylistAllTracks(HOT_SONG_PLAYLIST_ID, limit=top_n)
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
