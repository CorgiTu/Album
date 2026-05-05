"""
阶段三：Flet GUI 主界面
整合爬虫 + 网易云 API，提供完整的桌面端体验
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import flet as ft

import crawler
from netease import (
    search_song,
    create_playlist,
    add_songs_to_playlist,
    CookieInvalidError,
    SearchFailedError,
    PlaylistOperationError,
)

# COOKIE_FILE = str(Path(__file__).parent.parent / "cookie.txt")


class AppState:
    """集中管理界面控件引用和共享状态"""

    def __init__(self):
        self.artist_input: ft.TextField | None = None
        self.count_input: ft.TextField | None = None
        self.source_dropdown: ft.Dropdown | None = None
        self.playlist_input: ft.TextField | None = None
        self.cookie_input: ft.TextField | None = None

        self.generate_button: ft.FilledTonalButton | None = None

        # [注释保留] 扫码登录控件
        # self.api: NeteaseAPI | None = None
        # self.login_button: ft.ElevatedButton | None = None
        # self.qr_container: ft.Container | None = None
        # self.qr_image: ft.Image | None = None
        # self.login_status: ft.Text | None = None

        self.log_text: ft.Text | None = None
        self.progress_bar: ft.ProgressBar | None = None
        self.progress_text: ft.Text | None = None


def main(page: ft.Page):
    page.title = "专辑 - 你的专属歌单生成器"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 800
    page.window.height = 750
    page.window.resizable = False
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#000000"

    state = AppState()

    # ─── 头部标题 ──────────────────────────────────────────────
    title = ft.Text(
        "专辑 Album",
        size=32,
        weight=ft.FontWeight.W_800,
        color=ft.Colors.WHITE,
    )
    subtitle = ft.Text(
        "跨平台歌单自动化同步工具",
        size=14,
        color="#888888",
    )

    # ─── 输入控件 ──────────────────────────────────────────────
    state.artist_input = ft.TextField(
        label="歌手名",
        hint_text="请输入歌手名 (留空则默认抓取全网热歌榜)",
        prefix_icon=ft.Icons.PERSON,
        expand=2,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )
    state.count_input = ft.TextField(
        label="抓取数量",
        hint_text="默认 20",
        value="20",
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix_icon=ft.Icons.NUMBERS,
        expand=1,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )
    state.source_dropdown = ft.Dropdown(
        label="数据源选择",
        value=crawler.PLATFORM_QQ,
        options=[
            ft.dropdown.Option(crawler.PLATFORM_QQ),
            ft.dropdown.Option(crawler.PLATFORM_DOUYIN),
            ft.dropdown.Option(crawler.PLATFORM_BILIBILI),
        ],
        expand=1,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )
    state.playlist_input = ft.TextField(
        label="歌单名称（可选）",
        hint_text="不填则自动生成",
        prefix_icon=ft.Icons.PLAYLIST_ADD,
        expand=2,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )
    state.cookie_input = ft.TextField(
        label="网易云 Cookie",
        hint_text="请在此处粘贴网易云网页版抓取的 MUSIC_U Cookie",
        multiline=True,
        min_lines=3,
        max_lines=3,
        prefix_icon=ft.Icons.LOCK,
        password=True,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )

    # ─── 卡片 1：核心配置区 ───────────────────────────────────
    card_config = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [state.artist_input, state.count_input],
                    spacing=12,
                ),
                ft.Row(
                    [state.source_dropdown, state.playlist_input],
                    spacing=12,
                ),
            ],
            spacing=15,
        ),
        width=600,
        bgcolor="#121212",
        border_radius=16,
        padding=25,
        border=ft.border.all(1, "#282828"),
    )

    # ─── 卡片 2：鉴权配置区 ───────────────────────────────────
    card_auth = ft.Container(
        content=ft.Column(
            [
                ft.Text("网易云 MUSIC_U", size=14, weight=ft.FontWeight.BOLD, color="#AAAAAA"),
                state.cookie_input,
            ],
            spacing=15,
        ),
        width=600,
        bgcolor="#121212",
        border_radius=16,
        padding=25,
        border=ft.border.all(1, "#282828"),
    )

    # ─── 生成按钮 ──────────────────────────────────────────────
    state.generate_button = ft.FilledButton(
        "生成专属歌单",
        icon=ft.Icons.AUTO_AWESOME,
        disabled=False,
        on_click=lambda e: _start_generate(page, state),
        width=600,
        height=50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=25),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        ),
    )

    # ─── 进度条组件 ─────────────────────────────────────────────
    state.progress_text = ft.Text(
        "",
        size=12,
        color=ft.Colors.INDIGO_300,
        visible=False,
    )
    state.progress_bar = ft.ProgressBar(
        value=0,
        visible=False,
        bar_height=4,
        color=ft.Colors.INDIGO_400,
        bgcolor=ft.Colors.GREY_800,
    )

    # ─── 日志区域 ──────────────────────────────────────────────
    state.log_text = ft.Text(
        "",
        size=12,
        font_family="consolas",
        selectable=True,
    )
    log_container = ft.Container(
        content=ft.Column(
            [state.log_text],
            scroll=ft.ScrollMode.ALWAYS,
            height=200,
        ),
        width=600,
        height=200,
        bgcolor="#0A0A0A",
        border_radius=12,
        padding=15,
        border=ft.border.all(1, "#1A1A1A"),
    )

    # ─── 定宽主容器（600px，水平居中）────────────────────────
    main_col = ft.Column(
        [
            title,
            subtitle,
            card_config,
            card_auth,
            state.generate_button,
            state.progress_text,
            state.progress_bar,
            log_container,
        ],
        width=600,
        spacing=25,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.add(
        ft.Container(
            content=main_col,
            alignment=ft.alignment.Alignment(x=0, y=-1),
            padding=ft.padding.only(top=40),
        )
    )

    # ─── 启动时读取已保存的 Cookie（免去每次粘贴）─────────────
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            saved_cookie = data.get("cookie", "")
            if saved_cookie:
                state.cookie_input.value = saved_cookie
                page.update()
        except (json.JSONDecodeError, Exception):
            pass


# ─── [注释保留] 扫码登录流程 ──────────────────────────────────


# def _start_login(page: ft.Page, state: AppState):
#     page.run_task(_do_login, page, state)


# async def _do_login(page: ft.Page, state: AppState):
#     _log(state, "正在获取二维码...")
#     print("[登录调试] 开始获取二维码 unikey")
#
#     try:
#         unikey = await asyncio.to_thread(state.api._get_qrcode_key)
#     except Exception as e:
#         msg = f"获取二维码失败（网络异常: {e}）"
#         _log(state, msg)
#         print(f"[登录调试] {msg}")
#         return
#
#     if not unikey:
#         _log(state, "获取二维码失败！API 返回空")
#         print("[登录调试] 获取 unikey 失败（返回空）")
#         return
#
#     print(f"[登录调试] 获取 unikey 成功: {unikey}")
#
#     qr_content = f"https://music.163.com/login?codekey={unikey}"
#
#     import qrcode as qrcode_lib
#     qr = qrcode_lib.QRCode(box_size=10, border=2)
#     qr.add_data(qr_content)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="black", back_color="white")
#
#     buf = io.BytesIO()
#     img.save(buf, format="PNG")
#     buf.seek(0)
#
#     data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
#     state.qr_image.src = data_uri
#     state.qr_image.visible = True
#     state.qr_container.visible = True
#     page.update()
#
#     _log(state, "二维码已生成，请使用网易云音乐 App 扫码登录...")
#     print("[登录调试] 二维码已显示，进入轮询循环")
#
#     start = time.time()
#     max_wait = 120
#     poll_count = 0
#     while time.time() - start < max_wait:
#         poll_count += 1
#         try:
#             result = await asyncio.to_thread(
#                 state.api._weapi_post,
#                 "login/qrcode/client/login",
#                 {"key": unikey, "type": 1},
#             )
#         except Exception as e:
#             print(f"[登录调试] 第 {poll_count} 次轮询请求异常: {type(e).__name__}: {e}")
#             await asyncio.sleep(2)
#             continue
#
#         code = result.get("code", -1)
#         print(f"[登录调试] 第 {poll_count} 次轮询 | 状态码: {code} | 原始响应: {result}")
#
#         if code == 803:
#             _log(state, ">> 状态码 803：登录确认成功，正在提取 Cookie...")
#             print(f"[登录调试] 803 响应中的 url: {result.get('url', '')}")
#             try:
#                 state.api._parse_cookie_from_url(result.get("url", ""))
#                 state.api._save_cookie()
#                 state.api._fetch_account_info()
#             except Exception as e:
#                 msg = f"提取 Cookie 失败: {type(e).__name__}: {e}"
#                 _log(state, msg)
#                 print(f"[登录调试] {msg}")
#                 return
#             _log(state, "扫码登录成功！")
#             print(f"[登录调试] 登录成功！MUSIC_U 存在: {'MUSIC_U' in state.api.session.cookies}")
#             state.qr_container.visible = False
#             _set_logged_in_ui(state)
#             page.update()
#             return
#         elif code == 800:
#             _log(state, ">> 状态码 800：二维码已过期，请重新尝试")
#             print("[登录调试] 二维码过期")
#             state.qr_container.visible = False
#             page.update()
#             return
#         elif code == 8821:
#             msg = result.get("message", "环境风险拦截")
#             _log(state, f">> 状态码 8821：{msg}")
#             _log(state, "提示：网易云检测到当前网络环境存在风险")
#             _log(state, "      请点击「扫码登录」重新尝试，或切换网络后重试")
#             print(f"[登录调试] 8821: {result}")
#             state.qr_container.visible = False
#             page.update()
#             return
#         elif code == 802:
#             _log(state, ">> 状态码 802：已扫码，请在手机上确认登录...")
#             print("[登录调试] 已扫码待确认")
#         elif code == 801:
#             if int(time.time()) % 6 < 2:
#                 _log(state, ">> 状态码 801：等待扫码...")
#             print(f"[登录调试] 等待扫码中... (code=801)")
#         else:
#             _log(state, f">> 未知状态码: {code}")
#             print(f"[登录调试] 未知状态码: {code}")
#
#         await asyncio.sleep(2)
#
#     _log(state, "登录超时")
#     print("[登录调试] 轮询超时 120 秒")
#     state.qr_container.visible = False
#     page.update()


# def _set_logged_in_ui(state: AppState):
#     state.login_button.text = "已登录"
#     state.login_button.disabled = True
#     state.login_button.icon = ft.Icons.CHECK_CIRCLE
#     state.login_status.value = f"已登录: {state.api.nickname or '未知'} | UID: {state.api.uid or '未知'}"
#     state.login_status.color = ft.Colors.GREEN_400
#     state.generate_button.disabled = False
#     if state.log_text.page:
#         state.log_text.page.update()


# ─── 歌单生成流程 ──────────────────────────────────────────────


def _start_generate(page: ft.Page, state: AppState):
    state.generate_button.disabled = True
    page.update()
    page.run_task(
        _do_generate,
        page, state,
        state.artist_input.value.strip(),
        _safe_int(state.count_input.value, 20),
        state.playlist_input.value.strip() or None,
        state.cookie_input.value.strip(),
        state.source_dropdown.value,
    )


async def _do_generate(
    page: ft.Page, state: AppState,
    artist: str, count: int, playlist_name: str | None, cookie: str, source: str,
):
    # ── 动态状态提示 ──────────────────────────────────────────
    if source == crawler.PLATFORM_QQ and artist:
        _log(state, f"正在从 [{source}] 抓取 {artist} 的热门歌曲...")
    else:
        _log(state, f"正在从 [{source}] 抓取数据...")

    _log(state, f"数据源: {source} | 数量: {count}")

    # ── 校验 Cookie ────────────────────────────────────────────
    if not cookie:
        _log(state, "[错误] 请先在 Cookie 输入框中粘贴网易云 MUSIC_U Cookie")
        _log(state, "提示：打开网易云网页版 → F12 → 应用/Storage → Cookies → 复制 MUSIC_U 的值")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, "[1/5] 正在抓取歌曲列表...")
    try:
        songs = await crawler.crawl(source, artist, count)
    except Exception as e:
        _log(state, f"[错误] 抓取失败: {e}")
        state.generate_button.disabled = False
        page.update()
        return

    if not songs:
        if source == crawler.PLATFORM_QQ and artist:
            _log(state, "[错误] 未抓取到任何歌曲，请检查歌手名")
        else:
            _log(state, f"[错误] 未从 [{source}] 抓取到数据，请稍后重试")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"成功抓取 {len(songs)} 首歌曲:")
    for s in songs:
        _log(state, f"  {s['song']} - {s['artist']}")

    # ── 搜索 track_id ──────────────────────────────────────────
    _log(state, f"\n[2/5] 正在网易云搜索歌曲 ID（共 {len(songs)} 首）...")
    total_songs = len(songs)
    state.progress_text.value = f"正在搜索歌曲... (0/{total_songs})"
    state.progress_text.visible = True
    state.progress_bar.value = 0
    state.progress_bar.visible = True
    page.update()

    track_ids = []
    for i, s in enumerate(songs, 1):
        keyword = f"{s['song']} {s['artist']}".strip()
        state.progress_text.value = f"正在处理: {s['artist']} - {s['song']} ({i}/{total_songs})..."
        state.progress_bar.value = i / total_songs
        page.update()
        await asyncio.sleep(0)
        _log(state, f"  搜索 [{i}/{total_songs}]: {keyword}")
        try:
            tid = await asyncio.to_thread(search_song, keyword, cookie)
            if tid:
                track_ids.append(tid)
                _log(state, f"    ✓ 匹配成功 → ID: {tid}")
            else:
                _log(state, f"    ✗ 未找到匹配")
        except CookieInvalidError as e:
            _log(state, f"\n[错误] Cookie 无效: {e}")
            _log(state, "请重新粘贴有效的 MUSIC_U Cookie 后重试")
            state.generate_button.disabled = False
            state.progress_text.visible = False
            state.progress_bar.visible = False
            page.update()
            return
        except SearchFailedError as e:
            _log(state, f"    ✗ 搜索请求异常: {e}")
        except Exception as e:
            _log(state, f"    ✗ 搜索异常: {e}")
        await asyncio.sleep(0.5)

    if not track_ids:
        _log(state, "[错误] 未匹配到任何歌曲，无法创建歌单")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"成功匹配 {len(track_ids)}/{len(songs)} 首")

    # ── 创建歌单 ──────────────────────────────────────────────
    if not playlist_name:
        if artist:
            name = f"[{artist}] 专属精选"
        else:
            today = datetime.now().strftime("%m月%d日")
            name = f"全网热歌实时精选 [{today}]"
    else:
        name = playlist_name
    _log(state, f"\n[3/5] 正在创建歌单: {name}")
    try:
        playlist_id = await asyncio.to_thread(create_playlist, name, cookie)
    except CookieInvalidError as e:
        _log(state, f"\n[错误] Cookie 无效: {e}")
        _log(state, "请重新粘贴有效的 MUSIC_U Cookie 后重试")
        state.generate_button.disabled = False
        page.update()
        return
    except PlaylistOperationError as e:
        _log(state, f"[错误] 创建歌单失败: {e}")
        state.generate_button.disabled = False
        page.update()
        return
    except Exception as e:
        _log(state, f"[错误] 创建歌单失败: {e}")
        state.generate_button.disabled = False
        page.update()
        return

    if not playlist_id:
        _log(state, "[错误] 创建歌单失败，请检查 Cookie 是否有效")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"歌单创建成功! (ID: {playlist_id})")

    # ── 添加歌曲 ──────────────────────────────────────────────
    _log(state, f"\n[4/5] 正在将 {len(track_ids)} 首歌曲添加到歌单...")
    try:
        success = await asyncio.to_thread(
            add_songs_to_playlist, playlist_id, track_ids, cookie
        )
    except CookieInvalidError as e:
        _log(state, f"\n[错误] Cookie 无效: {e}")
        _log(state, "请重新粘贴有效的 MUSIC_U Cookie 后重试")
        state.generate_button.disabled = False
        page.update()
        return
    except PlaylistOperationError as e:
        _log(state, f"[错误] 添加歌曲失败: {e}")
        state.generate_button.disabled = False
        page.update()
        return
    except Exception as e:
        _log(state, f"[错误] 添加歌曲失败: {e}")
        state.generate_button.disabled = False
        page.update()
        return

    # ── 完成 ───────────────────────────────────────────────────
    _log(state, f"\n[5/5] 操作完成!")
    if success:
        _log(state, "=" * 40)
        _log(state, "✅ 歌单已成功生成！")
        _log(state, f"   歌单名称: {name}")
        _log(state, f"   歌曲数量: {len(track_ids)} 首")
        _log(state, "=" * 40)
        state.progress_text.value = "🎉 专属歌单创建成功！"
        state.progress_bar.value = 1.0
        # 保存有效的 Cookie 到 config.json，方便下次自动填充
        _save_cookie(cookie)
    else:
        _log(state, "⚠ 添加歌曲时遇到问题，请检查网易云歌单")
        state.progress_text.visible = False
        state.progress_bar.visible = False

    state.generate_button.disabled = False
    page.update()


# ─── 工具函数 ──────────────────────────────────────────────────


def _log(state: AppState, msg: str):
    tf = state.log_text
    tf.value = (tf.value or "") + msg + "\n"
    if tf.page:
        tf.page.update()


def _safe_int(value, default):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _save_cookie(cookie: str):
    """将有效的 Cookie 保存到 config.json 文件中"""
    config_path = Path(__file__).parent.parent / "config.json"
    try:
        config_path.write_text(
            json.dumps({"cookie": cookie}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[config] 保存 Cookie 失败: {e}")


if __name__ == "__main__":
    ft.run(main=main)
