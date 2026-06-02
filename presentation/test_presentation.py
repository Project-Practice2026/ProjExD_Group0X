"""presentation パッケージ（グラフ・HUD・対戦・サウンド）のテスト。"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from combat.boss_enemy import BossEnemy
from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.builder import Builder
from core.constants import (
    COLOR_BG,
    COLOR_HP_BAR_FG,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SE_BOSS_DIE,
    SE_DEFEAT,
    SE_ENEMY_DIE,
    SE_TOWER_FIRE,
    SE_TOWER_PLACE,
    SE_VERSUS_SEND,
    SE_VICTORY,
    SE_WAVE_START,
    VERSUS_FIELD_GAP,
    VERSUS_HINT_BOTTOM_MARGIN,
    VERSUS_HUD_MARGIN,
)
from core.fortress import Fortress
from core.wave_manager import WaveManager
from core.world import World, _NullSound
from presentation.evolution_graph import EvolutionGraph, GenerationRecord
from presentation.extended_hud import ExtendedHud
from presentation.sound_manager import SoundManager
from presentation.tutorial import TutorialOverlay
from presentation.versus_mode import VersusEvent, VersusGame


class _RecordingSound:
    """テスト用：play_se 等を記録するスタブ。"""

    def __init__(self) -> None:
        self.se: list[str] = []
        self.bgm: list[str] = []
        self.stopped: int = 0

    def play_se(self, name: str) -> None:
        self.se.append(name)

    def play_bgm(self, name: str, loops: int = -1) -> None:
        _ = loops
        self.bgm.append(name)

    def stop_bgm(self) -> None:
        self.stopped += 1


# ===== EvolutionGraph =====


def test_evolution_graph_add_and_latest() -> None:
    graph = EvolutionGraph()
    assert graph.get_latest() is None
    graph.add(1, best=10.0, avg=5.0)
    graph.add(2, best=15.0, avg=8.0)
    latest = graph.get_latest()
    assert isinstance(latest, GenerationRecord)
    assert latest.generation == 2
    assert latest.best == 15.0


def test_evolution_graph_max_records_trims_old() -> None:
    graph = EvolutionGraph(max_records=3)
    for i in range(10):
        graph.add(i, best=float(i), avg=float(i) / 2)
    records = graph.get_records()
    assert len(records) == 3
    assert records[0].generation == 7
    assert records[-1].generation == 9


def test_evolution_graph_draws_without_crash() -> None:
    pg.init()
    surface = pg.Surface((400, 200))
    graph = EvolutionGraph()
    # データなしでも落ちない
    graph.draw(surface, (10, 10))
    for i in range(5):
        graph.add(i, best=float(i) * 10, avg=float(i) * 5)
    graph.draw(surface, (10, 10), size=(200, 100))


# ===== ExtendedHud =====


def test_extended_hud_basic_draw() -> None:
    pg.init()
    surface = pg.Surface((960, 540))
    hud = ExtendedHud()
    hud.set_max_hp(1000)
    state = {
        "core_hp": 800,
        "core_max_hp": 1000,
        "resource": 120,
        "wave": 3,
        "generation": 4,
    }
    hud.draw(surface, state)


def test_extended_hud_with_optional_panels() -> None:
    pg.init()
    surface = pg.Surface((960, 540))
    hud = ExtendedHud()
    state = {
        "core_hp": 500,
        "core_max_hp": 1000,
        "resource": 50,
        "wave": 5,
        "generation": 7,
        "selected_tower": {
            "element": "fire",
            "level": 2,
            "damage": 15,
            "range": 140,
            "cooldown": 0.9,
            "cost": 30,
        },
        "skills": [
            {"name": "dash", "cooldown": 8.0, "cooldown_left": 2.0, "active": True},
            {"name": "area", "cooldown": 12.0, "cooldown_left": 0.0, "active": False},
        ],
        "best_fitness": 234.5,
        "opponent_core_hp": 750,
        "opponent_core_max_hp": 1000,
    }
    hud.draw(surface, state)


# ===== TutorialOverlay =====


def test_tutorial_overlay_visibility_controls() -> None:
    overlay = TutorialOverlay()
    assert overlay.is_visible()

    overlay.hide()
    assert not overlay.is_visible()

    overlay.show()
    assert overlay.is_visible()


def test_tutorial_overlay_draws_without_crash() -> None:
    pg.init()
    surface = pg.Surface((960, 540))
    overlay = TutorialOverlay()

    overlay.draw(surface)

    assert overlay.get_close_rect().width == overlay.CLOSE_BUTTON_SIZE


def test_tutorial_overlay_closes_with_key() -> None:
    overlay = TutorialOverlay()

    handled = overlay.handle_event(pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE}))

    assert handled
    assert not overlay.is_visible()


def test_tutorial_overlay_closes_with_click() -> None:
    overlay = TutorialOverlay()

    handled = overlay.handle_event(
        pg.event.Event(pg.MOUSEBUTTONDOWN, {"button": 1, "pos": (10, 10)})
    )

    assert handled
    assert not overlay.is_visible()


def test_tutorial_overlay_skip_next_time_accessors() -> None:
    """次回から表示しない設定を getter / setter で扱える。"""
    overlay = TutorialOverlay()

    assert not overlay.get_skip_next_time()
    overlay.set_skip_next_time(True)

    assert overlay.get_skip_next_time()


def test_tutorial_overlay_checkbox_click_toggles_without_closing() -> None:
    """チェック欄クリックは設定だけ切り替え、オーバーレイは閉じない。"""
    pg.init()
    surface = pg.Surface((960, 540))
    overlay = TutorialOverlay()
    overlay.draw(surface)
    checkbox_center = overlay.get_skip_checkbox_rect().center

    handled = overlay.handle_event(
        pg.event.Event(pg.MOUSEBUTTONDOWN, {"button": 1, "pos": checkbox_center})
    )

    assert handled
    assert overlay.is_visible()
    assert overlay.get_skip_next_time()


# ===== SoundManager =====


def test_sound_manager_safe_when_no_sources() -> None:
    sm = SoundManager(asset_dir="nonexistent_directory_for_test")
    # ミキサーが OK でも、音源未配置でも、全 API がノークラッシュ
    sm.play_se("does_not_exist")
    sm.play_bgm("not_there")
    sm.stop_bgm()
    sm.set_se_volume(0.3)
    sm.set_bgm_volume(0.2)
    # SoundSink Protocol を満たす（ダックタイピング検査）
    assert hasattr(sm, "play_se")
    assert hasattr(sm, "play_bgm")
    assert hasattr(sm, "stop_bgm")


def test_sound_manager_auto_load_handles_missing_dir() -> None:
    sm = SoundManager(asset_dir="nonexistent_directory_for_test")
    assert sm.auto_load_from_dir() == 0
    assert sm.get_loaded_se_names() == []


def test_sound_manager_default_init_invokes_auto_load() -> None:
    """``SoundManager()`` のデフォルト動作で ``auto_load_from_dir`` が呼ばれる。

    ``auto_load_from_dir`` をスパイし、``__init__`` 完了時点で 1 回呼ばれて
    いることを確認する。
    """
    call_count = {"value": 0}
    original = SoundManager.auto_load_from_dir

    def spy(self: SoundManager, directory: str | None = None) -> int:
        call_count["value"] += 1
        return original(self, directory)

    SoundManager.auto_load_from_dir = spy  # type: ignore[method-assign]
    try:
        sm = SoundManager(asset_dir="nonexistent_directory_for_test")
    finally:
        SoundManager.auto_load_from_dir = original  # type: ignore[method-assign]

    assert call_count["value"] == 1
    assert sm.get_loaded_se_names() == []


def test_sound_manager_auto_load_false_skips_auto_load() -> None:
    """``auto_load=False`` を渡すと ``__init__`` 内では走査されない。"""
    call_count = {"value": 0}
    original = SoundManager.auto_load_from_dir

    def spy(self: SoundManager, directory: str | None = None) -> int:
        call_count["value"] += 1
        return original(self, directory)

    SoundManager.auto_load_from_dir = spy  # type: ignore[method-assign]
    try:
        SoundManager(asset_dir="nonexistent_directory_for_test", auto_load=False)
    finally:
        SoundManager.auto_load_from_dir = original  # type: ignore[method-assign]

    assert call_count["value"] == 0


def test_null_sound_is_safe() -> None:
    null = _NullSound()
    null.play_se("anything")
    null.play_bgm("any")
    null.stop_bgm()


# ===== VersusGame =====


def test_versus_game_initial_state() -> None:
    game = VersusGame()
    assert game.get_winner() is None
    assert not game.is_finished()
    assert game.get_field("left").get_gold() > 0
    assert game.get_field("right").get_gold() > 0


def test_versus_send_enemy_consumes_gold_and_spawns_on_opponent() -> None:
    rec = _RecordingSound()
    game = VersusGame(sound=rec)
    left = game.get_field("left")
    right = game.get_field("right")
    left_gold_before = left.get_gold()
    enemies_right_before = len(right.get_world().get_enemies())

    def factory(pos: tuple[float, float]) -> BaseEnemy:
        return BaseEnemy(pos=pos)

    ok = game.send_enemy("left", factory)
    assert ok
    assert left.get_gold() < left_gold_before
    assert len(right.get_world().get_enemies()) == enemies_right_before + 1
    assert SE_VERSUS_SEND in rec.se


def test_versus_send_enemy_fails_with_insufficient_gold() -> None:
    game = VersusGame()
    game.get_field("left").set_gold(0)

    def factory(pos: tuple[float, float]) -> BaseEnemy:
        return BaseEnemy(pos=pos)

    ok = game.send_enemy("left", factory)
    assert not ok


def test_versus_winner_decided_when_fortress_destroyed() -> None:
    game = VersusGame()
    # 左の拠点を破壊して右の勝利
    left_fortress = game.get_field("left").get_fortress()
    left_fortress.take_damage(left_fortress.get_max_hp())
    game.update(1.0 / 60.0)
    assert game.is_finished()
    assert game.get_winner() == "right"


def test_versus_winner_plays_one_result_se_for_local_winner() -> None:
    rec = _RecordingSound()
    game = VersusGame(sound=rec, local_side="right")
    left_fortress = game.get_field("left").get_fortress()
    left_fortress.take_damage(left_fortress.get_max_hp())

    game.update(1.0 / 60.0)

    assert rec.se == [SE_VICTORY]


def test_versus_winner_plays_one_result_se_for_local_loser() -> None:
    rec = _RecordingSound()
    game = VersusGame(sound=rec, local_side="left")
    left_fortress = game.get_field("left").get_fortress()
    left_fortress.take_damage(left_fortress.get_max_hp())

    game.update(1.0 / 60.0)

    assert rec.se == [SE_DEFEAT]


def test_versus_apply_remote_event_spawns_enemy() -> None:
    game = VersusGame()
    right_before = len(game.get_field("right").get_world().get_enemies())

    def factory(pos: tuple[float, float]) -> BaseEnemy:
        return BaseEnemy(pos=pos)

    event = VersusEvent(
        type="send_enemy",
        payload={"target_side": "right", "enemy_factory": factory},
    )
    game.apply_remote_event(event)
    assert len(game.get_field("right").get_world().get_enemies()) == right_before + 1


def test_player_field_independent_gold() -> None:
    game = VersusGame()
    game.get_field("left").add_gold(50)
    assert game.get_field("left").get_gold() != game.get_field("right").get_gold()


# ===== SE 注入点（hook 経路の存在確認） =====


def test_world_plays_enemy_die_when_dead() -> None:
    rec = _RecordingSound()
    fortress = Fortress(pos=(900.0, 100.0))
    world = World(fortress=fortress, sound=rec)
    enemy = BaseEnemy(pos=(100.0, 100.0), hp=1)
    world.add_enemy(enemy)
    enemy.take_damage(99)
    world.update(1.0 / 60.0)
    assert SE_ENEMY_DIE in rec.se


def test_world_plays_tower_fire_for_new_bullets() -> None:
    rec = _RecordingSound()
    world = World(sound=rec)
    tower = BaseTower(pos=(100.0, 100.0))
    world.add_tower(tower)
    enemy = BaseEnemy(pos=(110.0, 110.0), hp=100)
    world.add_enemy(enemy)
    world.update(1.0 / 60.0)
    assert SE_TOWER_FIRE in rec.se


def test_builder_plays_tower_place() -> None:
    rec = _RecordingSound()
    world = World(sound=rec)
    builder = Builder(pos=(50.0, 50.0))
    placed = builder._try_place_tower(world, (300, 300))
    assert placed
    assert SE_TOWER_PLACE in rec.se


def test_wave_manager_plays_wave_start() -> None:
    rec = _RecordingSound()
    world = World(sound=rec)
    wm = WaveManager()
    # PREPARE_SECONDS（3秒）超えで BATTLE 遷移→ SE_WAVE_START
    for _ in range(int(3.5 * 60)):
        wm.update(world, 1.0 / 60.0)
    assert SE_WAVE_START in rec.se


def test_boss_death_effect_plays_se() -> None:
    rec = _RecordingSound()
    world = World(sound=rec)
    boss = BossEnemy(pos=(200.0, 100.0))
    boss.take_damage(99999)
    boss.trigger_death_effect(world)
    assert SE_BOSS_DIE in rec.se


def test_world_uses_boss_death_hook_without_generic_enemy_die() -> None:
    rec = _RecordingSound()
    world = World(sound=rec)
    boss = BossEnemy(pos=(200.0, 100.0))
    world.add_enemy(boss)
    boss.take_damage(99999)

    world.update(1.0 / 60.0)

    assert rec.se == [SE_BOSS_DIE]


# ===== Versus 起動経路（Issue #93） =====


def test_versus_draw_renders_hud_for_both_sides() -> None:
    """対戦モードの draw が左右両サイドに HUD（拠点HPバー + 操作ヒント）を描く（Issue #157）。

    pygame ヘッドレスで draw を呼び、HUD 想定位置のピクセルが BG 色ではない
    （= 何かが描画されている）ことで描画されたことを確認する。
    """
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = VersusGame(enemy_factory=BaseEnemy)
    game.start()
    game.draw(screen)

    half_width = (SCREEN_WIDTH - VERSUS_FIELD_GAP) // 2
    # 左サイド HUD：HP バー上端のピクセルが FG 色（満タンなので fg_width > 0）
    left_bar_px = screen.get_at((VERSUS_HUD_MARGIN + 4, VERSUS_HUD_MARGIN + 4))
    assert tuple(left_bar_px)[:3] == COLOR_HP_BAR_FG, "左サイド拠点HPバーが描画されていない"

    # 右サイド HUD：右盤面領域の左端マージン位置
    right_origin = half_width + VERSUS_FIELD_GAP
    right_bar_px = screen.get_at((right_origin + VERSUS_HUD_MARGIN + 4, VERSUS_HUD_MARGIN + 4))
    assert tuple(right_bar_px)[:3] == COLOR_HP_BAR_FG, "右サイド拠点HPバーが描画されていない"

    # 操作ヒント：画面下部中央に何かが描画されている（BG 以外のピクセルがある）
    hint_y = SCREEN_HEIGHT - VERSUS_HINT_BOTTOM_MARGIN - 6
    found_text = False
    for x in range(SCREEN_WIDTH // 2 - 200, SCREEN_WIDTH // 2 + 200):
        if tuple(screen.get_at((x, hint_y)))[:3] != COLOR_BG:
            found_text = True
            break
    assert found_text, "画面下部中央に操作ヒントが描画されていない"
    pg.quit()


def test_versus_handle_events_space_sends_enemy_from_left() -> None:
    """SPACE で左フィールドから右へ敵が送信される。"""
    pg.init()
    pg.display.set_mode((400, 200))
    game = VersusGame(enemy_factory=BaseEnemy)
    game.start()
    right_before = len(game.get_field("right").get_world().get_enemies())
    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_SPACE}))
    game.handle_events()
    right_after = len(game.get_field("right").get_world().get_enemies())
    assert right_after == right_before + 1
    pg.quit()


def test_versus_handle_events_return_sends_enemy_from_right() -> None:
    """RETURN で右フィールドから左へ敵が送信される。"""
    pg.init()
    pg.display.set_mode((400, 200))
    game = VersusGame(enemy_factory=BaseEnemy)
    game.start()
    left_before = len(game.get_field("left").get_world().get_enemies())
    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_RETURN}))
    game.handle_events()
    left_after = len(game.get_field("left").get_world().get_enemies())
    assert left_after == left_before + 1
    pg.quit()


def test_versus_handle_events_escape_stops_running() -> None:
    """ESC で running フラグが False になる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    game = VersusGame()
    game.start()
    assert game.is_running()
    pg.event.post(pg.event.Event(pg.KEYDOWN, {"key": pg.K_ESCAPE}))
    game.handle_events()
    assert not game.is_running()
    pg.quit()


