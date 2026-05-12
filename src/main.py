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
    get_playlist_track_ids,
    init_session_once,
    search_song_shared,
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

        # ── 模式切换 ──────────────────────────────────────────
        self.mode_radio_group: ft.RadioGroup | None = None
        self.mode_hint: ft.Text | None = None

        # ── 过滤选项 ───────────────────────────────────────────
        self.exclude_cover_cb: ft.Checkbox | None = None
        self.exclude_live_cb: ft.Checkbox | None = None
        self.exclude_inst_cb: ft.Checkbox | None = None
        self.filter_hint: ft.Text | None = None

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
    def _on_artist_changed(e):
        """歌手名输入变化时，联动过滤控件状态"""
        has_artist = bool(state.artist_input.value.strip())
        state.exclude_cover_cb.disabled = not has_artist
        if has_artist:
            state.exclude_cover_cb.value = True
            state.filter_hint.visible = False
        else:
            state.exclude_cover_cb.value = False
            state.filter_hint.visible = True
        page.update()

    def _on_mode_changed(e):
        """模式切换时，联动歌单输入框的提示文案"""
        is_append = state.mode_radio_group.value == "append"
        state.playlist_input.hint_text = (
            "请输入目标歌单的 ID (必填)" if is_append
            else "请输入新歌单名称 (可选)"
        )
        state.playlist_input.label = (
            "目标歌单 ID" if is_append
            else "歌单名称（可选）"
        )
        state.playlist_input.prefix_icon = (
            ft.Icons.PLAYLIST_ADD_CHECK if is_append
            else ft.Icons.PLAYLIST_ADD
        )
        state.mode_hint.visible = is_append
        state.playlist_input.value = ""
        page.update()

    state.artist_input = ft.TextField(
        label="歌手名",
        hint_text="输入歌手名（多个请用逗号或空格分隔，留空则抓取热榜）",
        prefix_icon=ft.Icons.PERSON,
        expand=2,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
        on_change=_on_artist_changed,
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
        options=[ft.dropdown.Option(p) for p in crawler.get_all_platforms()],
        expand=1,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )
    state.playlist_input = ft.TextField(
        label="歌单名称（可选）",
        hint_text="请输入新歌单名称 (可选)",
        prefix_icon=ft.Icons.PLAYLIST_ADD,
        expand=1,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
    )

    state.mode_radio_group = ft.RadioGroup(
        content=ft.Row(
            [
                ft.Radio(value="new", label="新建歌单"),
                ft.Radio(value="append", label="追加到已有"),
            ],
            spacing=4,
        ),
        value="new",
        on_change=_on_mode_changed,
    )
    state.mode_hint = ft.Text(
        "右键网易云歌单分享链接可查看 ID",
        size=10,
        color="#666666",
        visible=False,
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

    # ── 过滤选项控件 ──────────────────────────────────────────
    state.exclude_cover_cb = ft.Checkbox(
        label="排除翻唱",
        value=True,
        disabled=False,
        fill_color=ft.Colors.INDIGO_400,
        check_color=ft.Colors.WHITE,
    )
    state.exclude_live_cb = ft.Checkbox(
        label="排除 Live",
        value=False,
        fill_color=ft.Colors.INDIGO_400,
        check_color=ft.Colors.WHITE,
    )
    state.exclude_inst_cb = ft.Checkbox(
        label="排除伴奏",
        value=True,
        fill_color=ft.Colors.INDIGO_400,
        check_color=ft.Colors.WHITE,
    )
    state.filter_hint = ft.Text(
        value="热榜模式下，翻唱过滤将自动关闭以保证榜单完整度",
        size=11,
        color="#888888",
        italic=True,
        visible=False,
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
                    [state.source_dropdown, state.mode_radio_group],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [state.playlist_input],
                    spacing=12,
                ),
                state.mode_hint,
                ft.Divider(height=1, color="#282828"),
                ft.Row(
                    [state.exclude_cover_cb, state.exclude_live_cb, state.exclude_inst_cb],
                    spacing=8,
                ),
                state.filter_hint,
            ],
            spacing=10,
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

    # ── 初始状态同步：歌手名为空 → 热榜模式 ──────────────────
    state.exclude_cover_cb.disabled = True
    state.exclude_cover_cb.value = False
    state.filter_hint.visible = True

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

    import re
    raw = state.artist_input.value.strip()
    if raw:
        target_list = [name.strip() for name in re.split(r'[,，\s]+', raw) if name.strip()]
    else:
        target_list = []

    page.run_task(
        _do_generate,
        page, state,
        target_list,
        _safe_int(state.count_input.value, 20),
        state.playlist_input.value.strip() or None,
        state.cookie_input.value.strip(),
        state.source_dropdown.value,
        state.mode_radio_group.value,
    )


