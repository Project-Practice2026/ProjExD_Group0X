"""起動メニュー（MenuScene / IpInputScene / is_valid_ipv4）のテスト。

描画には依存せず、選択ロジックと IP 入力・検証ロジックのみを検証する。
"""

from __future__ import annotations

import os
from itertools import pairwise

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from core.menu import MENU_OPTIONS, IpInputScene, MenuScene, is_valid_ipv4

pg.init()


# ===== MenuScene =====


def test_menu_first_option_is_solo() -> None:
    """初期選択は先頭（solo）。"""
    menu = MenuScene()
    assert menu.get_index() == 0
    assert menu.get_selected_value() == "solo"


def test_menu_cursor_cycles_within_options() -> None:
    """カーソルは端で循環する。"""
    menu = MenuScene()
    menu.move_cursor(-1)
    assert menu.get_index() == len(MENU_OPTIONS) - 1  # 上端 → 末尾へ循環
    menu.move_cursor(1)
    assert menu.get_index() == 0  # 末尾 → 先頭へ循環


def test_menu_down_then_enter_returns_selected_value() -> None:
    """↓で移動し Enter で選択値を返す。"""
    menu = MenuScene()
    assert menu.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_DOWN)) is None
    assert menu.get_selected_value() == "host"
    assert menu.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN)) == "host"


def test_menu_options_include_tutorial() -> None:
    """Tutorial option is included in the menu."""
    values = [value for value, _label in MENU_OPTIONS]
    assert "tutorial" in values


def test_menu_tutorial_option_can_be_selected() -> None:
    """Tutorial option can be selected with the existing menu logic."""
    menu = MenuScene()
    values = [value for value, _label in MENU_OPTIONS]
    tutorial_index = values.index("tutorial")
    for _ in range(tutorial_index):
        menu.move_cursor(1)
    assert menu.get_selected_value() == "tutorial"
    assert menu.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN)) == "tutorial"


def test_menu_escape_and_quit_return_quit() -> None:
    """Esc / QUIT は "quit" を返す。"""
    assert MenuScene().handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE)) == "quit"
    assert MenuScene().handle_event(pg.event.Event(pg.QUIT)) == "quit"


def test_menu_mouse_hover_and_click_selects_option() -> None:
    """ホバーで選択が動き、クリックでその項目を決定する。"""
    menu = MenuScene()
    target = 2  # client
    center = menu._option_rects()[target].center
    menu.handle_event(pg.event.Event(pg.MOUSEMOTION, pos=center))
    assert menu.get_index() == target
    result = menu.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=center))
    assert result == "client"


def test_menu_click_outside_options_does_nothing() -> None:
    """選択肢外のクリックでは決定しない。"""
    menu = MenuScene()
    assert menu.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(0, 0))) is None


def test_menu_click_off_glyph_but_in_row_selects_option() -> None:
    """文字の真上でなく行帯の端をクリックしても決定できる（Issue #146）。"""
    menu = MenuScene()
    target = 1  # host
    rect = menu._option_rects()[target]
    # 文字グリフ外（行帯の左端付近・上端付近）でも選べることを確認する。
    edge_pos = (rect.left + 2, rect.top + 2)
    menu.handle_event(pg.event.Event(pg.MOUSEMOTION, pos=edge_pos))
    assert menu.get_index() == target  # ホバーも行全体で反応する
    assert menu.handle_event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=edge_pos)) == "host"


def test_menu_option_rects_cover_full_row_without_gaps() -> None:
    """各当たり判定は行（OPTION_GAP）いっぱいで、隣接帯に隙間がない。"""
    rects = MenuScene()._option_rects()
    assert all(rect.height == MenuScene.OPTION_GAP for rect in rects)
    # 隣り合う帯は下端と次の上端が一致し、押しても無反応な隙間が生じない。
    assert all(lower.top == upper.bottom for upper, lower in pairwise(rects))


# ===== is_valid_ipv4 =====