def test_versus_try_send_from_uses_default_when_no_factory() -> None:
    """Factory 未注入時は BaseEnemy をデフォルトで送る。"""
    pg.init()
    pg.display.set_mode((400, 200))
    game = VersusGame()  # enemy_factory なし
    game.start()
    assert game._try_send_from("left") is True
    right_enemies = game.get_field("right").get_world().get_enemies()
    assert len(right_enemies) == 1
    assert isinstance(right_enemies[0], BaseEnemy)
    pg.quit()


def test_main_has_run_versus_callable() -> None:
    """Main モジュールに run_versus 関数が定義されている（--versus フラグ用）。"""
    import main as main_module  # noqa: PLC0415 - main は遅延 import（pygame 副作用回避）

    assert callable(main_module.run_versus)


def test_main_should_show_tutorial_from_seen_flag() -> None:
    """Tutorial_seen フラグから自動表示の有無を判定できる。"""
    import main as main_module  # noqa: PLC0415 - main の軽量ヘルパー確認

    assert main_module._should_show_tutorial(False)
    assert not main_module._should_show_tutorial(True)


if __name__ == "__main__":
    test_evolution_graph_add_and_latest()
    test_evolution_graph_max_records_trims_old()
    test_evolution_graph_draws_without_crash()
    test_extended_hud_basic_draw()
    test_extended_hud_with_optional_panels()
    test_tutorial_overlay_visibility_controls()
    test_tutorial_overlay_draws_without_crash()
    test_tutorial_overlay_closes_with_key()
    test_tutorial_overlay_closes_with_click()
    test_tutorial_overlay_skip_next_time_accessors()
    test_tutorial_overlay_checkbox_click_toggles_without_closing()
    test_sound_manager_safe_when_no_sources()
    test_sound_manager_auto_load_handles_missing_dir()
    test_sound_manager_default_init_invokes_auto_load()
    test_sound_manager_auto_load_false_skips_auto_load()
    test_null_sound_is_safe()
    test_versus_game_initial_state()
    test_versus_send_enemy_consumes_gold_and_spawns_on_opponent()
    test_versus_send_enemy_fails_with_insufficient_gold()
    test_versus_winner_decided_when_fortress_destroyed()
    test_versus_winner_plays_one_result_se_for_local_winner()
    test_versus_winner_plays_one_result_se_for_local_loser()
    test_versus_apply_remote_event_spawns_enemy()
    test_player_field_independent_gold()
    test_world_plays_enemy_die_when_dead()
    test_world_plays_tower_fire_for_new_bullets()
    test_builder_plays_tower_place()
    test_wave_manager_plays_wave_start()
    test_boss_death_effect_plays_se()
    test_world_uses_boss_death_hook_without_generic_enemy_die()
    test_versus_handle_events_space_sends_enemy_from_left()
    test_versus_handle_events_return_sends_enemy_from_right()
    test_versus_handle_events_escape_stops_running()
    test_versus_try_send_from_uses_default_when_no_factory()
    test_main_has_run_versus_callable()
    test_main_should_show_tutorial_from_seen_flag()
    print("All presentation tests passed.")
