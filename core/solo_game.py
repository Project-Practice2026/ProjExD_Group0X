"""1台のPCで両プレイヤーを操作する soloモード。

Game を継承し、Builder（プレイヤー1）と Fighter（プレイヤー2）を
1つのプロセスで同時に制御する。デバッグ環境＆発表時のフォールバック。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

import pygame as pg

from .base_enemy import BaseEnemy
from .base_hud import BaseHud
from .builder import Builder, TowerFactory
from .constants import (
    BGM_MAIN,
    BOSS_WAVE_CLEAR_FORTRESS_HEAL,
    BOSS_WAVE_CLEAR_GOLD_BONUS,
    BOSS_WAVE_MODULO,
    COLOR_TEXT,
    EVOLUTION_GRAPH_DEFAULT_ORIGIN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WAVE_CLEAR_FORTRESS_HEAL,
    WAVE_CLEAR_GOLD_BONUS,
)
from .fighter import Fighter
from .fonts import get_font
from .game import Game
from .wave_manager import EnemyFactory, WaveManager, WavePhase
from .world import EffectSink, SoundSink, World

if TYPE_CHECKING:
    from combat.boss_enemy import BossEnemy
    from combat.fighter_skills import BaseSkill
    from combat.weapons import BaseWeapon
    from evolution.evolution_driver import EvolutionDriver


class EvolutionGraphSink(Protocol):
    """EvolutionGraph の描画インターフェース（疎結合用）。"""

    def draw(
        self,
        screen: pg.Surface,
        origin: tuple[int, int],
        size: tuple[int, int] | None = None,
    ) -> None:
        """適応度グラフを描画する。

        Args:
            screen: 描画先 Surface。
            origin: グラフ左上の描画位置。
            size: 描画サイズ。未指定ならグラフ側の既定値を使う。
        """


class TowerSelector(Protocol):
    """タワー選択 UI に必要な描画インターフェース。"""

    def draw(
        self,
        screen: pg.Surface,
        builder: Builder,
        world: World,
        mouse_pos: tuple[int, int] | None = None,
    ) -> None:
        """選択 UI とゴーストプレビューを描画する。"""


class WeaponSelector(Protocol):
    """武器切替 UI の描画インターフェース。"""

    def draw(self, screen: pg.Surface, fighter: Fighter, weapon: BaseWeapon) -> None:
        """現在装備中の武器を描画する。"""


class TutorialOverlayView(Protocol):
    """操作説明オーバーレイの描画・入力インターフェース。"""

    def is_visible(self) -> bool:
        """表示中かどうかを返す。"""

    def handle_event(self, event: pg.event.Event) -> bool:
        """オーバーレイ用イベントを処理する。"""

    def get_skip_next_time(self) -> bool:
        """次回から自動表示しない設定が選ばれているかを返す。"""

    def draw(self, screen: pg.Surface) -> None:
        """オーバーレイを描画する。"""


BossSpawnedHandler = Callable[["BossEnemy"], None]


class SoloGame(Game):
    """1台で両プレイヤーを操作するゲームモード。"""

    TUTORIAL_OPEN_KEYS: tuple[int, ...] = (pg.K_p, pg.K_F1)
    # 画面下部に常時表示する操作ヒント（P でチュートリアルを開ける旨）
    TUTORIAL_HINT_TEXT: str = "[P] チュートリアルを表示"
    TUTORIAL_HINT_FONT_SIZE: int = 20
    TUTORIAL_HINT_MARGIN_BOTTOM: int = 12

    def __init__(  # noqa: PLR0913 - solo モードは合成層なので注入引数が増えやすい
        self,
        tower_factories: dict[str, TowerFactory] | None = None,
        tower_selector: TowerSelector | None = None,
        effects: EffectSink | None = None,
        sound: SoundSink | None = None,
        fighter_weapons: list[BaseWeapon] | None = None,
        fighter_skills: list[BaseSkill] | None = None,
        weapon_selector: WeaponSelector | None = None,
        enemy_factory: EnemyFactory | None = None,
        boss_factory: EnemyFactory | None = None,
        special_factory: EnemyFactory | None = None,
        max_wave: int = 3,
        evolution_driver: EvolutionDriver | None = None,
        evolution_graph: EvolutionGraphSink | None = None,
        evolution_graph_origin: tuple[int, int] = EVOLUTION_GRAPH_DEFAULT_ORIGIN,
        tutorial_overlay: TutorialOverlayView | None = None,
        tutorial_seen_saver: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__()
        self._world: World = World(effects=effects, sound=sound)
        self._builder: Builder = Builder(
            pos=(80.0, SCREEN_HEIGHT - 40.0),
            tower_factories=tower_factories,
        )
        self._fighter: Fighter = Fighter(
            pos=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2),
            weapons=fighter_weapons,
            skills=fighter_skills,
        )
        self._world.add_player(self._builder)
        self._world.add_player(self._fighter)
        # EvolutionDriver があれば enemy_factory として spawn_enemy を使う
        self._evolution_driver: EvolutionDriver | None = evolution_driver
        if self._evolution_driver is not None:
            self._evolution_driver.set_fortress_pos(self._world.get_fortress().get_pos())
            if enemy_factory is None:
                enemy_factory = self._evolution_driver.spawn_enemy
        self._wave_manager: WaveManager = WaveManager(
            enemy_factory=enemy_factory,
            max_wave=max_wave,
            boss_factory=boss_factory,
            special_factory=special_factory,
        )
        self._hud: BaseHud = BaseHud()
        self._hud.set_max_hp(self._world.get_fortress().get_max_hp())
        # 画面下部の操作ヒント用フォント（日本語表示のため共通ローダを使う）
        self._hint_font: pg.font.Font = get_font(self.TUTORIAL_HINT_FONT_SIZE)
        self._selector_ui: TowerSelector | None = tower_selector
        self._weapon_ui: WeaponSelector | None = weapon_selector
        self._evolution_graph: EvolutionGraphSink | None = evolution_graph
        self._evolution_graph_origin: tuple[int, int] = evolution_graph_origin
        self._tutorial_overlay: TutorialOverlayView | None = tutorial_overlay
        self._tutorial_seen_saver: Callable[[bool], None] | None = tutorial_seen_saver
        self._known_enemies: set[int] = set()
        self._generation: int = (
            self._evolution_driver.get_generation() if self._evolution_driver else 0
        )
        self._prev_wave_phase: WavePhase = self._wave_manager.get_phase()
        # BGM 起動（音源未配置でも no-op で安全）
        self._world.get_sound().play_bgm(BGM_MAIN)

    def get_world(self) -> World:
        """World を返す。"""
        return self._world

    def get_builder(self) -> Builder:
        """Builder を返す。"""
        return self._builder

    def get_fighter(self) -> Fighter:
        """Fighter を返す。"""
        return self._fighter

    def get_generation(self) -> int:
        """HUD とテスト用に現在表示中の進化世代を返す。"""
        return self._generation

    def get_tutorial_overlay(self) -> TutorialOverlayView | None:
        """操作説明オーバーレイを返す。"""
        return self._tutorial_overlay

    def handle_events(self) -> None:
        """QUIT 処理に加え、両プレイヤーに単発イベントを dispatch する。"""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self._running = False
                continue
            if self.is_tutorial_visible():
                overlay = self._tutorial_overlay
                if overlay is not None:
                    was_visible = overlay.is_visible()
                    overlay.handle_event(event)
                    if was_visible and not overlay.is_visible():
                        self._save_tutorial_seen_if_requested(overlay)
                continue
            if self._is_tutorial_open_event(event):
                self._show_tutorial_overlay()
                continue
            self._builder.handle_event(event, self._world)
            self._fighter.handle_event(event, self._world)

    def update(self, dt: float) -> None:
        """両プレイヤーの入力反映 → World 更新 → ウェーブ進行 → 世代切替。"""
        if self.is_tutorial_visible():
            return
        keys = pg.key.get_pressed()
        self._fighter.update_keys(keys, dt, self._world)

        # Fighter が発射した弾を World へ移送
        bullets = self._fighter.drain_pending_bullets()
        if bullets:
            self._world.add_bullets(bullets)

        # 早期ウェーブ開始リクエストを WaveManager へ反映
        if self._builder.consume_wave_skip():
            self._wave_manager.request_wave_skip()

        # ボス特殊行動と撃破演出
        self._update_bosses(dt)

        self._world.update(dt)
        self._wave_manager.update(self._world, dt)

        # 進化AIの戦績観測（死亡/到達した個体の終了時刻を確定）と世代切替
        if self._evolution_driver is not None:
            self._evolution_driver.observe_frame()
        self._tick_wave_transition()

    def draw(self) -> None:
        """World 描画 ＋ HUD オーバーレイ ＋ 各種 UI。"""
        self._world.draw(self._screen)
        self._hud.draw(
            self._screen,
            {
                "core_hp": self._world.get_fortress().get_hp(),
                "core_max_hp": self._world.get_fortress().get_max_hp(),
                "resource": self._builder.get_gold(),
                "wave": self._wave_manager.get_wave(),
                "generation": self._generation,
            },
        )
        if self._selector_ui is not None:
            self._selector_ui.draw(
                self._screen,
                builder=self._builder,
                world=self._world,
                mouse_pos=pg.mouse.get_pos(),
            )
        if self._weapon_ui is not None:
            current_weapon = self._fighter.get_current_weapon()
            if current_weapon is not None:
                self._weapon_ui.draw(self._screen, self._fighter, current_weapon)
        if self._evolution_graph is not None:
            self._evolution_graph.draw(self._screen, self._evolution_graph_origin)
        # チュートリアルを開ける旨のヒントを画面下部に表示する。
        # オーバーレイ表示中はオーバーレイ自身が説明を出すため重複表示を避ける。
        if not self.is_tutorial_visible():
            self._draw_tutorial_hint()
        if self._tutorial_overlay is not None:
            self._tutorial_overlay.draw(self._screen)

    def _draw_tutorial_hint(self) -> None:
        """画面下部中央に「P でチュートリアルを表示」のヒントを描画する。"""
        surface = self._hint_font.render(self.TUTORIAL_HINT_TEXT, True, COLOR_TEXT)
        rect = surface.get_rect(
            midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - self.TUTORIAL_HINT_MARGIN_BOTTOM)
        )
        self._screen.blit(surface, rect)

    def is_tutorial_visible(self) -> bool:
        """操作説明オーバーレイが表示中なら True を返す。"""
        return self._tutorial_overlay is not None and self._tutorial_overlay.is_visible()

    def _is_tutorial_open_event(self, event: pg.event.Event) -> bool:
        """ゲーム中に操作説明を開く入力なら True を返す。"""
        return event.type == pg.KEYDOWN and event.key in self.TUTORIAL_OPEN_KEYS

    def _show_tutorial_overlay(self) -> None:
        """非表示の操作説明オーバーレイをゲーム中に再表示する。"""
        overlay = self._tutorial_overlay
        if overlay is None:
            return
        show = getattr(overlay, "show", None)
        if callable(show):
            show()

    def _save_tutorial_seen_if_requested(self, overlay: TutorialOverlayView) -> None:
        """チェック欄の状態をチュートリアル表示済みフラグとして保存する。"""
        if self._tutorial_seen_saver is None:
            return
        self._tutorial_seen_saver(overlay.get_skip_next_time())

    def _update_bosses(self, dt: float) -> None:
        """BossEnemy の特殊行動と撃破演出を呼ぶ。

        BaseEnemy 互換のため duck-typed に判定する（`combat` への runtime 依存を避ける）。
        """
        enemies: list[BaseEnemy] = self._world.get_enemies()
        # 特殊行動
        for enemy in enemies:
            tick = getattr(enemy, "update_with_world", None)
            if callable(tick):
                tick(dt, self._world)
        # 撃破演出（次フレームで World._enemies から除外される直前に検知）
        for enemy in enemies:
            if not enemy.is_dead():
                if id(enemy) in self._known_enemies:
                    continue
                self._known_enemies.add(id(enemy))
                continue
            death_hook = getattr(enemy, "trigger_death_effect", None)
            if callable(death_hook):
                death_hook(self._world)
        # 既知 ID セットから消えた敵を掃除（メモリリーク防止）
        live_ids = {id(e) for e in enemies if not e.is_dead()}
        self._known_enemies &= live_ids

    def _tick_wave_transition(self) -> None:
        """BATTLE→SUMMARY 遷移（ウェーブクリア）を検知し、世代切替とボーナスを処理する。"""
        current_phase = self._wave_manager.get_phase()
        wave_cleared = (
            self._prev_wave_phase is WavePhase.BATTLE and current_phase is WavePhase.SUMMARY
        )
        if wave_cleared:
            if self._evolution_driver is not None:
                self._evolution_driver.finalize_wave()
                self._generation = self._evolution_driver.get_generation()
            self._award_wave_clear_bonus()
        self._prev_wave_phase = current_phase

    def _award_wave_clear_bonus(self) -> None:
        """ウェーブクリア時に資源と拠点 HP の回復を付与する。

        ボスウェーブ（BOSS_WAVE_MODULO の倍数）クリア時は追加ボーナスを与える。
        拠点 HP は Fortress.set_hp 側で最大値にクランプされる。
        """
        wave = self._wave_manager.get_wave()
        gold_bonus = WAVE_CLEAR_GOLD_BONUS
        heal = WAVE_CLEAR_FORTRESS_HEAL
        if wave > 0 and wave % BOSS_WAVE_MODULO == 0:
            gold_bonus += BOSS_WAVE_CLEAR_GOLD_BONUS
            heal += BOSS_WAVE_CLEAR_FORTRESS_HEAL
        self._builder.set_gold(self._builder.get_gold() + gold_bonus)
        fortress = self._world.get_fortress()
        fortress.set_hp(fortress.get_hp() + heal)
