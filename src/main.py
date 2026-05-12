"""
阶段三：Flet GUI 主界面
整合爬虫 + 网易云 API，提供完整的桌面端体验
"""

import asyncio
import json
from pathlib import Path

import flet as ft

import crawler
from netease import (
    search_song_shared,
    create_playlist,
    add_songs_to_playlist,
    get_playlist_track_ids,
    init_session_once,
    get_user_info,
    get_user_created_playlists,
    fetch_image_as_base64_async,
    PLACEHOLDER_BASE64,
    CookieInvalidError,
    SearchFailedError,
    PlaylistOperationError,
)


class AppState:
    """集中管理界面控件引用和共享状态"""

    def __init__(self):
        self.artist_input: ft.TextField | None = None
        self.count_input: ft.TextField | None = None
        self.source_dropdown: ft.Dropdown | None = None
        self.cookie_input: ft.TextField | None = None

        self.fetch_button: ft.FilledButton | None = None
        self.confirm_button: ft.FilledButton | None = None

        # 搜索维度切换
        self.search_type_radio: ft.RadioGroup | None = None

        # 过滤选项
        self.exclude_cover_cb: ft.Checkbox | None = None
        self.exclude_live_cb: ft.Checkbox | None = None
        self.exclude_inst_cb: ft.Checkbox | None = None
        self.filter_hint: ft.Text | None = None

        # 日志与进度
        self.log_text: ft.Text | None = None
        self.progress_bar: ft.ProgressBar | None = None
        self.progress_text: ft.Text | None = None

        # 预览列表
        self.preview_listview: ft.ListView | None = None
        self.select_all_cb: ft.Checkbox | None = None
        self.preview_container: ft.Container | None = None
        self._preview_data: list[dict] = []

        # 左侧面板状态
        self.selected_playlist_id: int | None = None
        self.user_info_container: ft.Container | None = None
        self.playlist_listview: ft.ListView | None = None
        self.validate_button: ft.FilledTonalButton | None = None
        self._playlist_data: list[dict] = []
        self._cover_widgets: dict[int, ft.Container] = {}
        self._cover_cache: dict[int, str] = {}
        self._avatar_cache: str = ""


