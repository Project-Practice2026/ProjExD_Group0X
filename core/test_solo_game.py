"""SoloGame 単体（合成層）のテスト。"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from core.constants import (
    BOSS_WAVE_CLEAR_FORTRESS_HEAL,
    BOSS_WAVE_CLEAR_GOLD_BONUS,
    BOSS_WAVE_MODULO,
    WAVE_CLEAR_FORTRESS_HEAL,
    WAVE_CLEAR_GOLD_BONUS,
)
from core.solo_game import SoloGame


class _FakeTutorialOverlay:
    """保存連携テスト用のチュートリアルオーバーレイ。"""

    def __init__(self, skip_next_time: bool, visible: bool = True) -> None:
        self._visible: bool = visible
        self._skip_next_time: bool = skip_next_time
        self._show_count: int = 0

    def is_visible(self) -> bool:
        """表示中なら True を返す。"""
        return self._visible

    def show(self) -> None:
        """オーバーレイを表示する。"""
        self._visible = True
        self._show_count += 1

    def get_show_count(self) -> int:
        """show() が呼ばれた回数を返す。"""
        return self._show_count

    def handle_event(self, event: pg.event.Event) -> bool:
        """何らかの入力を受けたら閉じる。"""
        if event.type in {pg.KEYDOWN, pg.MOUSEBUTTONDOWN}:
            self._visible = False
            return True
        return False

    def get_skip_next_time(self) -> bool:
        """次回から表示しない設定を返す。"""
        return self._skip_next_time

    def draw(self, screen: pg.Surface) -> None:
        """テスト用なので描画しない。"""
        _ = screen


class _LegacyTutorialOverlay:
    """保存設定を持たない旧形式のチュートリアルオーバーレイ。"""

    def __init__(self) -> None:
        self._visible: bool = True

    def is_visible(self) -> bool:
        """表示中なら True を返す。"""
        return self._visible

    def handle_event(self, event: pg.event.Event) -> bool:
        """何らかの入力を受けたら閉じる。"""
        if event.type in {pg.KEYDOWN, pg.MOUSEBUTTONDOWN}:
            self._visible = False
            return True
        return False

    def draw(self, screen: pg.Surface) -> None:
        """テスト用なので描画しない。"""
        _ = screen


def _make_game() -> SoloGame:
    pg.init()
    pg.display.set_mode((400, 200))
    return SoloGame(max_wave=BOSS_WAVE_MODULO)


def test_normal_wave_clear_awards_gold_and_heal() -> None:
    """通常ウェーブクリアで資源加算と拠点HP回復が行われる。"""
    game = _make_game()
    fortress = game.get_world().get_fortress()
    # 回復が観測できるよう拠点HPを十分減らしておく
    fortress.take_damage(fortress.get_max_hp() // 2)
    gold_before = game.get_builder().get_gold()
    hp_before = fortress.get_hp()

    game._wave_manager._wave = 1  # 非ボスウェーブ
    game._award_wave_clear_bonus()

    assert game.get_builder().get_gold() == gold_before + WAVE_CLEAR_GOLD_BONUS
    assert fortress.get_hp() == hp_before + WAVE_CLEAR_FORTRESS_HEAL


def test_boss_wave_clear_awards_extra_bonus() -> None:
    """ボスウェーブクリアでは追加ボーナスが上乗せされる。"""
    game = _make_game()
    fortress = game.get_world().get_fortress()
    fortress.take_damage(fortress.get_max_hp() // 2)
    gold_before = game.get_builder().get_gold()
    hp_before = fortress.get_hp()

    game._wave_manager._wave = BOSS_WAVE_MODULO  # ボスウェーブ
    game._award_wave_clear_bonus()

    assert game.get_builder().get_gold() == (
        gold_before + WAVE_CLEAR_GOLD_BONUS + BOSS_WAVE_CLEAR_GOLD_BONUS
    )
    assert fortress.get_hp() == (
        hp_before + WAVE_CLEAR_FORTRESS_HEAL + BOSS_WAVE_CLEAR_FORTRESS_HEAL
    )


def test_wave_clear_heal_clamped_to_max_hp() -> None:
    """満タン付近では回復が最大HPでクランプされる。"""
    game = _make_game()
    fortress = game.get_world().get_fortress()
    # ほぼ満タン（最大-1）にしておくと回復は最大HPで頭打ち
    fortress.set_hp(fortress.get_max_hp() - 1)

    game._wave_manager._wave = 1
    game._award_wave_clear_bonus()

    assert fortress.get_hp() == fortress.get_max_hp()


def test_tutorial_overlay_opens_with_pause_key() -> None:
    """ゲーム中に P キーで非表示の操作説明を開ける。"""
    pg.init()
    pg.display.set_mode((400, 200))
    overlay = _FakeTutorialOverlay(skip_next_time=False, visible=False)
    game = SoloGame(max_wave=BOSS_WAVE_MODULO, tutorial_overlay=overlay)

    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_p}))
    game.handle_events()

    assert overlay.is_visible()
    assert overlay.get_show_count() == 1


def test_tutorial_seen_saved_when_skip_checked() -> None:
    """チェック欄 ON で閉じると表示済みフラグ保存が呼ばれる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    saved_values: list[bool] = []
    overlay = _FakeTutorialOverlay(skip_next_time=True)
    game = SoloGame(
        max_wave=BOSS_WAVE_MODULO,
        tutorial_overlay=overlay,
        tutorial_seen_saver=saved_values.append,
    )

    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE}))
    game.handle_events()

    assert saved_values == [True]
    assert not overlay.is_visible()


