"""
插件系统基类与注册机制

所有数据源插件需继承 BaseCrawler 并使用 @register 装饰器注册。
插件被放置在 src/plugins/ 目录下，由 crawler.py 自动扫描加载。
"""

from abc import ABC, abstractmethod

_REGISTRY: dict[str, type["BaseCrawler"]] = {}


def register(platform_name: str):
    """装饰器：将爬虫类注册到全局插件注册表"""
    def wrapper(cls):
        _REGISTRY[platform_name] = cls
        cls.PLATFORM_NAME = platform_name
        return cls
    return wrapper


def get_crawler(name: str) -> "BaseCrawler | None":
    """根据平台名称获取已注册的爬虫实例"""
    cls = _REGISTRY.get(name)
    if cls is None:
        return None
    return cls()


def get_all_platforms() -> list[str]:
    """返回所有已注册的平台名称列表"""
    return list(_REGISTRY.keys())


class BaseCrawler(ABC):
    """数据源爬虫基类

    所有插件必须实现 fetch(target, count) 方法，
    返回 [{"song": "歌名", "artist": "歌手"}, ...] 格式的列表。
    """
    PLATFORM_NAME: str = ""

    @abstractmethod
    async def fetch(self, target: str = "", count: int = 20) -> list[dict]:
        ...