def main(page: ft.Page):
    page.title = "专辑 - 你的专属歌单生成器"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1100
    page.window.height = 780
    page.window.resizable = False
    page.padding = 0
    page.bgcolor = "#000000"

    state = AppState()

    # ─── 工具函数 ──────────────────────────────────────────────
    def _log(msg: str):
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
        config_path = Path(__file__).parent.parent / "config.json"
        try:
            config_path.write_text(
                json.dumps({"cookie": cookie}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[config] 保存 Cookie 失败: {e}")

    # ─── 左侧面板交互 ──────────────────────────────────────────
    def _on_artist_changed(e):
        has_artist = bool(state.artist_input.value.strip())
        state.exclude_cover_cb.disabled = not has_artist
        if has_artist:
            state.exclude_cover_cb.value = True
            state.filter_hint.visible = False
        else:
            state.exclude_cover_cb.value = False
            state.filter_hint.visible = True
        page.update()

    def _on_playlist_click(pid: int):
        state.selected_playlist_id = pid
        _rebuild_playlist_list()

    def _rebuild_playlist_list():
        state.playlist_listview.controls.clear()
        state._cover_widgets.clear()
        for pl in state._playlist_data:
            pid = pl["id"]
            is_selected = pid == state.selected_playlist_id

            cached_b64 = state._cover_cache.get(pid)
            if cached_b64:
                cover_content = ft.Image(
                    src=cached_b64,
                    width=40,
                    height=40,
                    fit="cover",
                )
                cover_widget = ft.Container(
                    content=cover_content,
                    width=40,
                    height=40,
                    border_radius=6,
                )
            else:
                cover_widget = ft.Container(
                    content=ft.Icon(ft.Icons.LIBRARY_MUSIC, size=22, color="#444444"),
                    width=40,
                    height=40,
                    border_radius=6,
                    bgcolor="#1A1A1A",
                )
            state._cover_widgets[pid] = cover_widget

            card = ft.Container(
                content=ft.Row([
                    cover_widget,
                    ft.Column([
                        ft.Text(
                            pl["name"],
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            width=180,
                        ),
                        ft.Text(
                            f"{pl['trackCount']} 首",
                            size=11,
                            color="#888888",
                        ),
                    ], spacing=2, expand=True),
                ], spacing=10),
                bgcolor="#2A2A2A" if is_selected else "transparent",
                border=ft.Border.all(
                    1.5 if is_selected else 0,
                    ft.Colors.INDIGO_400 if is_selected else "transparent",
                ),
                border_radius=10,
                padding=ft.Padding.all(10),
                ink=True,
                on_click=lambda _, p=pid: _on_playlist_click(p),
                animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            )
            state.playlist_listview.controls.append(card)
        page.update()

    async def _update_left_panel():
        cookie = state.cookie_input.value.strip()
        if not cookie:
            state.user_info_container.content = ft.Text(
                "请在右侧输入 Cookie",
                size=13,
                color="#888888",
                italic=True,
            )
            state.playlist_listview.controls.clear()
            state._playlist_data = []
            state.selected_playlist_id = None
            page.update()
            return

        try:
            user_info = await asyncio.to_thread(get_user_info, cookie)
            uid = user_info["uid"]
            playlists = await asyncio.to_thread(get_user_created_playlists, uid, cookie)
        except CookieInvalidError as e:
            state.user_info_container.content = ft.Text(
                f"Cookie 无效: {e}",
                size=13,
                color=ft.Colors.RED_400,
            )
            state.playlist_listview.controls.clear()
            state._playlist_data = []
            state.selected_playlist_id = None
            page.update()
            return
        except Exception as e:
            state.user_info_container.content = ft.Text(
                f"加载失败: {e}",
                size=13,
                color=ft.Colors.RED_400,
            )
            state.playlist_listview.controls.clear()
            state._playlist_data = []
            state.selected_playlist_id = None
            page.update()
            return

        # ── 第1阶段：秒开文字 + 图标占位 ─────────────────────
        nickname = user_info["nickname"]
        avatar_url = user_info["avatarUrl"]

        if state._avatar_cache:
            avatar_widget = ft.CircleAvatar(
                foreground_image_src=state._avatar_cache,
                width=42,
                height=42,
            )
        elif nickname:
            avatar_widget = ft.CircleAvatar(
                content=ft.Text(
                    nickname[0],
                    size=18,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.WHITE,
                ),
                bgcolor="#333333",
                width=42,
                height=42,
            )
        else:
            avatar_widget = ft.CircleAvatar(
                bgcolor="#333333",
                width=42,
                height=42,
            )

        state.user_info_container.content = ft.Row([
            avatar_widget,
            ft.Column([
                ft.Text(
                    nickname,
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.WHITE,
                ),
                ft.Text(f"UID: {uid}", size=11, color="#888888"),
            ], spacing=2),
        ], spacing=12)

        state._playlist_data = playlists
        state.selected_playlist_id = None
        state._cover_cache.clear()
        state._avatar_cache = ""
        _rebuild_playlist_list()
        _log(f"已加载 {len(playlists)} 个自建歌单")
        page.update()

        # ── 第2阶段：后台无感补图 ─────────────────────────────
        if playlists or avatar_url:
            asyncio.create_task(_hydrate_images(avatar_url, uid))

    async def _hydrate_images(avatar_url: str, uid: int):
        """后台补图任务：全量并发下载，按歌单ID缓存结果，逐个替换活控件"""
        cover_urls: list[tuple[int, str]] = [
            (pl["id"], pl["coverImgUrl"])
            for pl in state._playlist_data
            if pl.get("coverImgUrl")
        ]

        tasks = [fetch_image_as_base64_async(url) for _, url in cover_urls]
        if avatar_url:
            tasks.append(fetch_image_as_base64_async(avatar_url))

        if not tasks:
            return

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            if i < len(cover_urls):
                pid, _ = cover_urls[i]
                if result and result != PLACEHOLDER_BASE64:
                    state._cover_cache[pid] = result
                    cw = state._cover_widgets.get(pid)
                    if cw is not None:
                        try:
                            cw.bgcolor = None
                            cw.content = ft.Image(
                                src=result, width=40, height=40, fit="cover",
                            )
                            cw.update()
                        except Exception:
                            pass
            elif avatar_url:
                if result and result != PLACEHOLDER_BASE64:
                    state._avatar_cache = result
                    try:
                        existing = state.user_info_container.content
                        if hasattr(existing, "controls") and len(existing.controls) > 0:
                            existing.controls[0] = ft.CircleAvatar(
                                foreground_image_src=result,
                                width=42,
                                height=42,
                            )
                            state.user_info_container.update()
                    except Exception:
                        pass

    async def _on_validate_click(e):
        cookie = state.cookie_input.value.strip()
        if not cookie:
            _log("提示: 请先粘贴网易云 MUSIC_U Cookie")
            return
        state.validate_button.disabled = True
        state.validate_button.text = "验证中..."
        page.update()
        _save_cookie(cookie)
        await _update_left_panel()
        state.validate_button.disabled = False
        state.validate_button.text = "验证并加载"
        page.update()

    async def _on_create_playlist_click(e):
        name_input = ft.TextField(
            label="歌单名称",
            hint_text="输入新歌单的名称",
            autofocus=True,
        )
        dialog = ft.AlertDialog(
            title=ft.Text("新建歌单", size=18, weight=ft.FontWeight.W_700),
            content=name_input,
            actions=[
                ft.TextButton("取消", on_click=lambda _: _close()),
                ft.FilledButton("创建", on_click=lambda _: _confirm()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

        def _close():
            dialog.open = False
            page.update()

        async def _confirm():
            name = name_input.value.strip()
            if not name:
                return
            cookie = state.cookie_input.value.strip()
            _close()
            _log(f"正在创建歌单: {name}")
            try:
                pid = await asyncio.to_thread(create_playlist, name, cookie)
                if pid:
                    _log(f"歌单创建成功! (ID: {pid})")
                    await _update_left_panel()
                else:
                    _log("创建歌单失败")
            except CookieInvalidError as ex:
                _log(f"Cookie 无效: {ex}")
            except PlaylistOperationError as ex:
                _log(f"创建失败: {ex}")
            except Exception as ex:
                _log(f"创建异常: {ex}")

    # ─── 预览列表渲染 ─────────────────────────────────────────
    def _rebuild_preview_list():
        state.preview_listview.controls.clear()
        for s in state._preview_data:
            row = ft.Row([
                ft.Checkbox(
                    value=s.get("checked", True),
                    on_change=lambda e, d=s: d.update({"checked": e.control.value}),
                    fill_color=ft.Colors.INDIGO_400,
                    check_color=ft.Colors.WHITE,
                ),
                ft.Text(s["song"], size=13, color=ft.Colors.WHITE, expand=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(s["artist"], size=12, color="#AAAAAA", width=140,
                        overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=8)
            state.preview_listview.controls.append(row)
        state.confirm_button.visible = bool(state._preview_data)
        state.preview_container.visible = bool(state._preview_data)
        page.update()

    def _on_select_all(e):
        checked = state.select_all_cb.value
        for s in state._preview_data:
            s["checked"] = checked
        _rebuild_preview_list()

    # ─── 执行抓取并预览 ──────────────────────────────────────
    def _start_fetch():
        if state.selected_playlist_id is None:
            _log("提示: 请先在左侧选择要同步的网易云歌单")
            return

        state.fetch_button.disabled = True
        page.update()

        import re
        raw = state.artist_input.value.strip()
        search_type = state.search_type_radio.value
        target_list = [name.strip() for name in re.split(r'[,，\s]+', raw) if name.strip()] if raw else []

        page.run_task(
            _do_fetch,
            target_list,
            _safe_int(state.count_input.value, 20),
            state.cookie_input.value.strip(),
            state.source_dropdown.value,
            search_type,
        )

    async def _do_fetch(
        artists: list[str], count: int, cookie: str, source: str, search_type: str,
    ):
        if not cookie:
            _log("错误: 请先在 Cookie 输入框中粘贴网易云 MUSIC_U Cookie")
            state.fetch_button.disabled = False
            page.update()
            return

        _log(f"数据源: {source} | 数量: {count}")
        if artists:
            _log(f"目标: {' / '.join(artists)} (共 {len(artists)} 个关键词)")
        else:
            _log("模式: 全网热歌榜")

        # ── 清空旧预览 ─────────────────────────────────────────
        state._preview_data = []
        state.preview_listview.controls.clear()
        state.confirm_button.visible = False
        page.update()

        # ── 第1步：多关键词聚合抓取 ──────────────────────────
        _log("[1/3] 正在抓取歌曲列表...")
        state.progress_text.value = "正在抓取歌曲..."
        state.progress_text.visible = True
        state.progress_bar.value = None
        state.progress_bar.visible = True
        page.update()

        all_songs: list[dict] = []
        targets_to_crawl = artists if artists else [""]

        for target in targets_to_crawl:
            display_name = target if target else "全网热歌榜"
            _log(f"  ▶ 正在抓取 [{display_name}] 的歌曲...")
            try:
                songs = await crawler.crawl(source, target, count, search_type)
            except Exception as e:
                _log(f"  ⚠ [{display_name}] 抓取失败: {e}")
                continue

            if not songs:
                _log(f"  ⚠ [{display_name}] 未抓取到歌曲")
                continue

            exclude_cover = state.exclude_cover_cb.value
            exclude_live = state.exclude_live_cb.value
            exclude_inst = state.exclude_inst_cb.value

            filtered = []
            for s in songs:
                if crawler.filter_song(
                    s["song"], s["artist"], target if target else "",
                    exclude_cover, exclude_live, exclude_inst,
                ):
                    filtered.append(s)

            dropped = len(songs) - len(filtered)
            if dropped > 0:
                _log(f"  ⚠ 过滤掉 {dropped} 首（翻唱/Live/伴奏）")

            if filtered:
                _log(f"  ✓ [{display_name}] 成功获取 {len(filtered)} 首")
                all_songs.extend(filtered)

        if not all_songs:
            _log("错误: 未抓取到任何歌曲，请检查关键词或数据源")
            state.fetch_button.disabled = False
            state.progress_text.visible = False
            state.progress_bar.visible = False
            page.update()
            return

        _log(f"聚合完成，共 {len(all_songs)} 首歌曲:")
        for s in all_songs:
            _log(f"  {s['song']} - {s['artist']}")

        # ── 联合主键去重 ───────────────────────────────────────
        seen_signatures: set[str] = set()
        unique_songs: list[dict] = []
        for s in all_songs:
            sig = f"{s['song'].strip()}||{s['artist'].strip()}"
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                unique_songs.append(s)
        dedup_count = len(all_songs) - len(unique_songs)
        if dedup_count > 0:
            _log(f"  去重: 移除 {dedup_count} 首重复歌曲")
        all_songs = unique_songs

        # ── 第2步：填充预览列表 ──────────────────────────────
        _log(f"\n[2/3] 正在搜索网易云曲库匹配...")
        total_songs = len(all_songs)
        state.progress_text.value = f"正在搜索歌曲... (0/{total_songs})"
        state.progress_bar.value = 0
        page.update()

        try:
            init_session_once(cookie)
        except CookieInvalidError as e:
            _log(f"\n错误: Cookie 无效: {e}")
            state.fetch_button.disabled = False
            state.progress_text.visible = False
            state.progress_bar.visible = False
            page.update()
            return

        semaphore = asyncio.Semaphore(5)
        completed = [0]

        async def _search_one(song: dict) -> dict:
            async with semaphore:
                keyword = f"{song['song']} {song['artist']}".strip()
                tid = None
                try:
                    tid = await asyncio.to_thread(search_song_shared, keyword)
                except Exception:
                    pass
                finally:
                    done = completed[0] + 1
                    completed[0] = done
                    state.progress_text.value = f"正在搜索歌曲... ({done}/{total_songs})"
                    state.progress_bar.value = done / total_songs
                    page.update()
            return {**song, "track_id": tid, "checked": True}

        search_results = await asyncio.gather(*[_search_one(s) for s in all_songs])
        matched = [s for s in search_results if s["track_id"] is not None]
        _log(f"  搜索完成: {len(matched)} 首匹配成功, {len(search_results) - len(matched)} 首未找到")

        # ── 第3步：展示预览 ──────────────────────────────────
        _log(f"\n[3/3] 预览歌曲列表 ({len(matched)} 首可导入)")

        state._preview_data = matched
        state.select_all_cb.value = True
        _rebuild_preview_list()

        state.progress_text.value = "请在预览列表中勾选需要导入的歌曲"
        state.progress_bar.visible = False
        state.fetch_button.disabled = False
        page.update()

    # ─── 确认导入 ──────────────────────────────────────────────
    def _start_import():
        if state.selected_playlist_id is None:
            _log("提示: 请先在左侧选择要同步的网易云歌单")
            return

        checked = [s for s in state._preview_data if s.get("checked")]
        if not checked:
            _log("提示: 请至少勾选一首歌曲后再导入")
            return

        state.confirm_button.disabled = True
        state.fetch_button.disabled = True
        page.update()

        page.run_task(
            _do_import,
            checked,
            state.cookie_input.value.strip(),
        )

    async def _do_import(
        checked_songs: list[dict], cookie: str,
    ):
        playlist_id = state.selected_playlist_id
        track_ids = [s["track_id"] for s in checked_songs if s["track_id"] is not None]

        if not track_ids:
            _log("错误: 勾选的歌曲均无有效 track_id")
            state.confirm_button.disabled = False
            state.fetch_button.disabled = False
            page.update()
            return

        # ── 查重 ─────────────────────────────────────────────
        _log(f"\n正在查询目标歌单 (ID: {playlist_id}) 现有曲目...")
        try:
            existing_ids = await asyncio.to_thread(
                get_playlist_track_ids, playlist_id, cookie
            )
        except CookieInvalidError as e:
            _log(f"\n错误: Cookie 无效: {e}")
            state.confirm_button.disabled = False
            state.fetch_button.disabled = False
            page.update()
            return
        except Exception as e:
            _log(f"错误: 查询歌单失败: {e}")
            state.confirm_button.disabled = False
            state.fetch_button.disabled = False
            page.update()
            return

        new_ids = [tid for tid in track_ids if tid not in existing_ids]
        skip_count = len(track_ids) - len(new_ids)
        _log(
            f"[增量更新] 检测完毕: 跳过 {skip_count} 首已有歌曲, "
            f"即将追加 {len(new_ids)} 首新歌"
        )

        if not new_ids:
            _log("所有歌曲均已存在，无需追加")
            _log("=" * 40)
            _log("✅ 歌单已是最新！")
            _log("=" * 40)
            state.confirm_button.disabled = False
            state.fetch_button.disabled = False
            page.update()
            return

        # ── 追加 ─────────────────────────────────────────────
        _log(f"正在将 {len(new_ids)} 首新歌追加到歌单...")
        try:
            success = await asyncio.to_thread(
                add_songs_to_playlist, playlist_id, new_ids, cookie
            )
        except Exception as e:
            _log(f"错误: 添加歌曲失败: {e}")
            state.confirm_button.disabled = False
            state.fetch_button.disabled = False
            page.update()
            return

        if success:
            _log("=" * 40)
            _log("✅ 导入成功！")
            _log(f"   歌单 ID: {playlist_id}")
            _log(f"   本次导入: {len(new_ids)} 首")
            _log(f"   歌单总量: {len(existing_ids) + len(new_ids)} 首")
            _log("=" * 40)
            _save_cookie(cookie)
        else:
            _log("⚠ 导入时遇到问题，请检查网易云歌单")

        state.confirm_button.disabled = False
        state.fetch_button.disabled = False
        page.update()

    # ════════════════════════════════════════════════════════════
    # UI 构建
    # ════════════════════════════════════════════════════════════

    # ─── 左侧面板控件 ──────────────────────────────────────────
    state.user_info_container = ft.Container(
        content=ft.Text(
            "请在右侧输入 Cookie",
            size=13,
            color="#888888",
            italic=True,
        ),
        padding=ft.Padding.all(10),
    )

    state.playlist_listview = ft.ListView(spacing=6, padding=ft.Padding.only(top=4))

    state.validate_button = ft.FilledTonalButton(
        "验证并加载",
        icon=ft.Icons.VERIFIED,
        on_click=lambda e: page.run_task(_on_validate_click, e),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            bgcolor="#2A2A2A",
            color=ft.Colors.INDIGO_200,
        ),
    )

    # ─── 左侧面板 ──────────────────────────────────────────────
    left_panel = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("专辑 Album", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
                    ft.Text("歌单管理", size=11, color="#666666"),
                ]),
                padding=ft.Padding.only(left=15, top=20, bottom=10),
            ),
            ft.Divider(height=1, color="#1A1A1A"),
            ft.Container(
                content=state.user_info_container,
                padding=ft.Padding.all(10),
            ),
            ft.Divider(height=1, color="#1A1A1A"),
            ft.Container(
                content=ft.Row([
                    ft.Text("我的歌单", size=13, weight=ft.FontWeight.W_700, color="#AAAAAA"),
                    ft.IconButton(
                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                        icon_size=20,
                        icon_color="#888888",
                        tooltip="新建歌单",
                        on_click=lambda e: page.run_task(_on_create_playlist_click, e),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding.only(left=15, right=5, top=8, bottom=4),
            ),
            ft.Container(
                content=state.playlist_listview,
                expand=True,
                padding=ft.Padding.symmetric(horizontal=10),
            ),
        ]),
        width=360,
        bgcolor="#0A0A0A",
        border=ft.Border.all(1, "#1A1A1A"),
    )

    # ─── 右侧面板控件 ──────────────────────────────────────────
    state.cookie_input = ft.TextField(
        label="网易云 Cookie",
        hint_text="粘贴 MUSIC_U Cookie 值",
        multiline=True,
        min_lines=2,
        max_lines=2,
        prefix_icon=ft.Icons.LOCK,
        password=True,
        border=ft.InputBorder.NONE,
        bgcolor="#1E1E1E",
        border_radius=8,
        content_padding=15,
        expand=True,
    )

    cookie_row = ft.Row(
        [state.cookie_input, state.validate_button],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    state.search_type_radio = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="artist", label="搜索歌手名"),
            ft.Radio(value="song", label="直接搜索歌曲名"),
        ], spacing=4),
        value="artist",
    )

    state.artist_input = ft.TextField(
        label="歌手名",
        hint_text="多个请用逗号或空格分隔，留空则抓取热榜",
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

    config_card = ft.Container(
        content=ft.Column([
            state.search_type_radio,
            ft.Divider(height=1, color="#282828"),
            ft.Row([state.artist_input, state.count_input, state.source_dropdown], spacing=12),
            ft.Divider(height=1, color="#282828"),
            ft.Row(
                [state.exclude_cover_cb, state.exclude_live_cb, state.exclude_inst_cb],
                spacing=8,
            ),
            state.filter_hint,
        ], spacing=10),
        bgcolor="#121212",
        border_radius=16,
        padding=25,
        border=ft.Border.all(1, "#282828"),
    )

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

    state.log_text = ft.Text(
        "",
        size=12,
        font_family="consolas",
        selectable=True,
    )
    log_container = ft.Container(
        content=ft.Column([state.log_text], scroll=ft.ScrollMode.ALWAYS, height=200),
        height=200,
        bgcolor="#0A0A0A",
        border_radius=12,
        padding=15,
        border=ft.Border.all(1, "#1A1A1A"),
    )

    state.select_all_cb = ft.Checkbox(
        label="全选",
        value=True,
        on_change=_on_select_all,
        fill_color=ft.Colors.INDIGO_400,
        check_color=ft.Colors.WHITE,
    )

    state.preview_listview = ft.ListView(spacing=4, height=180)

    state.preview_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("待导入歌曲", size=13, weight=ft.FontWeight.W_700, color="#AAAAAA"),
                state.select_all_cb,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            state.preview_listview,
        ], spacing=6),
        bgcolor="#121212",
        border_radius=12,
        padding=15,
        border=ft.Border.all(1, "#282828"),
        visible=False,
    )

    state.fetch_button = ft.FilledButton(
        "执行抓取并预览",
        icon=ft.Icons.SEARCH,
        disabled=False,
        on_click=lambda _: _start_fetch(),
        height=48,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=25),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        ),
    )

    state.confirm_button = ft.FilledButton(
        "确认导入",
        icon=ft.Icons.DOWNLOAD_DONE,
        disabled=False,
        visible=False,
        on_click=lambda _: _start_import(),
        height=48,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=25),
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
        ),
    )

    # ─── 右侧面板 ──────────────────────────────────────────────
    right_col = ft.Column([
        ft.Text("网易云同步", size=20, weight=ft.FontWeight.W_800, color=ft.Colors.WHITE),
        ft.Text("跨平台歌单自动化同步工具", size=13, color="#888888"),
        cookie_row,
        config_card,
        state.progress_text,
        state.progress_bar,
        state.preview_container,
        ft.Row([state.fetch_button, state.confirm_button], spacing=12),
        log_container,
    ], spacing=16, scroll=ft.ScrollMode.AUTO)

    right_panel = ft.Container(
        content=right_col,
        expand=True,
        padding=ft.Padding.all(25),
        bgcolor="#000000",
    )

    # ── 初始状态同步 ──────────────────────────────────────────
    state.exclude_cover_cb.disabled = True
    state.exclude_cover_cb.value = False
    state.filter_hint.visible = True

    # ── 主布局 ────────────────────────────────────────────────
    page.add(
        ft.Row(
            [left_panel, right_panel],
            spacing=0,
            expand=True,
        )
    )

    # ─── 启动时读取已保存的 Cookie ──────────────────────────
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


if __name__ == "__main__":
    ft.run(main=main)
