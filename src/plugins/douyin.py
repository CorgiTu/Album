"""
抖音热歌榜数据源插件

注意：抖音开放平台对个人开发者获取热歌榜有严格限制。
当前提供模拟的真实热歌数据以保证主流程跑通，
后续可对接第三方 API（如 https://api.xx.com/douyin/hot）替换。
"""

from . import BaseCrawler, register


@register("抖音热歌榜")
class DouyinCrawler(BaseCrawler):
    """抖音热歌榜数据抓取"""

    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        print(f"[douyin] 抓取抖音热歌榜 (top_n={count})")
        mock_songs = [
            {"song": "离别开出花", "artist": "叶恨水"},
            {"song": "有你在", "artist": "Bomb比尔"},
            {"song": "若月亮没来", "artist": "王宇宙Leto / 乔浚丞"},
            {"song": "绽放", "artist": "王靖雯"},
            {"song": "如果爱忘了", "artist": "汪苏泷 / 单依纯"},
            {"song": "奢香夫人", "artist": "凤凰传奇"},
            {"song": "爱财爱己", "artist": "周林枫 / 陈凯彤"},
            {"song": "借过一下", "artist": "周深"},
            {"song": "无名的人", "artist": "毛不易"},
            {"song": "小美满", "artist": "周深"},
            {"song": "蜚蜚", "artist": "陈僖仪"},
            {"song": "盛夏光年", "artist": "五月天"},
            {"song": "慢冷", "artist": "梁静茹"},
            {"song": "指纹", "artist": "杜宣达"},
            {"song": "悬溺", "artist": "葛东琪"},
            {"song": "爱的回归线", "artist": "陈韵若 / 陈每文"},
            {"song": "说好的幸福呢", "artist": "周杰伦"},
            {"song": "遇见", "artist": "孙燕姿"},
            {"song": "童话", "artist": "光良"},
            {"song": "嘉宾", "artist": "张远"},
        ]
        return mock_songs[:count]