async def _do_generate(
    page: ft.Page, state: AppState,
    artists: list[str], count: int, playlist_name: str | None, cookie: str, source: str,
    mode: str,
):
    # ── 校验 Cookie ────────────────────────────────────────────
    if not cookie:
        _log(state, "[错误] 请先在 Cookie 输入框中粘贴网易云 MUSIC_U Cookie")
        _log(state, "提示：打开网易云网页版 → F12 → 应用/Storage → Cookies → 复制 MUSIC_U 的值")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"数据源: {source} | 数量: {count}")
    if artists:
        _log(state, f"目标歌手: {' / '.join(artists)} (共 {len(artists)} 位)")
    else:
        _log(state, "模式: 全网热歌榜")

    # ── 第1步：多歌手聚合抓取 ──────────────────────────────────
    _log(state, "[1/5] 正在抓取歌曲列表...")
    all_songs: list[dict] = []
    artists_to_crawl = artists if artists else [""]

    for target_artist in artists_to_crawl:
        display_name = target_artist if target_artist else "全网热歌榜"
        _log(state, f"  ▶ 正在抓取 [{display_name}] 的歌曲...")
        try:
            songs = await crawler.crawl(source, target_artist, count)
        except Exception as e:
            _log(state, f"  ⚠ [{display_name}] 抓取失败: {e}")
            continue

        if not songs:
            _log(state, f"  ⚠ [{display_name}] 未抓取到歌曲")
            continue

        exclude_cover = state.exclude_cover_cb.value
        exclude_live = state.exclude_live_cb.value
        exclude_inst = state.exclude_inst_cb.value

        filtered = []
        for s in songs:
            if crawler.filter_song(
                s["song"], s["artist"], target_artist if target_artist else "",
                exclude_cover, exclude_live, exclude_inst,
            ):
                filtered.append(s)

        dropped = len(songs) - len(filtered)
        if dropped > 0:
            _log(state, f"  ⚠ 过滤掉 {dropped} 首（翻唱/Live/伴奏）")

        if filtered:
            _log(state, f"  ✓ [{display_name}] 成功获取 {len(filtered)} 首")
            all_songs.extend(filtered)

    if not all_songs:
        _log(state, "[错误] 未抓取到任何歌曲，请检查歌手名或数据源")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"聚合完成，共 {len(all_songs)} 首歌曲:")
    for s in all_songs:
        _log(state, f"  {s['song']} - {s['artist']}")

    # ── 第2步：搜索 track_id（高并发版） ──────────────────────
    _log(state, f"\n[2/5] 正在网易云搜索歌曲 ID（共 {len(all_songs)} 首）...")
    total_songs = len(all_songs)
    state.progress_text.value = f"正在搜索歌曲... (0/{total_songs})"
    state.progress_text.visible = True
    state.progress_bar.value = 0
    state.progress_bar.visible = True
    page.update()

    try:
        init_session_once(cookie)
    except CookieInvalidError as e:
        _log(state, f"\n[错误] Cookie 无效: {e}")
        _log(state, "请重新粘贴有效的 MUSIC_U Cookie 后重试")
        state.generate_button.disabled = False
        state.progress_text.visible = False
        state.progress_bar.visible = False
        page.update()
        return

    semaphore = asyncio.Semaphore(5)
    completed = [0]

    async def _search_one(song: dict) -> tuple[dict, int | None, str | None]:
        async with semaphore:
            keyword = f"{song['song']} {song['artist']}".strip()
            try:
                tid = await asyncio.to_thread(search_song_shared, keyword)
            except SearchFailedError as e:
                return (song, None, f"搜索请求异常: {e}")
            except Exception as e:
                return (song, None, f"搜索异常: {e}")
            else:
                return (song, tid, None)
            finally:
                done = completed[0] + 1
                completed[0] = done
                state.progress_text.value = (
                    f"正在搜索歌曲... ({done}/{total_songs})"
                )
                state.progress_bar.value = done / total_songs
                page.update()

    search_results = await asyncio.gather(
        *[_search_one(s) for s in all_songs]
    )

    track_ids = []
    match_count = 0
    for song, tid, error in search_results:
        if tid is not None:
            track_ids.append(tid)
            match_count += 1

    _log(state, f"  搜索完成: {match_count} 首匹配成功, "
                f"{total_songs - match_count} 首未找到")

    if not track_ids:
        _log(state, "[错误] 未匹配到任何歌曲，无法创建歌单")
        state.generate_button.disabled = False
        page.update()
        return

    _log(state, f"成功匹配 {len(track_ids)}/{len(all_songs)} 首")

    # ── 分支：新建歌单 vs 追加到已有 ─────────────────────────
    if mode == "append":
        # ── 追加模式：查重后增量追加 ──────────────────────────
        try:
            raw_pid = playlist_name.strip() if playlist_name else ""
            target_pid = int(raw_pid)
        except (ValueError, AttributeError):
            _log(state, "[错误] 请填写有效的歌单 ID（纯数字）")
            _log(state, "提示：右键网易云歌单分享链接可查看 ID")
            state.generate_button.disabled = False
            page.update()
            return

        _log(state, f"\n[3/5] 正在查询目标歌单 (ID: {target_pid}) 现有曲目...")
        try:
            existing_ids = await asyncio.to_thread(
                get_playlist_track_ids, target_pid, cookie
            )
        except CookieInvalidError as e:
            _log(state, f"\n[错误] Cookie 无效: {e}")
            _log(state, "请重新粘贴有效的 MUSIC_U Cookie 后重试")
            state.generate_button.disabled = False
            page.update()
            return
        except PlaylistOperationError as e:
            _log(state, f"[错误] 查询歌单失败: {e}")
            state.generate_button.disabled = False
            page.update()
            return
        except Exception as e:
            _log(state, f"[错误] 查询歌单异常: {e}")
            state.generate_button.disabled = False
            page.update()
            return

        new_ids = [tid for tid in track_ids if tid not in existing_ids]
        skip_count = len(track_ids) - len(new_ids)
        _log(
            state,
            f"[增量更新] 检测完毕：跳过 {skip_count} 首已有歌曲，"
            f"即将追加 {len(new_ids)} 首新歌",
        )

        if not new_ids:
            _log(state, "[增量更新] 所有歌曲均已存在，无需追加")
            _log(state, "=" * 40)
            _log(state, "✅ 歌单已是最新！")
            _log(state, "=" * 40)
            state.generate_button.disabled = False
            page.update()
            return

        _log(state, f"\n[4/5] 正在将 {len(new_ids)} 首新歌追加到歌单...")
        try:
            success = await asyncio.to_thread(
                add_songs_to_playlist, target_pid, new_ids, cookie
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
            _log(state, f"[错误] 添加歌曲异常: {e}")
            state.generate_button.disabled = False
            page.update()
            return

        _log(state, f"\n[5/5] 操作完成!")
        if success:
            _log(state, "=" * 40)
            _log(state, "✅ 增量更新成功！")
            _log(state, f"   歌单 ID: {target_pid}")
            _log(state, f"   本次追加: {len(new_ids)} 首")
            _log(state, f"   歌单总量: {len(existing_ids) + len(new_ids)} 首")
            _log(state, "=" * 40)
            state.progress_text.value = "🎉 歌单增量更新成功！"
            state.progress_bar.value = 1.0
            _save_cookie(cookie)
        else:
            _log(state, "⚠ 追加歌曲时遇到问题，请检查网易云歌单")
            state.progress_text.visible = False
            state.progress_bar.visible = False

        state.generate_button.disabled = False
        page.update()
        return

    # ── 新建模式 ──────────────────────────────────────────────
    if not playlist_name:
        if artists:
            artist_str = " + ".join(artists)
            name = f"[{artist_str}] 专属精选"
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

    _log(state, f"\n[5/5] 操作完成!")
    if success:
        _log(state, "=" * 40)
        _log(state, "✅ 歌单已成功生成！")
        _log(state, f"   歌单名称: {name}")
        _log(state, f"   歌曲数量: {len(track_ids)} 首")
        _log(state, "=" * 40)
        state.progress_text.value = "🎉 专属歌单创建成功！"
        state.progress_bar.value = 1.0
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
