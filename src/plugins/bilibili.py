"""
B站音乐区热门数据源插件

注意：B站官方 API 需要申请 referer 验证。
当前提供模拟的真实热门翻唱/原创数据以保证主流程跑通，
后续可对接 B站 API（如 https://api.bilibili.com/x/web-interface/ranking/v2?rid=3）替换。
"""

from . import BaseCrawler, register


@register("B站音乐区热门")
class BilibiliCrawler(BaseCrawler):
    """B站音乐区热门数据抓取"""

    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        print(f"[bilibili] 抓取 B站音乐区热门 (top_n={count})")
        mock_songs = [
            {"song": "青花瓷（翻唱）", "artist": "某声君"},
            {"song": "起风了（翻唱）", "artist": "买辣椒也用券"},
            {"song": "错位时空（翻唱）", "artist": "艾辰"},
            {"song": "孤勇者（翻唱）", "artist": "祖娅纳惜"},
            {"song": "向云端（翻唱）", "artist": "黄霄雲"},
            {"song": "我记得（翻唱）", "artist": "赵让"},
            {"song": "行走的鱼（翻唱）", "artist": "汪苏泷"},
            {"song": "笼（翻唱）", "artist": "张碧晨"},
            {"song": "就让这大雨全都落下（翻唱）", "artist": "容祖儿"},
            {"song": "山茶花读不懂白玫瑰（翻唱）", "artist": "L（桃籽）"},
            {"song": "字字句句（翻唱）", "artist": "卢卢快闭嘴"},
            {"song": "霸王别姬（翻唱）", "artist": "周深"},
            {"song": "我曾遇到一束光（翻唱）", "artist": "叶里"},
            {"song": "是你（翻唱）", "artist": "梦然"},
            {"song": "光亮（翻唱）", "artist": "周深"},
            {"song": "一程山路（翻唱）", "artist": "毛不易"},
            {"song": "花开忘忧（翻唱）", "artist": "叶炫清"},
            {"song": "黑月光（翻唱）", "artist": "张碧晨 / 毛不易"},
            {"song": "人间烟火（翻唱）", "artist": "程响"},
            {"song": "光芒（翻唱）", "artist": "王栎鑫"},
        ]
        return mock_songs[:count]
