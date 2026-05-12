"""
汽水音乐数据源插件

汽水音乐为字节跳动旗下音乐平台，目前暂无公开 API。
当前为框架实现，返回测试数据保证流程可跑通。
"""

from . import BaseCrawler, register

HOT_SONGS_FALLBACK = [
    {"song": "不如", "artist": "秦海清"},
    {"song": "难却", "artist": "平生不晚"},
    {"song": "小城夏天", "artist": "LBI利比"},
    {"song": "落在生命里的光", "artist": "尹昔眠"},
    {"song": "追寻", "artist": "刘至佳"},
    {"song": "爱人错过", "artist": "告五人"},
    {"song": "偷心", "artist": "陈小满"},
    {"song": "心跳的证明", "artist": "不是花火呀"},
    {"song": "爱都爱了", "artist": "小洲"},
    {"song": "祝你爱我到天荒地老", "artist": "颜人中 / 邹念慈"},
    {"song": "世间美好与你环环相扣", "artist": "柏松"},
    {"song": "执迷不悟", "artist": "铁脑袋"},
    {"song": "飞鸟和蝉", "artist": "任然"},
    {"song": "一吻天荒", "artist": "胡歌"},
    {"song": "来不及", "artist": "何洁"},
    {"song": "盛夏", "artist": "毛不易"},
    {"song": "指纹", "artist": "杜宣达"},
    {"song": "我们说好的", "artist": "张靓颖"},
    {"song": "下一个天亮", "artist": "郭静"},
    {"song": "雨爱", "artist": "杨丞琳"},
]


@register("汽水音乐")
class QishuiCrawler(BaseCrawler):
    """汽水音乐歌曲获取器（框架实现）"""

    async def fetch(self, target: str = "", count: int = 20, search_type: str = "artist") -> list[dict]:
        if not target or not target.strip():
            return self._get_fallback(count)
        print(f"[qishui] 汽水音乐暂未开放公开 API，返回测试数据")
        return self._get_fallback(count)

    def _get_fallback(self, top_n: int) -> list[dict]:
        return HOT_SONGS_FALLBACK[:top_n]