def test_is_valid_ipv4_accepts_normal() -> None:
    """正常な IPv4 を受理する。"""
    for ip in ("127.0.0.1", "0.0.0.0", "255.255.255.255", "192.168.1.10"):
        assert is_valid_ipv4(ip), ip


def test_is_valid_ipv4_rejects_invalid() -> None:
    """範囲外・形式不正・先頭ゼロを拒否する。"""
    for ip in ("256.0.0.1", "1.2.3", "1.2.3.4.5", "1.2.3.a", "", "192.168.01.1", "010.0.0.1"):
        assert not is_valid_ipv4(ip), ip


# ===== IpInputScene =====


def test_ip_input_filters_characters() -> None:
    """数字と '.' のみ受理する。"""
    scene = IpInputScene(initial_ip="")
    for ch in "12a.3!4":
        scene.insert_char(ch)
    assert scene.get_text() == "12.34"


def test_ip_input_respects_max_length() -> None:
    """最大長を超える入力は無視する。"""
    scene = IpInputScene(initial_ip="1" * IpInputScene.MAX_LENGTH)
    scene.insert_char("9")
    assert len(scene.get_text()) == IpInputScene.MAX_LENGTH


def test_ip_input_backspace_deletes_last_char() -> None:
    """Backspace は末尾を 1 文字削除する。"""
    scene = IpInputScene(initial_ip="12.3")
    scene.backspace()
    assert scene.get_text() == "12."


def test_ip_input_confirm_valid_and_invalid() -> None:
    """確定は妥当時に IP を返し、無効時は None＋エラー設定。"""
    assert IpInputScene(initial_ip="10.0.0.5").try_confirm() == "10.0.0.5"
    invalid = IpInputScene(initial_ip="999.1.1.1")
    assert invalid.try_confirm() is None
    assert invalid.get_error() != ""


def test_ip_input_handle_event_flow() -> None:
    """文字入力 → Backspace → 無効確定（継続）→ 有効確定 の流れ。"""
    scene = IpInputScene(initial_ip="")
    for ch in "9.9.9.9":
        key = pg.K_PERIOD if ch == "." else pg.K_9
        done, ip = scene.handle_event(pg.event.Event(pg.KEYDOWN, key=key, unicode=ch))
        assert done is False
        assert ip is None
    assert scene.get_text() == "9.9.9.9"

    scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_BACKSPACE))
    assert scene.get_text() == "9.9.9."

    done, ip = scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    assert done is False  # 無効なので確定しない
    assert ip is None
    assert scene.get_error() != ""

    scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_9, unicode="9"))
    done, ip = scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN))
    assert done is True
    assert ip == "9.9.9.9"


def test_ip_input_escape_and_quit_cancel() -> None:
    """Esc / QUIT は取消（done=True, ip=None）。"""
    cancelled_esc = IpInputScene(initial_ip="1.2.3.4").handle_event(
        pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE)
    )
    assert cancelled_esc == (True, None)
    cancelled_quit = IpInputScene(initial_ip="1.2.3.4").handle_event(pg.event.Event(pg.QUIT))
    assert cancelled_quit == (True, None)


if __name__ == "__main__":
    test_menu_first_option_is_solo()
    test_menu_cursor_cycles_within_options()
    test_menu_down_then_enter_returns_selected_value()
    test_menu_options_include_tutorial()
    test_menu_tutorial_option_can_be_selected()
    test_menu_escape_and_quit_return_quit()
    test_menu_mouse_hover_and_click_selects_option()
    test_menu_click_outside_options_does_nothing()
    test_menu_click_off_glyph_but_in_row_selects_option()
    test_menu_option_rects_cover_full_row_without_gaps()
    test_is_valid_ipv4_accepts_normal()
    test_is_valid_ipv4_rejects_invalid()
    test_ip_input_filters_characters()
    test_ip_input_respects_max_length()
    test_ip_input_backspace_deletes_last_char()
    test_ip_input_confirm_valid_and_invalid()
    test_ip_input_handle_event_flow()
    test_ip_input_escape_and_quit_cancel()
    print("All menu tests passed.")