def test_tutorial_seen_false_saved_when_skip_unchecked() -> None:
    """チェック欄 OFF で閉じると表示済みフラグ False が保存される。"""
    pg.init()
    pg.display.set_mode((400, 200))
    saved_values: list[bool] = []
    overlay = _FakeTutorialOverlay(skip_next_time=False)
    game = SoloGame(
        max_wave=BOSS_WAVE_MODULO,
        tutorial_overlay=overlay,
        tutorial_seen_saver=saved_values.append,
    )

    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE}))
    game.handle_events()

    assert saved_values == [False]
    assert not overlay.is_visible()


def test_tutorial_hint_drawn_when_overlay_hidden() -> None:
    """オーバーレイ非表示中は画面下部のチュートリアルヒントを描画する。"""
    pg.init()
    pg.display.set_mode((400, 200))
    overlay = _FakeTutorialOverlay(skip_next_time=False, visible=False)
    game = SoloGame(max_wave=BOSS_WAVE_MODULO, tutorial_overlay=overlay)

    calls: list[int] = []
    game._draw_tutorial_hint = lambda: calls.append(1)  # type: ignore[method-assign]
    game.draw()

    assert calls == [1]


def test_tutorial_hint_hidden_when_overlay_visible() -> None:
    """オーバーレイ表示中はヒントを重複表示しない。"""
    pg.init()
    pg.display.set_mode((400, 200))
    overlay = _FakeTutorialOverlay(skip_next_time=False, visible=True)
    game = SoloGame(max_wave=BOSS_WAVE_MODULO, tutorial_overlay=overlay)

    calls: list[int] = []
    game._draw_tutorial_hint = lambda: calls.append(1)  # type: ignore[method-assign]
    game.draw()

    assert calls == []


def test_tutorial_hint_renders_without_error() -> None:
    """ヒント描画が例外なく Surface へ blit できる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    game = SoloGame(max_wave=BOSS_WAVE_MODULO)

    # 例外が出ないこと、ヒント文言が空でないことを確認する
    assert game.TUTORIAL_HINT_TEXT
    game._draw_tutorial_hint()


def test_tutorial_seen_saver_none_allows_legacy_overlay() -> None:
    """保存コールバックが無い場合は旧形式オーバーレイでも閉じられる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    overlay = _LegacyTutorialOverlay()
    game = SoloGame(max_wave=BOSS_WAVE_MODULO, tutorial_overlay=overlay)

    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE}))
    game.handle_events()

    assert not overlay.is_visible()


if __name__ == "__main__":
    test_normal_wave_clear_awards_gold_and_heal()
    test_boss_wave_clear_awards_extra_bonus()
    test_wave_clear_heal_clamped_to_max_hp()
    test_tutorial_overlay_opens_with_pause_key()
    test_tutorial_seen_saved_when_skip_checked()
    test_tutorial_seen_false_saved_when_skip_unchecked()
    test_tutorial_hint_drawn_when_overlay_hidden()
    test_tutorial_hint_hidden_when_overlay_visible()
    test_tutorial_hint_renders_without_error()
    test_tutorial_seen_saver_none_allows_legacy_overlay()
    print("All solo_game tests passed.")
