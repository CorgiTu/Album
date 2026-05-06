"""
网易云音乐 API 交互模块（基于 pyncm 库）
使用成熟的 AES+RSA 加密库处理鉴权，支持手动 Cookie 登录
"""

import pyncm
from pyncm.apis.login import LoginViaCookie, GetCurrentLoginStatus
from pyncm.apis.cloudsearch import GetSearchResult
from pyncm.apis.playlist import SetCreatePlaylist, SetManipulatePlaylistTracks, GetPlaylistInfo


class NeteaseError(Exception):
    """网易云 API 操作基类异常"""


class CookieInvalidError(NeteaseError):
    """Cookie 无效或已过期"""


class SearchFailedError(NeteaseError):
    """歌曲搜索失败"""


class PlaylistOperationError(NeteaseError):
    """歌单操作失败"""


def _parse_music_u(cookie: str) -> str:
    """从 Cookie 字符串中提取 MUSIC_U 值

    兼容两种粘贴方式：
      1. 完整格式: ``MUSIC_U=xxxxx; OTHER=yyy``  （从请求头或 Cookie 编辑器复制）
      2. 纯值格式: ``xxxxx``                        （从浏览器 DevTools Value 列复制）
    """
    raw = cookie.strip()

    # 方式一：从键值对中提取
    for item in raw.replace("\n", ";").split(";"):
        item = item.strip()
        if item.startswith("MUSIC_U="):
            return item[len("MUSIC_U="):]

    # 方式二：用户只粘贴了 MUSIC_U 的纯值（最常见）
    # 纯值通常是一段无空白、无 "=" 的较长字符串
    if raw and "=" not in raw and " " not in raw:
        return raw

    raise CookieInvalidError(
        "无法识别输入的 Cookie 格式\n\n"
        "正确操作：\n"
        "  1. 打开 https://music.163.com 并登录\n"
        "  2. 按 F12 → 应用(Application) → Storage → Cookies\n"
        "  3. 找到 `MUSIC_U`，双击 Value 单元格 → Ctrl+C 复制\n"
        "  4. 回到本程序，直接 Ctrl+V 粘贴到输入框\n\n"
        "常见错误：\n"
        "  - 复制了 `MUSIC_U=` 以外的其他 Cookie 字段\n"
        "  - 复制了网页源码中的非 Cookie 内容"
    )


def _init_session(cookie: str) -> dict:
    """
    初始化 pyncm Session 并加载 Cookie

    Args:
        cookie: 用户粘贴的 Cookie 字符串（含 MUSIC_U=xxx）

    Returns:
        登录状态信息

    Raises:
        CookieInvalidError: Cookie 无效或登录失败
    """
    music_u = _parse_music_u(cookie)

    pyncm.SetNewSession()
    try:
        result = LoginViaCookie(MUSIC_U=music_u)
    except Exception as e:
        raise CookieInvalidError(f"Cookie 登录失败: {e}")

    # LoginViaCookie 返回 {"code": 200, "result": session.login_info}
    # 真正的登录结果存储在 result.result.success 中
    login_info = result.get("result", {})
    if not login_info.get("success"):
        content = login_info.get("content", {})
        if isinstance(content, dict):
            error_msg = content.get("message", str(content.get("code", "未知错误")))
        else:
            error_msg = str(content)
        raise CookieInvalidError(f"Cookie 登录失败: {error_msg}")

    status = GetCurrentLoginStatus()
    if not status.get("account"):
        raise CookieInvalidError("Cookie 已过期，请重新获取")

    return status


def search_song(keyword: str, cookie: str) -> int | None:
    """
    搜索歌曲，返回第一首匹配的 track_id

    Args:
        keyword: 搜索关键词，如 "天黑黑 孙燕姿"
        cookie: 网易云 MUSIC_U Cookie 字符串

    Returns:
        匹配到的 track_id，未找到返回 None

    Raises:
        CookieInvalidError: Cookie 无效
        SearchFailedError: 搜索请求失败
    """
    _init_session(cookie)

    try:
        result = GetSearchResult(keyword, limit=5)
    except Exception as e:
        raise SearchFailedError(f"搜索请求异常: {e}") from e

    if result.get("code") != 200:
        return None

    songs = result.get("result", {}).get("songs", [])
    if not songs:
        return None

    return songs[0]["id"]


def create_playlist(name: str, cookie: str) -> int | None:
    """
    创建新歌单

    Args:
        name: 歌单名称（如 "孙燕姿专属精选"）
        cookie: 网易云 MUSIC_U Cookie 字符串

    Returns:
        新建歌单的 playlist_id，失败返回 None

    Raises:
        CookieInvalidError: Cookie 无效
        PlaylistOperationError: 创建歌单请求失败
    """
    _init_session(cookie)

    try:
        result = SetCreatePlaylist(name)
    except Exception as e:
        raise PlaylistOperationError(f"创建歌单请求异常: {e}") from e

    if result.get("code") == 200:
        return result.get("playlist", {}).get("id")
    return None


def add_songs_to_playlist(playlist_id: int, track_ids: list[int], cookie: str) -> bool:
    """
    批量添加歌曲到指定歌单

    Args:
        playlist_id: 目标歌单 ID
        track_ids: 歌曲 ID 列表
        cookie: 网易云 MUSIC_U Cookie 字符串

    Returns:
        是否添加成功（code=200 或 502 视为成功）

    Raises:
        CookieInvalidError: Cookie 无效
        PlaylistOperationError: 添加歌曲请求失败
    """
    _init_session(cookie)

    str_ids = [str(tid) for tid in track_ids]
    try:
        result = SetManipulatePlaylistTracks(str_ids, playlist_id, op="add")
    except Exception as e:
        raise PlaylistOperationError(f"添加歌曲请求异常: {e}") from e

    if result.get("code") == 200:
        return True
    return result.get("code") == 502


def get_playlist_track_ids(playlist_id: int, cookie: str) -> set[int]:
    """
    查询指定歌单中所有已有歌曲的 ID 集合

    Args:
        playlist_id: 歌单 ID
        cookie: 网易云 MUSIC_U Cookie 字符串

    Returns:
        歌曲 ID 的集合（set[int]），可用于 O(1) 查重

    Raises:
        CookieInvalidError: Cookie 无效
        PlaylistOperationError: 获取歌单信息失败
    """
    _init_session(cookie)

    try:
        result = GetPlaylistInfo(playlist_id)
    except Exception as e:
        raise PlaylistOperationError(f"获取歌单信息异常: {e}") from e

    if result.get("code") != 200:
        raise PlaylistOperationError(
            f"获取歌单信息失败，API 返回 code={result.get('code')}"
        )

    playlist = result.get("playlist", {})
    track_ids_raw = playlist.get("trackIds", [])

    return {item["id"] for item in track_ids_raw if "id" in item}
